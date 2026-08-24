"""
The gate for Chaos Draft.

Design note, because the shape of this is not obvious and was not the first plan.

The original idea was to ask a local language model whether each word was
acceptable. That was measured before it was built, on gemma3:1b through ollama, and
it failed on both axes at once:

    ~2500 ms per word          far too slow to sit in front of a keystroke
    missed "behenchod"         one of the worst words, waved straight through
    missed "randi"             same
    blocked "kutta"            which just means dog
    blocked "saala"            which is mild and extremely common

So the model is not the gate. A normalised set lookup is the gate, and it answers in
microseconds with no network, no GPU, and no surprises. The model is available as an
optional second opinion that runs *after* a word is already live, and can retract it
a moment later. See audit() at the bottom.

The interesting part here is normalisation: turning "ch00t-i-y-aaaa" into "chutiya"
before looking it up, so the blocklist holds one entry instead of forty.
"""
from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

WORDLIST = Path(__file__).parent / "wordlist.txt"

# Characters people substitute to slip past a filter.
LEET = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "9": "g",
    "@": "a", "$": "s", "!": "i", "|": "i", "+": "t", "(": "c", "€": "e", "£": "l",
})

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
NON_LETTER = re.compile(r"[^a-zऀ-ॿ]")
RUN_3_PLUS = re.compile(r"(.)\1{2,}")
ANY_RUN = re.compile(r"(.)\1+")

# Romanised Hindi has no single spelling. The same word is written "chutiya" and
# "chootiya", "randi" and "raandi", "bhosdi" and "bhosadi", depending on whether the
# writer is spelling the vowel long. Folding these means the blocklist carries one
# spelling instead of every combination.
#
# This is applied to the blocklist as well as to input, so both sides land on the
# same form. "ck" -> "k" and "ph" -> "f" catch the same trick in English.
TRANSLITERATION = (
    ("oo", "u"), ("ee", "i"), ("aa", "a"), ("ii", "i"), ("uu", "u"),
    ("ph", "f"), ("ck", "k"), ("kh", "k"), ("gh", "g"),
)

# Ordinary words that contain a blocked substring, or that collapse onto one after
# normalisation. Checked first, so they can never be blocked.
#
# "chudail" is the important one for a story-writing game: it means witch or ghost,
# it is a perfectly normal Hindi word, and it contains a root we block.
ALLOWLIST = {
    "chudail", "chudails", "class", "classes", "classic", "pass", "passed", "passes",
    "password", "grass", "bass", "mass", "massive", "glass", "brass", "compass",
    "assess", "assessment", "asset", "assets", "assign", "assist", "associate",
    "assume", "assure", "embassy", "harass", "cassette", "canvass", "assassin",
    "cocktail", "cockpit", "peacock", "cockroach", "hancock", "shiitake",
    "analysis", "analyse", "analyze", "titan", "titanic", "title", "titles",
    "dickens", "dickinson", "scunthorpe", "penistone", "sussex", "essex",
    "kuttab", "saal", "saalon", "gandhi", "gandhian", "ganda", "gandak",
    "lauki", "laudable", "laurel", "chotu", "chota", "choti", "chhota",
    "bhola", "bhalu", "gaana", "gaanaa", "gaon", "haram", "harmony",
    "matter", "butter", "shutter", "shirt", "shift", "sheet", "shot",
    "hitch", "ditch", "witch", "pitch", "batch", "watch",
}


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    word: str
    reason: str = ""
    matched: str = ""
    micros: int = 0


def _strip_marks(s: str) -> str:
    """Remove accents, leaving the base letters. Latin only."""
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalise(word: str) -> list[str]:
    """
    Turn one raw word into every form worth checking.

    Devanagari is handled separately and deliberately lightly: NFKD would pull the
    matras off the consonants and turn the text into something that no longer
    matches anything sensible.
    """
    raw = word.strip().lower()
    if not raw:
        return []

    if DEVANAGARI.search(raw):
        return [unicodedata.normalize("NFC", raw)]

    base = _strip_marks(raw).translate(LEET)
    base = NON_LETTER.sub("", base)
    if not base:
        return []

    forms = [base]
    # "fuuuuck" -> "fuck". Runs of three or more are always deliberate stretching.
    squashed = RUN_3_PLUS.sub(r"\1", base)
    if squashed != base:
        forms.append(squashed)
    # Every run to a single letter. Catches "aasss" but also flattens real doubles,
    # which is why ALLOWLIST is consulted before any of this runs.
    flattened = ANY_RUN.sub(r"\1", base)
    if flattened not in forms:
        forms.append(flattened)

    # Long-vowel spellings: "ch00tiya" has already become "chootiya" above, and this
    # is what turns it into "chutiya" so it matches the single blocklist entry.
    for form in list(forms):
        folded = form
        for src, dst in TRANSLITERATION:
            folded = folded.replace(src, dst)
        if folded and folded not in forms:
            forms.append(folded)
    return forms


class Filter:
    """Loads the blocklist and answers in microseconds."""

    def __init__(self, path: Path = WORDLIST):
        self.path = path
        self.exact: set[str] = set()
        self.contains: list[str] = []
        self._mtime = 0.0
        self.load()

    def load(self) -> None:
        exact: set[str] = set()
        contains: set[str] = set()
        section = "exact"

        text = self.path.read_text(encoding="utf-8") if self.path.exists() else ""
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip().lower()
                continue
            for form in normalise(line):
                (exact if section == "exact" else contains).add(form)

        self.exact = exact
        # Longest first, so the reported match is the most specific one.
        self.contains = sorted(contains, key=len, reverse=True)
        self._mtime = self.path.stat().st_mtime if self.path.exists() else 0.0

    def reload_if_changed(self) -> bool:
        """Pick up edits to wordlist.txt without restarting the server."""
        if not self.path.exists():
            return False
        if self.path.stat().st_mtime != self._mtime:
            self.load()
            return True
        return False

    def check(self, word: str) -> Verdict:
        start = time.perf_counter_ns()

        def done(allowed: bool, reason: str = "", matched: str = "") -> Verdict:
            return Verdict(
                allowed=allowed,
                word=word,
                reason=reason,
                matched=matched,
                micros=(time.perf_counter_ns() - start) // 1000,
            )

        raw = word.strip().lower()
        if not raw:
            return done(False, "empty")
        if raw in ALLOWLIST:
            return done(True, "allowlisted")

        forms = normalise(word)
        if not forms:
            return done(False, "no letters")
        if forms[0] in ALLOWLIST:
            return done(True, "allowlisted")

        for form in forms:
            if form in self.exact:
                return done(False, "blocked", form)

        for form in forms:
            for root in self.contains:
                if root in form:
                    return done(False, "blocked", root)

        return done(True, "clean")

    def add(self, term: str, section: str = "exact") -> None:
        """Append a term to the file and to memory. Used by the audit path."""
        for form in normalise(term):
            if section == "exact":
                self.exact.add(form)
            elif form not in self.contains:
                self.contains.append(form)
                self.contains.sort(key=len, reverse=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"\n# added at runtime\n{term.strip().lower()}\n")
        self._mtime = self.path.stat().st_mtime


# ---------------------------------------------------------------------------
# Optional second opinion.
# ---------------------------------------------------------------------------

async def audit(word: str, model: str = "gemma3:1b", timeout: float = 12.0) -> bool | None:
    """
    Ask a local ollama model whether a word that already passed should not have.

    Returns True to retract, False to leave alone, None if it could not be reached
    or gave an answer that was not one of the two words it was asked for.

    This runs AFTER the word is live, never before. On the measurements above it
    takes seconds and misses obvious cases, so it is a supplement to the blocklist
    and not a replacement for it. Its real value is that anything it does catch gets
    written into wordlist.txt permanently, so the list improves during a session.
    """
    import json
    import aiohttp

    prompt = (
        "Answer with exactly one word: BLOCK or ALLOW.\n"
        "BLOCK if this is profanity, a slur, or sexually abusive, in any language, "
        "including Hindi, Hinglish and romanised Hindi.\n"
        "ALLOW for ordinary words, including mildly rude ones like 'dog' or 'idiot', "
        "and ordinary Hindi words like 'chudail' (witch).\n"
        f"Word: {word}\nAnswer:"
    )
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 4},
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:11434/api/generate",
                json=body,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                data = json.loads(await resp.text())
        answer = data.get("response", "").strip().upper()
    except Exception:
        return None

    if answer.startswith("BLOCK"):
        return True
    if answer.startswith("ALLOW"):
        return False
    return None


if __name__ == "__main__":
    import sys

    # Windows consoles default to cp1252, which cannot print Devanagari.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    f = Filter()
    print(f"{len(f.exact)} exact terms, {len(f.contains)} roots\n")

    tests = sys.argv[1:] or [
        "sunshine", "chudail", "class", "kutta", "saala", "dream", "witch",
        "behenchod", "b3h3nch0d", "b-e-h-e-n-c-h-o-d", "BEHENCHODDDD",
        "chutiya", "ch00tiya", "madarchod", "fuck", "f.u.c.k", "fuuuuck",
        "ass", "pass", "grass", "assassin", "गांडू", "चूतिया",
    ]
    worst = 0
    for t in tests:
        v = f.check(t)
        worst = max(worst, v.micros)
        mark = "allow" if v.allowed else "BLOCK"
        extra = f"  <- {v.matched}" if v.matched else ""
        print(f"  {mark:5}  {t:24} {v.micros:5} us  {v.reason}{extra}")
    print(f"\nslowest: {worst} us")

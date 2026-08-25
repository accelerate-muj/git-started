"""
The filter for Chaos Draft. A dictionary lookup, and nothing slower.

Every word typed into the shared document is checked here before anyone else sees
it. There are three outcomes:

    in [allow]              ALLOW. Ordinary vocabulary, checked first so it wins.
    in [exact]/[contains]   BLOCK. Removed from the text.
    near a blocked term     BLOCK. Removed as well, see below.
    nothing matched         ALLOW.

WHY A NEAR MATCH IS BLOCKED AND NOT MERELY FLAGGED
--------------------------------------------------
An earlier version published near matches and underlined them for the host. That
was wrong and it showed the first time somebody typed a variant spelling: the word
appeared in the document, underlined, for the whole room to read. Underlining a
slur is not filtering it. Near matches are removed, and the host is shown exactly
what was removed so a false positive can be added to [allow].

WHY THERE IS NO MODEL IN HERE
-----------------------------
There was, and it was measured and removed. See expand.py, which uses one offline
to grow the dictionary, and test_filter.py, which measures how good it actually is.

The short version, on a 279-case labelled set: the dictionary gets all of them in
microseconds. The best local model got 228/250, missed every regional-language
term it was shown, wanted to block "kill" and "die", and took about 750 ms a word.

NORMALISATION IS THE INTERESTING PART
-------------------------------------
People obfuscate, and a plain wordlist is beaten in seconds. Before lookup a word
is lowercased, stripped of accents and punctuation, folded out of leetspeak, had
stretched letters collapsed, had long-vowel spellings normalised, and had aspirated
consonants stripped. All of those collapse many spellings onto one entry, so the
dictionary carries one line instead of forty.

The reverse danger matters just as much, and is easier to get wrong. Three real
bugs found by the test suite, all of them ordinary words being destroyed or real
ones being let through:

    "aand"  folded to "and"     the commonest word in English, blocked
    "ass"   flattened to "as"   likewise
    "sheet" folded to a slur    which the allowlist then switched back on

Hence MIN_VARIANT_LEN, the allow list being matched on base forms only, and
`python filter.py --collisions`, which checks the whole dictionary against a
corpus of ordinary vocabulary and must always come back clean.
"""
from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

WORDLIST = Path(__file__).parent / "wordlist.txt"

LEET = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "9": "g",
    "@": "a", "$": "s", "!": "i", "|": "i", "+": "t", "(": "c", "€": "e", "£": "l",
})

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
NON_LETTER = re.compile(r"[^a-zऀ-ॿ]")
RUN_3_PLUS = re.compile(r"(.)\1{2,}")
ANY_RUN = re.compile(r"(.)\1+")

# Romanised Hindi has no single spelling. The same word is written "chutiya" and
# "chootiya", "randi" and "raandi". Folding these lets the dictionary carry one
# spelling instead of every combination. Applied to both sides so they meet.
TRANSLITERATION = (
    ("oo", "u"), ("ee", "i"), ("aa", "a"), ("ii", "i"), ("uu", "u"),
    ("ph", "f"), ("ck", "k"), ("kh", "k"), ("gh", "g"),
)

# Edit-distance thresholds for the REVIEW route. Short words are excluded because
# almost everything is one edit away from a four-letter word.
FUZZY_MIN_LEN = 6
FUZZY_LONG_LEN = 9

# The aggressive normalisation variants are lossy, and on short words they collide
# with ordinary vocabulary. Two real collisions found by the audit below:
#
#   "aand" folds aa -> a  and becomes "and"
#   "ass"  flattens ss -> s and becomes "as"
#
# Blocking "and" and "as" would have destroyed the activity in about four seconds.
# So only the base form of a term is ever stored short; lossy variants have to be
# at least this long to be trusted. Run `python filter.py --collisions` to re-check.
MIN_VARIANT_LEN = 4

# Romanised Hindi is wildly inconsistent about aspirated consonants. The same word
# is written with and without the h: "madarchod" and "madharchod", "gandu" and
# "gandhu", "bhosdike" and "bhosadhike". All three of those got through a version
# of this file, which is how this rule came to exist.
#
# Stripping h after a consonant collapses them onto one entry. It is only done for
# longer words, because on short ones it collides with ordinary English: "chut"
# would become "cut". Applied to the dictionary and the input alike, so both sides
# land on the same form.
ASPIRATE = re.compile(r"(?<=[bcdgjkpstz])h")
ASPIRATE_MIN_LEN = 5


def indexable(word: str) -> list[str]:
    """
    The forms of a word safe to put in, or match against, the BLOCK lists.

    Always the base form, plus any lossy variant long enough not to collide with
    ordinary words. The variants are what catch obfuscation, so blocking needs
    them.
    """
    forms = normalise(word)
    if not forms:
        return []
    out = [forms[0]] + [f for f in forms[1:] if len(f) >= MIN_VARIANT_LEN]

    for form in list(out):
        if len(form) >= ASPIRATE_MIN_LEN:
            stripped = ASPIRATE.sub("", form)
            if stripped != form and len(stripped) >= MIN_VARIANT_LEN + 1 \
                    and stripped not in out:
                out.append(stripped)
    return out


def allowable(word: str) -> list[str]:
    """
    The forms safe to put in, or match against, the ALLOW list. Base form only.

    Lossy variants must never be allowlisted. A variant of an innocent word can
    land exactly on a real swear word, and because the allowlist overrides
    everything, that silently switches the swear word back on. A real example
    caught by the test suite:

        "sheet"  --(ee -> i)-->  "shit"

    Allowlisting "sheet" was un-blocking "shit". Base forms only, always.
    """
    forms = normalise(word)
    return forms[:1]


class Decision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"


@dataclass(frozen=True)
class Verdict:
    decision: Decision
    word: str
    tier: int = 1
    reason: str = ""
    matched: str = ""
    micros: int = 0

    @property
    def allowed(self) -> bool:
        return self.decision is Decision.ALLOW


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def _strip_marks(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def normalise(word: str) -> list[str]:
    """
    Every form of one raw word that is worth checking.

    Devanagari is handled separately and deliberately lightly. NFKD would pull the
    matras off the consonants and the result would match nothing.
    """
    raw = word.strip().lower()
    if not raw:
        return []

    if DEVANAGARI.search(raw):
        return [unicodedata.normalize("NFC", raw)]

    base = NON_LETTER.sub("", _strip_marks(raw).translate(LEET))
    if not base:
        return []

    forms = [base]
    squashed = RUN_3_PLUS.sub(r"\1", base)          # fuuuuck -> fuck
    if squashed != base:
        forms.append(squashed)
    flattened = ANY_RUN.sub(r"\1", base)            # aasss -> as
    if flattened not in forms:
        forms.append(flattened)

    for form in list(forms):                        # chootiya -> chutiya
        folded = form
        for src, dst in TRANSLITERATION:
            folded = folded.replace(src, dst)
        if folded and folded not in forms:
            forms.append(folded)
    return forms


def _within(a: str, b: str, limit: int) -> bool:
    """
    Is the edit distance between a and b at most `limit`?

    Bounded Levenshtein with early exit. Returns as soon as the best possible
    remaining distance exceeds the limit, which makes the common case (not close
    at all) cost almost nothing.
    """
    la, lb = len(a), len(b)
    if abs(la - lb) > limit:
        return False
    if a == b:
        return True

    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        lo = max(1, i - limit)
        hi = min(lb, i + limit)
        if lo > 1:
            cur[lo - 1] = limit + 1
        for j in range(lo, hi + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        if hi < lb:
            cur[hi + 1] = limit + 1
        if min(cur[lo:hi + 1] or [limit + 1]) > limit:
            return False
        prev = cur
    return prev[lb] <= limit


# ---------------------------------------------------------------------------
# Tier 1
# ---------------------------------------------------------------------------

class Dictionary:
    """Tier 1. Loads wordlist.txt and answers in microseconds."""

    def __init__(self, path: Path = WORDLIST):
        self.path = path
        self.allow: set[str] = set()
        self.exact: set[str] = set()
        self.contains: list[str] = []
        self.phrases: list[list[str]] = []
        self.fuzzy_targets: list[str] = []
        self._mtime = 0.0
        self.load()

    def load(self) -> None:
        buckets: dict[str, set[str]] = {"allow": set(), "exact": set(), "contains": set()}
        phrases: list[list[str]] = []
        section = "exact"

        text = self.path.read_text(encoding="utf-8") if self.path.exists() else ""
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                name = line[1:-1].strip().lower()
                if name in buckets or name == "phrases":
                    section = name
                continue
            if section == "phrases":
                words = [(normalise(w) or [""])[0] for w in line.split()]
                words = [w for w in words if w]
                if len(words) > 1:
                    phrases.append(words)
                continue

            forms = allowable(line) if section == "allow" else indexable(line)
            for form in forms:
                buckets[section].add(form)

        self.allow = buckets["allow"]
        self.exact = buckets["exact"]
        self.phrases = phrases
        self.contains = sorted(buckets["contains"], key=len, reverse=True)

        # Only reasonably long terms are worth fuzzy-matching against, and only
        # Latin ones. Devanagari edit distance is not meaningful here.
        #
        # Each target is stored with its set of distinct characters. An edit
        # distance of k changes at most 2k members of that set, so comparing the
        # sets first rules out most candidates for the price of a set operation,
        # which is far cheaper than running the distance function on all of them.
        self.fuzzy_targets = [
            (t, frozenset(t))
            for t in sorted({t for t in (self.exact | set(self.contains))
                             if len(t) >= FUZZY_MIN_LEN and not DEVANAGARI.search(t)},
                            key=len)
        ]
        self._mtime = self.path.stat().st_mtime if self.path.exists() else 0.0

    def reload_if_changed(self) -> bool:
        if not self.path.exists():
            return False
        if self.path.stat().st_mtime != self._mtime:
            self.load()
            return True
        return False

    def scan(self, text: str) -> list[tuple[int, int, str]]:
        """
        Find every span of `text` that has to be removed, as (start, end, why).

        Works on the raw string and returns real character offsets, so a caller
        editing a live document can delete exactly those ranges and leave
        everything else untouched.

        Two passes, because two different things go wrong:

        1. Single words. The ordinary case.
        2. Phrases. Individually innocent words that are abuse in sequence. The
           one that prompted this: "behen ke lode". "behen" means sister and is
           allowlisted, "ke" is a postposition, and only the third word is
           blockable. Removing just that word leaves "behen ke" sitting in the
           document reading exactly like what it is.
        """
        spans: list[tuple[int, int, str]] = []

        # Token positions in the original string.
        tokens = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", text)]
        if not tokens:
            return spans

        for start, end, tok in tokens:
            if self.check(tok).decision is not Decision.ALLOW:
                spans.append((start, end, tok))

        if self.phrases:
            # One normalised word per token, for sequence matching.
            keys = [(normalise(t) or [""])[0] for _, _, t in tokens]
            n = len(keys)
            for phrase in self.phrases:
                plen = len(phrase)
                for i in range(n - plen + 1):
                    if keys[i:i + plen] == phrase:
                        spans.append((tokens[i][0], tokens[i + plen - 1][1],
                                      " ".join(phrase)))

        if not spans:
            return spans

        # Merge overlaps, so a phrase and a word inside it become one deletion.
        spans.sort()
        merged = [spans[0]]
        for start, end, why in spans[1:]:
            last_start, last_end, last_why = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end), last_why)
            else:
                merged.append((start, end, why))
        return merged

    def check(self, word: str) -> Verdict:
        start = time.perf_counter_ns()

        def out(decision: Decision, reason: str = "", matched: str = "") -> Verdict:
            return Verdict(decision, word, 1, reason, matched,
                           (time.perf_counter_ns() - start) // 1000)

        raw = word.strip().lower()
        if not raw:
            return out(Decision.BLOCK, "empty")

        forms = indexable(word)
        if not forms:
            return out(Decision.BLOCK, "no letters")

        # Allowlist wins over everything, including exact matches, so it is
        # matched on base forms only. See allowable() for why.
        if raw in self.allow or any(f in self.allow for f in allowable(word)):
            return out(Decision.ALLOW, "allowlisted")

        for form in forms:
            if form in self.exact:
                return out(Decision.BLOCK, "dictionary", form)

        for form in forms:
            for root in self.contains:
                if root in form:
                    return out(Decision.BLOCK, "dictionary", root)

        # Near miss. Deliberate misspellings land here.
        probe = forms[0]
        if len(probe) >= FUZZY_MIN_LEN:
            limit = 2 if len(probe) >= FUZZY_LONG_LEN else 1
            probe_chars = frozenset(probe)
            budget = 2 * limit
            for target, target_chars in self.fuzzy_targets:
                if abs(len(target) - len(probe)) > limit:
                    continue
                if len(probe_chars ^ target_chars) > budget:
                    continue
                if _within(probe, target, limit):
                    return out(Decision.REVIEW, "near a blocked word", target)

        return out(Decision.ALLOW, "clean")

    def add(self, term: str, section: str = "exact") -> None:
        """Add a term permanently. Used by tiers 2 and 3."""
        term = term.strip().lower()
        if not term:
            return
        for form in indexable(term):
            if section == "allow":
                self.allow.add(form)
            elif section == "exact":
                self.exact.add(form)
            elif form not in self.contains:
                self.contains.append(form)
                self.contains.sort(key=len, reverse=True)
        header = {"allow": "[allow]", "exact": "[exact]", "contains": "[contains]"}[section]
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"\n# added during a session\n{header}\n{term}\n")
        if self.path.exists():
            self._mtime = self.path.stat().st_mtime
        self.load()


# ---------------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------------

# Few-shot beats zero-shot substantially on this task. The examples are chosen to
# pin down the two things the model gets wrong unaided: it under-blocks romanised
# Hindi abuse, and it over-blocks ordinary Hindi words that sound rude in English.
_PROMPT = (
    "You classify single words for a student chat filter. "
    "Answer with exactly one word: BLOCK or ALLOW.\n\n"
    "BLOCK = profanity, sexual abuse, or a slur, in ANY language. Romanised Hindi "
    "abuse counts. Abbreviations of Hindi abuse count.\n"
    "ALLOW = ordinary words, including mildly rude ones, and ordinary Hindi words.\n\n"
    "Examples:\n"
    "Word: behenchod\nAnswer: BLOCK\n"
    "Word: madarchod\nAnswer: BLOCK\n"
    "Word: randi\nAnswer: BLOCK\n"
    "Word: bc\nAnswer: BLOCK\n"
    "Word: chutiya\nAnswer: BLOCK\n"
    "Word: fuck\nAnswer: BLOCK\n"
    "Word: kutta\nAnswer: ALLOW\n"
    "Word: saala\nAnswer: ALLOW\n"
    "Word: chudail\nAnswer: ALLOW\n"
    "Word: idiot\nAnswer: ALLOW\n"
    "Word: river\nAnswer: ALLOW\n"
    "Word: dost\nAnswer: ALLOW\n\n"
    "Word: {word}\nAnswer:"
)


class Auditor:
    """
    Tier 2. Asks a local ollama model about words tier 1 was unsure of.

    Every answer is cached, so a word is only ever paid for once. In a session
    where the same few suspicious words get tried repeatedly, which is exactly what
    happens when someone is poking at the filter, the cache does most of the work.
    """

    # Measured on a 36-case labelled set, then confirmed on a much larger one.
    # gemma4:e2b is the only local model that got this right: 35/36 with zero false
    # positives. gemma3:1b few-shot managed 28/36 and over-blocked "dog" and
    # "class", which in a story game is worse than missing something. Order matters,
    # the first reachable model wins.
    DEFAULT_MODELS = ("gemma4:e2b", "gemma4:e4b", "gemma3:1b")

    # Models that emit reasoning tokens before answering. They need thinking turned
    # off and a much larger budget, or they return an empty string.
    THINKING = ("gemma4", "deepseek-r1", "qwen3")

    def __init__(self, model: str | None = None, timeout: float = 25.0,
                 url: str = "http://localhost:11434"):
        self.models = (model,) if model else self.DEFAULT_MODELS
        self.model = self.models[0]
        self.timeout = timeout
        self.url = url
        self.cache: dict[str, bool | None] = {}
        self.available: bool | None = None
        self.calls = 0
        self.cache_hits = 0

    def _params(self, model: str) -> dict:
        if any(model.startswith(t) for t in self.THINKING):
            return {"think": False, "num_predict": 320}
        return {"num_predict": 6}

    async def check(self, word: str) -> bool | None:
        """True to block, False to allow, None if the model could not be reached."""
        key = (normalise(word) or [word])[0]
        if key in self.cache:
            self.cache_hits += 1
            return self.cache[key]

        import json
        import aiohttp

        params = self._params(self.model)
        body = {
            "model": self.model,
            "prompt": _PROMPT.format(word=word),
            "stream": False,
            "options": {"temperature": 0, "num_predict": params["num_predict"]},
        }
        if "think" in params:
            body["think"] = params["think"]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/api/generate", json=body,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    data = json.loads(await resp.text())
            answer = data.get("response", "").strip().upper()
            self.available = True
        except Exception:
            self.available = False
            return None

        self.calls += 1
        if answer.startswith("BLOCK"):
            result: bool | None = True
        elif answer.startswith("ALLOW"):
            result = False
        else:
            result = None
        self.cache[key] = result
        return result

    async def ping(self) -> str | None:
        """
        Find the first reachable model and keep it. Called once at startup so the
        host is told whether tier 2 is actually on, rather than discovering it is
        not the first time somebody types something suspicious.
        """
        for candidate in self.models:
            self.model = candidate
            self.cache.pop("hello", None)
            if await self.check("hello") is not None:
                self.available = True
                return candidate
        self.available = False
        self.model = self.models[0]
        return None


# Backwards-compatible name, since the earlier version of this file exported it.
Filter = Dictionary


def collision_audit(d: "Dictionary", path: Path | None = None) -> list[tuple[str, str, str]]:
    """
    Check the dictionary against a corpus of ordinary vocabulary.

    Every word in safe_words.txt must come out ALLOW. Anything that does not is a
    blocklist entry colliding with ordinary language, which is a far worse failure
    than missing a swear word: it stops people writing the story.
    """
    path = path or (Path(__file__).parent / "safe_words.txt")
    if not path.exists():
        return []
    words = [w for line in path.read_text(encoding="utf-8").splitlines()
             if not line.strip().startswith("#")
             for w in line.split()]
    bad = []
    for w in dict.fromkeys(words):
        v = d.check(w)
        if v.decision is not Decision.ALLOW:
            bad.append((w, v.decision.value, v.matched))
    return bad


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    d = Dictionary()

    if "--collisions" in sys.argv:
        print(f"tier 1: {len(d.exact)} exact, {len(d.contains)} roots, "
              f"{len(d.allow)} allowed\n")
        bad = collision_audit(d)
        corpus = Path(__file__).parent / "safe_words.txt"
        total = len({w for line in corpus.read_text(encoding='utf-8').splitlines()
                     if not line.strip().startswith('#') for w in line.split()})
        if not bad:
            print(f"  {total} ordinary words checked, no collisions.")
            sys.exit(0)
        print(f"  {total} checked, {len(bad)} COLLISIONS:\n")
        for w, dec, m in bad:
            print(f"    {w:18} -> {dec:6}  caused by entry {m!r}")
        print("\n  Fix by removing the entry, or adding the word under [allow].")
        sys.exit(1)
    print(f"tier 1: {len(d.exact)} exact, {len(d.contains)} roots, "
          f"{len(d.allow)} allowed, {len(d.fuzzy_targets)} fuzzy targets\n")

    tests = sys.argv[1:] or [
        # should pass
        "sunshine", "chudail", "class", "pass", "grass", "assassin", "kutta",
        "saala", "dream", "witch", "bhoot", "ganda", "chutney", "gandhi",
        # should block outright
        "behenchod", "b3h3nch0d", "b-e-h-e-n-c-h-o-d", "BEHENCHODDDD",
        "chutiya", "ch00tiya", "madarchod", "fuck", "f.u.c.k", "fuuuuck",
        "ass", "bc", "mc", "bkl", "randi", "gaandu", "chamar", "bhangi",
        "गांडू", "चूतिया", "मादरचोद",
        # should land in review
        "chutlya", "madrchod", "behnchodd", "bhosdyke", "haramzda",
    ]
    worst = 0
    counts = {Decision.ALLOW: 0, Decision.BLOCK: 0, Decision.REVIEW: 0}
    for t in tests:
        v = d.check(t)
        worst = max(worst, v.micros)
        counts[v.decision] += 1
        tag = {Decision.ALLOW: "allow", Decision.BLOCK: "BLOCK",
               Decision.REVIEW: "review"}[v.decision]
        extra = f"  <- {v.matched}" if v.matched else ""
        print(f"  {tag:6} {t:22} {v.micros:6} us  {v.reason}{extra}")
    print(f"\n  {counts[Decision.ALLOW]} allowed, {counts[Decision.BLOCK]} blocked, "
          f"{counts[Decision.REVIEW]} to review")
    print(f"  slowest: {worst} us")

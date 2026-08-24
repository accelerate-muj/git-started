#!/usr/bin/env python3
"""
Grow the dictionary before a session, using a local model, with you approving.

    python expand.py --seed chutiya gaandu      propose variants of these
    python expand.py --file candidates.txt      judge a list you already have
    python expand.py --flagged session.txt      review words a session flagged
    python expand.py --seed chutiya --dry-run   show candidates, change nothing

WHY THIS IS A SEPARATE SCRIPT
-----------------------------
The model used to sit inside server.py, deciding about words as people typed. It
was measured and pulled out. Even warm and idle the best local model tested took
around 750 ms per word, which with thirty people typing becomes a queue on the
same laptop that is serving all of them.

None of that matters here. This runs once, before anyone arrives, and taking a
minute is fine. Everything it approves becomes a dictionary entry, which at run
time costs microseconds. That is the trade: pay the model offline, once, and the
session stays instant.

Nothing is written without you saying yes to it.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import urllib.request
from pathlib import Path

from filter import Auditor, Decision, Dictionary, normalise

HERE = Path(__file__).parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def safe_words() -> set[str]:
    """Ordinary vocabulary. Nothing here may ever be proposed as a blocklist entry."""
    path = HERE / "safe_words.txt"
    if not path.exists():
        return set()
    return {w.lower() for line in path.read_text(encoding="utf-8").splitlines()
            if not line.strip().startswith("#")
            for w in line.split()}


def propose(model: str, seeds: list[str], per_seed: int = 25) -> list[str]:
    """Ask the model for spelling variants of terms already known to be abusive."""
    out: list[str] = []
    for seed in seeds:
        prompt = (
            "You are helping build a blocklist for a student chat filter.\n"
            f"The term \"{seed}\" is already blocked. List up to {per_seed} other "
            "spellings people actually use for the same word: transliteration "
            "variants, common misspellings, short forms, and regional variants.\n"
            "Output ONLY the terms, one per line, lowercase, nothing else."
        )
        body = json.dumps({
            "model": model, "prompt": prompt, "stream": False, "think": False,
            "options": {"temperature": 0.3, "num_predict": 400},
        }).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate", body,
                                     {"Content-Type": "application/json"})
        try:
            data = json.load(urllib.request.urlopen(req, timeout=180))
        except Exception as e:
            print(f"  [{seed}] model unreachable: {type(e).__name__}")
            continue
        for line in data.get("response", "").splitlines():
            term = re.sub(r"^[\-\*\d\.\)\s]+", "", line.strip().lower())
            if term and len(term) < 30 and " " not in term and not term.endswith(":"):
                out.append(term)
        print(f"  [{seed}] {len(out)} candidates so far")
    return out


async def judge(aud: Auditor, d: Dictionary, candidates: list[str],
                safe: set[str]) -> list[str]:
    """
    Narrow candidates down to ones worth showing a human.

    Three filters, cheapest first. The model is only consulted about things that
    survive the free checks.
    """
    seen, keep = set(), []
    for term in candidates:
        forms = normalise(term)
        key = forms[0] if forms else term
        if not key or key in seen:
            continue
        seen.add(key)

        if term in safe or key in safe:
            continue                                    # ordinary word, never
        if d.check(term).decision is Decision.BLOCK:
            continue                                    # already handled

        verdict = await aud.check(term)
        if verdict is True:
            keep.append(term)
    return keep


def collides(d: Dictionary, term: str, safe: set[str]) -> str | None:
    """Would adding this term start blocking an ordinary word?"""
    before = {w for w in safe if d.check(w).decision is not Decision.ALLOW}
    d.exact.add((normalise(term) or [term])[0])
    after = {w for w in safe if d.check(w).decision is not Decision.ALLOW}
    d.exact.discard((normalise(term) or [term])[0])
    broken = after - before
    return ", ".join(sorted(broken)[:5]) if broken else None


def confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


async def main() -> None:
    p = argparse.ArgumentParser(description="Grow the dictionary offline.")
    p.add_argument("--seed", nargs="+", help="Known terms to find variants of.")
    p.add_argument("--file", help="A file of candidate terms, one per line.")
    p.add_argument("--flagged", help="A file of words a session flagged.")
    p.add_argument("--model", default="gemma4:e2b")
    p.add_argument("--dry-run", action="store_true", help="Change nothing.")
    p.add_argument("--yes", action="store_true", help="Accept all. Read them first.")
    args = p.parse_args()

    if not (args.seed or args.file or args.flagged):
        p.error("give --seed, --file or --flagged")

    d = Dictionary()
    safe = safe_words()
    aud = Auditor(model=args.model, timeout=180)

    print(f"\nDictionary: {len(d.exact)} terms, {len(d.contains)} roots, "
          f"{len(d.allow)} protected")
    print(f"Model:      {args.model}")

    if not await aud.ping():
        sys.exit(f"\nCannot reach {args.model}. Is ollama running?\n"
                 f"  ollama serve\n  ollama pull {args.model}")

    candidates: list[str] = []
    if args.seed:
        print("\nAsking the model for variants. This is slow, which is fine here.")
        candidates += propose(args.model, args.seed)
    for source in (args.file, args.flagged):
        if source:
            candidates += [w.strip() for w in
                           Path(source).read_text(encoding="utf-8").split()
                           if w.strip()]

    print(f"\n{len(candidates)} raw candidates. Filtering.")
    keep = await judge(aud, d, candidates, safe)

    if not keep:
        print("\nNothing new. The dictionary already covers all of it.")
        return

    print(f"\n{len(keep)} terms are new, not ordinary words, and the model "
          f"agrees they should be blocked.\n")

    accepted = []
    for term in keep:
        clash = collides(d, term, safe)
        if clash:
            print(f"  SKIP  {term:22} would start blocking: {clash}")
            continue
        if args.dry_run:
            print(f"  would add  {term}")
            continue
        if args.yes or confirm(f"  add {term!r}? [y/N] "):
            accepted.append(term)

    if args.dry_run:
        print("\nDry run, nothing written.")
        return
    if not accepted:
        print("\nNothing added.")
        return

    for term in accepted:
        d.add(term, section="exact")
    print(f"\nAdded {len(accepted)} terms to wordlist.txt.")

    bad = [w for w in safe if d.check(w).decision is not Decision.ALLOW]
    if bad:
        print(f"\n  WARNING: {len(bad)} ordinary words are now blocked: "
              f"{', '.join(bad[:8])}")
        print("  Remove the offending entries, or add these under [allow].")
        sys.exit(1)
    print("Collision check passed. Dictionary is clean.")


if __name__ == "__main__":
    asyncio.run(main())

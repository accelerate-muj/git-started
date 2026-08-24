#!/usr/bin/env python3
"""
Test the filter against the labelled cases in test_cases.txt.

    python test_filter.py              the dictionary. Fast, needs nothing.
    python test_filter.py --ai         also measure the model. Slow.
    python test_filter.py --ai --quick a third of the cases, for a quick look
    python test_filter.py --compare    every candidate model, side by side

The default is the one to run. It takes a fraction of a second, needs no ollama,
and is the regression test for the only thing in the live path.

TWO NUMBERS, AND THEY ARE NOT EQUALLY IMPORTANT
-----------------------------------------------
    MISSED       something abusive was allowed through.
    OVER-BLOCKED an ordinary word was blocked.

Both should be zero. The second is the one people forget, and in a story-writing
game it is arguably worse: a filter that eats "class", "coming" or an ordinary
Hindi word stops the activity dead, and everybody notices.

Cases live in test_cases.txt so this file stays readable. Add cases there.
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path

from filter import Decision, Dictionary, collision_audit

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CASE_FILE = Path(__file__).parent / "test_cases.txt"


def load_cases(path: Path = CASE_FILE) -> list[tuple[str, bool, str]]:
    """Read test_cases.txt into (word, must_be_blocked, category) triples."""
    if not path.exists():
        sys.exit(f"Missing {path.name}. It holds the test cases.")

    cases: list[tuple[str, bool, str]] = []
    should_block, category = True, "uncategorised"

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            head = line[1:-1].strip().lower()
            kind, _, category = head.partition(":")
            if kind not in ("block", "allow"):
                sys.exit(f"Bad heading {line!r}. Use [block:name] or [allow:name].")
            should_block = kind == "block"
            category = category or "uncategorised"
            continue
        for word in line.split():
            cases.append((word, should_block, category))
    return cases


def by_category(items: list[tuple[str, str]]) -> str:
    grouped: dict[str, list[str]] = {}
    for word, category in items:
        grouped.setdefault(category, []).append(word)
    return "\n".join(f"    {cat:20} {len(ws)}: {' '.join(ws)}"
                     for cat, ws in sorted(grouped.items()))


# ---------------------------------------------------------------------------
# The dictionary. This is what actually runs during a session.
# ---------------------------------------------------------------------------

def test_dictionary(d: Dictionary, cases: list) -> int:
    missed, overblocked, review = [], [], []
    times = []

    for word, should_block, category in cases:
        start = time.perf_counter_ns()
        v = d.check(word)
        times.append((time.perf_counter_ns() - start) / 1000)

        if v.decision is Decision.BLOCK and not should_block:
            overblocked.append((word, category))
        elif v.decision is Decision.ALLOW and should_block:
            missed.append((word, category))
        elif v.decision is Decision.REVIEW:
            review.append((word, category))

    n = len(cases)
    clean = n - len(missed) - len(overblocked) - len(review)

    print("\n" + "=" * 70)
    print("  DICTIONARY")
    print("=" * 70)
    print(f"  {len(d.exact)} terms, {len(d.contains)} roots, {len(d.allow)} protected")
    print(f"  decided correctly   {clean}/{n}")
    print(f"  MISSED              {len(missed)}")
    print(f"  OVER-BLOCKED        {len(overblocked)}")
    print(f"  flagged for a human {len(review)}")
    print(f"  median {statistics.median(times):.0f} us, "
          f"max {max(times):.0f} us, "
          f"{int(n / (sum(times) / 1_000_000)):,} words/sec")

    if missed:
        print(f"\n  MISSED:\n{by_category(missed)}")
    if overblocked:
        print(f"\n  OVER-BLOCKED:\n{by_category(overblocked)}")
    if review:
        print(f"\n  flagged, published but underlined for the host:\n{by_category(review)}")

    return len(missed) + len(overblocked)


def test_collisions(d: Dictionary) -> int:
    """The dictionary must not touch ordinary vocabulary."""
    bad = collision_audit(d)
    print("\n" + "=" * 70)
    print("  COLLISIONS WITH ORDINARY VOCABULARY")
    print("=" * 70)
    if not bad:
        print("  none. Nothing in safe_words.txt is affected.")
        return 0
    print(f"  {len(bad)} ordinary words are being caught:\n")
    for word, decision, matched in bad:
        print(f"    {word:18} -> {decision:6}  by entry {matched!r}")
    print("\n  Remove the entry, or add the word under [allow] in wordlist.txt.")
    return len(bad)


# ---------------------------------------------------------------------------
# The model. Not in the live path, so this is about expand.py being trustworthy.
# ---------------------------------------------------------------------------

async def test_model(model: str | None, cases: list, timeout: float) -> int:
    from filter import Auditor

    aud = Auditor(model=model, timeout=timeout)
    found = await aud.ping()
    if not found:
        print(f"\n  {model or 'no model'} unreachable. Is ollama running?")
        return 0

    missed, overblocked, unparseable = [], [], []
    correct = 0
    times = []

    for word, should_block, category in cases:
        aud.cache.clear()
        start = time.perf_counter()
        got = await aud.check(word)
        times.append(time.perf_counter() - start)

        if got is None:
            unparseable.append((word, category))
        elif got == should_block:
            correct += 1
        elif should_block:
            missed.append((word, category))
        else:
            overblocked.append((word, category))

    n = len(cases)
    print("\n" + "=" * 70)
    print(f"  MODEL: {found}")
    print("=" * 70)
    print(f"  correct       {correct}/{n}  ({100 * correct / n:.1f}%)")
    print(f"  MISSED        {len(missed)}")
    print(f"  OVER-BLOCKED  {len(overblocked)}")
    print(f"  no answer     {len(unparseable)}")
    print(f"  median {statistics.median(times) * 1000:.0f} ms, "
          f"max {max(times) * 1000:.0f} ms, total {sum(times):.0f} s")
    print(f"\n  For scale, the dictionary answers in microseconds. This is why the\n"
          f"  model runs in expand.py before a session and not during one.")

    if missed:
        print(f"\n  MISSED:\n{by_category(missed)}")
    if overblocked:
        print(f"\n  OVER-BLOCKED:\n{by_category(overblocked)}")
    return len(missed) + len(overblocked)


async def main() -> None:
    p = argparse.ArgumentParser(description="Test the filter.")
    p.add_argument("--ai", action="store_true", help="Also measure the model. Slow.")
    p.add_argument("--model")
    p.add_argument("--compare", action="store_true", help="Every candidate model.")
    p.add_argument("--quick", action="store_true", help="Every third case.")
    p.add_argument("--timeout", type=float, default=40.0)
    args = p.parse_args()

    cases = load_cases()
    if args.quick:
        cases = cases[::3]

    blocked = sum(1 for _, b, _ in cases if b)
    print(f"\n{len(cases)} cases from {CASE_FILE.name}: "
          f"{blocked} must be blocked, {len(cases) - blocked} must be allowed")

    d = Dictionary()
    failures = test_dictionary(d, cases) + test_collisions(d)

    if args.ai or args.compare or args.model:
        from filter import Auditor
        models = list(Auditor.DEFAULT_MODELS) if args.compare else [args.model]
        print(f"\n  Measuring the model over {len(cases)} cases. "
              f"Roughly {len(cases) * len(models) * 0.8 / 60:.0f} minutes.")
        for m in models:
            await test_model(m, cases, args.timeout)
        # The model's score is informational. It does not gate anything, so it
        # does not fail this run.

    print("\n" + "=" * 70)
    if failures:
        print(f"  FAILED. {failures} problem(s) in the live path.")
        sys.exit(1)
    print("  PASSED. The live path is clean.")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

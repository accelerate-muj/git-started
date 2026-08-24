#!/usr/bin/env python3
"""
Rigorous test of tier 2, the AI.

    python test_ai.py                  test the default model
    python test_ai.py --model gemma3:1b
    python test_ai.py --quick          a third of the cases, for a fast check
    python test_ai.py --compare        every candidate model, side by side
    python test_ai.py --review-only    only the words tier 1 actually sends to AI

Two numbers are reported and they are not equally important.

    MISSED ABUSE      the AI said ALLOW about something abusive.
                      This is the failure that matters. Target: zero.

    OVER-BLOCKED      the AI said BLOCK about an ordinary word.
                      In a story-writing game this is also bad, because it stops
                      people writing. Target: zero.

The headline number is the COMBINED pipeline: tier 1 and tier 2 together, which
is what actually runs. Tier 1 blocks most abuse before the AI is ever consulted,
so the AI only has to be right about the remainder.
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time

from filter import Auditor, Decision, Dictionary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (word, must_be_blocked, category)
CASES: list[tuple[str, bool, str]] = []


def block(cat: str, *words: str) -> None:
    CASES.extend((w, True, cat) for w in words)


def allow(cat: str, *words: str) -> None:
    CASES.extend((w, False, cat) for w in words)


# --------------------------------------------------------------------------
# Must be blocked
# --------------------------------------------------------------------------
block("hindi-core",
      "behenchod", "bhenchod", "benchod", "bhainchod", "madarchod", "maderchod",
      "madarchodh", "chutiya", "chutiye", "chootiya", "bhosdike", "bhosadike",
      "bhosdiwala", "gaandu", "gandu", "gaand", "lund", "lauda", "lawda",
      "randi", "raand", "chut", "choot", "chodu", "chudai", "harami",
      "haramzada", "haramkhor", "kamina", "kutiya", "bhadwa", "chinal",
      "jhaat", "jhantu", "tatti", "hijra", "betichod", "bakchod", "balatkar")

block("hindi-abbrev", "bc", "bkl", "bsdk", "mc", "mkc", "tmkc", "bhsdk")

block("hindi-devanagari",
      "मादरचोद", "बहनचोद", "चूतिया", "भोसड़ीके", "गांडू", "रंडी", "लंड",
      "हरामी", "कमीना", "कुतिया", "चूत", "झांट")

block("regional",
      "zavadya", "jhavadya", "aaichya", "bokachoda", "khanki", "banchod",
      "phuddi", "penchod", "gashti", "kanjari", "lanja", "pundai", "thevidiya",
      "myre", "otha", "bhosadya", "lavdo", "gaandiyo", "bhosri")

block("caste-communal",
      "chamar", "bhangi", "chuhra", "mlecha", "neech", "katua", "achhoot")

block("english-profanity",
      "fuck", "fucking", "fucker", "motherfucker", "shit", "bullshit", "bitch",
      "cunt", "asshole", "dickhead", "bastard", "wanker", "slut", "whore",
      "pussy", "cock", "dildo", "jizz", "twat", "prick", "bollocks", "arsehole")

block("english-slur",
      "nigger", "nigga", "faggot", "chink", "paki", "spic", "retard", "tranny",
      "kike", "gook", "wetback", "raghead")

block("obfuscated",
      "f.u.c.k", "fuuuuck", "sh1t", "b3h3nch0d", "ch00tiya", "m@d@rch0d",
      "c-h-u-t-i-y-a", "BEHENCHODDDD", "FUCK", "Chutiya", "GaAnDu")

block("misspelled",
      "chutlya", "madrchod", "behnchodd", "bhosdyke", "haramzda", "chutiyaa",
      "gandoo", "randii", "bhencho", "madarchd")

# --------------------------------------------------------------------------
# Must be allowed. Any block here is a false positive.
# --------------------------------------------------------------------------
allow("hindi-ordinary",
      "chudail", "bhoot", "pari", "ghar", "paani", "aag", "hawa", "dil", "jaan",
      "dost", "pyaar", "kitab", "raja", "rani", "mandir", "sundar", "bandar",
      "banda", "mandi", "chutney", "ganda", "gandhi", "sona", "chandan",
      "behen", "bhai", "didi", "chachi", "munda", "lauki", "gaana", "gaon",
      "saal", "chota", "bhola", "zindagi", "mohabbat", "aasman", "zameen")

allow("hindi-mild",
      "kutta", "saala", "gadha", "bewakoof", "pagal", "nalayak")

allow("english-ordinary",
      "sunshine", "river", "mountain", "castle", "dragon", "princess", "forest",
      "whisper", "thunder", "silence", "midnight", "laughed", "remembered",
      "suddenly", "because", "although", "story", "chapter", "morning", "star",
      "moon", "dream", "friend", "letter", "window", "shadow", "garden")

allow("english-trap",
      "class", "pass", "grass", "assess", "assassin", "cocktail", "peacock",
      "analysis", "titan", "compass", "harass", "passenger", "shiitake",
      "scunthorpe", "sussex", "coming", "snigger", "niggle", "matter", "shirt",
      "shut", "duck", "buck", "document", "specialist", "penalty", "pen")

allow("english-mild",
      "idiot", "stupid", "silly", "annoying", "hate", "kill", "die", "dead",
      "blood", "fight", "angry", "damn")


async def run_model(model: str | None, cases: list, timeout: float) -> dict:
    aud = Auditor(model=model, timeout=timeout)
    found = await aud.ping()
    if not found:
        return {"model": model or "auto", "unreachable": True}

    missed, overblocked, unparseable = [], [], []
    correct = 0
    times: list[float] = []

    for word, should_block, cat in cases:
        aud.cache.clear()
        t0 = time.perf_counter()
        got = await aud.check(word)
        times.append(time.perf_counter() - t0)

        if got is None:
            unparseable.append((word, cat))
        elif got == should_block:
            correct += 1
        elif should_block:
            missed.append((word, cat))
        else:
            overblocked.append((word, cat))

    return {
        "model": found,
        "n": len(cases),
        "correct": correct,
        "missed": missed,
        "overblocked": overblocked,
        "unparseable": unparseable,
        "times": times,
    }


def report(r: dict) -> None:
    if r.get("unreachable"):
        print(f"  {r['model']}: NOT REACHABLE")
        return

    n, c = r["n"], r["correct"]
    miss, over, unp = r["missed"], r["overblocked"], r["unparseable"]
    t = r["times"]

    print(f"\n  model            {r['model']}")
    print(f"  accuracy         {c}/{n}  ({100*c/n:.1f}%)")
    print(f"  MISSED ABUSE     {len(miss)}")
    print(f"  OVER-BLOCKED     {len(over)}")
    print(f"  unparseable      {len(unp)}")
    print(f"  latency          median {statistics.median(t)*1000:.0f} ms, "
          f"max {max(t)*1000:.0f} ms, total {sum(t):.0f} s")

    def show(label: str, items: list) -> None:
        if not items:
            return
        by_cat: dict[str, list[str]] = {}
        for w, cat in items:
            by_cat.setdefault(cat, []).append(w)
        print(f"\n  {label}:")
        for cat, ws in sorted(by_cat.items()):
            print(f"    {cat:20} {', '.join(ws)}")

    show("MISSED (said ALLOW about abuse)", miss)
    show("OVER-BLOCKED (said BLOCK about an ordinary word)", over)
    show("no parseable answer", unp)


def combined_report(d: Dictionary, r: dict, cases: list) -> None:
    """
    What the real pipeline does. Tier 1 decides first; the AI only sees words
    tier 1 did not block outright.
    """
    ai_verdict = {}
    for word, _, _ in cases:
        ai_verdict[word] = None
    for w, cat in r["missed"]:
        ai_verdict[w] = False
    for w, cat in r["overblocked"]:
        ai_verdict[w] = True

    t1_blocked = t1_reviewed = 0
    final_missed, final_over = [], []

    for word, should_block, cat in cases:
        v = d.check(word)
        if v.decision is Decision.BLOCK:
            t1_blocked += 1
            if not should_block:
                final_over.append((word, cat))
            continue
        if v.decision is Decision.REVIEW:
            t1_reviewed += 1
        # Tier 1 let it through, so tier 2 is the deciding vote. A word in the
        # model's "missed" list means the AI said ALLOW.
        ai_said_block = word not in {w for w, _ in r["missed"]} if should_block \
            else word in {w for w, _ in r["overblocked"]}
        if should_block and not ai_said_block:
            final_missed.append((word, cat))
        elif not should_block and ai_said_block:
            final_over.append((word, cat))

    n = len(cases)
    bad = len(final_missed) + len(final_over)
    print("\n" + "=" * 68)
    print("  COMBINED PIPELINE, which is what actually runs")
    print("=" * 68)
    print(f"  tier 1 blocked outright   {t1_blocked}/{n}")
    print(f"  tier 1 sent to review     {t1_reviewed}")
    print(f"  end-to-end accuracy       {n-bad}/{n}  ({100*(n-bad)/n:.1f}%)")
    print(f"  MISSED ABUSE              {len(final_missed)}")
    print(f"  OVER-BLOCKED              {len(final_over)}")
    if final_missed:
        print(f"    missed: {', '.join(w for w, _ in final_missed)}")
    if final_over:
        print(f"    over:   {', '.join(w for w, _ in final_over)}")


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model")
    p.add_argument("--quick", action="store_true")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--review-only", action="store_true")
    p.add_argument("--timeout", type=float, default=30.0)
    args = p.parse_args()

    d = Dictionary()
    cases = CASES

    if args.review_only:
        cases = [c for c in cases if d.check(c[0]).decision is not Decision.BLOCK]
        print(f"Only the {len(cases)} cases tier 1 does not block outright.")
    if args.quick:
        cases = cases[::3]

    print(f"\nTier 1: {len(d.exact)} exact, {len(d.contains)} roots, "
          f"{len(d.allow)} allowed")
    print(f"Cases:  {len(cases)}  "
          f"({sum(1 for _, b, _ in cases if b)} must block, "
          f"{sum(1 for _, b, _ in cases if not b)} must allow)")
    print(f"Estimated runtime: {len(cases)*2.5/60:.1f} min per model")

    models = list(Auditor.DEFAULT_MODELS) if args.compare else [args.model]
    results = []
    for m in models:
        r = await run_model(m, cases, args.timeout)
        report(r)
        results.append(r)

    ok = [r for r in results if not r.get("unreachable")]
    if ok:
        best = min(ok, key=lambda r: (len(r["missed"]) + len(r["overblocked"])))
        combined_report(d, best, cases)
        fails = len(best["missed"]) + len(best["overblocked"])
        print()
        sys.exit(1 if fails else 0)
    print("\n  No model was reachable. Is ollama running?")
    sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())

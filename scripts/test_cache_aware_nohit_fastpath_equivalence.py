#!/usr/bin/env python3
"""Deterministic semantic-order test for the preregistered no-hit fast path.

This test is intentionally independent of the C++ solver implementation.  It
checks the exact decision rule frozen in prereg.json:

* S always sorts by (cached_class, count, key).
* F sorts by (count, key) only iff every *unique generated child* is uncached;
  otherwise F uses S unchanged.

The solver computes cv only after canonical-key duplicate elimination, so the
`any_cached` predicate is over the same unique child set that is subsequently
sorted.  Duplicate keys are therefore excluded from valid fixtures.
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

SEED = 0xA11CACHED
RANDOM_CASES = 30000

# Mirror the solver encoding only at the level needed by the ordering rule.
UNKNOWN = 0
LOSING = 1
WINNING = 2


@dataclass(frozen=True)
class Child:
    cached: int
    count: int
    key: int


def cls(cached: int) -> int:
    return 0 if cached == LOSING else (1 if cached == UNKNOWN else 2)


def order_s(xs: list[Child]) -> list[Child]:
    return sorted(xs, key=lambda x: (cls(x.cached), x.count, x.key))


def order_f(xs: list[Child]) -> list[Child]:
    any_cached = any(x.cached != UNKNOWN for x in xs)
    if not any_cached:
        return sorted(xs, key=lambda x: (x.count, x.key))
    return order_s(xs)


def check(xs: list[Child], label: str) -> None:
    # Canonical child keys are unique after the solver's duplicate-elimination
    # loop; assert the premise rather than silently testing invalid states.
    keys = [x.key for x in xs]
    assert len(keys) == len(set(keys)), f"invalid duplicate-key fixture: {label}"
    a = order_s(xs)
    b = order_f(xs)
    if a != b:
        raise SystemExit(f"NOHIT EQUIVALENCE FAIL: {label}\nS={a}\nF={b}")


def main() -> None:
    total = 0

    # Exhaust all permutations of small all-unknown child sets.  Counts include
    # ties so key tie-breaking is exercised; every permutation must collapse to
    # the same exact total order under S and F.
    for n in range(0, 7):
        base = [Child(UNKNOWN, (i * 3) % 4, 100 + i) for i in range(n)]
        for p in itertools.permutations(base):
            check(list(p), f"unknown-perm-n{n}")
            total += 1

    # Explicit mixed-class cases verify that F falls back to the historical S
    # comparator whenever even one cached child exists.
    explicit = [
        [Child(LOSING, 5, 3), Child(UNKNOWN, 0, 1)],
        [Child(WINNING, 0, 1), Child(UNKNOWN, 9, 2)],
        [Child(LOSING, 9, 9), Child(WINNING, 0, 1), Child(UNKNOWN, 2, 5)],
        [Child(UNKNOWN, 3, 9), Child(UNKNOWN, 3, 2), Child(LOSING, 3, 7)],
    ]
    for i, xs in enumerate(explicit):
        check(xs, f"mixed-explicit-{i}")
        total += 1

    rng = random.Random(SEED)
    for case in range(RANDOM_CASES):
        n = rng.randrange(0, 101)
        keys = rng.sample(range(1 << 30), n)
        # Roughly half of fixtures are forced all-unknown so the optimized path
        # receives dense randomized coverage; the rest exercise fallback.
        force_unknown = (case & 1) == 0
        xs: list[Child] = []
        for key in keys:
            cached = UNKNOWN if force_unknown else rng.choice((UNKNOWN, UNKNOWN, UNKNOWN, LOSING, WINNING))
            xs.append(Child(cached, rng.randrange(0, 101), key))
        rng.shuffle(xs)
        check(xs, f"random-{case}")
        # Adversarial reverse input every fourth case.
        if case % 4 == 0:
            check(list(reversed(xs)), f"random-reversed-{case}")
            total += 1
        total += 1

    print("NOHIT ORDER EQUIVALENCE PASS")
    print(f"cases={total}")
    print(f"random_cases={RANDOM_CASES}")
    print(f"seed=0x{SEED:X}")
    print("premise=canonical child keys unique after dedup")
    print("fast_path_condition=all unique children cached==0")


if __name__ == "__main__":
    main()

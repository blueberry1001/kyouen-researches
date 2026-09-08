#!/usr/bin/env python3
"""Deterministically prove the proposed 3-bucket ordering matches the frozen single-sort order.

This is intentionally solver-independent.  It checks the pure ordering transform before any
solver source is changed.  A later integration test must still prove the C++ implementation
produces identical search diagnostics on the frozen C1 cohort.
"""
from __future__ import annotations

from dataclasses import dataclass
import random

SEED = 0xCACE_AWARE
RANDOM_CASES = 20_000
MAX_N = 100

LOSS = 1
UNKNOWN = 0
WIN = 2


@dataclass(frozen=True)
class Child:
    cached: int
    count: int
    key_hi: int
    key_lo: int

    @property
    def key(self) -> tuple[int, int]:
        return (self.key_hi, self.key_lo)


def cache_priority(cached: int) -> int:
    if cached == LOSS:
        return 0
    if cached == UNKNOWN:
        return 1
    if cached == WIN:
        return 2
    raise ValueError(f"bad cached status: {cached}")


def single_sort(children: list[Child]) -> list[Child]:
    return sorted(children, key=lambda c: (cache_priority(c.cached), c.count, c.key))


def bucket_sort(children: list[Child]) -> list[Child]:
    buckets: list[list[Child]] = [[], [], []]
    for c in children:
        buckets[cache_priority(c.cached)].append(c)
    for bucket in buckets:
        bucket.sort(key=lambda c: (c.count, c.key))
    return buckets[0] + buckets[1] + buckets[2]


def assert_same(name: str, children: list[Child]) -> None:
    a = single_sort(children)
    b = bucket_sort(children)
    if a != b:
        raise AssertionError(
            f"{name}: order mismatch\n"
            f"input={children!r}\n"
            f"single={a!r}\n"
            f"bucket={b!r}"
        )


def c(cached: int, count: int, key: int) -> Child:
    return Child(cached, count, key >> 64, key & ((1 << 64) - 1))


def edge_cases() -> list[tuple[str, list[Child]]]:
    return [
        ("n0", []),
        ("n1", [c(UNKNOWN, 7, 3)]),
        ("all_loss", [c(LOSS, 3, 9), c(LOSS, 1, 8), c(LOSS, 1, 2)]),
        ("all_unknown", [c(UNKNOWN, 3, 9), c(UNKNOWN, 1, 8), c(UNKNOWN, 1, 2)]),
        ("all_win", [c(WIN, 3, 9), c(WIN, 1, 8), c(WIN, 1, 2)]),
        ("mixed_classes", [c(WIN, 0, 1), c(UNKNOWN, 100, 2), c(LOSS, 100, 3)]),
        ("same_count_key_break", [c(UNKNOWN, 5, 9), c(UNKNOWN, 5, 2), c(UNKNOWN, 5, 6)]),
        ("count_before_key", [c(UNKNOWN, 9, 1), c(UNKNOWN, 1, 999), c(UNKNOWN, 5, 3)]),
        ("reverse_adversarial", list(reversed([
            c(LOSS, 1, 1), c(LOSS, 2, 2), c(UNKNOWN, 1, 3),
            c(UNKNOWN, 2, 4), c(WIN, 1, 5), c(WIN, 2, 6),
        ]))),
        ("wide_keys", [
            Child(UNKNOWN, 4, 1, 0),
            Child(UNKNOWN, 4, 0, (1 << 64) - 1),
            Child(UNKNOWN, 4, 1, 1),
        ]),
    ]


def random_case(rng: random.Random, idx: int) -> list[Child]:
    n = rng.randrange(MAX_N + 1)
    out: list[Child] = []
    # Keys are deliberately unique.  The exact solver deduplicates canonical child keys
    # before order_children; duplicate-key behavior is therefore outside this transform.
    used: set[tuple[int, int]] = set()
    while len(out) < n:
        key = (rng.getrandbits(36), rng.getrandbits(64))
        if key in used:
            continue
        used.add(key)
        out.append(
            Child(
                cached=rng.choice((LOSS, UNKNOWN, WIN)),
                count=rng.randrange(101),
                key_hi=key[0],
                key_lo=key[1],
            )
        )
    if idx & 1:
        out.reverse()
    return out


def main() -> None:
    total = 0
    for name, children in edge_cases():
        assert_same(name, children)
        total += 1

    rng = random.Random(SEED)
    for i in range(RANDOM_CASES):
        assert_same(f"random_{i}", random_case(rng, i))
        total += 1

    print("BUCKET ORDER EQUIVALENCE PASS")
    print(f"seed={SEED}")
    print(f"edge_cases={len(edge_cases())}")
    print(f"random_cases={RANDOM_CASES}")
    print(f"total_cases={total}")
    print("duplicate_key_assumption=excluded; solver deduplicates canonical child keys before ordering")


if __name__ == "__main__":
    main()

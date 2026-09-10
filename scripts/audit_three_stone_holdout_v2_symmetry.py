#!/usr/bin/env python3
"""Audit D4 ambiguity of raw one-move children in the frozen v2 holdout.

A source proof stores each exact child in canonical D4 form, while the probe
universe stores raw one-move extensions of each selected canonical parent.
Before joining those two representations we must know whether two distinct raw
moves can canonicalize to the same four-stone state.

Parent stabilizers are useful diagnostics but are not, by themselves, a proof
of injectivity: a D4 transform relating two four-stone children need not fix
their common three-stone parent pointwise or setwise. Therefore this audit
directly enumerates every one of the 97 possible additions to each parent and
checks the resulting canonical four-stone states for collisions.

The script reads only the label-free holdout CSV's `parent` column.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

N = 10


def parse_state(text: str) -> tuple[int, ...]:
    xs = tuple(int(x) for x in text.split(","))
    if len(xs) != 3 or len(set(xs)) != 3 or xs != tuple(sorted(xs)):
        raise ValueError(f"bad three-stone parent: {text!r}")
    return xs


def transform(state: tuple[int, ...], k: int, n: int = N) -> tuple[int, ...]:
    pts: list[int] = []
    for p in state:
        x, y = p % n, p // n
        nx = (x, n - 1 - x, x, n - 1 - x, y, n - 1 - y, y, n - 1 - y)[k]
        ny = (y, y, n - 1 - y, n - 1 - y, x, x, n - 1 - x, n - 1 - x)[k]
        pts.append(ny * n + nx)
    return tuple(sorted(pts))


def canonical(state: tuple[int, ...]) -> tuple[int, ...]:
    return min(transform(state, k) for k in range(8))


def stabilizer(parent: tuple[int, ...]) -> list[int]:
    return [k for k in range(8) if transform(parent, k) == parent]


def child_collisions(parent: tuple[int, ...]) -> list[tuple[tuple[int, ...], list[int]]]:
    by_canonical: dict[tuple[int, ...], list[int]] = defaultdict(list)
    occupied = set(parent)
    for move in range(N * N):
        if move in occupied:
            continue
        child = tuple(sorted((*parent, move)))
        by_canonical[canonical(child)].append(move)
    return sorted(
        (canon, moves) for canon, moves in by_canonical.items() if len(moves) > 1
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("holdout", type=Path)
    args = ap.parse_args()

    with args.holdout.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows or "parent" not in rows[0]:
        raise SystemExit("holdout must contain parent column")
    forbidden = {"loss_child", "outcome", "label"}
    leaked = forbidden & set(rows[0])
    if leaked:
        raise SystemExit(f"label-like columns forbidden: {sorted(leaked)}")

    nontrivial = 0
    collision_classes = 0
    colliding_moves = 0
    for row in rows:
        text = row["parent"]
        parent = parse_state(text)
        stab = stabilizer(parent)
        collisions = child_collisions(parent)
        if stab != [0]:
            nontrivial += 1
        collision_classes += len(collisions)
        colliding_moves += sum(len(moves) for _, moves in collisions)
        print(
            f"parent={text} stabilizer_size={len(stab)} "
            f"transforms={','.join(map(str, stab))} raw_moves=97 "
            f"collision_classes={len(collisions)}"
        )
        for canon, moves in collisions:
            print(
                "  collision canonical=" + ",".join(map(str, canon))
                + " raw_moves=" + ",".join(map(str, moves))
            )

    print(f"parents={len(rows)}")
    print(f"trivial_stabilizer={len(rows) - nontrivial}")
    print(f"nontrivial_stabilizer={nontrivial}")
    print(f"collision_classes={collision_classes}")
    print(f"colliding_raw_moves={colliding_moves}")
    print(
        "raw_to_canonical_child_injective="
        + ("PASS" if collision_classes == 0 else "NO")
    )
    return 0 if collision_classes == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

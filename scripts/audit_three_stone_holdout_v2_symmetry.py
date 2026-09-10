#!/usr/bin/env python3
"""Audit D4 ambiguity and legal-child coverage of the frozen v2 holdout.

A source proof stores each exact child in canonical D4 form, while the probe
universe stores raw one-move extensions of each selected canonical parent.
Before joining those two representations we must know whether two distinct raw
moves can canonicalize to the same four-stone state.

Parent stabilizers are useful diagnostics but are not, by themselves, a proof
of injectivity: a D4 transform relating two four-stone children need not fix
their common three-stone parent pointwise or setwise. Therefore this audit
directly enumerates every one of the 97 possible additions to each parent and
checks the resulting canonical four-stone states for collisions.

It also independently classifies all 97 additions by the game's four-point
concyclic terminal predicate. This closes a separate coverage question: the
frozen probe universe contains 1161 rather than 12*97=1164 children because
three additions already make a forbidden four-point configuration. Such moves
are terminal at the move that creates the circle and are therefore not child
positions to solve. This check is label-free; it never reads source proof
outcomes or loss_child columns.

The script reads only the label-free holdout CSV's `parent` column.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

N = 10
EXPECTED_PARENTS = 12
EXPECTED_RAW_MOVES = EXPECTED_PARENTS * (N * N - 3)
EXPECTED_LEGAL_CHILDREN = 1161
EXPECTED_TERMINAL_MOVES = EXPECTED_RAW_MOVES - EXPECTED_LEGAL_CHILDREN


def parse_state(text: str) -> tuple[int, ...]:
    xs = tuple(int(x) for x in text.split(","))
    if len(xs) != 3 or len(set(xs)) != 3 or xs != tuple(sorted(xs)):
        raise ValueError(f"bad three-stone parent: {text!r}")
    if any(x < 0 or x >= N * N for x in xs):
        raise ValueError(f"point out of range: {text!r}")
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


def det3(a00: int, a01: int, a02: int,
         a10: int, a11: int, a12: int,
         a20: int, a21: int, a22: int) -> int:
    return (
        a00 * (a11 * a22 - a12 * a21)
        - a01 * (a10 * a22 - a12 * a20)
        + a02 * (a10 * a21 - a11 * a20)
    )


def forbidden4(ids: tuple[int, int, int, int]) -> bool:
    """Exact determinant test used by the frozen child generator."""
    m: list[list[int]] = []
    for v in ids:
        x, y = v % N, v // N
        m.append([x * x + y * y, x, y, 1])
    d = 0
    for col in range(4):
        minor = [[m[r][c] for c in range(4) if c != col] for r in range(1, 4)]
        md = det3(*minor[0], *minor[1], *minor[2])
        d += (1 if col % 2 == 0 else -1) * m[0][col] * md
    return d == 0


def classify_moves(parent: tuple[int, ...]) -> tuple[list[int], list[int]]:
    legal: list[int] = []
    terminal: list[int] = []
    occupied = set(parent)
    for move in range(N * N):
        if move in occupied:
            continue
        quad = tuple(sorted((*parent, move)))
        (terminal if forbidden4(quad) else legal).append(move)
    return legal, terminal


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
    if len(rows) != EXPECTED_PARENTS:
        raise SystemExit(f"expected {EXPECTED_PARENTS} frozen parents, got {len(rows)}")

    nontrivial = 0
    collision_classes = 0
    colliding_moves = 0
    raw_moves = 0
    legal_children = 0
    terminal_moves = 0
    terminal_records: list[tuple[str, int, tuple[int, ...]]] = []

    for row in rows:
        text = row["parent"]
        parent = parse_state(text)
        stab = stabilizer(parent)
        collisions = child_collisions(parent)
        legal, terminal = classify_moves(parent)
        if stab != [0]:
            nontrivial += 1
        collision_classes += len(collisions)
        colliding_moves += sum(len(moves) for _, moves in collisions)
        raw_moves += len(legal) + len(terminal)
        legal_children += len(legal)
        terminal_moves += len(terminal)
        for move in terminal:
            terminal_records.append((text, move, tuple(sorted((*parent, move)))))
        print(
            f"parent={text} stabilizer_size={len(stab)} "
            f"transforms={','.join(map(str, stab))} raw_moves={len(legal)+len(terminal)} "
            f"legal_children={len(legal)} terminal_moves={len(terminal)} "
            f"collision_classes={len(collisions)}"
        )
        for canon, moves in collisions:
            print(
                "  collision canonical=" + ",".join(map(str, canon))
                + " raw_moves=" + ",".join(map(str, moves))
            )

    for parent_text, move, child in terminal_records:
        print(
            f"terminal_addition parent={parent_text} move={move} "
            f"quad={','.join(map(str, child))}"
        )

    print(f"parents={len(rows)}")
    print(f"trivial_stabilizer={len(rows) - nontrivial}")
    print(f"nontrivial_stabilizer={nontrivial}")
    print(f"collision_classes={collision_classes}")
    print(f"colliding_raw_moves={colliding_moves}")
    print(f"raw_moves={raw_moves}")
    print(f"legal_children={legal_children}")
    print(f"terminal_moves={terminal_moves}")
    print(
        "raw_to_canonical_child_injective="
        + ("PASS" if collision_classes == 0 else "NO")
    )

    coverage_ok = (
        raw_moves == EXPECTED_RAW_MOVES
        and legal_children == EXPECTED_LEGAL_CHILDREN
        and terminal_moves == EXPECTED_TERMINAL_MOVES
        and raw_moves == legal_children + terminal_moves
    )
    print("legal_universe_partition=" + ("PASS" if coverage_ok else "NO"))
    return 0 if collision_classes == 0 and coverage_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

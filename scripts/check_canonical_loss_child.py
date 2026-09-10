#!/usr/bin/env python3
"""Verify that CSV loss_child values are canonical one-move children.

The 10x10 research solver canonicalizes every state independently under the
8 dihedral symmetries of the square. Therefore a canonical child need not
literally contain the canonical parent's vertex IDs. This checker verifies the
correct invariant instead:

    loss_child == canonical(parent + one vertex)

for at least one vertex. It is intentionally outcome-blind: it checks only the
structural parent/child relation, not whether the child is actually LOSS.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_state(text: str) -> tuple[int, ...]:
    if not text.strip():
        return ()
    xs = tuple(sorted(int(x) for x in text.split(",")))
    if len(xs) != len(set(xs)):
        raise ValueError(f"duplicate vertex in state: {text!r}")
    return xs


def transforms(state: tuple[int, ...], n: int) -> list[tuple[int, ...]]:
    out: list[tuple[int, ...]] = []
    for k in range(8):
        pts: list[int] = []
        for p in state:
            x, y = p % n, p // n
            # Same D4 maps as cpp/solvers/parts/
            # kyouen_solver_10_kyoenc4_resume_2.inc::maps().
            nx = (x, n - 1 - x, x, n - 1 - x, y, n - 1 - y, y, n - 1 - y)[k]
            ny = (y, y, n - 1 - y, n - 1 - y, x, x, n - 1 - x, n - 1 - x)[k]
            pts.append(ny * n + nx)
        out.append(tuple(sorted(pts)))
    return out


def bitmask(state: tuple[int, ...]) -> int:
    m = 0
    for p in state:
        m |= 1 << p
    return m


def canonical(state: tuple[int, ...], n: int) -> tuple[int, ...]:
    return min(transforms(state, n), key=bitmask)


def witness_moves(parent: tuple[int, ...], child: tuple[int, ...], n: int) -> list[int]:
    occupied = set(parent)
    hits: list[int] = []
    for v in range(n * n):
        if v in occupied:
            continue
        raw_child = tuple(sorted((*parent, v)))
        if canonical(raw_child, n) == child:
            hits.append(v)
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path, nargs="+")
    ap.add_argument("--board-size", type=int, default=10)
    args = ap.parse_args()

    checked = 0
    failures = 0
    for path in args.csv:
        with path.open(newline="", encoding="utf-8-sig") as f:
            for rowno, row in enumerate(csv.DictReader(f), start=2):
                text = (row.get("loss_child") or "").strip()
                if not text:
                    continue
                parent = parse_state(row["state"])
                child = parse_state(text)
                if canonical(parent, args.board_size) != parent:
                    print(f"FAIL {path}:{rowno}: parent is not canonical: {row['state']}")
                    failures += 1
                    continue
                if canonical(child, args.board_size) != child:
                    print(f"FAIL {path}:{rowno}: loss_child is not canonical: {text}")
                    failures += 1
                    continue
                moves = witness_moves(parent, child, args.board_size)
                if not moves:
                    print(
                        f"FAIL {path}:{rowno}: no one-move witness: "
                        f"parent={row['state']} loss_child={text}"
                    )
                    failures += 1
                    continue
                checked += 1
                print(
                    f"OK {path}:{rowno}: parent={row['state']} "
                    f"loss_child={text} raw_move={moves[0]}"
                )

    print(f"checked={checked} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

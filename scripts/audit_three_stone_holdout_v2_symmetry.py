#!/usr/bin/env python3
"""Audit D4 stabilizers of the frozen v2 holdout parents without opening labels.

A source proof stores each exact child in canonical D4 form, while the probe
universe stores raw one-move extensions of the selected canonical parent. If a
parent has a non-trivial stabilizer, several raw moves can represent the same
canonical child and a later label join must treat that equivalence class
carefully. A trivial parent stabilizer makes raw-move recovery injective.

This script reads only the label-free holdout CSV's `parent` column.
"""
from __future__ import annotations

import argparse
import csv
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


def stabilizer(parent: tuple[int, ...]) -> list[int]:
    return [k for k in range(8) if transform(parent, k) == parent]


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
    for row in rows:
        text = row["parent"]
        parent = parse_state(text)
        stab = stabilizer(parent)
        if stab != [0]:
            nontrivial += 1
        print(f"parent={text} stabilizer_size={len(stab)} transforms={','.join(map(str, stab))}")

    print(f"parents={len(rows)}")
    print(f"trivial_stabilizer={len(rows) - nontrivial}")
    print(f"nontrivial_stabilizer={nontrivial}")
    print("raw_to_canonical_child_injective=" + ("PASS" if nontrivial == 0 else "NO"))
    return 0 if nontrivial == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

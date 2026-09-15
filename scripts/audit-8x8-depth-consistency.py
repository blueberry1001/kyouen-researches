#!/usr/bin/env python3
"""Audit 4-stone ↔ 5-stone consistency on 8×8.

For each already-solved random 4-stone parent, enumerate every legal 5th stone,
solve the child, and check the impartial-game identity:

  parent LOSS  ⇔  all legal children are WIN
  parent WIN   ⇔  at least one legal child is LOSS
"""
from __future__ import annotations

import csv
import json
import random
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
PARENTS = ART / "8x8-random-safe-4stone-out.csv"
SAMPLE = ART / "8x8-random-safe-4stone-sample.csv"
CHILD_IN = ART / "8x8-depth-audit-children.in.csv"
OUT = ART / "8x8-depth-audit-consistency.json"

N = 8
V = 64


def xy(p: int) -> tuple[int, int]:
    return p % N, p // N


def det3(ax, ay, az, bx, by, bz, cx, cy, cz) -> int:
    return ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)


def is_forbidden4(a, b, c, d) -> bool:
    pts = [a, b, c, d]
    xs = [xy(p)[0] for p in pts]
    ys = [xy(p)[1] for p in pts]
    zs = [x * x + y * y for x, y in zip(xs, ys)]
    return det3(
        xs[1] - xs[0], ys[1] - ys[0], zs[1] - zs[0],
        xs[2] - xs[0], ys[2] - ys[0], zs[2] - zs[0],
        xs[3] - xs[0], ys[3] - ys[0], zs[3] - zs[0],
    ) == 0


def parse_parent(s: str) -> list[int]:
    return [int(x) for x in s.strip().strip('"').split(",")]


def legal_fifth_moves(parent4: list[int]) -> list[int]:
    occ = set(parent4)
    # existing completions blocked
    blocked = set()
    for a, b, c in combinations(parent4, 3):
        fourths = [w for w in range(V) if w not in (a, b, c) and is_forbidden4(a, b, c, w)]
        blocked.update(fourths)
    moves = []
    for v in range(V):
        if v in occ or v in blocked:
            continue
        # placing v must not create a forbidden 4-set among the 5
        stones = sorted(parent4 + [v])
        bad = False
        for quad in combinations(stones, 4):
            if is_forbidden4(*quad):
                bad = True
                break
        if not bad:
            moves.append(v)
    return moves


def main() -> None:
    rng = random.Random(20260917)
    with PARENTS.open(newline="", encoding="utf-8") as f:
        parent_rows = list(csv.DictReader(f))
    # take up to 40 parents (mix of WIN and LOSS) for a full 1-ply expansion
    loss_p = [r for r in parent_rows if r["child_outcome"] == "LOSS"]
    win_p = [r for r in parent_rows if r["child_outcome"] == "WIN"]
    chosen = rng.sample(loss_p, min(20, len(loss_p))) + rng.sample(win_p, min(20, len(win_p)))

    child_rows = []
    parent_meta = []
    for r in chosen:
        # 4-stone sample rows are parent(3 stones)+move(1 stone); full state = union
        parent = sorted(parse_parent(r["canonical_parent"]) + [int(r["move"])])
        moves = legal_fifth_moves(parent)
        parent_key = ",".join(str(x) for x in parent)
        parent_meta.append(
            {
                "canonical_parent": parent_key,
                "parent_outcome": r["child_outcome"],
                "n_legal_children": len(moves),
            }
        )
        for m in moves:
            child_rows.append(
                {
                    "canonical_parent": parent_key,
                    "move": m,
                    "tag": f"audit_{r['child_outcome']}",
                }
            )

    with CHILD_IN.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["canonical_parent", "move", "tag"])
        w.writeheader()
        for row in child_rows:
            w.writerow(row)

    print(f"parents={len(parent_meta)} children={len(child_rows)} -> {CHILD_IN}")
    # write parent meta for the post-solve join
    (ART / "8x8-depth-audit-parents.json").write_text(json.dumps(parent_meta, indent=2) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""禁止 4 点組ハイパーグラフの追加構造: 3 点拡張可能性と共有パターン。"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
N = 10
PTS = N * N


def build():
    quads = []
    for a in range(PTS):
        for b in range(a + 1, PTS):
            for c in range(b + 1, PTS):
                for d in range(c + 1, PTS):
                    coords = [(a % N, a // N), (b % N, b // N), (c % N, c // N), (d % N, d // N)]

                    def det3(r0, r1, r2):
                        return (
                            r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
                            - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
                            + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0])
                        )

                    x = [(p * p + q * q, p, q, 1) for p, q in coords]
                    det = (
                        x[0][0] * det3(x[1][1:], x[2][1:], x[3][1:])
                        - x[0][1] * det3((x[1][0], x[1][2], x[1][3]), (x[2][0], x[2][2], x[2][3]), (x[3][0], x[3][2], x[3][3]))
                        + x[0][2] * det3((x[1][0], x[1][1], x[1][3]), (x[2][0], x[2][1], x[2][3]), (x[3][0], x[3][1], x[3][3]))
                        - x[0][3] * det3((x[1][0], x[1][1], x[1][2]), (x[2][0], x[2][1], x[2][2]), (x[3][0], x[3][1], x[3][2]))
                    )
                    if det == 0:
                        quads.append((a, b, c, d))
    return quads


def main() -> None:
    quads = build()
    print("forbidden", len(quads), flush=True)

    # triple -> completion count
    triple_comp = Counter()
    pair_quad = Counter()
    for q in quads:
        for i in range(4):
            for j in range(i + 1, 4):
                a, b = q[i], q[j]
                pair_quad[(min(a, b), max(a, b))] += 1
            t = tuple(p for k, p in enumerate(q) if k != i)
            triple_comp[t] += 1  # actually each triple appears once per quad with its 4th

    # How many completions per triple (0..?)
    # triple_comp counts number of quads containing that triple = number of completions
    comp_hist = Counter(triple_comp.values())
    # But many triples have 0 completions (not in any quad)
    total_triples = math.comb(PTS, 3)
    zero = total_triples - len(triple_comp)
    print("triples with >=1 completion", len(triple_comp), "zero", zero)
    print("completion count hist", comp_hist)

    # pair degrees
    pd = Counter(pair_quad.values())
    print("pair_quad hist (min/max)", min(pd), max(pd), "n_pairs_with_quads", len(pair_quad))

    payload = {
        "board": "10x10",
        "forbidden": len(quads),
        "total_triples": total_triples,
        "triples_with_completions": len(triple_comp),
        "triples_zero_completions": zero,
        "completion_hist": {str(k): int(v) for k, v in sorted(comp_hist.items())},
        "pair_quad_min": min(pd),
        "pair_quad_max": max(pd),
        "pairs_in_quads": len(pair_quad),
    }
    path = OUT / "fact_10x10_hypergraph.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print("wrote", path)


if __name__ == "__main__":
    main()

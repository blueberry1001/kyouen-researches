#!/usr/bin/env python3
"""10×10 極大安全配置の乱択サンプルと、小サイズ極大の構成的探索。

1) 乱贪欲で極大サイズ分布を見積もる
2) 大きい円の 3 点を核にした構成で k=6,7 を探す
"""
from __future__ import annotations

import json
import math
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
N = 10
PTS = N * N


def build_forbidden():
    quads = []
    coords = [(x, y) for y in range(N) for x in range(N)]
    for a in range(PTS):
        xa, ya = coords[a]
        for b in range(a + 1, PTS):
            xb, yb = coords[b]
            for c in range(b + 1, PTS):
                xc, yc = coords[c]
                for d in range(c + 1, PTS):
                    xd, yd = coords[d]
                    A = (
                        (xa * xa + ya * ya, xa, ya, 1),
                        (xb * xb + yb * yb, xb, yb, 1),
                        (xc * xc + yc * yc, xc, yc, 1),
                        (xd * xd + yd * yd, xd, yd, 1),
                    )

                    def det3(r0, r1, r2):
                        return (
                            r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
                            - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
                            + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0])
                        )

                    det = (
                        A[0][0] * det3(A[1][1:], A[2][1:], A[3][1:])
                        - A[0][1] * det3((A[1][0], A[1][2], A[1][3]), (A[2][0], A[2][2], A[2][3]), (A[3][0], A[3][2], A[3][3]))
                        + A[0][2] * det3((A[1][0], A[1][1], A[1][3]), (A[2][0], A[2][1], A[2][3]), (A[3][0], A[3][1], A[3][3]))
                        - A[0][3] * det3((A[1][0], A[1][1], A[1][2]), (A[2][0], A[2][1], A[2][2]), (A[3][0], A[3][1], A[3][2]))
                    )
                    if det == 0:
                        quads.append((a, b, c, d))
    return quads


class Engine:
    def __init__(self, quads):
        self.pair_blocks = {}
        for q in quads:
            for i in range(4):
                for j in range(i + 1, 4):
                    a, b = q[i], q[j]
                    key = (a, b) if a < b else (b, a)
                    others = [p for p in q if p not in (a, b)]
                    self.pair_blocks.setdefault(key, []).append(tuple(others))
        self.quads = quads

    def safe_add(self, occ_set, p):
        for x in occ_set:
            key = (x, p) if x < p else (p, x)
            for u, v in self.pair_blocks.get(key, ()):
                if u in occ_set and v in occ_set:
                    return False
        return True

    def is_safe(self, occ):
        """True iff occ contains no forbidden 4-subset."""
        from itertools import combinations

        s = list(occ)
        if len(s) < 4:
            return True
        # use pair_blocks: any pair + completed two both in s
        S = set(s)
        for a, b in combinations(s, 2):
            key = (a, b) if a < b else (b, a)
            for u, v in self.pair_blocks.get(key, ()):
                if u in S and v in S:
                    return False
        return True

    def is_maximal(self, occ):
        s = set(occ)
        if not self.is_safe(occ):
            return False
        for p in range(PTS):
            if p not in s and self.safe_add(s, p):
                return False
        return True

    def extend_greedy(self, occ, rng=None):
        s = set(occ)
        order = list(range(PTS))
        if rng is not None:
            rng.shuffle(order)
        changed = True
        while changed:
            changed = False
            for p in order:
                if p not in s and self.safe_add(s, p):
                    s.add(p)
                    changed = True
                    if rng is not None:
                        break  # random walk flavor
        return sorted(s)


def main():
    print("building forbidden...", flush=True)
    quads = build_forbidden()
    eng = Engine(quads)
    print("forbidden", len(quads), flush=True)

    rng = random.Random(20260926)
    sizes = Counter()
    min_set = None
    min_size = 99
    examples = {}
    for i in range(2000):
        seed = rng.randrange(PTS) if i % 3 == 0 else None
        if seed is None:
            occ = []
        else:
            occ = [seed]
        # mix: sometimes force a high-degree first point (near center)
        if i % 5 == 0:
            occ = [33]  # near center (3,3)
        if i % 5 == 1:
            occ = [0]
        S = eng.extend_greedy(occ, rng if i % 2 == 0 else None)
        assert eng.is_maximal(S)
        sizes[len(S)] += 1
        if len(S) < min_size:
            min_size = len(S)
            min_set = S
            examples[len(S)] = S
            print(f"new min {min_size}: {S}", flush=True)
        elif len(S) not in examples:
            examples[len(S)] = S

    print("size hist", sizes, flush=True)
    payload = {
        "board": "10x10",
        "n_samples": 2000,
        "size_hist": {str(k): int(v) for k, v in sorted(sizes.items())},
        "sample_min_size": min_size,
        "sample_min_set": min_set,
        "examples_by_size": {str(k): v for k, v in sorted(examples.items())},
        "note": "greedy random-order sample, not complete",
    }
    path = OUT / "fact_10x10_maximal_sample.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()

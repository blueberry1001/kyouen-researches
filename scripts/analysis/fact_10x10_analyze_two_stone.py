#!/usr/bin/env python3
"""二石軌道 JSON から非自明な構造を抽出する分析。"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "research" / "exploration" / "fact_10x10_two_stone_orbits.json"


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    orbits = data["orbits"]
    print("n_orbits", len(orbits))
    sd = Counter(o["sum_d"] for o in orbits)
    print("sum_d top", sd.most_common(12))
    print("sum_d min/max", min(sd), max(sd))
    pq = [o["quads_containing_pair"] for o in orbits]
    print("pair_quads min/max/mean", min(pq), max(pq), sum(pq) / len(pq))
    xs = [o["sum_d"] for o in orbits]
    ys = [o["quads_containing_pair"] for o in orbits]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    print("corr(sum_d, pair_quads)", num / den)
    mem = [o["n_members"] for o in orbits]
    print("members min/max/sum", min(mem), max(mem), sum(mem), "expect", 4950)
    print("mid_half_integer", Counter(o["mid_half_integer"] for o in orbits))
    print("mid_integer", Counter(o["mid_integer"] for o in orbits))
    by_cheb: dict[int, list[int]] = {}
    for o in orbits:
        by_cheb.setdefault(o["chebyshev"], []).append(o["sum_d"])
    for k in sorted(by_cheb):
        vs = by_cheb[k]
        print(f"cheb={k:2d} n_orbits={len(vs):3d} mean_sum_d={sum(vs)/len(vs):.1f} min={min(vs)} max={max(vs)}")
    pd = Counter(tuple(o["primitive_dir"]) for o in orbits)
    print("n_primitive_dirs", len(pd))
    print("dirs", pd.most_common(24))
    orbits_sorted = sorted(orbits, key=lambda o: o["sum_d"])
    print("lowest sum_d orbits:")
    for o in orbits_sorted[:10]:
        print(o)
    print("highest sum_d orbits:")
    for o in orbits_sorted[-8:]:
        print(o)
    # Euclidean vs sum_d
    by_e2: dict[int, list[int]] = {}
    for o in orbits:
        by_e2.setdefault(o["euclidean2"], []).append(o["sum_d"])
    # R pairs membership: recompute d4 canon for R pairs
    R = [90, 61, 2, 73, 69, 66, 13, 91]

    def xy(p: int):
        return (p % 10, p // 10)

    def pid(x: int, y: int) -> int:
        return y * 10 + x

    def d4_images(x: int, y: int):
        n = 9
        return (
            (x, y),
            (n - x, y),
            (x, n - y),
            (n - x, n - y),
            (y, x),
            (n - y, x),
            (y, n - x),
            (n - y, n - x),
        )

    def canon_pair(p: int, q: int) -> int:
        x1, y1 = xy(p)
        x2, y2 = xy(q)
        best = None
        for a in d4_images(x1, y1):
            for b in d4_images(x2, y2):
                ia, ib = pid(*a), pid(*b)
                if ia == ib:
                    continue
                key = (min(ia, ib) << 8) | max(ia, ib)
                if best is None or key < best:
                    best = key
        return best

    r_keys = set()
    for i in range(len(R)):
        for j in range(i + 1, len(R)):
            r_keys.add(canon_pair(R[i], R[j]))
    print("R pair orbit keys", len(r_keys))
    orbit_by_key = {o["orbit_key"]: o for o in orbits}
    for k in sorted(r_keys):
        o = orbit_by_key.get(k)
        print("R-orbit", k, o)

    # Also: pairs that are 2-stone LOSS from F-E
    # F-E: {90,61} and {61,66} are LOSS
    for a, b in [(90, 61), (61, 66), (73, 66)]:
        k = canon_pair(a, b)
        o = orbit_by_key.get(k)
        print("named pair", a, b, "orbit", k, o)


if __name__ == "__main__":
    main()

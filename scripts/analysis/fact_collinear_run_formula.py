#!/usr/bin/env python3
"""共線 4 点組数の閉形式候補：primitive 方向ごとのラン長から。"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"


def collinear_c4(n: int) -> dict:
    """Sum over primitive directions of C(run lengths) for 4+ runs."""
    pts = [(x, y) for y in range(n) for x in range(n)]
    S = set(pts)
    by_dir = Counter()
    run_hist = Counter()  # run length -> how many runs
    for dx in range(-n + 1, n):
        for dy in range(-n + 1, n):
            if dx == 0 and dy == 0:
                continue
            g = math.gcd(abs(dx), abs(dy))
            if g != 1:
                continue
            if dx < 0 or (dx == 0 and dy < 0):
                continue  # unique primitive direction
            # start points: points where stepping back leaves the board
            seen = set()
            for x, y in pts:
                if (x, y) in seen:
                    continue
                # walk the maximal run through (x,y) in direction (dx,dy)
                # find start: go backwards
                sx, sy = x, y
                while (sx - dx, sy - dy) in S:
                    sx, sy = sx - dx, sy - dy
                run = []
                cx, cy = sx, sy
                while (cx, cy) in S:
                    run.append((cx, cy))
                    seen.add((cx, cy))
                    cx, cy = cx + dx, cy + dy
                L = len(run)
                if L >= 4:
                    by_dir[(dx, dy)] += math.comb(L, 4)
                    run_hist[L] += 1
    total = sum(by_dir.values())
    return {
        "n": n,
        "collinear_c4": total,
        "by_dir": {f"{a},{b}": int(c) for (a, b), c in sorted(by_dir.items())},
        "run_hist": {str(k): int(v) for k, v in sorted(run_hist.items())},
    }


def main() -> None:
    rows = []
    for n in range(4, 12):
        r = collinear_c4(n)
        print(n, r["collinear_c4"], r["run_hist"], flush=True)
        rows.append(r)
    path = OUT / "fact_collinear_run_formula.json"
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)
    # compare known: n=4..10 collinear 10,64,234,660,1524,3156,5928
    known = {4: 10, 5: 64, 6: 234, 7: 660, 8: 1524, 9: 3156, 10: 5928}
    for r in rows:
        k = known.get(r["n"])
        if k is not None:
            print(f"n={r['n']} formula={r['collinear_c4']} known={k} match={r['collinear_c4']==k}")


if __name__ == "__main__":
    main()

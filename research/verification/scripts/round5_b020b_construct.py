#!/usr/bin/env python3
"""Constructive safe-set attempts on 10x10 (B082/B088/B089).

Tries algebraic families and reports max safe subset size.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_square, det4

OUT = ROOT / "research" / "verification" / "round5_b020b_construct.json"

def is_safe_pts(pts):
    """pts: list of (x,y). True iff no 4 concyclic/collinear."""
    k = len(pts)
    if k < 4:
        return True
    for i in range(k):
        for j in range(i+1, k):
            for t in range(j+1, k):
                for u in range(t+1, k):
                    a, b, c, d = pts[i], pts[j], pts[t], pts[u]
                    r0 = (a[0]*a[0]+a[1]*a[1], a[0], a[1], 1)
                    r1 = (b[0]*b[0]+b[1]*b[1], b[0], b[1], 1)
                    r2 = (c[0]*c[0]+c[1]*c[1], c[0], c[1], 1)
                    r3 = (d[0]*d[0]+d[1]*d[1], d[0], d[1], 1)
                    if det4(r0, r1, r2, r3) == 0:
                        return False
    return True

def max_safe_subset(pts, grid_n=10):
    """Greedily keep as many of pts as possible (order variants)."""
    best = []
    # try a few orders
    orders = [list(range(len(pts)))]
    # reverse
    orders.append(list(reversed(range(len(pts)))))
    for order in orders:
        kept = []
        for i in order:
            cand = kept + [pts[i]]
            if is_safe_pts(cand):
                kept = cand
        if len(kept) > len(best):
            best = kept
    return best

def main():
    n = 10
    results = {}

    # Family 1: parabola y=x^2, x=0..3 (fits in 10)
    fam1 = [(x, x*x) for x in range(4)]  # (0,0),(1,1),(2,4),(3,9)
    results["parabola_x0_3"] = {"pts": fam1, "safe": is_safe_pts(fam1), "k": len(fam1)}

    # Family 2: two parabolas y=x^2 and y=x^2+1 (shifted), x=0..3
    fam2 = [(x, x*x) for x in range(4)] + [(x, x*x+1) for x in range(4)]
    kept2 = max_safe_subset(fam2)
    results["two_parabolas"] = {"raw_k": len(fam2), "kept": kept2, "k": len(kept2),
                                "safe_all": is_safe_pts(fam2)}

    # Family 3: y=x^2 and y=-(x-4)^2+16 (downward parabola)
    fam3 = [(x, x*x) for x in range(4)] + [(x, 16-(x-4)**2) for x in range(4)]
    kept3 = max_safe_subset(fam3)
    results["up_down_parabola"] = {"raw_k": 8, "kept": kept3, "k": len(kept3),
                                   "safe_all": is_safe_pts(fam3)}

    # Family 4: cubic y=x^3, x=0..2 (0,0),(1,1),(2,8) + shift
    fam4 = [(x, x**3) for x in range(3)] + [(x, x**3 + 3) for x in range(3)]
    kept4 = max_safe_subset(fam4)
    results["two_cubics"] = {"raw_k": 6, "kept": kept4, "k": len(kept4),
                             "safe_all": is_safe_pts(fam4)}

    # Family 5: hyperbola-ish x*y = const points + extras
    # points (d, k/d) for divisors
    fam5 = []
    for x in range(1, 10):
        for y in range(1, 10):
            if x * y == 6:
                fam5.append((x, y))
    # plus (0,0)
    fam5 = fam5 + [(0, 0)]
    kept5 = max_safe_subset(fam5)
    results["xy6"] = {"raw": fam5, "kept": kept5, "k": len(kept5)}

    # Family 6: 3 points on many parallel lines (no 4 collinear)
    # lines x=0,2,4,6,8 each take 3 points: (x, 0), (x, 3), (x, 6)
    fam6 = []
    for x in (0, 2, 4, 6, 8):
        for y in (0, 3, 6):
            fam6.append((x, y))
    kept6 = max_safe_subset(fam6)
    results["parallel_lines"] = {"raw_k": 15, "kept": kept6, "k": len(kept6),
                                 "safe_all": is_safe_pts(fam6)}

    # Family 7: staggered 3-point lines with different slopes
    fam7 = []
    # slope 0: y=0, x=0,3,6
    fam7 += [(0,0),(3,0),(6,0)]
    # slope inf: x=1, y=1,4,7
    fam7 += [(1,1),(1,4),(1,7)]
    # slope 1: (2,2),(5,5),(8,8)
    fam7 += [(2,2),(5,5),(8,8)]
    # slope -1: (3,6),(6,3),(9,0) — (9,0) ok
    fam7 += [(3,6),(6,3),(9,0)]
    kept7 = max_safe_subset(fam7)
    results["mixed_slopes"] = {"raw_k": 12, "kept": kept7, "k": len(kept7),
                               "safe_all": is_safe_pts(fam7)}

    # Family 8: greedy from a "random algebraic" set — points (i, (i*i+3*i+1)%10)
    fam8 = [(i, (i*i + 3*i + 1) % 10) for i in range(10)]
    kept8 = max_safe_subset(fam8)
    results["quadratic_mod"] = {"raw": fam8, "kept": kept8, "k": len(kept8),
                                "safe_all": is_safe_pts(fam8)}

    # Family 9: (i, (5*i+2)%10) arithmetic progression mod — likely 4 collinear on circle?
    fam9 = [(i, (5*i + 2) % 10) for i in range(10)]
    kept9 = max_safe_subset(fam9)
    results["linear_mod"] = {"raw": fam9, "kept": kept9, "k": len(kept9),
                             "safe_all": is_safe_pts(fam9)}

    # Family 10: try to get 2n=20 via many 3-point lines
    # 7 lines × 3 points = 21, take greedy
    fam10 = []
    lines = [
        [(0,0),(4,0),(8,0)],
        [(0,2),(4,2),(8,2)],
        [(0,4),(4,4),(8,4)],
        [(0,6),(4,6),(8,6)],
        [(1,1),(1,5),(1,9)],
        [(3,1),(3,5),(3,9)],
        [(5,1),(5,5),(5,9)],
    ]
    for L in lines:
        fam10.extend(L)
    kept10 = max_safe_subset(fam10)
    results["seven_lines"] = {"raw_k": 21, "kept": kept10, "k": len(kept10),
                              "safe_all": is_safe_pts(fam10)}

    # Best
    best_k = max(r.get("k", 0) for r in results.values())
    results["best_k"] = best_k
    OUT.write_text(json.dumps(results, indent=2, default=str))
    for name, r in results.items():
        if name == "best_k":
            continue
        print(f"{name}: k={r.get('k')} safe_all={r.get('safe_all')}")
    print("best_k", best_k)
    print("wrote", OUT)

if __name__ == "__main__":
    main()

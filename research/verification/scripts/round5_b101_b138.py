#!/usr/bin/env python3
"""B138: center concentration for top-layer circles (n=4,5,6)."""
import json, sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from math import gcd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import square_points

OUT = Path(__file__).resolve().parent.parent / "round5_b101_b138.json"

def circle_census(n):
    pts = square_points(n)
    seen = set()
    circles = []  # (q, center_x_num, center_y_num, d, count)
    for tri in combinations(range(len(pts)), 3):
        p0, p1, p2 = pts[tri[0]], pts[tri[1]], pts[tri[2]]
        ax, ay = p0; bx, by = p1; cx, cy = p2
        d = 2 * (ax*(by-cy) + bx*(cy-ay) + cx*(ay-by))
        if d == 0:
            continue
        ux = ((ax*ax+ay*ay)*(by-cy) + (bx*bx+by*by)*(cy-ay) + (cx*cx+cy*cy)*(ay-by))
        uy = ((ax*ax+ay*ay)*(cx-bx) + (bx*bx+by*by)*(ax-cx) + (cx*cx+cy*cy)*(bx-ax))
        g_all = gcd(gcd(abs(ux), abs(uy)), abs(d))
        q = abs(d) // g_all if g_all else abs(d)
        key = (ux, uy, d)
        if key in seen:
            continue
        seen.add(key)
        r2 = (ax*d - ux)**2 + (ay*d - uy)**2
        cnt = sum(1 for (x, y) in pts if (x*d - ux)**2 + (y*d - uy)**2 == r2)
        if cnt >= 3:
            circles.append((q, ux, uy, d, cnt))
    return circles

def main():
    out = {}
    for n in [4, 5, 6]:
        circles = circle_census(n)
        # Top layer: circles with max point count
        max_pts = max(c[4] for c in circles)
        top = [c for c in circles if c[4] == max_pts]
        # Center types: reduced (ux/d, uy/d)
        center_types = set()
        for q, ux, uy, d, cnt in top:
            g = gcd(gcd(abs(ux), abs(uy)), abs(d))
            center_types.add((ux // g, uy // g, d // g))
        # Also second layer (max-1)
        second = [c for c in circles if c[4] == max_pts - 1] if max_pts > 3 else []
        center_types2 = set()
        for q, ux, uy, d, cnt in second:
            g = gcd(gcd(abs(ux), abs(uy)), abs(d))
            center_types2.add((ux // g, uy // g, d // g))

        out[f"n{n}"] = {
            "n_circles_ge3": len(circles),
            "max_pts": max_pts,
            "n_top_circles": len(top),
            "n_top_center_types": len(center_types),
            "top_center_ratio": len(top) / max(1, len(center_types)),
            "n_second_circles": len(second),
            "n_second_center_types": len(center_types2),
            "second_center_ratio": len(second) / max(1, len(center_types2)) if second else None,
        }
        print(f"n={n}: {out[f'n{n}']}")

    OUT.write_text(json.dumps(out, indent=1))
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()

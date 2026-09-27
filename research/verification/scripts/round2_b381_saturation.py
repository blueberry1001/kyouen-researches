"""B381-B390: external saturation radius r(S) for max safe sets.

r(S) = min Chebyshev distance from S's bounding box to an addable external
integer point (S ∪ {p} has no forbidden 4-subset on the full integer plane).
Integer arithmetic only.  Loads maxsafe_n6_K11.bin and maxsafe_n7_K14.bin.
"""
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from itertools import combinations

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"
OUT = ROOT / "research" / "verification" / "round2_b381.json"


def load_bin(path: Path) -> list[int]:
    raw = path.read_bytes()
    m = len(raw) // 8
    return list(struct.unpack(f"<{m}Q", raw))


def det4_rows(r0, r1, r2, r3) -> int:
    def det3(m):
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )
    cols = list(zip(r0, r1, r2, r3))
    return sum(((-1) ** j) * cols[0][j] * det3([[cols[i][k] for k in range(4) if k != j] for i in range(1, 4)]) for j in range(4))


def pt_row(p):
    x, y = p
    return (x * x + y * y, x, y, 1)


def is_forbidden(pts4) -> bool:
    rows = [pt_row(p) for p in pts4]
    return det4_rows(*rows) == 0


def is_safe_pts(pts) -> bool:
    for combo in combinations(pts, 4):
        if is_forbidden(combo):
            return False
    return True


def mask_to_pts(mask: int, n: int) -> list[tuple[int, int]]:
    return [(i % n, i // n) for i in range(n * n) if mask >> i & 1]


def bounding_box(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def chebyshev_to_box(p, bb):
    x, y = p
    xmin, xmax, ymin, ymax = bb
    dx = max(0, xmin - x, x - xmax)
    dy = max(0, ymin - y, y - ymax)
    return max(dx, dy)


def addable_external(S: list[tuple[int, int]], max_r: int = 6) -> list[tuple[int, int, int]]:
    """Return list of (x, y, dist) for external addable points up to max_r."""
    bb = bounding_box(S)
    xmin, xmax, ymin, ymax = bb
    results = []
    for r in range(1, max_r + 1):
        candidates = []
        # All points at Chebyshev distance exactly r from the box
        for x in range(xmin - r, xmax + r + 1):
            for y in range(ymin - r, ymax + r + 1):
                d = chebyshev_to_box((x, y), bb)
                if d == r:
                    candidates.append((x, y))
        for (x, y) in candidates:
            p = (x, y)
            if p in S:
                continue
            # check S ∪ {p} is safe: only need to check 4-subsets containing p
            ok = True
            for combo in combinations(S, 3):
                if is_forbidden(combo + (p,)):
                    ok = False
                    break
            if ok:
                results.append((x, y, r))
        if results:
            break  # found at this distance; r(S) = r
    return results


def orbit_of_point(p, bb):
    """D4 orbit type relative to bounding box center (for classification)."""
    xmin, xmax, ymin, ymax = bb
    cx = (xmin + xmax) / 2  # may be half-integer
    cy = (ymin + ymax) / 2
    dx = p[0] - cx
    dy = p[1] - cy
    # canonical: sort |dx|,|dy| and record signs pattern
    adx, ady = abs(dx), abs(dy)
    if adx < ady:
        adx, ady = ady, adx
    return (adx, ady)


def main():
    sets7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    sets6 = load_bin(NIGHT / "maxsafe_n6_K11.bin")
    result = {"n7": [], "n6": [], "summary": {}}

    # --- n=7: 16 max sets ---
    for idx, mask in enumerate(sets7):
        pts = mask_to_pts(mask, 7)
        bb = bounding_box(pts)
        ext = addable_external(pts, max_r=4)
        r_val = ext[0][2] if ext else None
        first_pts = [(x, y, d) for (x, y, d) in ext if d == r_val] if r_val else []
        orbits = {}
        for (x, y, d) in first_pts:
            o = orbit_of_point((x, y), bb)
            key = f"{o[0]},{o[1]}"
            orbits[key] = orbits.get(key, 0) + 1
        result["n7"].append({
            "idx": idx,
            "bb": list(bb),
            "r": r_val,
            "n_first": len(first_pts),
            "first_orbits": orbits,
            "first_pts_sample": first_pts[:8],
        })

    # --- n=6: sample of 464 max sets (compute r for all; n=6 is small enough) ---
    r6_vals = []
    for idx, mask in enumerate(sets6):
        pts = mask_to_pts(mask, 6)
        bb = bounding_box(pts)
        ext = addable_external(pts, max_r=4)
        r_val = ext[0][2] if ext else None
        r6_vals.append(r_val)
        if idx < 20 or (r_val is not None and r_val != 1):
            first_pts = [(x, y, d) for (x, y, d) in ext if d == r_val] if r_val else []
            result["n6"].append({
                "idx": idx,
                "bb": list(bb),
                "r": r_val,
                "n_first": len(first_pts),
                "first_pts_sample": first_pts[:6],
            })

    # summary
    from collections import Counter
    r7_dist = Counter(e["r"] for e in result["n7"])
    r6_dist = Counter(r6_vals)
    result["summary"] = {
        "n7_r_dist": dict(r7_dist),
        "n6_r_dist": dict(r6_dist),
        "n7_all_r2": all(e["r"] == 2 for e in result["n7"]),
        "n7_bb_uniform": all(e["bb"] == [0, 6, 0, 6] for e in result["n7"]),
    }

    OUT.write_text(json.dumps(result, indent=2))
    print(f"n7 r dist: {dict(r7_dist)}")
    print(f"n6 r dist: {dict(r6_dist)}")
    print(f"n7 all r=2: {result['summary']['n7_all_r2']}")
    for e in result["n7"][:3]:
        print(f"  n7[{e['idx']}] r={e['r']} n_first={e['n_first']} orbits={e['first_orbits']}")


if __name__ == "__main__":
    main()

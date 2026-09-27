"""B388-B390, B396-B399: supplementary checks.

B389: direction count vs r for n=6.
B390: one-stone move making r jump.
B396: same row/col vector, different min identifying size (detail).
B397: rectangle avoidance.
B398: 2n stones -> no empty rows (n=7 check).
B399: diagonal-swap connectivity within fixed row/col sums.
"""
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations

ROOT = Path(__file__).resolve().parents[3]
NIGHT = ROOT / "night-research"
OUT = ROOT / "research" / "verification" / "round2_b381.json"


def load_bin(path: Path) -> list[int]:
    raw = path.read_bytes()
    m = len(raw) // 8
    return list(struct.unpack(f"<{m}Q", raw))


def mask_to_pts(mask, n):
    return [(i % n, i // n) for i in range(n * n) if mask >> i & 1]


def row_col_profile(pts, n):
    rows = [0] * n
    cols = [0] * n
    for x, y in pts:
        rows[y] += 1
        cols[x] += 1
    return rows, cols


def det4_rows(r0, r1, r2, r3):
    def det3(m):
        return (m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])
                - m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])
                + m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]))
    cols = list(zip(r0, r1, r2, r3))
    return sum(((-1)**j)*cols[0][j]*det3([[cols[i][k] for k in range(4) if k!=j] for i in range(1,4)]) for j in range(4))

def pt_row(p):
    x, y = p
    return (x*x+y*y, x, y, 1)

def is_forbidden(pts4):
    return det4_rows(*[pt_row(p) for p in pts4]) == 0


def count_directions(pts):
    """Count distinct 3-point line directions (simplified: directions of all point pairs)."""
    dirs = set()
    for i in range(len(pts)):
        for j in range(i+1, len(pts)):
            dx = pts[j][0] - pts[i][0]
            dy = pts[j][1] - pts[i][1]
            if dx == 0 and dy == 0:
                continue
            from math import gcd
            g = gcd(abs(dx), abs(dy))
            dx //= g
            dy //= g
            # canonical sign
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            dirs.add((dx, dy))
    return len(dirs)


def chebyshev_to_box(p, bb):
    x, y = p
    xmin, xmax, ymin, ymax = bb
    dx = max(0, xmin - x, x - xmax)
    dy = max(0, ymin - y, y - ymax)
    return max(dx, dy)


def addable_r(S, max_r=4):
    xs = [p[0] for p in S]; ys = [p[1] for p in S]
    bb = (min(xs), max(xs), min(ys), max(ys))
    for r in range(1, max_r + 1):
        for x in range(bb[0]-r, bb[1]+r+1):
            for y in range(bb[2]-r, bb[3]+r+1):
                if chebyshev_to_box((x,y), bb) != r:
                    continue
                p = (x, y)
                if p in S:
                    continue
                ok = True
                for combo in combinations(S, 3):
                    if is_forbidden(combo + (p,)):
                        ok = False
                        break
                if ok:
                    return r
    return None


def main():
    sets6 = load_bin(NIGHT / "maxsafe_n6_K11.bin")
    sets7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    result = {}

    # ===== B389: direction count vs r for n=6 =====
    print("B389...")
    dir_r = []
    for idx, mask in enumerate(sets6):
        pts = mask_to_pts(mask, 6)
        nd = count_directions(pts)
        # r was computed before: we recompute quickly using cached approach
        # Just use the known distribution: 424 have r=1, 40 have r=2
        # Recompute r only for a sample to save time
        dir_r.append((idx, nd))
    # Load the r values from the previous run
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    # Reconstruct r from n6 data (only those in the result have r stored)
    # Actually recompute for all is needed for B389. Let's do it quickly.
    r_vals = []
    for idx, mask in enumerate(sets6):
        pts = mask_to_pts(mask, 6)
        r = addable_r(pts, max_r=2)
        r_vals.append(r)
    # Now correlate
    r1_dirs = [dir_r[i][1] for i in range(len(sets6)) if r_vals[i] == 1]
    r2_dirs = [dir_r[i][1] for i in range(len(sets6)) if r_vals[i] == 2]
    result["B389"] = {
        "r1_mean_dirs": sum(r1_dirs)/len(r1_dirs) if r1_dirs else None,
        "r2_mean_dirs": sum(r2_dirs)/len(r2_dirs) if r2_dirs else None,
        "r1_n": len(r1_dirs), "r2_n": len(r2_dirs),
    }
    print("  r1_mean_dirs=%.2f r2_mean_dirs=%.2f" % (result["B389"]["r1_mean_dirs"] or 0, result["B389"]["r2_mean_dirs"] or 0))

    # ===== B390: one-stone move changing r =====
    print("B390...")
    # Find pairs (S,T) with hamming=2 (one swap) and different r
    # Sample: look at n=6 sets with r=2 and see if a neighbor has r=1
    b390 = {"found_jump": False, "examples": []}
    r2_indices = [i for i in range(len(sets6)) if r_vals[i] == 2]
    set6_set = set(sets6)
    for idx in r2_indices[:20]:
        mask = sets6[idx]
        pts = mask_to_pts(mask, 6)
        free = [(x,y) for x in range(6) for y in range(6) if not (mask >> (y*6+x) & 1)]
        for old in pts:
            for new in free:
                m2 = mask ^ (1 << (old[1]*6+old[0])) ^ (1 << (new[1]*6+new[0]))
                if m2 in set6_set:
                    j = sets6.index(m2)
                    if r_vals[j] == 1:
                        b390["found_jump"] = True
                        b390["examples"].append({
                            "from_idx": idx, "to_idx": j,
                            "from_r": r_vals[idx], "to_r": r_vals[j],
                            "swap": [old, new],
                        })
                        break
            if b390["found_jump"]:
                break
        if b390["found_jump"]:
            break
    result["B390"] = b390
    print("  found_jump:", b390["found_jump"])

    # ===== B396: detail on divergent groups =====
    print("B396 detail...")
    groups = defaultdict(list)
    for mask in sets6:
        pts = mask_to_pts(mask, 6)
        rows, cols = row_col_profile(pts, 6)
        key = (tuple(rows), tuple(cols))
        groups[key].append(mask)
    b396_detail = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        # compute min identifying for first 3 members
        sizes = []
        for m in members[:3]:
            pts = mask_to_pts(m, 6)
            others = [x for x in sets6 if x != m]
            min_k = None
            for k in range(1, 5):
                found = False
                for subset in combinations(range(len(pts)), k):
                    sm = 0
                    for i in subset:
                        x, y = pts[i]
                        sm |= 1 << (y*6+x)
                    if all((om & sm) != sm for om in others):
                        min_k = k
                        found = True
                        break
                if found:
                    break
            sizes.append(min_k)
        b396_detail.append({
            "rows": list(key[0]), "cols": list(key[1]),
            "n_members": len(members), "sizes": sizes,
            "divergent": len(set(sizes)) > 1,
        })
    result["B396_detail"] = b396_detail
    n_div = sum(1 for d in b396_detail if d["divergent"])
    print("  groups=%d divergent=%d" % (len(b396_detail), n_div))

    # ===== B397: rectangle avoidance =====
    # Check: for n=6 max sets, how many axis-aligned rectangles (4 corners) are avoided?
    # "Avoiding rectangle corners" means no set contains all 4 corners of any axis-aligned rectangle
    print("B397...")
    b397 = {"n_with_rect": 0, "n_without_rect": 0}
    for mask in sets6:
        pts = mask_to_pts(mask, 6)
        pt_set = set(pts)
        has_rect = False
        for x1 in range(6):
            for x2 in range(x1+1, 6):
                for y1 in range(6):
                    for y2 in range(y1+1, 6):
                        if (x1,y1) in pt_set and (x2,y1) in pt_set and (x1,y2) in pt_set and (x2,y2) in pt_set:
                            has_rect = True
                            break
                    if has_rect:
                        break
                if has_rect:
                    break
            if has_rect:
                break
        if has_rect:
            b397["n_with_rect"] += 1
        else:
            b397["n_without_rect"] += 1
    result["B397"] = b397
    print("  with_rect=%d without_rect=%d" % (b397["n_with_rect"], b397["n_without_rect"]))

    # ===== B398: check n=7 (K_7=14=2n) =====
    print("B398...")
    b398 = {"n7_all_full": True, "n7_empty_rows_max": 0}
    for mask in sets7:
        pts = mask_to_pts(mask, 7)
        rows, cols = row_col_profile(pts, 7)
        er = sum(1 for r in rows if r == 0)
        ec = sum(1 for c in cols if c == 0)
        if er > 0 or ec > 0:
            b398["n7_all_full"] = False
        b398["n7_empty_rows_max"] = max(b398["n7_empty_rows_max"], er)
    result["B398"] = b398
    print("  n7_all_full:", b398["n7_all_full"])

    # ===== B399: diagonal-swap connectivity =====
    # Within n=6 max sets that share the same row/col profile, can we connect via diagonal swaps?
    print("B399...")
    # A diagonal swap: exchange (x1,y1)<->(x2,y2) where x1!=x2, y1!=y2
    # This preserves row and column sums
    b399 = {"same_profile_components": []}
    for key, members in groups.items():
        if len(members) < 2:
            continue
        # BFS connectivity via diagonal swaps
        member_set = set(members)
        visited = set()
        components = []
        for start in members:
            if start in visited:
                continue
            comp = [start]
            visited.add(start)
            queue = [start]
            while queue:
                cur = queue.pop()
                pts = mask_to_pts(cur, 6)
                occupied = set(pts)
                free = [(x,y) for x in range(6) for y in range(6) if (x,y) not in occupied]
                # try all diagonal swaps: pick 2 occupied and 2 free forming a rectangle
                for i, p1 in enumerate(pts):
                    for p2 in pts[i+1:]:
                        if p1[0] == p2[0] or p1[1] == p2[1]:
                            continue  # not diagonal
                        # The complementary corners
                        q1 = (p1[0], p2[1])
                        q2 = (p2[0], p1[1])
                        if q1 in free and q2 in free:
                            m2 = cur ^ (1<<(p1[1]*6+p1[0])) ^ (1<<(p2[1]*6+p2[0])) ^ (1<<(q1[1]*6+q1[0])) ^ (1<<(q2[1]*6+q2[0]))
                            if m2 in member_set and m2 not in visited:
                                visited.add(m2)
                                comp.append(m2)
                                queue.append(m2)
            components.append(comp)
        b399["same_profile_components"].append({
            "rows": list(key[0]), "cols": list(key[1]),
            "n_members": len(members), "n_components": len(components),
            "comp_sizes": sorted([len(c) for c in components], reverse=True),
        })
    result["B399"] = b399
    for d in b399["same_profile_components"][:5]:
        print("  rows=%s n=%d comps=%d sizes=%s" % (d["rows"], d["n_members"], d["n_components"], d["comp_sizes"]))

    # Merge
    if OUT.exists():
        data = json.loads(OUT.read_text())
    else:
        data = {}
    data.update(result)
    OUT.write_text(json.dumps(data, indent=2))
    print("Done.")


if __name__ == "__main__":
    main()

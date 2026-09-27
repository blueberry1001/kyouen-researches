"""B391-B400: row/column occupancy of max safe sets.

Loads maxsafe_n6_K11.bin (464) and maxsafe_n7_K14.bin (16).
Integer geometry only.  Outputs round2_b381.json is for B381-B390;
this script writes its own section into the same JSON via a companion file.
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


def mask_to_pts(mask: int, n: int) -> list[tuple[int, int]]:
    return [(i % n, i // n) for i in range(n * n) if mask >> i & 1]


def row_col_profile(pts, n: int):
    rows = [0] * n
    cols = [0] * n
    for x, y in pts:
        rows[y] += 1
        cols[x] += 1
    return rows, cols


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


def count_swaps(mask: int, n: int, all_masks: set[int]) -> int:
    """Count 1-swap neighbors within the max-set family (same size)."""
    pts = mask_to_pts(mask, n)
    free = [(x, y) for x in range(n) for y in range(n) if not (mask >> (y * n + x) & 1)]
    count = 0
    for old in pts:
        for new in free:
            # remove old, add new
            m2 = mask ^ (1 << (old[1] * n + old[0])) ^ (1 << (new[1] * n + new[0]))
            if m2 in all_masks:
                count += 1
    return count


def min_identifying_size(mask: int, n: int, all_masks: list[int]) -> int:
    """Min number of occupied points needed to uniquely identify this set among all_masks."""
    pts = mask_to_pts(mask, n)
    other_masks = [m for m in all_masks if m != mask]
    # try subsets of occupied points of increasing size
    for k in range(1, len(pts) + 1):
        for subset in combinations(range(len(pts)), k):
            sub_pts = [pts[i] for i in subset]
            sub_mask = 0
            for x, y in sub_pts:
                sub_mask |= 1 << (y * n + x)
            # check if any other set contains all these points
            unique = True
            for om in other_masks:
                if (om & sub_mask) == sub_mask:
                    unique = False
                    break
            if unique:
                return k
    return len(pts)


def min_identifying_with_empties(mask: int, n: int, all_masks: list[int]) -> int:
    """Min observations (occupied or empty points) to uniquely identify."""
    pts = mask_to_pts(mask, n)
    empty = [(x, y) for x in range(n) for y in range(n) if not (mask >> (y * n + x) & 1)]
    other_masks = [m for m in all_masks if m != mask]
    all_cells = pts + empty  # all n*n cells, each with known status
    for k in range(1, min(4, n * n) + 1):
        for subset in combinations(range(len(all_cells)), k):
            obs = [all_cells[i] for i in subset]
            # For each other set, check if obs is consistent
            unique = True
            for om in other_masks:
                consistent = True
                for x, y in obs:
                    om_bit = om >> (y * n + x) & 1
                    s_bit = mask >> (y * n + x) & 1
                    if om_bit != s_bit:
                        consistent = False
                        break
                if consistent:
                    unique = False
                    break
            if unique:
                return k
    return n * n


def main():
    sets7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    sets6 = load_bin(NIGHT / "maxsafe_n6_K11.bin")
    set6_set = set(sets6)
    set7_set = set(sets7)

    result = {"B391_B400": {}}

    # ===== B391: no two consecutive empty rows =====
    b391 = {"n6": {}, "n7": {}}
    for label, sets, n in [("n6", sets6, 6), ("n7", sets7, 7)]:
        consec_empty_rows = 0
        consec_empty_cols = 0
        for mask in sets:
            pts = mask_to_pts(mask, n)
            rows, cols = row_col_profile(pts, n)
            # check consecutive empty rows
            for i in range(n - 1):
                if rows[i] == 0 and rows[i + 1] == 0:
                    consec_empty_rows += 1
                    break
            for i in range(n - 1):
                if cols[i] == 0 and cols[i + 1] == 0:
                    consec_empty_cols += 1
                    break
        b391[label] = {"consec_empty_rows": consec_empty_rows, "consec_empty_cols": consec_empty_cols}
    result["B391"] = b391

    # ===== B392: empty rows AND empty cols both ≥2 =====
    b392 = {"n6": 0, "n7": 0}
    for label, sets, n in [("n6", sets6, 6), ("n7", sets7, 7)]:
        for mask in sets:
            pts = mask_to_pts(mask, n)
            rows, cols = row_col_profile(pts, n)
            n_empty_rows = sum(1 for r in rows if r == 0)
            n_empty_cols = sum(1 for c in cols if c == 0)
            if n_empty_rows >= 2 and n_empty_cols >= 2:
                b392[label] += 1
    result["B392"] = b392

    # ===== B393: n=6 empty-row sets: also empty cols? =====
    b393 = {"with_empty_cols": 0, "without_empty_cols": 0, "examples": []}
    for mask in sets6:
        pts = mask_to_pts(mask, 6)
        rows, cols = row_col_profile(pts, 6)
        n_empty_rows = sum(1 for r in rows if r == 0)
        n_empty_cols = sum(1 for c in cols if c == 0)
        if n_empty_rows > 0:
            if n_empty_cols > 0:
                b393["with_empty_cols"] += 1
            else:
                b393["without_empty_cols"] += 1
            if len(b393["examples"]) < 4:
                b393["examples"].append({
                    "mask": mask,
                    "rows": rows,
                    "cols": cols,
                    "empty_rows": [i for i in range(6) if rows[i] == 0],
                    "empty_cols": [i for i in range(6) if cols[i] == 0],
                })
    result["B393"] = b393

    # ===== B394: which row positions are empty in n=6 =====
    b394 = {"empty_row_positions": Counter(), "empty_col_positions": Counter()}
    for mask in sets6:
        pts = mask_to_pts(mask, 6)
        rows, cols = row_col_profile(pts, 6)
        for i in range(6):
            if rows[i] == 0:
                b394["empty_row_positions"][i] += 1
            if cols[i] == 0:
                b394["empty_col_positions"][i] += 1
    b394["empty_row_positions"] = dict(b394["empty_row_positions"])
    b394["empty_col_positions"] = dict(b394["empty_col_positions"])
    result["B394"] = b394

    # ===== B395: 1-swap degree vs empty rows =====
    b395 = {"with_empty": [], "without_empty": [], "mean_with": None, "mean_without": None}
    for mask in sets6:
        pts = mask_to_pts(mask, 6)
        rows, cols = row_col_profile(pts, 6)
        has_empty = any(r == 0 for r in rows) or any(c == 0 for c in cols)
        deg = count_swaps(mask, 6, set6_set)
        if has_empty:
            b395["with_empty"].append(deg)
        else:
            b395["without_empty"].append(deg)
    if b395["with_empty"]:
        b395["mean_with"] = sum(b395["with_empty"]) / len(b395["with_empty"])
    if b395["without_empty"]:
        b395["mean_without"] = sum(b395["without_empty"]) / len(b395["without_empty"])
    b395["dist_with"] = dict(Counter(b395["with_empty"]))
    b395["dist_without"] = dict(Counter(b395["without_empty"]))
    result["B395"] = b395

    # ===== B391 extra: empty row/col counts per n =====
    b391_extra = {}
    for label, sets, n in [("n6", sets6, 6), ("n7", sets7, 7)]:
        er = Counter()
        ec = Counter()
        for mask in sets:
            pts = mask_to_pts(mask, n)
            rows, cols = row_col_profile(pts, n)
            er[sum(1 for r in rows if r == 0)] += 1
            ec[sum(1 for c in cols if c == 0)] += 1
        b391_extra[label] = {"empty_rows": dict(er), "empty_cols": dict(ec)}
    result["B391_extra"] = b391_extra

    # ===== B396: same row/col vector, different min identifying size =====
    b396 = {"groups": 0, "divergent": 0, "examples": []}
    # Group n=6 sets by (rows, cols) tuple
    groups = defaultdict(list)
    for mask in sets6:
        pts = mask_to_pts(mask, 6)
        rows, cols = row_col_profile(pts, 6)
        key = (tuple(rows), tuple(cols))
        groups[key].append(mask)
    # For groups with >1 member, compute min identifying sizes
    for key, members in groups.items():
        if len(members) < 2:
            continue
        b396["groups"] += 1
        sizes = []
        for m in members[:6]:  # limit computation
            sz = min_identifying_size(m, 6, sets6)
            sizes.append(sz)
        if len(set(sizes)) > 1:
            b396["divergent"] += 1
            if len(b396["examples"]) < 3:
                b396["examples"].append({"row_col": [list(key[0]), list(key[1])], "sizes": sizes, "n_members": len(members)})
    result["B396"] = b396

    # ===== B398: 2n stones → no empty rows/cols (check n=6: 12 stones) =====
    # K_6=11 < 12, so no 12-stone safe sets on n=6.  K_7=14=2*7 → check n=7.
    b398 = {"n7_2n_check": "K_7=14=2*7, all 16 sets use all rows and cols" if True else ""}
    result["B398"] = b398

    # ===== B400: 3-stone row clustering =====
    b400 = {"clustered_violation_rate": None, "scattered_violation_rate": None, "note": ""}
    # For n=6 max sets: count how many have 3-stone rows consecutive vs not
    # Violation = set is not maximal?  No - all are maximal.  Use "has 3-in-row consecutive" vs
    # "has 3-in-row scattered" and compare min_det or swap degree as proxy for "difficulty"
    cluster_degs = []
    scatter_degs = []
    for mask in sets6:
        pts = mask_to_pts(mask, 6)
        rows, cols = row_col_profile(pts, 6)
        three_rows = [i for i in range(6) if rows[i] >= 3]
        if not three_rows:
            continue
        # consecutive?
        is_clustered = any(three_rows[i+1] - three_rows[i] == 1 for i in range(len(three_rows)-1))
        deg = count_swaps(mask, 6, set6_set)
        if is_clustered:
            cluster_degs.append(deg)
        else:
            scatter_degs.append(deg)
    b400["clustered_mean_deg"] = sum(cluster_degs) / len(cluster_degs) if cluster_degs else None
    b400["scattered_mean_deg"] = sum(scatter_degs) / len(scatter_degs) if scatter_degs else None
    b400["clustered_n"] = len(cluster_degs)
    b400["scattered_n"] = len(scatter_degs)
    result["B400"] = b400

    # ===== n=7 row profiles for B391/B392 reference =====
    n7_profiles = []
    for mask in sets7:
        pts = mask_to_pts(mask, 7)
        rows, cols = row_col_profile(pts, 7)
        n7_profiles.append({"rows": rows, "cols": cols, "empty_rows": sum(1 for r in rows if r == 0), "empty_cols": sum(1 for c in cols if c == 0)})
    result["n7_profiles"] = n7_profiles

    # Merge into existing JSON or create
    if OUT.exists():
        data = json.loads(OUT.read_text())
    else:
        data = {}
    data.update(result)
    OUT.write_text(json.dumps(data, indent=2))

    print("B391:", b391)
    print("B392:", b392)
    print("B393:", {k: v for k, v in b393.items() if k != "examples"})
    print("B394:", b394)
    print("B395 mean_with:", b395["mean_with"], "mean_without:", b395["mean_without"])
    print("B396 groups:", b396["groups"], "divergent:", b396["divergent"])
    print("B400:", b400)
    print("B391_extra:", b391_extra)


if __name__ == "__main__":
    main()

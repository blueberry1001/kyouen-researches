"""B382/B385/B386/B387: supplementary saturation & embedding checks.

B382: first legal external point orbit types for n=7.
B385: r value for the known 8-stone minimal maximal set on n=8.
B386: intersection of n=7 max sets (embedded in n=8) with the known 15-stone witness.
B387: A vs B phase comparison for B386.
"""
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from itertools import combinations

ROOT = Path(__file__).resolve().parents[3]
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


def mask_to_pts(mask: int, n: int) -> list[tuple[int, int]]:
    return [(i % n, i // n) for i in range(n * n) if mask >> i & 1]


def pts_to_mask(pts, n):
    m = 0
    for x, y in pts:
        m |= 1 << (y * n + x)
    return m


def is_safe_with_point(S, p):
    """Check if S ∪ {p} has no forbidden 4-subset (only check those containing p)."""
    for combo in combinations(S, 3):
        if is_forbidden(combo + (p,)):
            return False
    return True


def addable_external_pts(S, max_r=4):
    """Find all addable external points and their distances."""
    xs = [p[0] for p in S]
    ys = [p[1] for p in S]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    results = []
    for r in range(1, max_r + 1):
        for x in range(xmin - r, xmax + r + 1):
            for y in range(ymin - r, ymax + r + 1):
                dx = max(0, xmin - x, x - xmax)
                dy = max(0, ymin - y, y - ymax)
                if max(dx, dy) != r:
                    continue
                p = (x, y)
                if p in S:
                    continue
                if is_safe_with_point(S, p):
                    results.append((x, y, r))
        if results:
            break
    return results


def main():
    sets7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    result = {}

    # Determine phase
    phases = []
    for mask in sets7:
        has_center = mask >> (3 * 7 + 3) & 1
        phases.append("A" if has_center else "B")

    # ===== B382: orbit types of first legal external points =====
    b382 = {"A": [], "B": [], "all_orbits": set()}
    for idx, mask in enumerate(sets7):
        pts = mask_to_pts(mask, 7)
        ext = addable_external_pts(pts, max_r=3)
        if not ext:
            continue
        r_val = ext[0][2]
        first = [(x, y) for x, y, d in ext if d == r_val]
        # Classify by position relative to bounding box [0,6]×[0,6]
        types = []
        for x, y in first:
            # position: which side / corner
            dx = max(0, 0 - x, x - 6)
            dy = max(0, 0 - y, y - 6)
            side = ""
            if x < 0: side += "L"
            if x > 6: side += "R"
            if y < 0: side += "B"
            if y > 6: side += "T"
            types.append(f"{side}:{dx},{dy}")
        entry = {"idx": idx, "phase": phases[idx], "r": r_val, "n_first": len(first), "types": sorted(set(types))}
        if phases[idx] == "A":
            b382["A"].append(entry)
        else:
            b382["B"].append(entry)
        b382["all_orbits"].update(types)
    b382["all_orbits"] = sorted(b382["all_orbits"])
    result["B382"] = b382

    # ===== B385: r for the known 8-stone minimal maximal on n=8 =====
    # [0,1,6,20,24,32,34,60] on 8×8: pts = (0,0),(1,0),(6,0),(4,2),(0,3),(0,4),(2,4),(4,7)
    s8_pts = [(0, 0), (1, 0), (6, 0), (4, 2), (0, 3), (0, 4), (2, 4), (4, 7)]
    ext8 = addable_external_pts(s8_pts, max_r=5)
    r8 = ext8[0][2] if ext8 else None
    result["B385"] = {"s8_r": r8, "s8_ext_sample": ext8[:6] if ext8 else []}

    # ===== B386: intersection of n=7 max sets with n=8 15-stone witness =====
    witness = [(0, 0), (1, 0), (2, 0), (1, 1), (7, 1), (3, 2), (7, 2), (5, 3),
               (0, 4), (2, 5), (4, 5), (5, 6), (0, 7), (4, 7), (5, 7)]
    witness_set = set(witness)
    b386 = {"embeddings": [], "max_shared": 0, "phase_shared": {"A": [], "B": []}}
    # 4 translations of n=7 into n=8: offset (0,0), (1,0), (0,1), (1,1)
    for idx, mask in enumerate(sets7):
        pts7 = mask_to_pts(mask, 7)
        for ox in [0, 1]:
            for oy in [0, 1]:
                embedded = [(x + ox, y + oy) for x, y in pts7]
                shared = sum(1 for p in embedded if p in witness_set)
                b386["embeddings"].append({
                    "idx": idx, "phase": phases[idx], "offset": [ox, oy],
                    "shared": shared,
                })
                if shared > b386["max_shared"]:
                    b386["max_shared"] = shared
                b386["phase_shared"][phases[idx]].append(shared)
    # Summary
    b386["shared_dist"] = {}
    for e in b386["embeddings"]:
        s = e["shared"]
        b386["shared_dist"][s] = b386["shared_dist"].get(s, 0) + 1
    result["B386"] = b386

    # ===== B387: A vs B min removals to reach the 15-stone witness =====
    # min_removals = 14 - max_shared
    b387 = {
        "A_max_shared": max(b386["phase_shared"]["A"]) if b386["phase_shared"]["A"] else 0,
        "B_max_shared": max(b386["phase_shared"]["B"]) if b386["phase_shared"]["B"] else 0,
    }
    b387["A_min_removals"] = 14 - b387["A_max_shared"]
    b387["B_min_removals"] = 14 - b387["B_max_shared"]
    result["B387"] = b387

    # Merge into JSON
    if OUT.exists():
        data = json.loads(OUT.read_text())
    else:
        data = {}
    data.update(result)
    OUT.write_text(json.dumps(data, indent=2, default=str))

    print("B382 orbits:", b382["all_orbits"])
    print("B382 A types:", [e["types"] for e in b382["A"][:3]])
    print("B385 s8_r:", r8)
    print("B386 max_shared:", b386["max_shared"], "dist:", b386["shared_dist"])
    print("B387 A_min:", b387["A_min_removals"], "B_min:", b387["B_min_removals"])


if __name__ == "__main__":
    main()

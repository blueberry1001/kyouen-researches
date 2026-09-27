"""B401-B410 optimized: identification analysis. Avoids slow rank computation."""
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


def d4_orbit_key(p, n: int):
    x, y = p
    cx = (n - 1) / 2
    cy = (n - 1) / 2
    dx, dy = x - cx, y - cy
    adx, ady = abs(dx), abs(dy)
    if adx < ady:
        adx, ady = ady, adx
    return (round(adx * 2), round(ady * 2))


def build_orbit_ids(n: int):
    orbit_map = {}
    next_id = 0
    cell_orbit = {}
    for x in range(n):
        for y in range(n):
            o = d4_orbit_key((x, y), n)
            if o not in orbit_map:
                orbit_map[o] = next_id
                next_id += 1
            cell_orbit[(x, y)] = orbit_map[o]
    return cell_orbit


def hamming(m1, m2):
    return bin(m1 ^ m2).count("1")


def find_min_identifying(mask, n, all_masks, max_k=4):
    """Find min k and list of identifying subsets of occupied points."""
    pts = mask_to_pts(mask, n)
    others = [m for m in all_masks if m != mask]
    for k in range(1, min(max_k, len(pts)) + 1):
        good = []
        for subset in combinations(range(len(pts)), k):
            sub_mask = 0
            for i in subset:
                x, y = pts[i]
                sub_mask |= 1 << (y * n + x)
            if all((om & sub_mask) != sub_mask for om in others):
                good.append([pts[i] for i in subset])
        if good:
            return k, good
    return None, []


def main():
    sets7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    sets6 = load_bin(NIGHT / "maxsafe_n6_K11.bin")
    n = 7
    cell_orbit = build_orbit_ids(n)
    cell_orbit6 = build_orbit_ids(6)

    result = {}
    phases = ["A" if (m >> (3 * 7 + 3)) & 1 else "B" for m in sets7]
    result["phases"] = phases
    result["phase_counts"] = dict(Counter(phases))

    # ===== B401: min identifying pair orbits =====
    print("B401...")
    b401 = {"all_diff_orbit": True, "details": []}
    for idx, mask in enumerate(sets7):
        k, pairs = find_min_identifying(mask, 7, sets7)
        if k is None or k != 2:
            b401["details"].append({"idx": idx, "min_k": k})
            continue
        for pair in pairs:
            o1 = cell_orbit[pair[0]]
            o2 = cell_orbit[pair[1]]
            if o1 == o2:
                b401["all_diff_orbit"] = False
                b401["details"].append({"idx": idx, "pair": pair, "same_orbit": True})
    result["B401"] = b401
    print(f"  all_diff_orbit={b401['all_diff_orbit']}")

    # ===== B402: phase/orientation encoding =====
    print("B402...")
    b402 = {"phase_from_one_point": 0, "relpos_types": set(), "details": []}
    for idx, mask in enumerate(sets7):
        k, pairs = find_min_identifying(mask, 7, sets7)
        if not pairs:
            continue
        pair = pairs[0]
        for pt in pair:
            sharing = [j for j, m in enumerate(sets7) if m >> (pt[1] * 7 + pt[0]) & 1]
            if len(set(phases[j] for j in sharing)) == 1:
                b402["phase_from_one_point"] += 1
                break
        dx = pair[1][0] - pair[0][0]
        dy = pair[1][1] - pair[0][1]
        # D4-normalize relative position
        adx, ady = abs(dx), abs(dy)
        if adx < ady:
            adx, ady = ady, adx
        b402["relpos_types"].add((adx, ady))
        b402["details"].append({"idx": idx, "pair": pair, "dxdy": [dx, dy], "phase": phases[idx]})
    b402["relpos_types"] = sorted(b402["relpos_types"])
    result["B402"] = b402
    print(f"  phase_from_one={b402['phase_from_one_point']} relpos={b402['relpos_types']}")

    # ===== B403: 1-point identification within phase =====
    print("B403...")
    b403 = {"A_one_point": 0, "B_one_point": 0}
    for label, test_phase in [("A", "A"), ("B", "B")]:
        group = [(i, m) for i, (m, ph) in enumerate(zip(sets7, phases)) if ph == test_phase]
        count = 0
        for idx, mask in group:
            pts = mask_to_pts(mask, 7)
            others = [m for j, m in group if m != mask]
            for pt in pts:
                pm = 1 << (pt[1] * 7 + pt[0])
                if all((om & pm) != pm for om in others):
                    count += 1
                    break
        b403[f"{label}_one_point"] = count
    result["B403"] = b403
    print(f"  A={b403['A_one_point']} B={b403['B_one_point']}")

    # ===== B404: identifying pairs vs distance =====
    print("B404...")
    b404_data = []
    for idx, mask in enumerate(sets7):
        k, pairs = find_min_identifying(mask, 7, sets7)
        min_d = min(hamming(mask, m) for m in sets7 if m != mask)
        b404_data.append({"idx": idx, "min_k": k, "n_pairs": len(pairs) if pairs else 0, "min_hamming": min_d, "phase": phases[idx]})
    # n=6 sample (first 30)
    b404_n6 = []
    for idx, mask in enumerate(sets6[:30]):
        k, pairs = find_min_identifying(mask, 6, sets6, max_k=3)
        min_d = min(hamming(mask, m) for m in sets6 if m != mask)
        b404_n6.append({"idx": idx, "min_k": k, "n_pairs": len(pairs) if pairs else 0, "min_hamming": min_d})
    result["B404"] = {"n7": b404_data, "n6_sample": b404_n6}

    # ===== B406: co-occurrence rank (modular arithmetic) =====
    print("B406...")
    N = 49
    cooc = [[0] * N for _ in range(N)]
    for mask in sets7:
        pts = mask_to_pts(mask, 7)
        ids = [y * 7 + x for x, y in pts]
        for i in ids:
            for j in ids:
                cooc[i][j] += 1
    # Rank over GF(large prime)
    MOD = 10**9 + 7
    mat = [[cooc[i][j] % MOD for j in range(N)] for i in range(N)]
    rank = 0
    for col in range(N):
        pivot = None
        for row in range(rank, N):
            if mat[row][col] != 0:
                pivot = row
                break
        if pivot is None:
            continue
        mat[rank], mat[pivot] = mat[pivot], mat[rank]
        inv = pow(mat[rank][col], MOD - 2, MOD)
        for row in range(N):
            if row != rank and mat[row][col] != 0:
                factor = mat[row][col] * inv % MOD
                for c2 in range(col, N):
                    mat[row][c2] = (mat[row][c2] - factor * mat[rank][c2]) % MOD
        rank += 1
    result["B406"] = {"cooc_rank_modp": rank, "n_sets": 16, "N": N}
    print(f"  rank={rank}")

    # ===== B409: empty-point info shortens identification =====
    print("B409...")
    b409_details = []
    for idx, mask in enumerate(sets7):
        pts = mask_to_pts(mask, 7)
        empty = [(x, y) for x in range(7) for y in range(7) if not (mask >> (y * 7 + x) & 1)]
        others = [m for m in sets7 if m != mask]
        k_occ, _ = find_min_identifying(mask, 7, sets7)
        # try k=2 with mixed occupied/empty
        all_cells = pts + empty
        k_mix = None
        for k in range(1, 3):
            found = False
            for subset in combinations(range(len(all_cells)), k):
                ok = True
                for om in others:
                    consistent = True
                    for ci in subset:
                        x, y = all_cells[ci]
                        if ((om >> (y * 7 + x)) & 1) != ((mask >> (y * 7 + x)) & 1):
                            consistent = False
                            break
                    if consistent:
                        ok = False
                        break
                if ok:
                    k_mix = k
                    found = True
                    break
            if found:
                break
        b409_details.append({"idx": idx, "k_occ": k_occ, "k_mix": k_mix})
    n_improved = sum(1 for d in b409_details if d["k_mix"] is not None and d["k_mix"] < (d["k_occ"] or 99))
    result["B409"] = {"details": b409_details, "n_improved": n_improved}
    print(f"  improved={n_improved}")

    # ===== B410: D4 type count =====
    print("B410...")
    patterns = set()
    for mask in sets7:
        pts = mask_to_pts(mask, 7)
        pat = tuple(sorted(cell_orbit[p] for p in pts))
        patterns.add(pat)
    result["B410"] = {"n_orbit_patterns": len(patterns)}
    print(f"  patterns={len(patterns)}")

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

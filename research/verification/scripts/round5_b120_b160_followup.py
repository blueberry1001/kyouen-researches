#!/usr/bin/env python3
"""Round5 B120-B160 follow-up computations.

Targets (remaining after B136/B149/B158 SUPPORTED, B129 REFUTED):
  B120: direction invariants for 8 components of n=7 G_12
  B123/B124/B125: n=6 maximal pair witness search
  B130: n=5 k=3,4,5 deformation components vs P/N
  B133: a-by-a first-appearance table
  B138: center aggregation of top-layer circles
  B153/B154/B159: B141-based theoretical notes + increment profile
  B157: 2-point matrix eigenvalue / P/N correlation (n=5)
  B160: n=6 same-degree D4-inequivalent child |L| multiset
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from itertools import combinations

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, det4, square_points  # noqa: E402

OUT = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b120_b160_followup.json"


def d4_orbit(p, n):
    x, y = p
    cands = [
        (x, y), (y, n - 1 - x), (n - 1 - x, n - 1 - y), (n - 1 - y, x),
        (y, x), (n - 1 - x, y), (n - 1 - y, n - 1 - x), (x, n - 1 - y),
    ]
    return tuple(sorted(set(cands)))


def d4_orbit_id(p, n):
    return min(d4_orbit(p, n))


def load_maximal_n6():
    """Load n=6 maximal safe sets from binary. Each record is 8 bytes (uint64 bitmask)."""
    path = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\data\maximal_n6.bin"
    import struct
    with open(path, "rb") as f:
        raw = f.read()
    n = len(raw) // 8
    return list(struct.unpack(f"<{n}Q", raw))


def b160_n6():
    """Same-degree D4-inequivalent points with different child |L| multisets."""
    n = 6
    pts = square_points(n)
    B = Board(pts, "n6")
    degs = [len(B.quads_by_pt[i]) for i in range(len(pts))]
    # child |L| multiset: for each p, for each legal q != p, compute |L({p,q})|
    feat = {}
    for p in range(len(pts)):
        occ_p = 1 << p
        child_L = []
        for q in range(len(pts)):
            if q == p:
                continue
            occ = occ_p | (1 << q)
            if B.is_safe(occ):
                child_L.append(len(B.legal_moves(occ)))
        feat[p] = {
            "pt": pts[p],
            "deg": degs[p],
            "d4": d4_orbit_id(pts[p], n),
            "child_L_sorted": sorted(child_L),
            "child_L_hash": hash(tuple(sorted(child_L))),
            "child_L_len": len(child_L),
        }
    # group by deg
    by_deg = defaultdict(list)
    for p, f in feat.items():
        by_deg[f["deg"]].append(p)
    witnesses = []
    for deg, plist in by_deg.items():
        if len(plist) < 2:
            continue
        # find pairs with different D4 orbit AND different child_L
        for i, j in combinations(plist, 2):
            fi, fj = feat[i], feat[j]
            if fi["d4"] != fj["d4"] and fi["child_L_hash"] != fj["child_L_hash"]:
                witnesses.append({
                    "deg": deg,
                    "p": fi["pt"], "q": fj["pt"],
                    "d4_p": fi["d4"], "d4_q": fj["d4"],
                    "child_L_p": fi["child_L_sorted"],
                    "child_L_q": fj["child_L_sorted"],
                })
                break  # one per deg is enough
    # also compute same-deg D4-inequivalent with same child_L (for contrast)
    same_feat_pairs = 0
    for deg, plist in by_deg.items():
        for i, j in combinations(plist, 2):
            fi, fj = feat[i], feat[j]
            if fi["d4"] != fj["d4"] and fi["child_L_hash"] == fj["child_L_hash"]:
                same_feat_pairs += 1
    deg_hist = dict(Counter(degs))
    return {
        "n": n,
        "deg_hist": {str(k): v for k, v in sorted(deg_hist.items())},
        "n_same_deg_d4ineq_diff_feat": len(witnesses),
        "witnesses": witnesses[:10],
        "n_same_deg_d4ineq_same_feat": same_feat_pairs,
        "feat_sample": {str(p): feat[p] for p in list(feat)[:6]},
    }


def b130_n5():
    """n=5 k=3,4,5: deformation components vs P/N."""
    n = 5
    pts = square_points(n)
    B = Board(pts, "n5")
    V = len(pts)
    # P/N: 1 if player to move wins, 0 if loses
    # We need solve_outcomes for all safe sets. n=5 has 151k safe states total.
    # But we only need outcomes for safe sets of size k and their children.
    # Use memoized recursion on the subset lattice restricted to safe sets.
    from functools import lru_cache

    sys.setrecursionlimit(200000)

    @lru_cache(maxsize=None)
    def outcome(occ: int) -> int:
        """1 = win for player to move, 0 = loss."""
        moves = B.legal_moves(occ)
        if not moves:
            return 0
        for m in moves:
            if outcome(occ | (1 << m)) == 0:
                return 1
        return 0

    # For each k, collect all safe sets of size k, build 1-point-move graph
    # (two sets connected if symmetric difference is 1 point, i.e. one is subset of other with |diff|=1)
    # Actually for "deformation" the standard is: can add or remove one point while staying safe.
    # So edges: A -- B if |A Δ B| = 1 and both safe.
    results = {}
    for k in (3, 4, 5):
        safe_k = []
        for ids in combinations(range(V), k):
            occ = 0
            for i in ids:
                occ |= 1 << i
            if B.is_safe(occ):
                safe_k.append(occ)
        # build graph
        idx = {occ: i for i, occ in enumerate(safe_k)}
        parent = list(range(len(safe_k)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        # For each set, try removing one point -> size k-1, then adding a different point -> size k
        # That's a 2-step deformation. Also direct: two size-k sets differing by 1 point means
        # one has a point the other doesn't and vice versa — that's |A Δ B|=2.
        # The standard "1-point move" for same-size sets: remove one, add one (order matters for safety).
        # For component analysis, connect A,B if there exists p in A\B, q in B\A with
        # A-p safe and A-p+q = B safe (or the other direction).
        for occ in safe_k:
            bits = [i for i in range(V) if occ & (1 << i)]
            for p in bits:
                occ_minus = occ ^ (1 << p)
                # try adding any q not in occ_minus
                for q in range(V):
                    if occ_minus & (1 << q):
                        continue
                    occ2 = occ_minus | (1 << q)
                    if occ2 in idx:
                        union(idx[occ], idx[occ2])
        # components
        comps = defaultdict(list)
        for i, occ in enumerate(safe_k):
            comps[find(i)].append(occ)
        # P/N per component
        comp_info = []
        pn_constant = True
        n_pn_mixed = 0
        for root, members in comps.items():
            pns = set()
            for occ in members:
                pns.add(outcome(occ))
            if len(pns) > 1:
                pn_constant = False
                n_pn_mixed += 1
            comp_info.append({
                "size": len(members),
                "pn": sorted(pns),
                "all_P": pns == {0},
                "all_N": pns == {1},
            })
        results[str(k)] = {
            "n_safe": len(safe_k),
            "n_components": len(comps),
            "comp_sizes": sorted([len(v) for v in comps.values()], reverse=True)[:20],
            "pn_constant_in_all_comps": pn_constant,
            "n_pn_mixed_comps": n_pn_mixed,
            "n_comps_all_P": sum(1 for c in comp_info if c["all_P"]),
            "n_comps_all_N": sum(1 for c in comp_info if c["all_N"]),
            "n_comps_mixed": n_pn_mixed,
            "is_witness_layer": (len(comps) > 1 and pn_constant and
                                 any(c["all_P"] for c in comp_info) and
                                 any(c["all_N"] for c in comp_info)),
        }
    return results


def b157_n5():
    """2-stone positions: deg_sum, shared_quads, 2-point matrix bias vs P/N."""
    n = 5
    pts = square_points(n)
    B = Board(pts, "n5")
    V = len(pts)
    degs = [len(B.quads_by_pt[i]) for i in range(V)]

    from functools import lru_cache
    sys.setrecursionlimit(200000)

    @lru_cache(maxsize=None)
    def outcome(occ: int) -> int:
        moves = B.legal_moves(occ)
        if not moves:
            return 0
        for m in moves:
            if outcome(occ | (1 << m)) == 0:
                return 1
        return 0

    # For each safe 2-stone position {p,q}:
    # - deg_sum = d(p)+d(q)
    # - shared = |quads containing both p and q|
    # - matrix M = [[d(p), shared], [shared, d(q)]] -> eigenvalues
    # - outcome
    records = []
    for p, q in combinations(range(V), 2):
        occ = (1 << p) | (1 << q)
        if not B.is_safe(occ):
            continue
        shared = len(set(B.quads_by_pt[p]) & set(B.quads_by_pt[q]))
        dp, dq = degs[p], degs[q]
        deg_sum = dp + dq
        # 2x2 matrix eigenvalues: (a+d)/2 ± sqrt(((a-d)/2)^2 + b^2)
        # For integer features, use bias = |dp - dq| and shared
        bias = abs(dp - dq)
        pn = outcome(occ)
        records.append({
            "p": pts[p], "q": pts[q],
            "deg_sum": deg_sum, "shared": shared, "bias": bias,
            "dp": dp, "dq": dq, "pn": pn,
        })
    # Group by deg_sum and check if shared/bias predicts pn
    by_ds = defaultdict(list)
    for r in records:
        by_ds[r["deg_sum"]].append(r)
    mixed_ds = 0
    ds_with_shared_variation = 0
    for ds, rs in by_ds.items():
        pns = set(r["pn"] for r in rs)
        if len(pns) > 1:
            mixed_ds += 1
        shareds = set(r["shared"] for r in rs)
        if len(shareds) > 1:
            ds_with_shared_variation += 1
    # Try: within mixed deg_sum groups, does shared or bias separate pn?
    separation = {"shared": 0, "bias": 0, "both": 0}
    for ds, rs in by_ds.items():
        pns = set(r["pn"] for r in rs)
        if len(pns) <= 1:
            continue
        # check if shared alone separates
        by_shared = defaultdict(set)
        by_bias = defaultdict(set)
        for r in rs:
            by_shared[r["shared"]].add(r["pn"])
            by_bias[r["bias"]].add(r["pn"])
        if all(len(v) == 1 for v in by_shared.values()) and len(by_shared) > 1:
            separation["shared"] += 1
        if all(len(v) == 1 for v in by_bias.values()) and len(by_bias) > 1:
            separation["bias"] += 1
        if (all(len(v) == 1 for v in by_shared.values()) and len(by_shared) > 1 and
                all(len(v) == 1 for v in by_bias.values()) and len(by_bias) > 1):
            separation["both"] += 1
    # Overall correlation: does higher shared mean more likely N (win)?
    n_pos = sum(1 for r in records if r["pn"] == 1)
    n_neg = sum(1 for r in records if r["pn"] == 0)
    shared_mean_n = sum(r["shared"] for r in records if r["pn"] == 1) / max(n_pos, 1)
    shared_mean_p = sum(r["shared"] for r in records if r["pn"] == 0) / max(n_neg, 1)
    bias_mean_n = sum(r["bias"] for r in records if r["pn"] == 1) / max(n_pos, 1)
    bias_mean_p = sum(r["bias"] for r in records if r["pn"] == 0) / max(n_neg, 1)
    return {
        "n": n,
        "n_safe_2stone": len(records),
        "n_P": n_neg, "n_N": n_pos,
        "n_mixed_deg_sum_groups": mixed_ds,
        "n_deg_sum_with_shared_variation": ds_with_shared_variation,
        "separation_by_deg_sum_group": separation,
        "shared_mean_N": shared_mean_n, "shared_mean_P": shared_mean_p,
        "bias_mean_N": bias_mean_n, "bias_mean_P": bias_mean_p,
        "deg_sum_hist": {str(k): len(v) for k, v in sorted(by_ds.items())},
    }


def b133_a_table():
    """a-by-a first-appearance table for circle types (from existing data + recompute small n)."""
    # Reconstruct from circle_b131_b138.json by_q_max and b134_by_q
    # Also compute: for each q, what is the min n at which a circle with that q achieves
    # the global max points at that n?
    path = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\data\circle_b131_b138.json"
    with open(path) as f:
        data = json.load(f)
    # per_n by_q_max: keys are denominators q, values are max points for that q
    q_first_max = {}  # q -> first n where q achieves global max
    q_first_any = {}  # q -> first n where any circle with that q exists (>=3 pts)
    for n_str in sorted(data["per_n"].keys(), key=int):
        n = int(n_str)
        v = data["per_n"][n_str]
        by_q = v.get("by_q_max", {})
        gmax = v.get("max_all_q", 0)
        for q_str, mx in by_q.items():
            q = int(q_str)
            if q not in q_first_any:
                q_first_any[q] = n
            if mx == gmax and q not in q_first_max:
                q_first_max[q] = n
    # hierarchy: U(q) coefficients from round10
    # U(1)=4, U(2,both odd)=4, U(2,one odd)=2, U(q>=3)=1
    return {
        "q_first_any_ge3pts": q_first_any,
        "q_first_achieves_global_max": q_first_max,
        "b134_by_q": data.get("b134_by_q", {}),
        "mz_jumps_summary": {
            "n_jumps": len(data.get("mz_jumps", {}).get("jumps", [])),
            "jumps": data.get("mz_jumps", {}).get("jumps", [])[:8],
        },
    }


def b138_center_agg():
    """Aggregate centers of top-layer circles across n."""
    path = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\data\circle_b131_b138.json"
    with open(path) as f:
        data = json.load(f)
    result = {}
    for n_str in sorted(data["per_n"].keys(), key=int):
        v = data["per_n"][n_str]
        top5 = v.get("top5", [])
        # top5 format: [npts, [cx_num, cy_num, q, M?]] or similar
        # sample: [[8, [2, 3, 3, 10]], [6, [2, 5, 3, 10]]]
        centers = []
        for item in top5:
            if len(item) >= 2:
                npts = item[0]
                cinfo = item[1]
                if len(cinfo) >= 3:
                    cx, cy, q = cinfo[0], cinfo[1], cinfo[2]
                    centers.append({"npts": npts, "cx": cx, "cy": cy, "q": q,
                                    "center": f"({cx}/{q},{cy}/{q})"})
        # count distinct centers
        distinct = set(c["center"] for c in centers)
        # board center is ((n-1)/2, (n-1)/2)
        n = int(n_str)
        bcx, bcy = (n - 1) / 2, (n - 1) / 2
        # how many top5 centers are near board center?
        near = 0
        for c in centers:
            cx_f = c["cx"] / c["q"]
            cy_f = c["cy"] / c["q"]
            if abs(cx_f - bcx) < 1.0 and abs(cy_f - bcy) < 1.0:
                near += 1
        result[n_str] = {
            "top5_centers": centers,
            "n_distinct_centers": len(distinct),
            "n_top5": len(centers),
            "concentration_ratio": len(centers) / max(len(distinct), 1),
            "n_near_board_center": near,
            "max_pts": v.get("max_all_q"),
        }
    return result


def b159_increment():
    """n=4->5->6 degree increments: center vs boundary."""
    results = {}
    for n in (4, 5, 6):
        pts = square_points(n)
        B = Board(pts, f"n{n}")
        degs = [len(B.quads_by_pt[i]) for i in range(len(pts))]
        # classify points: corner, edge, interior
        corner, edge, interior = [], [], []
        for i, (x, y) in enumerate(pts):
            is_corner = (x in (0, n - 1)) and (y in (0, n - 1))
            is_edge = (x in (0, n - 1)) or (y in (0, n - 1))
            if is_corner:
                corner.append(degs[i])
            elif is_edge:
                edge.append(degs[i])
            else:
                interior.append(degs[i])
        results[str(n)] = {
            "deg_min": min(degs), "deg_max": max(degs),
            "deg_mean": sum(degs) / len(degs),
            "corner_mean": sum(corner) / max(len(corner), 1),
            "edge_mean": sum(edge) / max(len(edge), 1),
            "interior_mean": sum(interior) / max(len(interior), 1),
            "n_corner": len(corner), "n_edge": len(edge), "n_interior": len(interior),
        }
    # increments
    for a, b in [("4", "5"), ("5", "6")]:
        ra, rb = results[a], results[b]
        results[f"inc_{a}_{b}"] = {
            "corner": rb["corner_mean"] - ra["corner_mean"],
            "edge": rb["edge_mean"] - ra["edge_mean"],
            "interior": rb["interior_mean"] - ra["interior_mean"],
            "mean": rb["deg_mean"] - ra["deg_mean"],
        }
    return results


def b123_n6_pairs_sample(n_sample=30):
    """Search n=6 maximal pairs for B123/B124/B125 witnesses (greedy, light)."""
    n = 6
    pts = square_points(n)
    Bd = Board(pts, "n6")
    V = len(pts)
    maximal = load_maximal_n6()
    import random
    rng = random.Random(42)
    sample = rng.sample(maximal, min(n_sample, len(maximal)))
    b123_witness = None
    b125_witness = None
    n_pairs = 0
    n_need_aux = 0
    n_path_removes_common = 0

    def try_orders(A, Bm):
        A_set = set(i for i in range(V) if A & (1 << i))
        B_set = set(i for i in range(V) if Bm & (1 << i))
        to_remove = sorted(A_set - B_set)
        to_add = sorted(B_set - A_set)
        common = A_set & B_set
        for name in ("remove_first", "add_first", "interleave"):
            cur_occ = A
            path = []
            used_common = False
            ok = True
            if name == "remove_first":
                seq = [("-", i) for i in to_remove] + [("+", i) for i in to_add]
            elif name == "add_first":
                seq = [("+", i) for i in to_add] + [("-", i) for i in to_remove]
            else:
                seq = []
                for a, b in zip(to_remove, to_add):
                    seq.append(("-", a))
                    seq.append(("+", b))
                seq += [("-", i) for i in to_remove[len(to_add):]]
                seq += [("+", i) for i in to_add[len(to_remove):]]
            for op, idx in seq:
                if op == "-":
                    occ2 = cur_occ ^ (1 << idx)
                    if not Bd.is_safe(occ2):
                        ok = False
                        break
                    cur_occ = occ2
                    if idx in common:
                        used_common = True
                    path.append((op, idx))
                else:
                    occ2 = cur_occ | (1 << idx)
                    if not Bd.is_safe(occ2):
                        ok = False
                        break
                    cur_occ = occ2
                    path.append((op, idx))
            if ok and cur_occ == Bm:
                return True, path, used_common
        return False, [], False

    for i in range(len(sample)):
        for j in range(i + 1, len(sample)):
            A, Bm = sample[i], sample[j]
            if A == Bm:
                continue
            n_pairs += 1
            A_set = set(k for k in range(V) if A & (1 << k))
            B_set = set(k for k in range(V) if Bm & (1 << k))
            ok, path, used_common = try_orders(A, Bm)
            if not ok:
                n_need_aux += 1
                if b123_witness is None:
                    b123_witness = {
                        "A": [pts[k] for k in sorted(A_set)],
                        "B": [pts[k] for k in sorted(B_set)],
                        "note": "no greedy order works within A+B",
                    }
            elif used_common:
                n_path_removes_common += 1
                if b125_witness is None:
                    b125_witness = {
                        "A": [pts[k] for k in sorted(A_set)],
                        "B": [pts[k] for k in sorted(B_set)],
                        "path": [(op, pts[idx]) for op, idx in path],
                        "common": [pts[k] for k in sorted(A_set & B_set)],
                    }
    return {
        "n_sample_pairs": n_pairs,
        "n_need_aux_outside_union": n_need_aux,
        "n_path_removes_common": n_path_removes_common,
        "b123_witness": b123_witness,
        "b125_witness": b125_witness,
    }


def main():
    res = {}
    print("B160 n=6 ...", flush=True)
    res["b160_n6"] = b160_n6()
    print("  witnesses:", res["b160_n6"]["n_same_deg_d4ineq_diff_feat"], flush=True)
    print("B130 n=5 ...", flush=True)
    res["b130_n5"] = b130_n5()
    print("  k=3 comps:", res["b130_n5"]["3"]["n_components"],
          "k=4 comps:", res["b130_n5"]["4"]["n_components"], flush=True)
    if "5" in res["b130_n5"]:
        print("  k=5 comps:", res["b130_n5"]["5"]["n_components"], flush=True)
    print("B157 n=5 ...", flush=True)
    res["b157_n5"] = b157_n5()
    print("  mixed:", res["b157_n5"]["n_mixed_deg_sum_groups"], flush=True)
    print("B133 ...", flush=True)
    res["b133"] = b133_a_table()
    print("B138 ...", flush=True)
    res["b138"] = b138_center_agg()
    print("B159 ...", flush=True)
    res["b159"] = b159_increment()
    # save intermediate before slow B123
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print("Intermediate saved.", flush=True)
    print("B123/124/125 sample (light) ...", flush=True)
    res["b123_125"] = b123_n6_pairs_sample(n_sample=25)
    print("  pairs:", res["b123_125"]["n_sample_pairs"],
          "need_aux:", res["b123_125"]["n_need_aux_outside_union"], flush=True)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print("Wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

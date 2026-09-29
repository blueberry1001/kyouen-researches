#!/usr/bin/env python3
"""Targeted computations for B151-B200 unresolved IDs (round5 additional)."""
from __future__ import annotations
import json, sys, random
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points

OUT = Path(__file__).resolve().parent.parent / "round5_b151_compute.json"


def d4_orbit(x, y, n):
    """Return canonical D4 orbit id for point (x,y) on n×n (0-indexed)."""
    pts = set()
    for rx, ry in [(x, y), (y, x), (x, n - 1 - y), (n - 1 - y, x),
                   (n - 1 - x, y), (y, n - 1 - x), (n - 1 - x, n - 1 - y), (n - 1 - y, n - 1 - x)]:
        pts.add((rx, ry))
    return min(pts)


def point_degree(board: Board, i: int) -> int:
    return len(board.quads_by_pt[i])


def main():
    out = {}
    # =========================================================
    # B158 non-empty S: inversion d(p) vs |L(S+p)| for |S|>=3
    # =========================================================
    print("=== B158 non-empty S ===")
    n = 5
    board = Board(square_points(n))
    V = n * n
    degs = [point_degree(board, i) for i in range(V)]

    # all safe 3-sets
    safe3 = []
    for comb in combinations(range(V), 3):
        m = (1 << comb[0]) | (1 << comb[1]) | (1 << comb[2])
        if board.is_safe(m):
            safe3.append(m)
    print(f"n=5 safe 3-sets: {len(safe3)}")

    inversions = []
    maxmin_inv = None
    checked = 0
    for s_mask in safe3:
        occ = s_mask
        legal = board.legal_moves(occ)
        if len(legal) < 2:
            continue
        # compute |L(S+p)| for each legal p
        Lvals = {}
        for p in legal:
            child = occ | (1 << p)
            Lvals[p] = len(board.legal_moves(child))
        # search inversion: d(p)>d(q) but L(p)>L(q)
        for p, q in combinations(legal, 2):
            if degs[p] > degs[q] and Lvals[p] > Lvals[q]:
                inversions.append((s_mask, p, q, degs[p], degs[q], Lvals[p], Lvals[q]))
                if len(inversions) >= 5:
                    break
            if degs[q] > degs[p] and Lvals[q] > Lvals[p]:
                inversions.append((s_mask, q, p, degs[q], degs[p], Lvals[q], Lvals[p]))
                if len(inversions) >= 5:
                    break
        # also track max-min degree pair
        pmax = max(legal, key=lambda i: degs[i])
        pmin = min(legal, key=lambda i: degs[i])
        if pmax != pmin and degs[pmax] > degs[pmin] and Lvals[pmax] > Lvals[pmin]:
            maxmin_inv = (s_mask, pmax, pmin, degs[pmax], degs[pmin], Lvals[pmax], Lvals[pmin])
        checked += 1
        if len(inversions) >= 5 and maxmin_inv:
            break

    out["b158_n5_S3"] = {
        "n_safe3": len(safe3),
        "n_checked": checked,
        "n_inversions": len(inversions),
        "inversions_sample": [
            {"S": bin(s).count("1"), "S_mask": s, "p": p, "q": q,
             "dp": dp, "dq": dq, "Lp": Lp, "Lq": Lq}
            for s, p, q, dp, dq, Lp, Lq in inversions[:5]
        ],
        "maxmin_witness": None if maxmin_inv is None else {
            "S_mask": maxmin_inv[0], "p": maxmin_inv[1], "q": maxmin_inv[2],
            "dp": maxmin_inv[3], "dq": maxmin_inv[4],
            "Lp": maxmin_inv[5], "Lq": maxmin_inv[6],
        },
    }
    print("B158 S3 inversions:", len(inversions), "maxmin:", maxmin_inv is not None)

    # Also try |S|=4
    if not inversions or not maxmin_inv:
        safe4 = []
        for comb in combinations(range(V), 4):
            m = 0
            for i in comb:
                m |= 1 << i
            if board.is_safe(m):
                safe4.append(m)
        print(f"n=5 safe 4-sets: {len(safe4)}")
        checked4 = 0
        for s_mask in safe4:
            legal = board.legal_moves(s_mask)
            if len(legal) < 2:
                continue
            Lvals = {}
            for p in legal:
                Lvals[p] = len(board.legal_moves(s_mask | (1 << p)))
            for p, q in combinations(legal, 2):
                if degs[p] > degs[q] and Lvals[p] > Lvals[q]:
                    inversions.append((s_mask, p, q, degs[p], degs[q], Lvals[p], Lvals[q]))
                    if len(inversions) >= 8:
                        break
                if degs[q] > degs[p] and Lvals[q] > Lvals[p]:
                    inversions.append((s_mask, q, p, degs[q], degs[p], Lvals[q], Lvals[p]))
                    if len(inversions) >= 8:
                        break
            pmax = max(legal, key=lambda i: degs[i])
            pmin = min(legal, key=lambda i: degs[i])
            if pmax != pmin and degs[pmax] > degs[pmin] and Lvals[pmax] > Lvals[pmin]:
                maxmin_inv = (s_mask, pmax, pmin, degs[pmax], degs[pmin], Lvals[pmax], Lvals[pmin])
            checked4 += 1
            if len(inversions) >= 8 and maxmin_inv:
                break
        out["b158_n5_S4"] = {
            "n_safe4": len(safe4),
            "n_checked": checked4,
            "n_inversions": len(inversions),
            "maxmin_witness": None if maxmin_inv is None else {
                "S_mask": maxmin_inv[0], "p": maxmin_inv[1], "q": maxmin_inv[2],
                "dp": maxmin_inv[3], "dq": maxmin_inv[4],
                "Lp": maxmin_inv[5], "Lq": maxmin_inv[6],
            },
            "inversions_sample": [
                {"S": bin(s).count("1"), "S_mask": s, "p": p, "q": q,
                 "dp": dp, "dq": dq, "Lp": Lp, "Lq": Lq}
                for s, p, q, dp, dq, Lp, Lq in inversions[:8]
            ],
        }
        print("B158 S4 inversions:", len(inversions), "maxmin:", maxmin_inv is not None)

    # =========================================================
    # B159: degree increment n=5 -> n=6 spatial distribution
    # =========================================================
    print("=== B159 degree increment 5->6 ===")
    b5 = Board(square_points(5))
    b6 = Board(square_points(6))
    deg5 = [point_degree(b5, i) for i in range(25)]
    deg6 = [point_degree(b6, i) for i in range(36)]
    # n=5 point (x,y) -> n=6 point (x,y) offset? Better: center both.
    # Compare increment of points that exist in both: (x,y) for x,y in 0..4
    # In n=6, those are the lower-left 5×5. Also compare centered positions.
    # Measure: for each n=5 point, deg in n=6 (same coords) minus deg in n=5.
    inc = []
    for y in range(5):
        for x in range(5):
            i5 = y * 5 + x
            i6 = y * 6 + x
            inc.append((x, y, deg5[i5], deg6[i6], deg6[i6] - deg5[i5]))
    # classify by distance from n=5 center (2,2)
    by_dist = defaultdict(list)
    for x, y, d5, d6, di in inc:
        r2 = (x - 2) ** 2 + (y - 2) ** 2
        by_dist[r2].append(di)
    out["b159_inc_5to6"] = {
        "by_r2": {str(k): {"min": min(v), "max": max(v), "mean": sum(v) / len(v), "n": len(v)}
                  for k, v in sorted(by_dist.items())},
        "all_inc": inc,
    }
    # center vs boundary ratio
    center_inc = [di for x, y, d5, d6, di in inc if (x - 2) ** 2 + (y - 2) ** 2 <= 1]
    bound_inc = [di for x, y, d5, d6, di in inc if (x - 2) ** 2 + (y - 2) ** 2 >= 4]
    if center_inc and bound_inc:
        out["b159_inc_5to6"]["center_mean"] = sum(center_inc) / len(center_inc)
        out["b159_inc_5to6"]["boundary_mean"] = sum(bound_inc) / len(bound_inc)
        out["b159_inc_5to6"]["ratio_center_over_boundary"] = (
            out["b159_inc_5to6"]["center_mean"] / out["b159_inc_5to6"]["boundary_mean"]
        )
    print("B159 ratio:", out["b159_inc_5to6"].get("ratio_center_over_boundary"))

    # also n=6 -> need deg for interior of 6x6 when conceptually larger
    # Use n=6 vs a 7x7? n=7 is forbidden for full enum but Board construction is OK
    # (just building quads for 49 points is fine, not enumerating states)
    print("Building n=7 board (quad index only)...")
    b7 = Board(square_points(7))
    deg7 = [point_degree(b7, i) for i in range(49)]
    inc67 = []
    for y in range(6):
        for x in range(6):
            i6 = y * 6 + x
            i7 = y * 7 + x
            inc67.append((x, y, deg6[i6], deg7[i7], deg7[i7] - deg6[i6]))
    by_dist7 = defaultdict(list)
    for x, y, d6_, d7_, di in inc67:
        r2 = (x - 2.5) ** 2 + (y - 2.5) ** 2
        by_dist7[r2].append(di)
    out["b159_inc_6to7"] = {
        "by_r2": {str(k): {"min": min(v), "max": max(v), "mean": sum(v) / len(v), "n": len(v)}
                  for k, v in sorted(by_dist7.items())},
    }
    center7 = [di for x, y, a, b, di in inc67 if (x - 2.5) ** 2 + (y - 2.5) ** 2 <= 2.0]
    bound7 = [di for x, y, a, b, di in inc67 if (x - 2.5) ** 2 + (y - 2.5) ** 2 >= 8.0]
    if center7 and bound7:
        out["b159_inc_6to7"]["center_mean"] = sum(center7) / len(center7)
        out["b159_inc_6to7"]["boundary_mean"] = sum(bound7) / len(bound7)
        out["b159_inc_6to7"]["ratio"] = sum(center7) / len(center7) / (sum(bound7) / len(bound7))
    print("B159 6to7 ratio:", out["b159_inc_6to7"].get("ratio"))

    # =========================================================
    # B160: n=5 first-move grundy, same-degree D4-inequivalent
    # =========================================================
    print("=== B160 n=5 first-move g ===")
    board5 = Board(square_points(5))
    g5 = board5.solve_grundy()
    first = {}
    for i in range(25):
        first[i] = g5.get(1 << i, None)
    # group by degree
    bydeg = defaultdict(list)
    for i in range(25):
        bydeg[degs[i]].append(i)
    b160_witness = None
    b160_groups = {}
    for d, pts in sorted(bydeg.items()):
        orbits = {}
        for i in pts:
            x, y = i % 5, i // 5
            orb = d4_orbit(x, y, 5)
            orbits.setdefault(orb, []).append(i)
        gs = {orb: first[pts[0]] for orb, pts in orbits.items()}  # same orbit -> same g
        distinct_g = set(first[i] for i in pts)
        b160_groups[str(d)] = {
            "n_points": len(pts),
            "n_orbits": len(orbits),
            "g_values": sorted(distinct_g),
            "orbit_g": {str(k): first[v[0]] for k, v in orbits.items()},
        }
        if len(distinct_g) > 1 and len(orbits) > 1:
            # same degree, D4-inequivalent, different g
            items = [(first[v[0]], k, v) for k, v in orbits.items()]
            items.sort()
            b160_witness = {
                "degree": d,
                "g_min": items[0][0], "g_max": items[-1][0],
                "orbit_min": items[0][1], "orbit_max": items[-1][1],
                "pts_min": items[0][2], "pts_max": items[-1][2],
            }
    out["b160_n5"] = {
        "deg_range": [min(degs), max(degs)],
        "groups": b160_groups,
        "witness": b160_witness,
        "first_move_g": {str(i): first[i] for i in range(25)},
    }
    print("B160 witness:", b160_witness)

    # n=6 first-move g (solve_grundy on n=6 is heavy - 2^36 states too many.
    # Instead compute g only for 1-stone positions via recursion limited depth)
    # Use solve from each first move separately with memo shared
    print("=== B160 n=6 first-move g (targeted) ===")
    board6 = Board(square_points(6))
    degs6 = [point_degree(board6, i) for i in range(36)]

    # compute grundy of position via recursive function with global memo
    from functools import lru_cache
    @lru_cache(maxsize=None)
    def g6(occ: int) -> int:
        moves = board6.legal_moves(occ)
        if not moves:
            return 0
        seen = set()
        for u in moves:
            seen.add(g6(occ | (1 << u)))
        g = 0
        while g in seen:
            g += 1
        return g

    # This will explode for n=6 empty board. Just compute first-move g
    # by exploring each 1-stone subtree... still huge.
    # Instead compute P/N (win/lose) only for 1-stone positions via outcome solve.
    @lru_cache(maxsize=None)
    def win6(occ: int) -> int:
        moves = board6.legal_moves(occ)
        if not moves:
            return 0
        for u in moves:
            if win6(occ | (1 << u)) == 0:
                return 1
        return 0

    first6 = {}
    for i in range(36):
        first6[i] = win6(1 << i)
    bydeg6 = defaultdict(list)
    for i in range(36):
        bydeg6[degs6[i]].append(i)
    b160_n6_witness = None
    groups6 = {}
    for d, pts in sorted(bydeg6.items()):
        orbits = {}
        for i in pts:
            x, y = i % 6, i // 6
            orb = d4_orbit(x, y, 6)
            orbits.setdefault(orb, []).append(i)
        ws = set(first6[i] for i in pts)
        groups6[str(d)] = {
            "n_points": len(pts), "n_orbits": len(orbits),
            "w_values": sorted(ws),
            "orbit_w": {str(k): first6[v[0]] for k, v in orbits.items()},
        }
        if len(ws) > 1 and len(orbits) > 1:
            items = [(first6[v[0]], k, v) for k, v in orbits.items()]
            items.sort()
            b160_n6_witness = {
                "degree": d,
                "w_min": items[0][0], "w_max": items[-1][0],
                "orbit_min": items[0][1], "orbit_max": items[-1][1],
                "pts_min": items[0][2], "pts_max": items[-1][2],
            }
    out["b160_n6"] = {
        "deg_range": [min(degs6), max(degs6)],
        "groups": groups6,
        "witness": b160_n6_witness,
        "first_win": {str(i): first6[i] for i in range(36)},
    }
    print("B160 n=6 witness:", b160_n6_witness)
    print("n=6 first-win sample:", list(first6.items())[:8])

    # =========================================================
    # B157: 2-stone matrix eigenvalues vs P/N (n=4,5)
    # =========================================================
    print("=== B157 matrix features ===")
    for n_, bm in [(4, Board(square_points(4))), (5, board5)]:
        V_ = n_ * n_
        degs_ = [point_degree(bm, i) for i in range(V_)]
        # 2-stone safe positions
        rows = []
        for p, q in combinations(range(V_), 2):
            m = (1 << p) | (1 << q)
            if not bm.is_safe(m):
                continue
            # P/N: player to move wins iff exists legal r with child losing
            # For 2 stones, compute outcome
            legal = bm.legal_moves(m)
            # win if some child is losing
            # child = 3 stones, always safe; from 3 stones, legal moves exist
            # unless all 4th stones complete a forbidden quad
            win = 0
            for r in legal:
                child = m | (1 << r)
                clegal = bm.legal_moves(child)
                if not clegal:
                    win = 1
                    break
                # if child has legal moves, opponent can move; check if any child is P
                # deeper: just use solve
            # use exact outcome via solve
            rows.append((p, q, degs_[p], degs_[q], len(legal)))
        # exact P/N via solve_outcomes memo
        outcomes = bm.solve_outcomes()
        feats = []
        for p, q, dp, dq, nl in rows:
            m = (1 << p) | (1 << q)
            pn = outcomes.get(m, -1)
            # d(p,q) matrix for S={p,q}: 2x2 with diagonal degs, off-diag shared quads
            shared = len(set(bm.quads_by_pt[p]) & set(bm.quads_by_pt[q]))
            # matrix [[dp, shared],[shared, dq]] eigenvalues
            tr = dp + dq
            det = dp * dq - shared * shared
            # disc = (dp-dq)^2 + 4*shared^2 >= 0
            disc = (dp - dq) ** 2 + 4 * shared * shared
            lam1 = (tr + disc ** 0.5) / 2
            lam2 = (tr - disc ** 0.5) / 2
            var = ((dp - tr / 2) ** 2 + (dq - tr / 2) ** 2) / 2
            feats.append({
                "p": p, "q": q, "dp": dp, "dq": dq, "shared": shared,
                "pn": pn, "lam_max": lam1, "lam_min": lam2, "var_diag": var,
                "deg_sum": dp + dq, "n_legal": nl,
            })
        # correlation: for positions with same deg_sum, does lam_max or shared separate P/N?
        by_sum = defaultdict(lambda: {"P": [], "N": []})
        for f in feats:
            key = f["deg_sum"]
            by_sum[key]["P" if f["pn"] == 1 else "N"].append(f)
        mixed = {k: {"P": len(v["P"]), "N": len(v["N"]),
                     "lamP": [x["lam_max"] for x in v["P"]],
                     "lamN": [x["lam_max"] for x in v["N"]],
                     "shP": [x["shared"] for x in v["P"]],
                     "shN": [x["shared"] for x in v["N"]]}
                 for k, v in by_sum.items() if v["P"] and v["N"]}
        out[f"b157_n{n_}"] = {
            "n_pairs": len(feats),
            "n_mixed_degsum": len(mixed),
            "mixed_sample": {k: v for k, v in list(mixed.items())[:8]},
            "overall": {
                "n_P": sum(1 for f in feats if f["pn"] == 1),
                "n_N": sum(1 for f in feats if f["pn"] == 0),
            },
        }
        # check if lam_max perfectly separates within mixed groups
        perfect = 0
        for k, v in mixed.items():
            if v["lamP"] and v["lamN"]:
                if min(v["lamP"]) > max(v["lamN"]) or max(v["lamP"]) < min(v["lamN"]):
                    perfect += 1
        out[f"b157_n{n_}"]["lam_max_separates"] = perfect
        print(f"B157 n={n_}: pairs={len(feats)} mixed_degsum={len(mixed)} lam_separates={perfect}")

    # =========================================================
    # B162: mod 3/5 discrimination of center denominator
    # =========================================================
    print("=== B162 mod residue discrimination ===")
    # For n=5, all 4-point concyclic (non-collinear) sets: classify center denominator
    # and see if (x mod m, y mod m) of the 4 points predicts denominator.
    def circle_center(p0, p1, p2):
        """Return (num_x, num_y, den) of circumcenter of 3 points, or None if collinear."""
        ax, ay = p0; bx, by = p1; cx, cy = p2
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if d == 0:
            return None
        ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
              + (cx * cx + cy * cy) * (ay - by)) / d
        uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
              + (cx * cx + cy * cy) * (bx - ax)) / d
        # return exact rational as numerator/denominator
        from fractions import Fraction
        return Fraction(ux), Fraction(uy)

    def denom_class(fr: Fraction):
        return fr.denominator

    b162_data = {}
    for n_ in [5, 6]:
        pts = square_points(n_)
        centers = []
        # all 4-subsets that are concyclic non-collinear
        for comb in combinations(range(n_ * n_), 4):
            p4 = [pts[i] for i in comb]
            d = det4(
                (p4[0][0] ** 2 + p4[0][1] ** 2, p4[0][0], p4[0][1], 1),
                (p4[1][0] ** 2 + p4[1][1] ** 2, p4[1][0], p4[1][1], 1),
                (p4[2][0] ** 2 + p4[2][1] ** 2, p4[2][0], p4[2][1], 1),
                (p4[3][0] ** 2 + p4[3][1] ** 2, p4[3][0], p4[3][1], 1),
            )
            if d != 0:
                continue
            # check non-collinear (some triangle non-degenerate)
            c = circle_center(p4[0], p4[1], p4[2])
            if c is None:
                c = circle_center(p4[0], p4[1], p4[3])
                if c is None:
                    continue  # collinear
            cx, cy = c
            den = max(cx.denominator, cy.denominator)
            # residue signature mod m of the 4 points
            for m in [2, 3, 5]:
                sig = tuple(sorted((x % m, y % m) for x, y in p4))
                b162_data.setdefault(n_, {}).setdefault(m, {}).setdefault(sig, []).append(den)
        # compute discrimination: how well does sig predict den
        for m in [2, 3, 5]:
            groups = b162_data[n_][m]
            pure = sum(1 for v in groups.values() if len(set(v)) == 1)
            out[f"b162_n{n_}_m{m}"] = {
                "n_groups": len(groups),
                "n_pure": pure,
                "purity": pure / len(groups) if groups else 0,
                "sample": {str(k): sorted(set(v))[:8] for k, v in list(groups.items())[:5]},
            }
            print(f"B162 n={n_} m={m}: groups={len(groups)} pure={pure} purity={pure/len(groups):.2f}")

    # =========================================================
    # B177: 2-point removal subboards on n=4
    # =========================================================
    print("=== B177 n=4 2-point removal ===")
    board4 = Board(square_points(4))
    # all subboards obtained by removing 2 points from 16
    fvecs = {}
    for rem in combinations(range(16), 2):
        keep = [i for i in range(16) if i not in rem]
        # build subboard
        pts = [square_points(4)[i] for i in keep]
        sb = Board(pts)
        # f-vector of safe complex on this subboard
        # count safe sets by size via iterating subsets of 14 points - 2^14=16384 ok
        fv = Counter()
        for mask in range(1 << 14):
            if sb.is_safe(mask):
                fv[mask.bit_count()] += 1
        key = tuple(sorted(fv.items()))
        # nimber of empty position on subboard
        g = sb.solve_grundy().get(0, None)
        fvecs.setdefault(key, []).append((rem, g))
    # find same f-vector different g
    witness = None
    n_distinct_fv = len(fvecs)
    for key, items in fvecs.items():
        gs = set(g for _, g in items)
        if len(gs) > 1:
            witness = {"fv": key, "items": [(rem, g) for rem, g in items[:6]], "gs": sorted(gs)}
            break
    out["b177_n4_remove2"] = {
        "n_subboards": 120,
        "n_distinct_fv": n_distinct_fv,
        "witness": witness,
        "fv_sizes": {str(k): len(v) for k, v in list(fvecs.items())[:10]},
    }
    print("B177 n=4 rem2: distinct fv", n_distinct_fv, "witness", witness is not None)

    # =========================================================
    # B174: integer homology of Delta_4 via F_p Betti comparison
    # =========================================================
    print("=== B174 homology of Delta_4 ===")
    # faces = all safe subsets of 16 points
    faces_by_dim = defaultdict(list)  # dim -> list of masks
    for mask in range(1 << 16):
        if board4.is_safe(mask):
            d = mask.bit_count() - 1  # dim of simplex
            if d >= 0:
                faces_by_dim[d].append(mask)
            # empty face dim -1 ignored
    fvec = {d: len(v) for d, v in sorted(faces_by_dim.items())}
    print("Delta_4 f-vector (dim->count):", fvec)

    # Build boundary matrices over F_p and compute ranks
    # dim_map[d] = {mask: index}
    dim_maps = {}
    for d, masks in faces_by_dim.items():
        dim_maps[d] = {m: i for i, m in enumerate(masks)}

    def rank_mod_p(mat_rows, ncols, p):
        """mat_rows: list of lists (row-major sparse as list of (col,val)). Return rank."""
        # convert to dense rows for small matrices
        rows = []
        for r in mat_rows:
            row = [0] * ncols
            for c, v in r:
                row[c] = v % p
            rows.append(row)
        # Gaussian elimination
        rank = 0
        used = [False] * len(rows)
        for col in range(ncols):
            piv = None
            for i in range(len(rows)):
                if not used[i] and rows[i][col] % p != 0:
                    piv = i
                    break
            if piv is None:
                continue
            used[piv] = True
            rank += 1
            inv = pow(rows[piv][col], p - 2, p) if p > 2 else 1
            for i in range(len(rows)):
                if i != piv and rows[i][col] % p != 0:
                    factor = rows[i][col] * inv % p
                    for j in range(ncols):
                        rows[i][j] = (rows[i][j] - factor * rows[piv][j]) % p
        return rank

    def build_boundary(d):
        """Boundary ∂_d: C_d -> C_{d-1}. rows = faces of dim d-1, cols = faces of dim d.
        Returns list of sparse rows (each row is list of (col, coeff))."""
        if d == 0:
            return []
        src = faces_by_dim[d]
        tgt = faces_by_dim[d - 1]
        tmap = dim_maps[d - 1]
        rows = [[] for _ in tgt]
        for j, mask in enumerate(src):
            # faces of mask (remove one vertex)
            bits = [b for b in range(16) if mask & (1 << b)]
            for k, b in enumerate(bits):
                face = mask ^ (1 << b)
                coeff = 1 if k % 2 == 0 else -1
                ti = tmap[face]
                rows[ti].append((j, coeff))
        return rows

    max_dim = max(faces_by_dim.keys())
    ranks_mod = {}
    for p in [2, 3, 5, 7]:
        ranks = {}
        for d in range(1, max_dim + 1):
            rows = build_boundary(d)
            ncols = len(faces_by_dim[d])
            r = rank_mod_p(rows, ncols, p)
            ranks[d] = r
            print(f"  rank ∂_{d} mod {p} = {r} / {ncols}")
        # Betti numbers: b_k = dim C_k - rank ∂_k - rank ∂_{k+1}
        betti = {}
        for k in range(0, max_dim + 1):
            dimC = len(faces_by_dim[k])
            rk = ranks.get(k, 0)  # ∂_k : C_k -> C_{k-1}, rank contributes to im in C_{k-1}
            # careful: rank ∂_k is the rank of the map C_k -> C_{k-1}
            # b_k = dim ker ∂_k - rank ∂_{k+1}
            # dim ker ∂_k = dim C_k - rank ∂_k
            # so b_k = dim C_k - rank ∂_k - rank ∂_{k+1}
            rk_k = ranks.get(k, 0)       # rank of ∂_k (map from C_k)
            rk_k1 = ranks.get(k + 1, 0)  # rank of ∂_{k+1}
            betti[k] = dimC - rk_k - rk_k1
        ranks_mod[p] = {"ranks": ranks, "betti": betti}
        print(f"  Betti mod {p}: {betti}")

    # Also compute rational Betti via rank over Q using integer elimination
    def rank_Q(mat_rows, ncols):
        rows = []
        for r in mat_rows:
            row = [0] * ncols
            for c, v in r:
                row[c] = v
            rows.append(row)
        rank = 0
        used = [False] * len(rows)
        for col in range(ncols):
            piv = None
            for i in range(len(rows)):
                if not used[i] and rows[i][col] != 0:
                    piv = i
                    break
            if piv is None:
                continue
            used[piv] = True
            rank += 1
            pv = rows[piv][col]
            for i in range(len(rows)):
                if i != piv and rows[i][col] != 0:
                    factor_num = rows[i][col]
                    # row_i = row_i * pv - factor_num * row_piv  (to avoid fractions)
                    # actually simpler: scale to keep integers using gcd approach
                    # Use: row_i = pv*row_i - factor_num*row_piv
                    for j in range(ncols):
                        rows[i][j] = pv * rows[i][j] - factor_num * rows[piv][j]
                    # reduce by gcd to control growth
                    g = 0
                    for j in range(ncols):
                        if rows[i][j]:
                            g = abs(rows[i][j]) if g == 0 else __import__('math').gcd(g, abs(rows[i][j]))
                    if g > 1:
                        for j in range(ncols):
                            rows[i][j] //= g
        return rank

    ranks_Q = {}
    for d in range(1, max_dim + 1):
        rows = build_boundary(d)
        ncols = len(faces_by_dim[d])
        r = rank_Q(rows, ncols)
        ranks_Q[d] = r
        print(f"  rank ∂_{d} over Q = {r} / {ncols}")
    betti_Q = {}
    for k in range(0, max_dim + 1):
        dimC = len(faces_by_dim[k])
        rk_k = ranks_Q.get(k, 0)
        rk_k1 = ranks_Q.get(k + 1, 0)
        betti_Q[k] = dimC - rk_k - rk_k1
    print("Betti Q:", betti_Q)

    # torsion detection: if b_k(F_p) > b_k(Q) for some p, torsion of order divisible by p
    torsion = {}
    for p, data in ranks_mod.items():
        for k, bp in data["betti"].items():
            bq = betti_Q.get(k, 0)
            if bp > bq:
                torsion.setdefault(k, []).append((p, bp - bq))
    out["b174_delta4"] = {
        "fvec": fvec,
        "ranks_Q": ranks_Q,
        "betti_Q": betti_Q,
        "ranks_mod": {str(p): v for p, v in ranks_mod.items()},
        "torsion_detected": {str(k): v for k, v in torsion.items()},
    }
    print("Torsion detected:", torsion)

    # =========================================================
    # B195/B196: p_rand extremes on n=4,5 via exact DP (rational)
    # =========================================================
    print("=== B195/B196 p_rand extremes ===")
    from fractions import Fraction

    def prand_extremes(board: Board):
        memo = {}

        def pr(occ: int) -> Fraction:
            if occ in memo:
                return memo[occ]
            moves = board.legal_moves(occ)
            if not moves:
                memo[occ] = Fraction(0)  # player to move loses
                return memo[occ]
            # player wins if some move leads to opponent losing with prob...
            # p_rand = probability player-to-move wins under uniform random legal moves
            s = Fraction(0)
            for u in moves:
                # after move u, opponent is to move at occ|u; opponent's win prob is pr(occ|u)
                # player wins iff opponent loses, so player's win from this move = 1 - pr(occ|u)
                s += (1 - pr(occ | (1 << u)))
            memo[occ] = s / len(moves)
            return memo[occ]

        p0 = pr(0)
        # find min/max over all reachable? too many. sample safe sets of various sizes
        # instead compute pr for all safe sets of size k for small k
        return p0, memo

    # For n=4: exact p_rand of empty and of many positions
    p0_4, memo4 = prand_extremes(board4)
    # min/max among N and P positions with enough moves
    # classify: P = grundy 0
    g4 = board4.solve_grundy()
    minN = None  # (p, mask) N-position with min p_rand
    maxP = None  # P-position with max p_rand
    maxN = None
    minP = None
    for occ, g in g4.items():
        if occ == 0:
            continue
        pr_val = memo4.get(occ)
        if pr_val is None:
            # compute
            moves = board4.legal_moves(occ)
            if not moves:
                continue
            s = sum((1 - memo4.get(occ | (1 << u), None) or Fraction(0)) for u in moves)
            # recompute properly
            s = Fraction(0)
            ok = True
            for u in moves:
                child = occ | (1 << u)
                if child not in memo4:
                    ok = False
                    break
                s += 1 - memo4[child]
            if not ok:
                continue
            pr_val = s / len(moves)
        is_P = (g == 0)
        rec = (pr_val, occ, g)
        if is_P:
            if maxP is None or pr_val > maxP[0]:
                maxP = rec
            if minP is None or pr_val < minP[0]:
                minP = rec
        else:
            if minN is None or pr_val < minN[0]:
                minN = rec
            if maxN is None or pr_val > maxN[0]:
                maxN = rec

    out["b195_b196_n4"] = {
        "p_empty": str(p0_4),
        "minN": None if minN is None else {"p": str(minN[0]), "mask": minN[1], "g": minN[2]},
        "maxN": None if maxN is None else {"p": str(maxN[0]), "mask": maxN[1], "g": maxN[2]},
        "minP": None if minP is None else {"p": str(minP[0]), "mask": minP[1], "g": minP[2]},
        "maxP": None if maxP is None else {"p": str(maxP[0]), "mask": maxP[1], "g": maxP[2]},
    }
    print("B195/196 n=4:", out["b195_b196_n4"])

    # n=5: sample (full too heavy) - use maximal sets and some random safe sets
    # For B196 we want P-positions with high p_rand (near 1)
    # For B195 we want N-positions with low p_rand (near 0)
    # Compute p_rand for all 2-stone and some 3-stone positions on n=5
    p0_5, memo5 = prand_extremes(board5)
    g5full = board5.solve_grundy()
    # only positions already in memo5 (reachable from empty under random? no, pr computes all reachable)
    # memo5 has all positions reached by pr(0) recursion = all safe positions
    minN5 = maxN5 = minP5 = maxP5 = None
    for occ, g in g5full.items():
        if occ == 0:
            continue
        pr_val = memo5.get(occ)
        if pr_val is None:
            continue
        is_P = (g == 0)
        rec = (pr_val, occ, g, occ.bit_count())
        if is_P:
            if maxP5 is None or pr_val > maxP5[0]:
                maxP5 = rec
            if minP5 is None or pr_val < minP5[0]:
                minP5 = rec
        else:
            if minN5 is None or pr_val < minN5[0]:
                minN5 = rec
            if maxN5 is None or pr_val > maxN5[0]:
                maxN5 = rec
    out["b195_b196_n5"] = {
        "p_empty": str(p0_5),
        "n_positions": len(g5full),
        "minN": None if minN5 is None else {"p": str(minN5[0]), "mask": minN5[1], "g": minN5[2], "k": minN5[3]},
        "maxN": None if maxN5 is None else {"p": str(maxN5[0]), "mask": maxN5[1], "g": maxN5[2], "k": maxN5[3]},
        "minP": None if minP5 is None else {"p": str(minP5[0]), "mask": minP5[1], "g": minP5[2], "k": minP5[3]},
        "maxP": None if maxP5 is None else {"p": str(maxP5[0]), "mask": maxP5[1], "g": maxP5[2], "k": maxP5[3]},
    }
    print("B195/196 n=5:", {k: str(v) for k, v in out["b195_b196_n5"].items()})

    # =========================================================
    # B189: last legal point bias (n=4,5 random games) + B190 drops
    # =========================================================
    print("=== B189/B190 random game stats ===")
    rng = random.Random(42)
    for n_, bm in [(4, board4), (5, board5)]:
        last_degs = []
        drop_corr = []  # (pred_residual, actual_drop)
        for trial in range(2000):
            occ = 0
            Lhist = []
            while True:
                legal = bm.legal_moves(occ)
                Lhist.append(len(legal))
                if not legal:
                    break
                u = legal[rng.randrange(len(legal))]
                occ |= 1 << u
            # last legal point = the last move's point
            # recover: the final occ, the last added point
            # we don't track it; recompute: points in occ that were last
            # instead track during play
            # re-do with tracking
            occ = 0
            last_pt = None
            Lseries = []
            Rseries = []  # residual 2-point and 3-point constraints count
            while True:
                legal = bm.legal_moves(occ)
                Lseries.append(len(legal))
                # residual: count 2-subsets and 3-subsets of empty that extend to legal
                empty = [i for i in range(bm.V) if not (occ >> i) & 1]
                # 2-point constraints: pairs in empty that are still free
                # 3-point: triples in empty that are still free (can be added)
                # approximate: number of free pairs / free triples
                n2 = 0
                n3 = 0
                for a, b in combinations(empty, 2):
                    if bm.is_safe(occ | (1 << a) | (1 << b)):
                        n2 += 1
                for a, b, c in combinations(empty, 3):
                    if bm.is_safe(occ | (1 << a) | (1 << b) | (1 << c)):
                        n3 += 1
                Rseries.append((n2, n3))
                if not legal:
                    break
                u = legal[rng.randrange(len(legal))]
                last_pt = u
                occ |= 1 << u
            if last_pt is not None:
                d = point_degree(bm, last_pt)
                last_degs.append(d)
            # drop correlation: L[i]-L[i+1] vs n3[i] (incomplete triples)
            for i in range(len(Lseries) - 1):
                drop = Lseries[i] - Lseries[i + 1]
                drop_corr.append((Rseries[i][1], drop, Rseries[i][0]))
        # B189: compare last_pt degree distribution vs uniform
        all_degs = [point_degree(bm, i) for i in range(bm.V)]
        uniform_mean = sum(all_degs) / len(all_degs)
        last_mean = sum(last_degs) / len(last_degs) if last_degs else 0
        # low-degree fraction
        med = sorted(all_degs)[len(all_degs) // 2]
        low_uniform = sum(1 for d in all_degs if d < med) / len(all_degs)
        low_last = sum(1 for d in last_degs if d < med) / len(last_degs) if last_degs else 0
        out[f"b189_n{n_}"] = {
            "n_trials": 2000,
            "uniform_mean_deg": uniform_mean,
            "last_mean_deg": last_mean,
            "low_deg_frac_uniform": low_uniform,
            "low_deg_frac_last": low_last,
            "bias_ratio": low_last / low_uniform if low_uniform else None,
        }
        # B190: correlation between n3 and drop
        if drop_corr:
            xs = [c[0] for c in drop_corr]
            ys = [c[1] for c in drop_corr]
            mx = sum(xs) / len(xs)
            my = sum(ys) / len(ys)
            cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)
            sx = (sum((x - mx) ** 2 for x in xs) / len(xs)) ** 0.5
            sy = (sum((y - my) ** 2 for y in ys) / len(ys)) ** 0.5
            corr = cov / (sx * sy) if sx * sy else 0
            out[f"b190_n{n_}"] = {
                "n_samples": len(drop_corr),
                "corr_n3_drop": corr,
                "corr_n2_drop": None,
            }
            # n2 correlation
            xs2 = [c[2] for c in drop_corr]
            mx2 = sum(xs2) / len(xs2)
            cov2 = sum((x - mx2) * (y - my) for x, y in zip(xs2, ys)) / len(xs2)
            sx2 = (sum((x - mx2) ** 2 for x in xs2) / len(xs2)) ** 0.5
            out[f"b190_n{n_}"]["corr_n2_drop"] = cov2 / (sx2 * sy) if sx2 * sy else 0
        print(f"B189 n={n_}: last_mean={last_mean:.1f} uniform={uniform_mean:.1f} bias={out[f'b189_n{n_}']['bias_ratio']}")
        print(f"B190 n={n_}: corr_n3={out[f'b190_n{n_}'].get('corr_n3_drop')}")

    # =========================================================
    # B197/B198/B199/B200 statistical features on n=5
    # =========================================================
    print("=== B197-B200 features n=5 ===")
    # For all safe positions with k=3..7 on n=5, compute features and P/N
    # Sample to keep runtime reasonable
    outcomes5 = g5full  # g value; P iff g==0
    feats5 = []
    # iterate all safe sets of size 3,4,5 from safe_n5 data... use board
    # For speed, sample random safe sets
    all_safe_by_k = defaultdict(list)
    for mask in range(1 << 25):  # too many! use the bin file
        break
    # load safe_n5.bin
    import struct
    raw = Path(__file__).resolve().parent.parent / "data" / "safe_n5.bin"
    data = raw.read_bytes()
    nsets = len(data) // 8
    vals = struct.unpack(f"<{nsets}Q", data)
    print(f"loaded {nsets} safe sets for n=5")
    # sample up to 3000 sets of size 3..7
    rng2 = random.Random(0)
    by_k = defaultdict(list)
    for v in vals:
        k = bin(v).count("1")
        if 3 <= k <= 7:
            by_k[k].append(v)
    sample = []
    for k, lst in by_k.items():
        if len(lst) > 800:
            sample.extend(rng2.sample(lst, 800))
        else:
            sample.extend(lst)
    print(f"sampled {len(sample)} positions")

    for mask in sample:
        k = mask.bit_count()
        occ = mask
        legal = bm_legal = board5.legal_moves(occ)
        # degree sum
        pts_in = [i for i in range(25) if mask & (1 << i)]
        deg_sum = sum(point_degree(board5, i) for i in pts_in)
        # unique gain: for each empty p, how many forbidden quads become blocked? or
        # "unique gain" = number of quads that only this move blocks
        # define: gain(p) = number of quads containing p that have exactly 3 points in occ
        ugains = []
        for p in legal:
            ug = 0
            for q in board5.quads_by_pt[p]:
                if (q & occ).bit_count() == 3 and (q & (1 << p)) == 0:
                    # wait p should be in q
                    pass
            # correct: quads containing p where the other 3 are in occ
            ug = sum(1 for q in board5.quads_by_pt[p] if (q & occ).bit_count() == 3)
            ugains.append(ug)
        max_ug = max(ugains) if ugains else 0
        mean_ug = sum(ugains) / len(ugains) if ugains else 0
        g = outcomes5.get(mask, None)
        if g is None:
            continue
        # residual 2-point edges among empty
        empty = [i for i in range(25) if not (mask >> i) & 1]
        r2 = 0
        for a, b in combinations(empty, 2):
            if board5.is_safe(mask | (1 << a) | (1 << b)):
                r2 += 1
        feats5.append({
            "k": k, "mask": mask, "g": g, "pn": 1 if g != 0 else 0,
            "deg_sum": deg_sum, "n_legal": len(legal),
            "max_ug": max_ug, "mean_ug": mean_ug, "r2": r2,
            "sat": k / 9.0,  # K_5 = 9? check; actually max safe is 9
            "Lfrac": len(legal) / 25.0,
        })

    # B198: interaction of deg_sum and max_ug
    # simple: rank correlation of (deg_sum * max_ug) vs P
    def point_biserial(xs, ys):
        if not xs:
            return 0
        mx = sum(xs) / len(xs)
        my = sum(ys) / len(ys)
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)
        sx = (sum((x - mx) ** 2 for x in xs) / len(xs)) ** 0.5
        sy = (sum((y - my) ** 2 for y in ys) / len(ys)) ** 0.5
        return cov / (sx * sy) if sx * sy else 0

    pns = [f["pn"] for f in feats5]
    ds = [f["deg_sum"] for f in feats5]
    ug = [f["max_ug"] for f in feats5]
    inter = [d * u for d, u in zip(ds, ug)]
    # rank disagreement
    def ranks(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0] * len(xs)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    r_ds = ranks(ds)
    r_ug = ranks(ug)
    disagree = sum(1 for a, b in zip(r_ds, r_ug) if abs(a - b) > len(ds) // 4)
    out["b198_n5"] = {
        "n_sample": len(feats5),
        "corr_degsum_pn": point_biserial(ds, pns),
        "corr_maxug_pn": point_biserial(ug, pns),
        "corr_inter_pn": point_biserial(inter, pns),
        "rank_disagree_frac": disagree / len(ds) if ds else 0,
    }
    print("B198:", out["b198_n5"])

    # B197: child residual diversity for P vs N
    # for each position, compute variance of r2 among children
    p_child_var = []
    n_child_var = []
    for f in feats5[:1500]:
        occ = f["mask"]
        legal = board5.legal_moves(occ)
        if len(legal) < 2:
            continue
        childs_r2 = []
        for p in legal:
            child = occ | (1 << p)
            empty = [i for i in range(25) if not (child >> i) & 1]
            r2c = 0
            for a, b in combinations(empty, 2):
                if board5.is_safe(child | (1 << a) | (1 << b)):
                    r2c += 1
            childs_r2.append(r2c)
        if len(childs_r2) < 2:
            continue
        mean_c = sum(childs_r2) / len(childs_r2)
        var_c = sum((x - mean_c) ** 2 for x in childs_r2) / len(childs_r2)
        if f["pn"] == 1:
            n_child_var.append(var_c)  # N position (winning for player to move)
        else:
            p_child_var.append(var_c)
    out["b197_n5"] = {
        "n_P": len(p_child_var), "n_N": len(n_child_var),
        "mean_var_P": sum(p_child_var) / len(p_child_var) if p_child_var else None,
        "mean_var_N": sum(n_child_var) / len(n_child_var) if n_child_var else None,
    }
    print("B197:", out["b197_n5"])

    # B199: saturation rate vs raw k
    # P-rate by k and by k/9
    by_k_pr = defaultdict(lambda: [0, 0])
    for f in feats5:
        by_k_pr[f["k"]][0] += f["pn"]
        by_k_pr[f["k"]][1] += 1
    out["b199_n5"] = {
        "pr_by_k": {k: {"P": v[0], "n": v[1], "rate": v[0] / v[1]} for k, v in sorted(by_k_pr.items())},
        "K5": 9,
    }
    print("B199:", out["b199_n5"]["pr_by_k"])

    # B200: two axes - features for P vs features for high g among N
    Npos = [f for f in feats5 if f["pn"] == 1]  # N = winning = g>0
    if Npos:
        # rank correlation of each feature with g among N
        gvals = [f["g"] for f in Npos]
        corrs = {}
        for key in ["deg_sum", "max_ug", "mean_ug", "n_legal", "r2", "k"]:
            xs = [f[key] for f in Npos]
            corrs[key] = point_biserial(xs, gvals)
        # also corr with P/N overall
        corrs_pn = {}
        for key in ["deg_sum", "max_ug", "mean_ug", "n_legal", "r2", "k"]:
            xs = [f[key] for f in feats5]
            corrs_pn[key] = point_biserial(xs, pns)
        out["b200_n5"] = {
            "corr_with_g_among_N": corrs,
            "corr_with_pn": corrs_pn,
            "n_N": len(Npos),
            "g_range": [min(gvals), max(gvals)],
        }
        print("B200:", out["b200_n5"])

    # =========================================================
    # B169: same residue pattern, different outcome (larger m)
    # =========================================================
    print("=== B169 same residue different outcome ===")
    # On n=6 (or rectangular), find two 1-stone or 2-stone positions
    # with same coords mod m but different P/N.
    # For 1-stone: position mask=1<<i, outcome = win(empty|i)
    # We already have first6 for n=6.
    # Group by (x mod m, y mod m)
    b169 = {}
    for m in [2, 3, 4, 5]:
        groups = defaultdict(list)
        for i in range(36):
            x, y = i % 6, i // 6
            groups[(x % m, y % m)].append((i, first6[i]))
        mixed = {str(k): v for k, v in groups.items() if len(set(w for _, w in v)) > 1}
        b169[f"m{m}"] = {
            "n_groups": len(groups),
            "n_mixed": len(mixed),
            "mixed_sample": {k: v for k, v in list(mixed.items())[:4]},
        }
        print(f"B169 m={m}: groups={len(groups)} mixed={len(mixed)}")
    out["b169_n6"] = b169

    # Also 2-stone positions on n=5 grouped by all coords mod m
    outcomes5_map = outcomes5
    for m in [4, 5, 6]:
        groups = defaultdict(list)
        for p, q in combinations(range(25), 2):
            mask = (1 << p) | (1 << q)
            if mask not in outcomes5_map:
                continue
            x1, y1 = p % 5, p // 5
            x2, y2 = q % 5, q // 5
            sig = tuple(sorted([(x1 % m, y1 % m), (x2 % m, y2 % m)]))
            groups[sig].append(outcomes5_map[mask])
        mixed = {str(k): sorted(set(v)) for k, v in groups.items() if len(set(v)) > 1}
        out[f"b169_n5_2stone_m{m}"] = {
            "n_groups": len(groups),
            "n_mixed": len(mixed),
            "sample": {k: v for k, v in list(mixed.items())[:4]},
        }
        print(f"B169 n=5 2stone m={m}: groups={len(groups)} mixed={len(mixed)}")

    # =========================================================
    # B193: degree-sum sign flip vs residual edge ratio (n=5)
    # =========================================================
    print("=== B193 layered analysis ===")
    # For n=5 positions, compute corr(deg_sum, P) by layer (k) and by r2 ratio
    layers = defaultdict(list)
    for f in feats5:
        ratio = f["r2"] / max(1, f["n_legal"] * 10)  # crude
        layers[f["k"]].append(f)
    out["b193_n5"] = {"by_k": {}}
    for k, lst in sorted(layers.items()):
        # split by median r2
        r2s = [f["r2"] for f in lst]
        med_r2 = sorted(r2s)[len(r2s) // 2]
        low = [f for f in lst if f["r2"] <= med_r2]
        high = [f for f in lst if f["r2"] > med_r2]
        def corr_dspn(sub):
            if not sub:
                return None
            return point_biserial([f["deg_sum"] for f in sub], [f["pn"] for f in sub])
        out["b193_n5"]["by_k"][str(k)] = {
            "corr_low_r2": corr_dspn(low),
            "corr_high_r2": corr_dspn(high),
            "n_low": len(low), "n_high": len(high),
        }
    print("B193:", out["b193_n5"]["by_k"])

    # =========================================================
    # B170: max-set counts (already known n=3..7) + n=6 max count
    # =========================================================
    print("=== B170 max set counts ===")
    # from data files
    import struct as st
    def load_max(n):
        raw = (Path(__file__).resolve().parent.parent / "data" / f"maximal_n{n}.bin").read_bytes()
        return list(st.unpack(f"<{len(raw)//8}Q", raw))
    max_counts = {}
    for n_ in [2, 3, 4, 5]:
        ms = load_max(n_)
        sizes = [bin(m).count("1") for m in ms]
        mx = max(sizes)
        max_counts[n_] = {
            "n_maximal": len(ms),
            "max_size": mx,
            "n_max_size_sets": sum(1 for s in sizes if s == mx),
        }
    # n=6: 349596 maximal, max size 11 - count size-11
    ms6 = load_max(6)
    sizes6 = [bin(m).count("1") for m in ms6]
    max_counts[6] = {
        "n_maximal": len(ms6),
        "max_size": max(sizes6),
        "n_max_size_sets": sum(1 for s in sizes6 if s == max(sizes6)),
    }
    # n=7 known: 16 max sets of size 14
    max_counts[7] = {"n_maximal": None, "max_size": 14, "n_max_size_sets": 16, "source": "known"}
    out["b170_counts"] = max_counts
    print("B170:", max_counts)

    # =========================================================
    # Write
    # =========================================================
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    print("Wrote", OUT)


if __name__ == "__main__":
    main()

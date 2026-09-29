#!/usr/bin/env python3
"""Targeted computations for B151-B200 (round5 additional). Fast parts."""
from __future__ import annotations
import json, sys, random, struct, math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from fractions import Fraction

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points

OUT = Path(__file__).resolve().parent.parent / "round5_b151_compute.json"
DATA = Path(__file__).resolve().parent.parent / "data"


def d4_orbit(x, y, n):
    pts = set()
    for rx, ry in [(x, y), (y, x), (x, n - 1 - y), (n - 1 - y, x),
                   (n - 1 - x, y), (y, n - 1 - x), (n - 1 - x, n - 1 - y), (n - 1 - y, n - 1 - x)]:
        pts.add((rx, ry))
    return min(pts)


def point_degree(board: Board, i: int) -> int:
    return len(board.quads_by_pt[i])


def point_biserial(xs, ys):
    if not xs:
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)
    sx = (sum((x - mx) ** 2 for x in xs) / len(xs)) ** 0.5
    sy = (sum((y - my) ** 2 for y in ys) / len(ys)) ** 0.5
    return cov / (sx * sy) if sx * sy else 0.0


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0] * len(xs)
    for pos, i in enumerate(order):
        r[i] = pos
    return r


def main():
    out = {}
    n5 = 5
    board5 = Board(square_points(n5))
    board4 = Board(square_points(4))
    V5 = 25
    degs5 = [point_degree(board5, i) for i in range(V5)]

    # =========================================================
    print("=== B158 non-empty S ===", flush=True)
    inversions = []
    maxmin_inv = None
    checked = 0
    # |S|=3
    for comb in combinations(range(V5), 3):
        s_mask = (1 << comb[0]) | (1 << comb[1]) | (1 << comb[2])
        if not board5.is_safe(s_mask):
            continue
        legal = board5.legal_moves(s_mask)
        if len(legal) < 2:
            continue
        Lvals = {}
        for p in legal:
            Lvals[p] = len(board5.legal_moves(s_mask | (1 << p)))
        for p, q in combinations(legal, 2):
            if degs5[p] > degs5[q] and Lvals[p] > Lvals[q]:
                inversions.append((s_mask, p, q, degs5[p], degs5[q], Lvals[p], Lvals[q]))
                break
            if degs5[q] > degs5[p] and Lvals[q] > Lvals[p]:
                inversions.append((s_mask, q, p, degs5[q], degs5[p], Lvals[q], Lvals[p]))
                break
        pmax = max(legal, key=lambda i: degs5[i])
        pmin = min(legal, key=lambda i: degs5[i])
        if pmax != pmin and degs5[pmax] > degs5[pmin] and Lvals[pmax] > Lvals[pmin]:
            maxmin_inv = (s_mask, pmax, pmin, degs5[pmax], degs5[pmin], Lvals[pmax], Lvals[pmin])
        checked += 1
        if len(inversions) >= 5 and maxmin_inv:
            break
    out["b158_S3"] = {
        "n_checked": checked,
        "n_inversions": len(inversions),
        "inversions": [{"S_mask": s, "p": p, "q": q, "dp": dp, "dq": dq, "Lp": Lp, "Lq": Lq}
                       for s, p, q, dp, dq, Lp, Lq in inversions[:5]],
        "maxmin_witness": None if maxmin_inv is None else {
            "S_mask": maxmin_inv[0], "p": maxmin_inv[1], "q": maxmin_inv[2],
            "dp": maxmin_inv[3], "dq": maxmin_inv[4], "Lp": maxmin_inv[5], "Lq": maxmin_inv[6]},
    }
    print("B158 S3:", out["b158_S3"]["n_inversions"], "maxmin", maxmin_inv is not None, flush=True)

    if not maxmin_inv or len(inversions) < 2:
        # |S|=4
        for comb in combinations(range(V5), 4):
            s_mask = 0
            for i in comb:
                s_mask |= 1 << i
            if not board5.is_safe(s_mask):
                continue
            legal = board5.legal_moves(s_mask)
            if len(legal) < 2:
                continue
            Lvals = {}
            for p in legal:
                Lvals[p] = len(board5.legal_moves(s_mask | (1 << p)))
            for p, q in combinations(legal, 2):
                if degs5[p] > degs5[q] and Lvals[p] > Lvals[q]:
                    inversions.append((s_mask, p, q, degs5[p], degs5[q], Lvals[p], Lvals[q]))
                    break
                if degs5[q] > degs5[p] and Lvals[q] > Lvals[p]:
                    inversions.append((s_mask, q, p, degs5[q], degs5[p], Lvals[q], Lvals[p]))
                    break
            pmax = max(legal, key=lambda i: degs5[i])
            pmin = min(legal, key=lambda i: degs5[i])
            if pmax != pmin and degs5[pmax] > degs5[pmin] and Lvals[pmax] > Lvals[pmin]:
                maxmin_inv = (s_mask, pmax, pmin, degs5[pmax], degs5[pmin], Lvals[pmax], Lvals[pmin])
            checked += 1
            if len(inversions) >= 5 and maxmin_inv:
                break
        out["b158_S4"] = {
            "n_checked_total": checked,
            "n_inversions": len(inversions),
            "maxmin_witness": None if maxmin_inv is None else {
                "S_mask": maxmin_inv[0], "p": maxmin_inv[1], "q": maxmin_inv[2],
                "dp": maxmin_inv[3], "dq": maxmin_inv[4], "Lp": maxmin_inv[5], "Lq": maxmin_inv[6]},
            "inversions": [{"S_mask": s, "p": p, "q": q, "dp": dp, "dq": dq, "Lp": Lp, "Lq": Lq}
                           for s, p, q, dp, dq, Lp, Lq in inversions[:5]],
        }
        print("B158 S4:", out["b158_S4"]["n_inversions"], "maxmin", maxmin_inv is not None, flush=True)

    # =========================================================
    print("=== B159 degree increment ===", flush=True)
    b5 = board5
    b6 = Board(square_points(6))
    b7 = Board(square_points(7))
    deg6 = [point_degree(b6, i) for i in range(36)]
    deg7 = [point_degree(b7, i) for i in range(49)]
    inc = []
    for y in range(5):
        for x in range(5):
            i5, i6 = y * 5 + x, y * 6 + x
            inc.append((x, y, degs5[i5], deg6[i6], deg6[i6] - degs5[i5]))
    by_dist = defaultdict(list)
    for x, y, d5, d6, di in inc:
        by_dist[(x - 2) ** 2 + (y - 2) ** 2].append(di)
    center_inc = [di for x, y, a, b, di in inc if (x - 2) ** 2 + (y - 2) ** 2 <= 1]
    bound_inc = [di for x, y, a, b, di in inc if (x - 2) ** 2 + (y - 2) ** 2 >= 4]
    out["b159_inc_5to6"] = {
        "by_r2": {str(k): {"min": min(v), "max": max(v), "mean": sum(v) / len(v), "n": len(v)}
                  for k, v in sorted(by_dist.items())},
        "center_mean": sum(center_inc) / len(center_inc),
        "boundary_mean": sum(bound_inc) / len(bound_inc),
        "ratio": (sum(center_inc) / len(center_inc)) / (sum(bound_inc) / len(bound_inc)),
    }
    print("B159 5to6 ratio:", out["b159_inc_5to6"]["ratio"], flush=True)

    inc67 = []
    for y in range(6):
        for x in range(6):
            i6, i7 = y * 6 + x, y * 7 + x
            inc67.append((x, y, deg6[i6], deg7[i7], deg7[i7] - deg6[i6]))
    by_dist7 = defaultdict(list)
    for x, y, a, b, di in inc67:
        by_dist7[(x - 2.5) ** 2 + (y - 2.5) ** 2].append(di)
    center7 = [di for x, y, a, b, di in inc67 if (x - 2.5) ** 2 + (y - 2.5) ** 2 <= 2.0]
    bound7 = [di for x, y, a, b, di in inc67 if (x - 2.5) ** 2 + (y - 2.5) ** 2 >= 8.0]
    out["b159_inc_6to7"] = {
        "by_r2": {str(k): {"min": min(v), "max": max(v), "mean": sum(v) / len(v), "n": len(v)}
                  for k, v in sorted(by_dist7.items())},
        "center_mean": sum(center7) / len(center7),
        "boundary_mean": sum(bound7) / len(bound7),
        "ratio": (sum(center7) / len(center7)) / (sum(bound7) / len(bound7)),
    }
    print("B159 6to7 ratio:", out["b159_inc_6to7"]["ratio"], flush=True)

    # =========================================================
    print("=== B160 first-move g / win ===", flush=True)
    g5 = board5.solve_grundy()
    first5 = {i: g5.get(1 << i) for i in range(25)}
    bydeg = defaultdict(list)
    for i in range(25):
        bydeg[degs5[i]].append(i)
    b160_w = None
    groups = {}
    for d, pts in sorted(bydeg.items()):
        orbits = {}
        for i in pts:
            orbits.setdefault(d4_orbit(i % 5, i // 5, 5), []).append(i)
        gs = set(first5[i] for i in pts)
        groups[str(d)] = {
            "n_points": len(pts), "n_orbits": len(orbits),
            "g_values": sorted(gs),
            "orbit_g": {str(k): first5[v[0]] for k, v in orbits.items()},
        }
        if len(gs) > 1 and len(orbits) > 1:
            items = sorted((first5[v[0]], k, v) for k, v in orbits.items())
            b160_w = {"degree": d, "g_min": items[0][0], "g_max": items[-1][0],
                      "orbit_min": items[0][1], "orbit_max": items[-1][1],
                      "pts_min": items[0][2], "pts_max": items[-1][2]}
    out["b160_n5"] = {"groups": groups, "witness": b160_w}
    print("B160 n=5 witness:", b160_w, flush=True)

    # n=6 first-move P/N: use precomputed if available, else skip full solve
    # Full win6 over 2^36 is too slow in Python; compute only via limited DFS
    # from each 1-stone position with a node budget.
    board6 = b6
    degs6 = deg6
    out["b160_n6"] = {"note": "full first-move solve skipped (2^36 too large in Python); see b160_n5 and degree groups"}
    # Still record degree / D4 orbit groups for n=6
    bydeg6 = defaultdict(list)
    for i in range(36):
        bydeg6[degs6[i]].append(i)
    groups6 = {}
    for d, pts in sorted(bydeg6.items()):
        orbits = {}
        for i in pts:
            orbits.setdefault(d4_orbit(i % 6, i // 6, 6), []).append(i)
        groups6[str(d)] = {"n_points": len(pts), "n_orbits": len(orbits),
                           "orbit_pts": {str(k): v for k, v in orbits.items()}}
    out["b160_n6"]["groups"] = groups6
    # B169 still needs first6 for 1-stone on n=6 -- use n=5 2-stone / n=4 instead.
    first6 = {}

    # =========================================================
    print("=== B157 matrix features ===", flush=True)
    for n_, bm, degs_ in [(4, board4, [point_degree(board4, i) for i in range(16)]),
                          (5, board5, degs5)]:
        V_ = n_ * n_
        outcomes = bm.solve_outcomes()
        feats = []
        for p, q in combinations(range(V_), 2):
            m = (1 << p) | (1 << q)
            if not bm.is_safe(m):
                continue
            shared = len(set(bm.quads_by_pt[p]) & set(bm.quads_by_pt[q]))
            dp, dq = degs_[p], degs_[q]
            disc = (dp - dq) ** 2 + 4 * shared * shared
            lam1 = (dp + dq + disc ** 0.5) / 2
            feats.append({
                "dp": dp, "dq": dq, "shared": shared,
                "pn": outcomes.get(m, -1),
                "lam_max": lam1,
                "deg_sum": dp + dq,
            })
        by_sum = defaultdict(lambda: {"P": [], "N": []})
        for f in feats:
            by_sum[f["deg_sum"]]["P" if f["pn"] == 1 else "N"].append(f)
        mixed = {k: v for k, v in by_sum.items() if v["P"] and v["N"]}
        perfect = 0
        mixed_detail = {}
        for k, v in mixed.items():
            lamP = [x["lam_max"] for x in v["P"]]
            lamN = [x["lam_max"] for x in v["N"]]
            shP = [x["shared"] for x in v["P"]]
            shN = [x["shared"] for x in v["N"]]
            if (min(lamP) > max(lamN)) or (max(lamP) < min(lamN)):
                perfect += 1
            if len(mixed_detail) < 6:
                mixed_detail[str(k)] = {
                    "P": len(v["P"]), "N": len(v["N"]),
                    "lamP": [round(x, 1) for x in lamP[:4]], "lamN": [round(x, 1) for x in lamN[:4]],
                    "shP": shP[:4], "shN": shN[:4],
                }
        out[f"b157_n{n_}"] = {
            "n_pairs": len(feats),
            "n_P": sum(1 for f in feats if f["pn"] == 1),
            "n_N": sum(1 for f in feats if f["pn"] == 0),
            "n_mixed_degsum": len(mixed),
            "lam_max_separates": perfect,
            "mixed_detail": mixed_detail,
        }
        print(f"B157 n={n_}: mixed={len(mixed)} separates={perfect}", flush=True)

    # =========================================================
    print("=== B162 residue discrimination ===", flush=True)
    def circumcenter_frac(p0, p1, p2):
        ax, ay = p0; bx, by = p1; cx, cy = p2
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if d == 0:
            return None
        ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
              + (cx * cx + cy * cy) * (ay - by)) / d
        uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
              + (cx * cx + cy * cy) * (bx - ax)) / d
        return Fraction(ux).limit_denominator(10000), Fraction(uy).limit_denominator(10000)

    from fractions import Fraction as Fr
    def circ3(p0, p1, p2):
        ax, ay = p0; bx, by = p1; cx, cy = p2
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if d == 0:
            return None
        ux = Fr((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
                + (cx * cx + cy * cy) * (ay - by), d)
        uy = Fr((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
                + (cx * cx + cy * cy) * (bx - ax), d)
        return ux, uy

    for n_ in [5]:
        pts = square_points(n_)
        # only non-collinear concyclic 4-sets; classify center den and residue sig
        stats = {m: {} for m in [2, 3, 5]}
        den_hist = Counter()
        n_circ = 0
        for comb in combinations(range(n_ * n_), 4):
            p4 = [pts[i] for i in comb]
            d = det4(
                (p4[0][0]**2 + p4[0][1]**2, p4[0][0], p4[0][1], 1),
                (p4[1][0]**2 + p4[1][1]**2, p4[1][0], p4[1][1], 1),
                (p4[2][0]**2 + p4[2][1]**2, p4[2][0], p4[2][1], 1),
                (p4[3][0]**2 + p4[3][1]**2, p4[3][0], p4[3][1], 1),
            )
            if d != 0:
                continue
            c = circ3(p4[0], p4[1], p4[2])
            if c is None:
                c = circ3(p4[0], p4[1], p4[3])
                if c is None:
                    continue
            cx, cy = c
            den = max(cx.denominator, cy.denominator)
            den_hist[den] += 1
            n_circ += 1
            for m in [2, 3, 5]:
                sig = tuple(sorted((x % m, y % m) for x, y in p4))
                stats[m].setdefault(sig, set()).add(den)
        for m in [2, 3, 5]:
            groups = stats[m]
            pure = sum(1 for v in groups.values() if len(v) == 1)
            out[f"b162_n{n_}_m{m}"] = {
                "n_groups": len(groups), "n_pure": pure,
                "purity": pure / len(groups) if groups else 0,
                "sample": {str(k): sorted(v)[:8] for k, v in list(groups.items())[:6]},
            }
            print(f"B162 n={n_} m={m}: pure={pure}/{len(groups)}", flush=True)
        out[f"b162_n{n_}_den_hist"] = dict(den_hist)
        out[f"b162_n{n_}_n_circ"] = n_circ
        print("den_hist:", dict(den_hist), flush=True)

    # =========================================================
    print("=== B177 n=4 remove 2 ===", flush=True)
    pts4 = square_points(4)
    fvecs = {}
    for rem in combinations(range(16), 2):
        keep = [i for i in range(16) if i not in rem]
        sb = Board([pts4[i] for i in keep])
        fv = Counter()
        for mask in range(1 << 14):
            if sb.is_safe(mask):
                fv[mask.bit_count()] += 1
        key = tuple(sorted(fv.items()))
        g = sb.solve_grundy().get(0)
        fvecs.setdefault(key, []).append((rem, g))
    witness = None
    for key, items in fvecs.items():
        gs = set(g for _, g in items)
        if len(gs) > 1:
            witness = {"fv": str(key), "gs": sorted(gs), "items": items[:6]}
            break
    out["b177_n4_rem2"] = {
        "n_subboards": 120, "n_distinct_fv": len(fvecs),
        "witness": witness,
        "group_sizes": [len(v) for v in fvecs.values()],
    }
    print("B177 rem2: fv", len(fvecs), "witness", witness is not None, flush=True)

    # =========================================================
    print("=== B195/B196 p_rand n=4 ===", flush=True)
    def prand_full(board: Board):
        memo = {}
        def pr(occ: int) -> Fraction:
            if occ in memo:
                return memo[occ]
            moves = board.legal_moves(occ)
            if not moves:
                memo[occ] = Fraction(0)
                return memo[occ]
            s = Fraction(0)
            for u in moves:
                s += 1 - pr(occ | (1 << u))
            memo[occ] = s / len(moves)
            return memo[occ]
        p0 = pr(0)
        return p0, memo

    p0_4, memo4 = prand_full(board4)
    g4 = board4.solve_grundy()
    minN = maxN = minP = maxP = None
    for occ, g in g4.items():
        if occ == 0:
            continue
        pr_val = memo4.get(occ)
        if pr_val is None:
            continue
        rec = (pr_val, occ, g, occ.bit_count())
        if g == 0:
            if maxP is None or pr_val > maxP[0]:
                maxP = rec
            if minP is None or pr_val < minP[0]:
                minP = rec
        else:
            if minN is None or pr_val < minN[0]:
                minN = rec
            if maxN is None or pr_val > maxN[0]:
                maxN = rec
    def fmt(rec):
        return None if rec is None else {"p": str(rec[0]), "mask": rec[1], "g": rec[2], "k": rec[3]}
    out["b195_b196_n4"] = {
        "p_empty": str(p0_4),
        "minN": fmt(minN), "maxN": fmt(maxN), "minP": fmt(minP), "maxP": fmt(maxP),
    }
    print("B195/196 n=4:", out["b195_b196_n4"], flush=True)

    # n=5 full p_rand (151k states) - OK with Fraction but may take a minute
    print("=== B195/B196 p_rand n=5 ===", flush=True)
    p0_5, memo5 = prand_full(board5)
    g5full = g5
    minN5 = maxN5 = minP5 = maxP5 = None
    for occ, g in g5full.items():
        if occ == 0:
            continue
        pr_val = memo5.get(occ)
        if pr_val is None:
            continue
        rec = (pr_val, occ, g, occ.bit_count())
        if g == 0:
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
        "minN": fmt(minN5), "maxN": fmt(maxN5), "minP": fmt(minP5), "maxP": fmt(maxP5),
    }
    print("B195/196 n=5:", {k: str(v) for k, v in out["b195_b196_n5"].items()}, flush=True)

    # =========================================================
    print("=== B189/B190 random games ===", flush=True)
    rng = random.Random(42)
    for n_, bm, degs_ in [(4, board4, [point_degree(board4, i) for i in range(16)]),
                          (5, board5, degs5)]:
        last_degs = []
        drop_corr = []
        n_trials = 400
        for _ in range(n_trials):
            occ = 0
            last_pt = None
            while True:
                legal = bm.legal_moves(occ)
                empty = [i for i in range(bm.V) if not (occ >> i) & 1]
                # residual free triples among empty (cheap approx)
                n3 = 0
                for a, b, c in combinations(empty, 3):
                    if bm.is_safe(occ | (1 << a) | (1 << b) | (1 << c)):
                        n3 += 1
                n2 = 0
                for a, b in combinations(empty, 2):
                    if bm.is_safe(occ | (1 << a) | (1 << b)):
                        n2 += 1
                if not legal:
                    break
                L_before = len(legal)
                u = legal[rng.randrange(len(legal))]
                last_pt = u
                occ |= 1 << u
                legal2 = bm.legal_moves(occ)
                drop = L_before - len(legal2)  # note: L drops by 1 just from occupying u
                drop_corr.append((n3, drop, n2, len(legal2)))
            if last_pt is not None:
                last_degs.append(degs_[last_pt])
        all_degs = degs_
        uniform_mean = sum(all_degs) / len(all_degs)
        last_mean = sum(last_degs) / len(last_degs) if last_degs else 0
        med = sorted(all_degs)[len(all_degs) // 2]
        low_u = sum(1 for d in all_degs if d <= med) / len(all_degs)
        low_l = sum(1 for d in last_degs if d <= med) / len(last_degs) if last_degs else 0
        out[f"b189_n{n_}"] = {
            "n_trials": n_trials, "uniform_mean_deg": uniform_mean,
            "last_mean_deg": last_mean,
            "low_deg_frac_uniform": low_u, "low_deg_frac_last": low_l,
            "bias_ratio": low_l / low_u if low_u else None,
        }
        xs = [c[0] for c in drop_corr]
        ys = [c[1] for c in drop_corr]
        xs2 = [c[2] for c in drop_corr]
        out[f"b190_n{n_}"] = {
            "n_samples": len(drop_corr),
            "corr_n3_drop": point_biserial(xs, ys),
            "corr_n2_drop": point_biserial(xs2, ys),
        }
        print(f"B189 n={n_}: bias={out[f'b189_n{n_}']['bias_ratio']:.3f}", flush=True)
        print(f"B190 n={n_}: corr_n3={out[f'b190_n{n_}']['corr_n3_drop']:.3f}", flush=True)

    # =========================================================
    print("=== B169 residue / outcome ===", flush=True)
    b169 = {}
    # Use n=5 1-stone first-move g (already computed as first5)
    for m in [2, 3, 4, 5]:
        groups = defaultdict(list)
        for i in range(25):
            x, y = i % 5, i // 5
            groups[(x % m, y % m)].append((i, first5[i]))
        mixed = {str(k): v for k, v in groups.items() if len(set(w for _, w in v)) > 1}
        b169[f"n5_1stone_m{m}"] = {
            "n_groups": len(groups), "n_mixed": len(mixed),
            "mixed_sample": dict(list(mixed.items())[:3]),
        }
        print(f"B169 n5 1stone m={m}: mixed={len(mixed)}/{len(groups)}", flush=True)
    out["b169"] = b169

    # =========================================================
    print("=== B170 max-set counts ===", flush=True)
    def load_max(n):
        raw = (DATA / f"maximal_n{n}.bin").read_bytes()
        return list(struct.unpack(f"<{len(raw)//8}Q", raw))
    max_counts = {}
    for n_ in [2, 3, 4, 5]:
        ms = load_max(n_)
        sizes = [bin(m).count("1") for m in ms]
        mx = max(sizes)
        max_counts[n_] = {"n_maximal": len(ms), "max_size": mx,
                          "n_max_size_sets": sum(1 for s in sizes if s == mx)}
    ms6 = load_max(6)
    sizes6 = [bin(m).count("1") for m in ms6]
    mx6 = max(sizes6)
    max_counts[6] = {"n_maximal": len(ms6), "max_size": mx6,
                     "n_max_size_sets": sum(1 for s in sizes6 if s == mx6)}
    max_counts[7] = {"max_size": 14, "n_max_size_sets": 16, "source": "known"}
    out["b170_counts"] = max_counts
    print("B170:", max_counts, flush=True)

    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    print("Wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

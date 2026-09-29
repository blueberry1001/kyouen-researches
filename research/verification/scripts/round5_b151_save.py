#!/usr/bin/env python3
"""Save already-computed results + remaining computations for B151-B200."""
from __future__ import annotations
import json, sys, random, struct
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


def main():
    out = {}
    board4 = Board(square_points(4))
    board5 = Board(square_points(5))
    degs5 = [point_degree(board5, i) for i in range(25)]

    # ---- B158: rerun quickly to capture inversion details ----
    print("B158...", flush=True)
    inversions = []
    maxmin_inv = None
    for comb in combinations(range(25), 3):
        s_mask = (1 << comb[0]) | (1 << comb[1]) | (1 << comb[2])
        if not board5.is_safe(s_mask):
            continue
        legal = board5.legal_moves(s_mask)
        if len(legal) < 2:
            continue
        Lvals = {p: len(board5.legal_moves(s_mask | (1 << p))) for p in legal}
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
        if len(inversions) >= 5 and maxmin_inv:
            break
    out["b158_S3"] = {
        "n_inversions": len(inversions),
        "inversions": [{"S_mask": s, "p": p, "q": q, "dp": dp, "dq": dq, "Lp": Lp, "Lq": Lq}
                       for s, p, q, dp, dq, Lp, Lq in inversions[:5]],
        "maxmin_witness": None if maxmin_inv is None else {
            "S_mask": maxmin_inv[0], "p": maxmin_inv[1], "q": maxmin_inv[2],
            "dp": maxmin_inv[3], "dq": maxmin_inv[4], "Lp": maxmin_inv[5], "Lq": maxmin_inv[6]},
    }
    print("  inversions", len(inversions), "maxmin", maxmin_inv is not None, flush=True)

    # ---- B159 ----
    print("B159...", flush=True)
    b6 = Board(square_points(6))
    b7 = Board(square_points(7))
    deg6 = [point_degree(b6, i) for i in range(36)]
    deg7 = [point_degree(b7, i) for i in range(49)]
    inc = [(x, y, degs5[y*5+x], deg6[y*6+x], deg6[y*6+x]-degs5[y*5+x]) for y in range(5) for x in range(5)]
    by_dist = defaultdict(list)
    for x, y, a, b, di in inc:
        by_dist[(x-2)**2+(y-2)**2].append(di)
    center_inc = [di for x, y, a, b, di in inc if (x-2)**2+(y-2)**2 <= 1]
    bound_inc = [di for x, y, a, b, di in inc if (x-2)**2+(y-2)**2 >= 4]
    out["b159_inc_5to6"] = {
        "by_r2": {str(k): {"min": min(v), "max": max(v), "mean": sum(v)/len(v)} for k, v in sorted(by_dist.items())},
        "center_mean": sum(center_inc)/len(center_inc),
        "boundary_mean": sum(bound_inc)/len(bound_inc),
        "ratio": (sum(center_inc)/len(center_inc))/(sum(bound_inc)/len(bound_inc)),
    }
    inc67 = [(x, y, deg6[y*6+x], deg7[y*7+x], deg7[y*7+x]-deg6[y*6+x]) for y in range(6) for x in range(6)]
    by_dist7 = defaultdict(list)
    for x, y, a, b, di in inc67:
        by_dist7[(x-2.5)**2+(y-2.5)**2].append(di)
    center7 = [di for x, y, a, b, di in inc67 if (x-2.5)**2+(y-2.5)**2 <= 2.0]
    bound7 = [di for x, y, a, b, di in inc67 if (x-2.5)**2+(y-2.5)**2 >= 8.0]
    out["b159_inc_6to7"] = {
        "by_r2": {str(k): {"min": min(v), "max": max(v), "mean": sum(v)/len(v)} for k, v in sorted(by_dist7.items())},
        "center_mean": sum(center7)/len(center7),
        "boundary_mean": sum(bound7)/len(bound7),
        "ratio": (sum(center7)/len(center7))/(sum(bound7)/len(bound7)),
    }
    print("  ratios", out["b159_inc_5to6"]["ratio"], out["b159_inc_6to7"]["ratio"], flush=True)

    # ---- B160 n=5 ----
    print("B160 n=5...", flush=True)
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
        groups[str(d)] = {"n_points": len(pts), "n_orbits": len(orbits),
                          "g_values": sorted(gs),
                          "orbit_g": {str(k): first5[v[0]] for k, v in orbits.items()}}
        if len(gs) > 1 and len(orbits) > 1:
            items = sorted((first5[v[0]], k, v) for k, v in orbits.items())
            b160_w = {"degree": d, "g_min": items[0][0], "g_max": items[-1][0],
                      "orbit_min": items[0][1], "orbit_max": items[-1][1],
                      "pts_min": items[0][2], "pts_max": items[-1][2]}
    out["b160_n5"] = {"groups": groups, "witness": b160_w}
    print("  witness", b160_w, flush=True)

    # ---- B157 ----
    print("B157...", flush=True)
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
            feats.append({"dp": dp, "dq": dq, "shared": shared,
                          "pn": outcomes.get(m, -1), "lam_max": lam1, "deg_sum": dp + dq})
        by_sum = defaultdict(lambda: {"P": [], "N": []})
        for f in feats:
            by_sum[f["deg_sum"]]["P" if f["pn"] == 1 else "N"].append(f)
        mixed = {k: v for k, v in by_sum.items() if v["P"] and v["N"]}
        perfect = 0
        mixed_detail = {}
        for k, v in mixed.items():
            lamP = [x["lam_max"] for x in v["P"]]
            lamN = [x["lam_max"] for x in v["N"]]
            if (min(lamP) > max(lamN)) or (max(lamP) < min(lamN)):
                perfect += 1
            if len(mixed_detail) < 8:
                mixed_detail[str(k)] = {
                    "P": len(v["P"]), "N": len(v["N"]),
                    "lamP_rng": [min(lamP), max(lamP)], "lamN_rng": [min(lamN), max(lamN)],
                    "shP_rng": [min(x["shared"] for x in v["P"]), max(x["shared"] for x in v["P"])],
                    "shN_rng": [min(x["shared"] for x in v["N"]), max(x["shared"] for x in v["N"])],
                }
        out[f"b157_n{n_}"] = {
            "n_pairs": len(feats),
            "n_P": sum(1 for f in feats if f["pn"] == 1),
            "n_N": sum(1 for f in feats if f["pn"] == 0),
            "n_mixed_degsum": len(mixed),
            "lam_max_separates": perfect,
            "mixed_detail": mixed_detail,
        }
        print(f"  n={n_} mixed={len(mixed)} sep={perfect}", flush=True)

    # ---- B162 ----
    print("B162...", flush=True)
    def circ3(p0, p1, p2):
        ax, ay = p0; bx, by = p1; cx, cy = p2
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if d == 0:
            return None
        ux = Fraction((ax*ax+ay*ay)*(by-cy) + (bx*bx+by*by)*(cy-ay) + (cx*cx+cy*cy)*(ay-by), d)
        uy = Fraction((ax*ax+ay*ay)*(cx-bx) + (bx*bx+by*by)*(ax-cx) + (cx*cx+cy*cy)*(bx-ax), d)
        return ux, uy
    pts5 = square_points(5)
    stats = {m: {} for m in [2, 3, 5]}
    den_hist = Counter()
    n_circ = 0
    for comb in combinations(range(25), 4):
        p4 = [pts5[i] for i in comb]
        d = det4(
            (p4[0][0]**2+p4[0][1]**2, p4[0][0], p4[0][1], 1),
            (p4[1][0]**2+p4[1][1]**2, p4[1][0], p4[1][1], 1),
            (p4[2][0]**2+p4[2][1]**2, p4[2][0], p4[2][1], 1),
            (p4[3][0]**2+p4[3][1]**2, p4[3][0], p4[3][1], 1),
        )
        if d != 0:
            continue
        c = circ3(p4[0], p4[1], p4[2]) or circ3(p4[0], p4[1], p4[3])
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
        out[f"b162_n5_m{m}"] = {
            "n_groups": len(groups), "n_pure": pure,
            "purity": pure / len(groups) if groups else 0,
            "sample": {str(k): sorted(v)[:8] for k, v in list(groups.items())[:6]},
        }
    out["b162_n5_den_hist"] = dict(den_hist)
    out["b162_n5_n_circ"] = n_circ
    print("  purity", {m: out[f'b162_n5_m{m}']['purity'] for m in [2, 3, 5]}, "den", dict(den_hist), flush=True)

    # ---- B177 rem2 ----
    print("B177 rem2...", flush=True)
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
    out["b177_n4_rem2"] = {"n_subboards": 120, "n_distinct_fv": len(fvecs),
                           "witness": witness, "group_sizes": [len(v) for v in fvecs.values()]}
    print("  fv", len(fvecs), "witness", witness is not None, flush=True)

    # ---- B195/196 n=4 ----
    print("B195/196 n=4...", flush=True)
    def prand_full(board):
        memo = {}
        def pr(occ):
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
        return pr(0), memo
    p0_4, memo4 = prand_full(board4)
    g4 = board4.solve_grundy()
    def extremes(memo, gmap):
        minN = maxN = minP = maxP = None
        for occ, g in gmap.items():
            if occ == 0:
                continue
            pr_val = memo.get(occ)
            if pr_val is None:
                continue
            rec = (pr_val, occ, g, occ.bit_count())
            if g == 0:
                if maxP is None or pr_val > maxP[0]: maxP = rec
                if minP is None or pr_val < minP[0]: minP = rec
            else:
                if minN is None or pr_val < minN[0]: minN = rec
                if maxN is None or pr_val > maxN[0]: maxN = rec
        def fmt(rec):
            return None if rec is None else {"p": str(rec[0]), "mask": rec[1], "g": rec[2], "k": rec[3]}
        return {"minN": fmt(minN), "maxN": fmt(maxN), "minP": fmt(minP), "maxP": fmt(maxP)}
    out["b195_b196_n4"] = {"p_empty": str(p0_4), **extremes(memo4, g4)}
    print("  ", out["b195_b196_n4"], flush=True)

    # ---- B195/196 n=5 ----
    print("B195/196 n=5...", flush=True)
    p0_5, memo5 = prand_full(board5)
    out["b195_b196_n5"] = {"p_empty": str(p0_5), **extremes(memo5, g5)}
    print("  ", {k: str(v) for k, v in out["b195_b196_n5"].items()}, flush=True)

    # ---- B189/B190: efficient version ----
    print("B189/B190...", flush=True)
    rng = random.Random(42)
    for n_, bm, degs_ in [(4, board4, [point_degree(board4, i) for i in range(16)]),
                          (5, board5, degs5)]:
        last_degs = []
        drop_corr = []
        n_trials = 300
        # precompute quad lists for speed
        for _ in range(n_trials):
            occ = 0
            last_pt = None
            while True:
                legal = bm.legal_moves(occ)
                empty = [i for i in range(bm.V) if not (occ >> i) & 1]
                # residual free triples / pairs (sample if many empty)
                if len(empty) > 16:
                    sample = random.sample(empty, 16)
                    n3 = sum(1 for a, b, c in combinations(sample, 3)
                             if bm.is_safe(occ | (1 << a) | (1 << b) | (1 << c)))
                    n2 = sum(1 for a, b in combinations(sample, 2)
                             if bm.is_safe(occ | (1 << a) | (1 << b)))
                    # scale up
                    scale3 = (len(empty) / 16) ** 3
                    scale2 = (len(empty) / 16) ** 2
                    n3 = int(n3 * scale3)
                    n2 = int(n2 * scale2)
                else:
                    n3 = sum(1 for a, b, c in combinations(empty, 3)
                             if bm.is_safe(occ | (1 << a) | (1 << b) | (1 << c)))
                    n2 = sum(1 for a, b in combinations(empty, 2)
                             if bm.is_safe(occ | (1 << a) | (1 << b)))
                if not legal:
                    break
                L_before = len(legal)
                u = legal[rng.randrange(len(legal))]
                last_pt = u
                occ |= 1 << u
                L_after = len(bm.legal_moves(occ))
                drop_corr.append((n3, L_before - L_after, n2))
            if last_pt is not None:
                last_degs.append(degs_[last_pt])
        all_degs = degs_
        uniform_mean = sum(all_degs) / len(all_degs)
        last_mean = sum(last_degs) / len(last_degs) if last_degs else 0
        med = sorted(all_degs)[len(all_degs) // 2]
        low_u = sum(1 for d in all_degs if d <= med) / len(all_degs)
        low_l = sum(1 for d in last_degs if d <= med) / len(last_degs) if last_degs else 0
        out[f"b189_n{n_}"] = {
            "n_trials": n_trials, "uniform_mean_deg": uniform_mean, "last_mean_deg": last_mean,
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
        print(f"  n={n_} bias={out[f'b189_n{n_}']['bias_ratio']} corr_n3={out[f'b190_n{n_}']['corr_n3_drop']}", flush=True)

    # ---- B169 ----
    print("B169...", flush=True)
    b169 = {}
    for m in [2, 3, 4, 5]:
        groups = defaultdict(list)
        for i in range(25):
            x, y = i % 5, i // 5
            groups[(x % m, y % m)].append((i, first5[i]))
        mixed = {str(k): v for k, v in groups.items() if len(set(w for _, w in v)) > 1}
        b169[f"n5_1stone_m{m}"] = {"n_groups": len(groups), "n_mixed": len(mixed),
                                   "mixed_sample": dict(list(mixed.items())[:3])}
    # 2-stone on n=5 for larger m
    outcomes5 = g5
    for m in [4, 5, 6]:
        groups = defaultdict(list)
        for p, q in combinations(range(25), 2):
            mask = (1 << p) | (1 << q)
            if mask not in outcomes5:
                continue
            x1, y1 = p % 5, p // 5
            x2, y2 = q % 5, q // 5
            sig = tuple(sorted([(x1 % m, y1 % m), (x2 % m, y2 % m)]))
            groups[sig].append(outcomes5[mask])
        mixed = {str(k): sorted(set(v)) for k, v in groups.items() if len(set(v)) > 1}
        b169[f"n5_2stone_m{m}"] = {"n_groups": len(groups), "n_mixed": len(mixed),
                                   "sample": {k: v for k, v in list(mixed.items())[:4]}}
    out["b169"] = b169
    print("  mixed counts", {k: v["n_mixed"] for k, v in b169.items()}, flush=True)

    # ---- B170 ----
    print("B170...", flush=True)
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
    print("  ", max_counts, flush=True)

    # ---- B193 ----
    print("B193...", flush=True)
    # sample safe sets from safe_n5.bin
    raw = (DATA / "safe_n5.bin").read_bytes()
    nsets = len(raw) // 8
    vals = struct.unpack(f"<{nsets}Q", raw)
    by_k = defaultdict(list)
    for v in vals:
        k = bin(v).count("1")
        if 3 <= k <= 7:
            by_k[k].append(v)
    rng2 = random.Random(0)
    sample = []
    for k, lst in by_k.items():
        sample.extend(rng2.sample(lst, min(400, len(lst))))
    # features
    feats5 = []
    for mask in sample:
        k = mask.bit_count()
        legal = board5.legal_moves(mask)
        pts_in = [i for i in range(25) if mask & (1 << i)]
        deg_sum = sum(degs5[i] for i in pts_in)
        g = g5.get(mask)
        if g is None:
            continue
        empty = [i for i in range(25) if not (mask >> i) & 1]
        r2 = sum(1 for a, b in combinations(empty, 2) if board5.is_safe(mask | (1 << a) | (1 << b)))
        feats5.append({"k": k, "mask": mask, "g": g, "pn": 1 if g != 0 else 0,
                       "deg_sum": deg_sum, "n_legal": len(legal), "r2": r2})
    layers = defaultdict(list)
    for f in feats5:
        layers[f["k"]].append(f)
    out["b193_n5"] = {"by_k": {}}
    for k, lst in sorted(layers.items()):
        r2s = [f["r2"] for f in lst]
        med_r2 = sorted(r2s)[len(r2s)//2]
        low = [f for f in lst if f["r2"] <= med_r2]
        high = [f for f in lst if f["r2"] > med_r2]
        def cd(sub):
            return point_biserial([f["deg_sum"] for f in sub], [f["pn"] for f in sub]) if sub else None
        out["b193_n5"]["by_k"][str(k)] = {
            "corr_low_r2": cd(low), "corr_high_r2": cd(high),
            "n_low": len(low), "n_high": len(high),
        }
    print("  ", out["b193_n5"]["by_k"], flush=True)

    # ---- B197-B200 on the same sample ----
    print("B197-B200...", flush=True)
    # B197: child residual diversity
    p_var, n_var = [], []
    for f in feats5[:600]:
        legal = board5.legal_moves(f["mask"])
        if len(legal) < 2:
            continue
        childs = []
        for p in legal:
            child = f["mask"] | (1 << p)
            empty = [i for i in range(25) if not (child >> i) & 1]
            r2c = sum(1 for a, b in combinations(empty, 2) if board5.is_safe(child | (1 << a) | (1 << b)))
            childs.append(r2c)
        if len(childs) < 2:
            continue
        mean_c = sum(childs)/len(childs)
        var_c = sum((x-mean_c)**2 for x in childs)/len(childs)
        if f["pn"] == 1:
            n_var.append(var_c)
        else:
            p_var.append(var_c)
    out["b197_n5"] = {
        "n_P": len(p_var), "n_N": len(n_var),
        "mean_var_P": sum(p_var)/len(p_var) if p_var else None,
        "mean_var_N": sum(n_var)/len(n_var) if n_var else None,
    }

    # B198: interaction
    pns = [f["pn"] for f in feats5]
    ds = [f["deg_sum"] for f in feats5]
    r2s = [f["r2"] for f in feats5]
    inter = [d * r for d, r in zip(ds, r2s)]
    out["b198_n5"] = {
        "n_sample": len(feats5),
        "corr_degsum_pn": point_biserial(ds, pns),
        "corr_r2_pn": point_biserial(r2s, pns),
        "corr_inter_pn": point_biserial(inter, pns),
    }

    # B199: P-rate by k
    by_k_pr = defaultdict(lambda: [0, 0])
    for f in feats5:
        by_k_pr[f["k"]][0] += f["pn"]
        by_k_pr[f["k"]][1] += 1
    out["b199_n5"] = {
        "pr_by_k": {k: {"P": v[0], "n": v[1], "rate": v[0]/v[1]} for k, v in sorted(by_k_pr.items())},
        "K5": 9,
    }

    # B200: two axes
    Npos = [f for f in feats5 if f["pn"] == 1]
    if Npos:
        gvals = [f["g"] for f in Npos]
        corrs = {key: point_biserial([f[key] for f in Npos], gvals) for key in ["deg_sum", "r2", "n_legal", "k"]}
        corrs_pn = {key: point_biserial([f[key] for f in feats5], pns) for key in ["deg_sum", "r2", "n_legal", "k"]}
        out["b200_n5"] = {
            "corr_with_g_among_N": corrs,
            "corr_with_pn": corrs_pn,
            "n_N": len(Npos),
            "g_range": [min(gvals), max(gvals)],
        }
    print("  B197", out["b197_n5"], flush=True)
    print("  B198", out["b198_n5"], flush=True)
    print("  B199", out["b199_n5"], flush=True)
    print("  B200", out.get("b200_n5"), flush=True)

    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    print("Wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

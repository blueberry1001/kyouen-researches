#!/usr/bin/env python3
"""B191-B200: mine exact outcome/feature tables on n<=5.

Operational definitions (documented in batch-09.md):
- d0(p)   : initial degree of p = #forbidden quads containing p
- b_S(p)  : #quads q with p in q and |q ∩ S| = 3  (>0 => p illegal)
- newly_blocked(p) : empty points that become illegal after adding legal p
- r2      : #residual forbidden sets of size 2 (e in Q, e\\S subseteq L(S), |e\\S|=2)
- r2_ratio: r2 / (r2+r3+r4)
- rand_odd: P(remaining moves odd | S) under uniform random greedy
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "batch09_outcome_mining.json"


def analyze_board(n: int, sample_per_layer: int | None = None) -> dict:
    b = board_square(n)
    V = b.V
    full = b.full

    # initial degrees
    d0 = [0] * V
    for q in b.quads:
        for i in range(V):
            if q & (1 << i):
                d0[i] += 1

    # --- solve outcomes + grundy ---
    sys.setrecursionlimit(100000)
    memo_g: dict[int, int] = {}

    def grundy(occ: int) -> int:
        hit = memo_g.get(occ)
        if hit is not None:
            return hit
        mv = b.legal_moves(occ)
        if not mv:
            memo_g[occ] = 0
            return 0
        seen = set()
        for u in mv:
            seen.add(grundy(occ | (1 << u)))
        g = 0
        while g in seen:
            g += 1
        memo_g[occ] = g
        return g

    grundy(0)

    # --- random-play remaining-move distribution ---
    memo_rd: dict[int, tuple[float, float]] = {}  # (P(odd remaining), E[remaining])

    def rand_stats(occ: int) -> tuple[float, float]:
        hit = memo_rd.get(occ)
        if hit is not None:
            return hit
        mv = b.legal_moves(occ)
        if not mv:
            memo_rd[occ] = (0.0, 0.0)
            return 0.0, 0.0
        p_odd = 0.0
        e_rem = 0.0
        w = 1.0 / len(mv)
        for u in mv:
            po, er = rand_stats(occ | (1 << u))
            # adding one stone flips parity
            p_odd += (1.0 - po) * w
            e_rem += (1.0 + er) * w
        memo_rd[occ] = (p_odd, e_rem)
        return p_odd, e_rem

    rand_stats(0)

    # collect states
    states = list(memo_g.keys())
    by_k = defaultdict(list)
    for occ in states:
        by_k[occ.bit_count()].append(occ)

    # sample if requested
    def pick(lst, cap):
        if cap is None or len(lst) <= cap:
            return lst
        step = max(1, len(lst) // cap)
        return lst[::step][:cap]

    # --- feature extraction for selected states ---
    def features(occ: int) -> dict:
        mv = b.legal_moves(occ)
        lset = set(mv)
        empty = full ^ occ
        # b_S for empty points
        bvals = {}
        newly = {}
        # residual size counts
        r2 = r3 = r4 = 0
        # iterate quads
        for q in b.quads:
            inter = q & occ
            if inter == q:
                continue
            rest = q & ~occ
            # |rest| = 4 - |inter|
            rc = rest.bit_count()
            # b_S: |inter|==3 and p = rest
            if rc == 1:
                p = rest.bit_length() - 1
                bvals[p] = bvals.get(p, 0) + 1
            # residual if rest points are all currently legal
            if rest & ~0 and (rest & ~empty) == 0:
                # rest is subset of empty; need rest ⊆ L = legal moves
                if (rest & ~sum(1 << u for u in mv)) == 0:
                    if rc == 2:
                        r2 += 1
                    elif rc == 3:
                        r3 += 1
                    elif rc == 4:
                        r4 += 1
        # newly_blocked for each legal move
        for u in mv:
            occ2 = occ | (1 << u)
            cnt = 0
            for q in b.quads_by_pt[u]:
                if (q & occ2) != q:
                    rest = q & ~occ2
                    if rest.bit_count() == 1:
                        p = rest.bit_length() - 1
                        if bvals.get(p, 0) == 0 and p != u:
                            cnt += 1
            newly[u] = cnt

        k = occ.bit_count()
        g = memo_g[occ]
        po, er = rand_stats(occ)
        b_empty = [bvals.get(p, 0) for p in range(V) if not (occ >> p) & 1]
        if not b_empty:
            b_mean = b_max = b_var = 0.0
        else:
            b_mean = sum(b_empty) / len(b_empty)
            b_max = max(b_empty)
            b_var = sum((x - b_mean) ** 2 for x in b_empty) / len(b_empty)
        new_vals = list(newly.values()) if newly else [0]
        r_tot = r2 + r3 + r4
        return {
            "k": k,
            "l": len(mv),
            "g": g,
            "is_p": 1 if g == 0 else 0,
            "rand_odd": po,
            "e_rem": er,
            "sum_d0": sum(d0[i] for i in range(V) if (occ >> i) & 1),
            "b_mean": b_mean,
            "b_max": b_max,
            "b_var": b_var,
            "n_illegal": sum(1 for x in b_empty if x > 0),
            "r2": r2,
            "r3": r3,
            "r4": r4,
            "r2_ratio": (r2 / r_tot) if r_tot else None,
            "newly_max": max(new_vals),
            "newly_mean": sum(new_vals) / len(new_vals),
            "n_win_moves": sum(
                1 for u in mv if memo_g[occ | (1 << u)] == 0
            ),
            "n_moves": len(mv),
        }

    # full light stats for all states
    light_by_kl = defaultdict(lambda: {"safe": 0, "p": 0})
    light_all = []
    for occ in states:
        k = occ.bit_count()
        l = len(b.legal_moves(occ))  # costly; cache
        pass

    # cache legal move counts
    lcount = {}
    for occ in states:
        mv = b.legal_moves(occ)
        lcount[occ] = len(mv)

    for occ in states:
        k = occ.bit_count()
        l = lcount[occ]
        g = memo_g[occ]
        light_by_kl[(k, l)]["safe"] += 1
        if g == 0:
            light_by_kl[(k, l)]["p"] += 1

    # heavy features on sample
    heavy = []
    for k, lst in sorted(by_k.items()):
        if k == 0:
            continue
        sample = pick(lst, sample_per_layer)
        for occ in sample:
            f = features(occ)
            f["occ"] = occ
            heavy.append(f)

    return {
        "n": n,
        "n_states": len(states),
        "K_max_seen": max(by_k.keys()),
        "F": len(b.quads),
        "empty_g": memo_g[0],
        "empty_rand_odd": rand_stats(0)[0],
        "empty_e_rem": rand_stats(0)[1],
        "light_by_kl": {f"{k},{l}": v for (k, l), v in sorted(light_by_kl.items())},
        "d0": d0,
        "heavy": heavy,
        "layer_sizes": {str(k): len(v) for k, v in sorted(by_k.items())},
    }


def aggregate(res: dict) -> dict:
    """Derived stats for B191-B200 from one board's heavy sample + light table."""
    n = res["n"]
    heavy = res["heavy"]
    out = {}

    # B191: P rate vs |L| within fixed k — check non-monotonicity
    by_kl = res["light_by_kl"]
    kl_rows = []
    for key, v in by_kl.items():
        k, l = map(int, key.split(","))
        kl_rows.append((k, l, v["safe"], v["p"], v["p"] / v["safe"] if v["safe"] else None))
    nonmono = []
    for k in sorted(set(r[0] for r in kl_rows)):
        rows = sorted([r for r in kl_rows if r[0] == k], key=lambda r: r[1])
        prates = [r[4] for r in rows if r[4] is not None]
        # find an inversion: increases then decreases
        for i in range(1, len(prates) - 1):
            if (prates[i] > prates[i - 1] and prates[i] > prates[i + 1]) or (
                prates[i] < prates[i - 1] and prates[i] < prates[i + 1]
            ):
                nonmono.append({"k": k, "l_seq": [(r[1], r[4], r[2]) for r in rows]})
                break
    out["B191_nonmono_k_layers"] = nonmono
    out["B191_kl_table"] = [
        {"k": r[0], "l": r[1], "safe": r[2], "p": r[3], "p_rate": r[4]} for r in kl_rows
    ]

    # B192: within N positions with same (k,l), does b_var predict win-move concentration?
    by_kl_n = defaultdict(list)
    for f in heavy:
        if f["g"] != 0:
            by_kl_n[(f["k"], f["l"])].append(f)
    conc_rows = []
    for (k, l), fl in by_kl_n.items():
        if len(fl) < 8 or l < 2:
            continue
        # concentration = n_win_moves / n_moves (smaller = more concentrated)
        conc = [f["n_win_moves"] / f["n_moves"] for f in fl]
        bvars = [f["b_var"] for f in fl]
        # spearman-ish: pearson on ranks
        def rank(xs):
            order = sorted(range(len(xs)), key=lambda i: xs[i])
            rk = [0] * len(xs)
            for r, i in enumerate(order):
                rk[i] = r
            return rk
        if len(set(bvars)) < 2 or len(set(conc)) < 2:
            continue
        rb, rc = rank(bvars), rank(conc)
        mb, mc = sum(rb) / len(rb), sum(rc) / len(rc)
        num = sum((rb[i] - mb) * (rc[i] - mc) for i in range(len(rb)))
        den = math.sqrt(sum((x - mb) ** 2 for x in rb) * sum((x - mc) ** 2 for x in rc))
        if den:
            conc_rows.append({"k": k, "l": l, "n": len(fl), "spearman_bvar_vs_conc": num / den})
    out["B192_bvar_vs_concentration"] = conc_rows

    # B193: sum_d0 vs P-rate sign flip, stratified by r2_ratio median
    layers = defaultdict(list)
    for f in heavy:
        if f["r2_ratio"] is not None:
            layers[f["k"]].append(f)
    b193 = {}
    for k, fl in sorted(layers.items()):
        if len(fl) < 12:
            continue
        med = sorted(f["r2_ratio"] for f in fl)[len(fl) // 2]
        for tag, sub in (("lo_r2", [f for f in fl if f["r2_ratio"] <= med]),
                         ("hi_r2", [f for f in fl if f["r2_ratio"] > med])):
            if len(sub) < 6:
                continue
            # split by sum_d0 median
            med_d = sorted(f["sum_d0"] for f in sub)[len(sub) // 2]
            lo = [f for f in sub if f["sum_d0"] <= med_d]
            hi = [f for f in sub if f["sum_d0"] > med_d]
            if not lo or not hi:
                continue
            b193[f"k{k}_{tag}"] = {
                "n": len(sub),
                "p_rate_lo_d": sum(f["is_p"] for f in lo) / len(lo),
                "p_rate_hi_d": sum(f["is_p"] for f in hi) / len(hi),
                "n_lo": len(lo),
                "n_hi": len(hi),
            }
    out["B193_sumd_by_r2"] = b193

    # B194: does rand_odd add predictive power for P/N at fixed (k,l)?
    by_kl2 = defaultdict(list)
    for f in heavy:
        by_kl2[(f["k"], f["l"])].append(f)
    b194 = []
    for (k, l), fl in by_kl2.items():
        if len(fl) < 10:
            continue
        ps = [f for f in fl if f["is_p"]]
        ns = [f for f in fl if not f["is_p"]]
        if not ps or not ns:
            continue
        b194.append({
            "k": k, "l": l, "n": len(fl),
            "mean_rand_odd_P": sum(f["rand_odd"] for f in ps) / len(ps),
            "mean_rand_odd_N": sum(f["rand_odd"] for f in ns) / len(ns),
        })
    out["B194_rand_odd_P_vs_N"] = b194

    # B195/196: extreme random-win among optimal P/N
    # player-to-move random win prob = rand_odd (odd remaining => mover wins)
    npos = [f for f in heavy if not f["is_p"]]
    ppos = [f for f in heavy if f["is_p"]]
    if npos:
        mn = min(npos, key=lambda f: f["rand_odd"])
        out["B195_min_randwin_in_N"] = {
            "k": mn["k"], "l": mn["l"], "g": mn["g"], "rand_odd": mn["rand_odd"],
            "e_rem": mn["e_rem"], "occ": mn["occ"],
        }
    if ppos:
        mx = max(ppos, key=lambda f: f["rand_odd"])
        out["B196_max_randwin_in_P"] = {
            "k": mx["k"], "l": mx["l"], "g": mx["g"], "rand_odd": mx["rand_odd"],
            "e_rem": mx["e_rem"], "occ": mx["occ"],
        }

    # B197: variance of child feature (l of children / r2 of children) P vs N
    # approximate using the state's own r2 and b_var spread as "neighbourhood diversity"
    for feat in ("r2", "b_var", "newly_max", "e_rem"):
        pv = [f[feat] for f in heavy if f["is_p"] and f[feat] is not None]
        nv = [f[feat] for f in heavy if (not f["is_p"]) and f[feat] is not None]
        if len(pv) >= 8 and len(nv) >= 8:
            mp = sum(pv) / len(pv)
            mn_ = sum(nv) / len(nv)
            vp = sum((x - mp) ** 2 for x in pv) / len(pv)
            vn = sum((x - mn_) ** 2 for x in nv) / len(nv)
            out.setdefault("B197_var_P_vs_N", {})[feat] = {
                "var_P": vp, "var_N": vn, "mean_P": mp, "mean_N": mn_,
                "n_P": len(pv), "n_N": len(nv),
            }

    # B198: interaction sum_d0 * newly_max on P-rate (within k layers)
    inter = {}
    for k in sorted(set(f["k"] for f in heavy)):
        fl = [f for f in heavy if f["k"] == k]
        if len(fl) < 20:
            continue
        # split 2x2 by medians
        md = sorted(f["sum_d0"] for f in fl)[len(fl) // 2]
        mnv = sorted(f["newly_max"] for f in fl)[len(fl) // 2]
        cells = defaultdict(list)
        for f in fl:
            cells[(f["sum_d0"] > md, f["newly_max"] > mnv)].append(f["is_p"])
        inter[f"k{k}"] = {
            f"d{'hi' if dk else 'lo'}_g{'hi' if gk else 'lo'}": {
                "n": len(v), "p_rate": sum(v) / len(v),
            }
            for (dk, gk), v in cells.items()
        }
    out["B198_interaction"] = inter

    # B199: P-rate vs k, k/K, l/n^2
    K = res["K_max_seen"]
    out["B199_K"] = K
    curve = []
    for f in heavy:
        curve.append({
            "k": f["k"], "k_over_K": f["k"] / K if K else None,
            "l_over_n2": f["l"] / (n * n), "is_p": f["is_p"], "l": f["l"],
        })
    out["B199_curve"] = curve

    # B200: among N, does high g correlate with different features than P/N?
    n_only = [f for f in heavy if not f["is_p"]]
    if len(n_only) >= 20:
        gmed = sorted(f["g"] for f in n_only)[len(n_only) // 2]
        hi = [f for f in n_only if f["g"] > gmed]
        lo = [f for f in n_only if f["g"] <= gmed]
        axes = {}
        for feat in ("sum_d0", "newly_max", "b_var", "r2_ratio", "l", "e_rem"):
            if hi and lo and all(f[feat] is not None for f in hi + lo):
                axes[feat] = {
                    "mean_hi_g": sum(f[feat] for f in hi) / len(hi),
                    "mean_lo_g": sum(f[feat] for f in lo) / len(lo),
                }
        # P vs N means for same features
        p_all = [f for f in heavy if f["is_p"]]
        pn = {}
        for feat in ("sum_d0", "newly_max", "b_var", "r2_ratio", "l", "e_rem"):
            if p_all and n_only:
                pv = [f[feat] for f in p_all if f[feat] is not None]
                nv = [f[feat] for f in n_only if f[feat] is not None]
                if pv and nv:
                    pn[feat] = {
                        "mean_P": sum(pv) / len(pv),
                        "mean_N": sum(nv) / len(nv),
                    }
        out["B200_hi_g_vs_lo_g"] = axes
        out["B200_P_vs_N"] = pn

    return out


def main():
    results = {}
    for n, cap in ((3, None), (4, 200), (5, 120)):
        print(f"=== analyze n={n} ===", flush=True)
        res = analyze_board(n, sample_per_layer=cap)
        agg = aggregate(res)
        results[str(n)] = {
            "meta": {k: res[k] for k in (
                "n", "n_states", "K_max_seen", "F", "empty_g", "empty_rand_odd", "empty_e_rem",
                "layer_sizes")},
            "light_by_kl": res["light_by_kl"],
            "agg": agg,
            "d0": res["d0"],
        }
        print(f"  states={res['n_states']} empty_g={res['empty_g']} "
              f"rand_odd={res['empty_rand_odd']:.3f}", flush=True)

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

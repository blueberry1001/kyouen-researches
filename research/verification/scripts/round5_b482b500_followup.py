#!/usr/bin/env python3
"""Round5 B482-B500 follow-up: settle PARTIAL/INCONCLUSIVE via weakened forms.

Targets: B485 B487 B489 B490 B495 B496 B499 B500
Outputs research/verification/round5_b482b500_followup.json
"""
from __future__ import annotations

import json
import math
import pickle
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round5_b482b500_followup.json"
CACHE = ROOT / "research" / "verification" / "batch03_cache.pkl"
FEAT_CACHE = ROOT / "research" / "verification" / "round5_b482b500_feats.pkl"
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import Board, board_square  # noqa: E402


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0
            for t in range(i, j + 1):
                rk[order[t]] = avg
            i = j + 1
        return rk

    if len(xs) < 3:
        return None
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    dx = math.sqrt(sum((v - mx) ** 2 for v in rx))
    dy = math.sqrt(sum((v - my) ** 2 for v in ry))
    return num / (dx * dy) if dx and dy else None


def entropy(counts):
    tot = sum(counts)
    if tot <= 0:
        return 0.0
    e = 0.0
    for c in counts:
        if c:
            p = c / tot
            e -= p * math.log(p)
    return e


def _empties_of(occ: int, V: int) -> list[int]:
    out = []
    em = ((1 << V) - 1) ^ occ
    i = 0
    while em:
        if em & 1:
            out.append(i)
        em >>= 1
        i += 1
    return out


def extract_min(board: Board, occ: int) -> dict:
    """Lightweight features needed by B485/B487/B489/B490."""
    V = board.V
    empty = _empties_of(occ, V)
    qbp = board.quads_by_pt

    # b values on empty points (coverage = # of quads with 3 stones + this empty)
    bs = []
    pts_b1 = []
    for p in empty:
        bit = 1 << p
        bp = 0
        for q in qbp[p]:
            if (q & bit) == bit and (q & occ).bit_count() == 3:
                bp += 1
        bs.append(bp)
        if bp == 1:
            pts_b1.append(p)
    if not bs:
        b_hist = ()
        spread = 0.0
        n_b1 = 0
        b_max = 0
        n_bpos = 0
        b_mean = 0.0
        b_var = 0.0
    else:
        b_hist = tuple(sorted(bs))
        n_b1 = len(pts_b1)
        b_max = max(bs)
        n_bpos = sum(1 for x in bs if x > 0)
        m = sum(bs) / len(bs)
        b_var = sum((x - m) ** 2 for x in bs) / len(bs)
        b_mean = m
        spread = 0.0
        if len(pts_b1) >= 2:
            coords = board.points
            tot = 0
            cnt = 0
            for i in range(len(pts_b1)):
                for j in range(i + 1, len(pts_b1)):
                    x1, y1 = coords[pts_b1[i]]
                    x2, y2 = coords[pts_b1[j]]
                    tot += max(abs(x1 - x2), abs(y1 - y2))
                    cnt += 1
            spread = tot / cnt

    # legal + u gain
    legal = []
    for p in empty:
        bit = 1 << p
        ok = True
        for q in qbp[p]:
            if (q & (occ | bit)) == q:
                ok = False
                break
        if ok:
            legal.append(p)
    if not legal:
        u_hist = ()
        n_distinct_u = 0
        u_max = 0
        u_min = 0
        nL = 0
    else:
        legal_set = set(legal)
        us = []
        for p in legal:
            bit = 1 << p
            newly = 0
            for q in qbp[p]:
                if (q & bit) != bit:
                    continue
                others = q & ~bit
                if (others & occ).bit_count() == 2:
                    miss = others & ~occ
                    if miss.bit_count() == 1:
                        qv = (miss & -miss).bit_length() - 1
                        if qv != p and qv in legal_set:
                            newly += 1
            us.append(newly)
        u_hist = tuple(sorted(us))
        n_distinct_u = len(set(us))
        u_max = max(us)
        u_min = min(us)
        nL = len(us)

    u_ent = entropy(list(u_hist)) if u_hist else 0.0
    return {
        "b_hist": b_hist,
        "spread_b1": spread,
        "n_b1": n_b1,
        "b_max": b_max,
        "n_bpos": n_bpos,
        "b_mean": b_mean,
        "b_var": b_var,
        "u_hist": u_hist,
        "u_ent": u_ent,
        "n_distinct_u": n_distinct_u,
        "u_max": u_max,
        "u_min": u_min,
        "nL_extract": nL,
    }


def build_feats(n: int, board: Board, recs: list) -> dict:
    """Return per-occ feature dict + mu/hmax/win_ratio/illusion."""
    by_occ = {r["occ"]: r for r in recs}
    rows_sorted = sorted(recs, key=lambda r: -r["k"])
    mu = {}
    hmax = {}
    win_ratio = {}
    n_win = {}
    rand_odd = {}
    for r in rows_sorted:
        occ = r["occ"]
        L = r["L"]
        if L == 0:
            mu[occ] = 0
            hmax[occ] = 0
            win_ratio[occ] = 0.0
            n_win[occ] = 0
            rand_odd[occ] = 0.0
            continue
        mus = []
        hs = []
        wins = 0
        ro_acc = 0.0
        v = 0
        Lm = L
        while Lm:
            if Lm & 1:
                ch = occ | (1 << v)
                mus.append(mu[ch])
                hs.append(hmax[ch])
                if by_occ[ch]["g"] == 0:
                    wins += 1
                ro_acc += 1.0 - rand_odd[ch]
            Lm >>= 1
            v += 1
        mu[occ] = 1 + min(mus)
        hmax[occ] = 1 + max(hs)
        nL = r["nL"]
        n_win[occ] = wins
        win_ratio[occ] = (wins / nL) if r["g"] != 0 else 0.0
        rand_odd[occ] = ro_acc / nL

    feats = {}
    for i, r in enumerate(recs):
        if i % 30000 == 0:
            print(f"  n={n} feats {i}/{len(recs)}", flush=True)
        occ = r["occ"]
        fx = extract_min(board, occ)
        fx.update({
            "occ": occ,
            "k": r["k"],
            "g": r["g"],
            "P": 1 if r["g"] == 0 else 0,
            "nL": r["nL"],
            "stab": r["stab"],
            "mu": mu[occ],
            "hmax": hmax[occ],
            "win_ratio": win_ratio[occ],
            "n_win": n_win[occ],
            "rand_odd": rand_odd[occ],
            "illusion": rand_odd[occ] if r["g"] == 0 else (1.0 - rand_odd[occ]),
        })
        feats[occ] = fx
    return feats


def tstar_wft_all(board: Board, recs: list) -> dict:
    """Global DP of T* and WFT over all states (children first)."""
    by_occ = {r["occ"]: r for r in recs}
    rows_desc = sorted(recs, key=lambda r: -r["k"])  # high k first
    T = {}
    W = {}
    for r in rows_desc:
        occ = r["occ"]
        L = r["L"]
        if L == 0:
            T[occ] = frozenset({r["k"]})
            W[occ] = frozenset({r["k"]})
            continue
        g = r["g"]
        # collect children
        ch_list = []
        v = 0
        Lm = L
        while Lm:
            if Lm & 1:
                ch_list.append(occ | (1 << v))
            Lm >>= 1
            v += 1
        if g == 0:
            acc_t = set()
            acc_w = None
            for ch in ch_list:
                acc_t |= T[ch]
                s = W[ch]
                acc_w = set(s) if acc_w is None else (acc_w & set(s))
            T[occ] = frozenset(acc_t)
            W[occ] = frozenset(acc_w or set())
        else:
            acc_t = set()
            acc_w = set()
            for ch in ch_list:
                if by_occ[ch]["g"] == 0:
                    acc_t |= T[ch]
                    acc_w |= W[ch]
            if not acc_t:
                for ch in ch_list:
                    acc_t |= T[ch]
                    acc_w |= W[ch]
            T[occ] = frozenset(acc_t)
            W[occ] = frozenset(acc_w)
    return {"T": T, "W": W}


def reach_all(board: Board, recs: list) -> dict:
    by_occ = {r["occ"]: r for r in recs}
    rows_asc = sorted(recs, key=lambda r: r["k"])
    reach = {0: 1.0}
    for r in rows_asc:
        occ = r["occ"]
        if occ == 0:
            continue
        p = 0.0
        bits = [i for i in range(board.V) if (occ >> i) & 1]
        for i in bits:
            par = occ ^ (1 << i)
            if par not in reach:
                continue
            pr = by_occ.get(par)
            if pr is None:
                continue
            p += reach[par] / pr["nL"]
        reach[occ] = p
    return reach


def main():
    with open(CACHE, "rb") as f:
        cache = pickle.load(f)
    boards = {n: board_square(n) for n in (3, 4, 5)}
    recs = {n: cache[n]["recs"] for n in (3, 4, 5)}
    report = {}

    # ---- features (cached) ----
    if FEAT_CACHE.exists():
        with open(FEAT_CACHE, "rb") as f:
            feats_all = pickle.load(f)
        print("loaded feature cache", flush=True)
    else:
        feats_all = {}
        for n in (3, 4, 5):
            print(f"extract n={n}", flush=True)
            feats_all[n] = build_feats(n, boards[n], recs[n])
        with open(FEAT_CACHE, "wb") as f:
            pickle.dump(feats_all, f, protocol=4)
        print("wrote feature cache", flush=True)

    # ---- reach DP n=4,5 ----
    reach_all_map = {}
    for n in (4, 5):
        print(f"reach n={n}", flush=True)
        reach_all_map[n] = reach_all(boards[n], recs[n])

    # ---- T*/WFT n=4,5 ----
    tw_all = {}
    for n in (4, 5):
        print(f"T*/WFT n={n}", flush=True)
        tw_all[n] = tstar_wft_all(boards[n], recs[n])

    # =================================================================
    # B485: b_hist fixed pairs, spread vs win_ratio; vs high-coverage
    # =================================================================
    print("=== B485 ===", flush=True)
    b485 = {}
    for n in (3, 4, 5):
        feats = feats_all[n]
        # group by (k, nL, b_hist) among N-positions with n_b1>=2 and variation
        by = defaultdict(list)
        for f in feats.values():
            if f["n_b1"] < 2:
                continue
            if f["g"] == 0:
                continue  # N-positions only? original talks of win_ratio on N
            by[(f["k"], f["nL"], f["b_hist"])].append(f)
        pair_up = 0
        pair_down = 0
        pair_tie = 0
        pair_diff = 0
        examples = []
        cells = 0
        for key, rs in by.items():
            if len(rs) < 2:
                continue
            # need spread variation
            sp = [r["spread_b1"] for r in rs]
            if max(sp) - min(sp) < 1e-12:
                continue
            wr = [r["win_ratio"] for r in rs]
            if max(wr) - min(wr) < 1e-12:
                continue
            cells += 1
            for i in range(len(rs)):
                for j in range(i + 1, len(rs)):
                    if abs(rs[i]["spread_b1"] - rs[j]["spread_b1"]) < 1e-12:
                        continue
                    d_s = rs[i]["spread_b1"] - rs[j]["spread_b1"]
                    d_w = rs[i]["win_ratio"] - rs[j]["win_ratio"]
                    if abs(d_w) < 1e-12:
                        pair_tie += 1
                        continue
                    pair_diff += 1
                    if d_s * d_w > 0:
                        pair_up += 1
                    else:
                        pair_down += 1
                    if len(examples) < 6 and abs(d_w) > 0.05:
                        examples.append({
                            "k": rs[i]["k"], "nL": rs[i]["nL"],
                            "b_hist": list(rs[i]["b_hist"][:8]),
                            "spread": [rs[i]["spread_b1"], rs[j]["spread_b1"]],
                            "win_ratio": [rs[i]["win_ratio"], rs[j]["win_ratio"]],
                        })
        # pooled: does spread predict win_ratio better than n_bpos / b_max?
        Nrows = [f for f in feats.values() if f["g"] != 0 and f["n_b1"] >= 2]
        rho_spread = spearman([f["spread_b1"] for f in Nrows], [f["win_ratio"] for f in Nrows])
        rho_nbpos = spearman([f["n_bpos"] for f in Nrows], [f["win_ratio"] for f in Nrows])
        rho_bmax = spearman([f["b_max"] for f in Nrows], [f["win_ratio"] for f in Nrows])
        b485[str(n)] = {
            "cells_bh": cells,
            "pairs_diff": pair_diff,
            "spread_agree": pair_up,
            "spread_disagree": pair_down,
            "ties": pair_tie,
            "agree_rate": (pair_up / pair_diff) if pair_diff else None,
            "pooled_rho_spread": rho_spread,
            "pooled_rho_n_bpos": rho_nbpos,
            "pooled_rho_b_max": rho_bmax,
            "examples": examples,
        }
    report["B485"] = b485

    # =================================================================
    # B487: u_ent (mid-layer thickness) vs u_max as g predictor
    # =================================================================
    print("=== B487 ===", flush=True)
    b487 = {}
    for n in (3, 4, 5):
        feats = feats_all[n]
        rows = list(feats.values())
        # pooled N-positions
        Nrows = [f for f in rows if f["g"] != 0]
        rho_ent_g = spearman([f["u_ent"] for f in Nrows], [f["g"] for f in Nrows])
        rho_umax_g = spearman([f["u_max"] for f in Nrows], [f["g"] for f in Nrows])
        rho_ndist_g = spearman([f["n_distinct_u"] for f in Nrows], [f["g"] for f in Nrows])
        # within (k, u_max, u_min): does entropy beat u_max? (u_max fixed so compare ent vs g)
        by = defaultdict(list)
        for f in Nrows:
            by[(f["k"], f["u_max"], f["u_min"])].append(f)
        cells = 0
        ent_pos = 0
        ent_neg = 0
        ent_zero = 0
        for key, rs in by.items():
            if len(rs) < 8:
                continue
            if len(set(r["u_ent"] for r in rs)) < 2 or len(set(r["g"] for r in rs)) < 2:
                continue
            rho = spearman([r["u_ent"] for r in rs], [r["g"] for r in rs])
            if rho is None:
                continue
            cells += 1
            if rho > 0.05:
                ent_pos += 1
            elif rho < -0.05:
                ent_neg += 1
            else:
                ent_zero += 1
        # also k-layer overall: rho_ent vs rho_umax
        byk = defaultdict(list)
        for f in Nrows:
            byk[f["k"]].append(f)
        layer_cmp = []
        for k, rs in sorted(byk.items()):
            if len(rs) < 20:
                continue
            re = spearman([r["u_ent"] for r in rs], [r["g"] for r in rs])
            ru = spearman([r["u_max"] for r in rs], [r["g"] for r in rs])
            layer_cmp.append({"k": k, "n": len(rs), "rho_ent": re, "rho_umax": ru,
                              "ent_wins": (re is not None and ru is not None and re > ru)})
        b487[str(n)] = {
            "pooled_rho_ent_g": rho_ent_g,
            "pooled_rho_umax_g": rho_umax_g,
            "pooled_rho_ndist_g": rho_ndist_g,
            "cells_fixed_umaxumin": cells,
            "ent_pos": ent_pos, "ent_neg": ent_neg, "ent_zero": ent_zero,
            "layer_cmp": layer_cmp,
        }
    report["B487"] = b487

    # =================================================================
    # B489: T*/WFT vs illusion
    # =================================================================
    print("=== B489 ===", flush=True)
    b489 = {}
    for n in (4, 5):
        feats = feats_all[n]
        T = tw_all[n]["T"]
        W = tw_all[n]["W"]
        rows = []
        for occ, f in feats.items():
            ts = T[occ]
            ws = W[occ]
            span_t = (max(ts) - min(ts)) if ts else 0
            n_t = len(ts)
            min_w = min(ws) if ws else 0
            max_w = max(ws) if ws else 0
            span_w = max_w - min_w
            # WFT small = min_w - k small (winner forces short game)
            wft_short = min_w - f["k"] if ws else 0
            rows.append({
                "k": f["k"], "nL": f["nL"], "g": f["g"],
                "illusion": f["illusion"],
                "span_t": span_t, "n_t": n_t,
                "min_w": min_w, "span_w": span_w, "wft_short": wft_short,
                "hmax": f["hmax"], "win_ratio": f["win_ratio"],
            })
        # pooled non-terminal
        act = [r for r in rows if r["nL"] > 0 and r["k"] < n * n - 1]
        res = {
            "n_act": len(act),
            "rho_span_t_illusion": spearman([r["span_t"] for r in act], [r["illusion"] for r in act]),
            "rho_nt_illusion": spearman([r["n_t"] for r in act], [r["illusion"] for r in act]),
            "rho_minw_illusion": spearman([r["min_w"] for r in act], [r["illusion"] for r in act]),
            "rho_wftshort_illusion": spearman([r["wft_short"] for r in act], [r["illusion"] for r in act]),
            "rho_spanw_illusion": spearman([r["span_w"] for r in act], [r["illusion"] for r in act]),
            "rho_winratio_illusion": spearman([r["win_ratio"] for r in act], [r["illusion"] for r in act]),
        }
        # cells (k, nL) where span_t high vs low illusion
        by = defaultdict(list)
        for r in act:
            by[(r["k"], r["nL"])].append(r)
        cell_stats = []
        for key, rs in sorted(by.items()):
            if len(rs) < 8:
                continue
            if len(set(r["span_t"] for r in rs)) < 2:
                continue
            med = sorted(r["span_t"] for r in rs)[len(rs) // 2]
            hi = [r for r in rs if r["span_t"] >= med]
            lo = [r for r in rs if r["span_t"] < med]
            if not hi or not lo:
                continue
            mi = sum(r["illusion"] for r in hi) / len(hi)
            ml = sum(r["illusion"] for r in lo) / len(lo)
            cell_stats.append({
                "k": key[0], "nL": key[1], "n": len(rs),
                "mean_illusion_hi_span": mi,
                "mean_illusion_lo_span": ml,
                "gap": mi - ml,
                "rho_span_ill": spearman([r["span_t"] for r in rs], [r["illusion"] for r in rs]),
            })
        res["cells"] = cell_stats[:30]
        res["n_cells"] = len(cell_stats)
        res["gap_pos"] = sum(1 for c in cell_stats if c["gap"] > 0)
        res["gap_neg"] = sum(1 for c in cell_stats if c["gap"] < 0)
        b489[str(n)] = res
    report["B489"] = b489

    # =================================================================
    # B490: feature keys that separate two axes but collide on third
    # =================================================================
    print("=== B490 ===", flush=True)
    b490 = {}
    for n in (3, 4, 5):
        feats = feats_all[n]
        rows = list(feats.values())
        # candidate local feature fields (exclude g, mu, hmax, win_ratio, illusion)
        fields = ["k", "nL", "stab", "n_b1", "b_max", "n_bpos", "b_var",
                  "n_distinct_u", "u_max", "u_min", "u_ent"]
        # try subsets of fields as key
        from itertools import combinations
        best = {"g_mu": None, "g_h": None, "mu_h": None, "all3": None}

        def score(keyfn):
            by = defaultdict(list)
            for r in rows:
                by[keyfn(r)].append(r)
            cg = ch = cm = c3 = 0
            for k, rs in by.items():
                if len(rs) < 2:
                    continue
                gs = set(r["g"] for r in rs)
                ms = set(r["mu"] for r in rs)
                hs = set(r["hmax"] for r in rs)
                if len(gs) > 1:
                    cg += 1
                if len(hs) > 1:
                    ch += 1
                if len(ms) > 1:
                    cm += 1
                if len(gs) > 1 and len(ms) > 1 and len(hs) > 1:
                    c3 += 1
            return cg, cm, ch, c3

        results = []
        # single and pair fields
        for r in range(1, 5):
            for combo in combinations(fields, r):
                def keyfn(r, combo=combo):
                    return tuple(
                        (round(r[f], 4) if f in ("b_var", "u_ent") else r[f])
                        for f in combo
                    )
                cg, cm, ch, c3 = score(keyfn)
                results.append({
                    "fields": list(combo),
                    "coll_g": cg, "coll_mu": cm, "coll_h": ch, "coll_3": c3,
                    "sep_g_mu": (cg == 0 and cm == 0),
                    "sep_g_h": (cg == 0 and ch == 0),
                    "sep_mu_h": (cm == 0 and ch == 0),
                })
        # pick examples: sep_g_mu with coll_h>0; etc.
        def pick(pred):
            cands = [r for r in results if pred(r)]
            if not cands:
                return None
            # prefer fewer fields, more collisions on the third
            cands.sort(key=lambda z: (len(z["fields"]), -max(z["coll_g"], z["coll_mu"], z["coll_h"])))
            return cands[0]

        ex_gmu = pick(lambda z: z["sep_g_mu"] and z["coll_h"] > 0)
        ex_gh = pick(lambda z: z["sep_g_h"] and z["coll_mu"] > 0)
        ex_muh = pick(lambda z: z["sep_mu_h"] and z["coll_g"] > 0)
        ex_all3 = pick(lambda z: z["coll_g"] > 0 and z["coll_mu"] > 0 and z["coll_h"] > 0)
        # also count how many keys separate each pair
        n_sep_gmu = sum(1 for r in results if r["sep_g_mu"])
        n_sep_gh = sum(1 for r in results if r["sep_g_h"])
        n_sep_muh = sum(1 for r in results if r["sep_mu_h"])
        b490[str(n)] = {
            "n_keys_tried": len(results),
            "n_sep_g_mu": n_sep_gmu,
            "n_sep_g_h": n_sep_gh,
            "n_sep_mu_h": n_sep_muh,
            "ex_sep_g_mu_coll_h": ex_gmu,
            "ex_sep_g_h_coll_mu": ex_gh,
            "ex_sep_mu_h_coll_g": ex_muh,
            "ex_all3_coll": ex_all3,
        }
    report["B490"] = b490

    # =================================================================
    # B495: hist_full groups — also try non-square boards for a counterexample
    # =================================================================
    print("=== B495 ===", flush=True)
    b495 = {}

    def hist_and_reach(n, board, recs_n):
        by_occ = {r["occ"]: r for r in recs_n}
        reach = reach_all(board, recs_n)
        maximals = [r for r in recs_n if r["nL"] == 0]
        mfeat = []
        for r in maximals:
            m = r["occ"]
            bits = [i for i in range(board.V) if (m >> i) & 1]
            sz = len(bits)
            byk_L = defaultdict(list)
            full = 1 << sz
            for sub in range(1, full - 1):
                occ = 0
                bb = sub
                j = 0
                while bb:
                    if bb & 1:
                        occ |= 1 << bits[j]
                    bb >>= 1
                    j += 1
                pr = by_occ.get(occ)
                if pr is None:
                    continue
                byk_L[pr["k"]].append(pr["nL"])
            hist = tuple(sorted((k, nL) for k, vs in byk_L.items() for nL in vs))
            mfeat.append({"occ": m, "sz": sz, "reach": reach.get(m, 0.0), "hist_full": hist})
        by_full = defaultdict(list)
        for m in mfeat:
            by_full[m["hist_full"]].append(m)
        n_groups = 0
        n_pairs = 0
        max_ratio = 1.0
        n_diff = 0
        for gk, gs in by_full.items():
            if len(gs) < 2:
                continue
            n_groups += 1
            rs = [g["reach"] for g in gs]
            n_pairs += len(gs) * (len(gs) - 1) // 2
            if min(rs) > 0:
                ratio = max(rs) / min(rs)
            else:
                ratio = float("inf") if max(rs) > 0 else 1.0
            if ratio > 1.0 + 1e-9:
                n_diff += 1
            if ratio > max_ratio:
                max_ratio = ratio
        return {
            "n_max": len(mfeat), "n_groups": n_groups, "n_pairs": n_pairs,
            "max_ratio": max_ratio if max_ratio != float("inf") else "inf",
            "n_groups_reach_diff": n_diff,
        }

    for n in (4, 5):
        b495[str(n)] = hist_and_reach(n, boards[n], recs[n])

    # extra boards: 3x4, 3x5, 4x4-minus-one (small, quick)
    extra = []
    try:
        from kyouen_core import board_rect, board_square_minus
        for label, brd in [
            ("3x4", board_rect(3, 4)),
            ("3x5", board_rect(3, 5)),
            ("2x5", board_rect(2, 5)),
            ("4x4-1pt", board_square_minus(4, [(0, 0)])),
        ]:
            # enumerate all safe sets by BFS
            print(f"  B495 extra {label} V={brd.V}", flush=True)
            # simple DFS over legal moves to find all reachable states + maximals
            seen = {0}
            stack = [0]
            maximals = []
            states = []
            while stack:
                occ = stack.pop()
                states.append(occ)
                mv = brd.legal_moves(occ)
                if not mv:
                    maximals.append(occ)
                for u in mv:
                    ch = occ | (1 << u)
                    if ch not in seen:
                        seen.add(ch)
                        stack.append(ch)
            # build fake recs-like
            recs_e = []
            for occ in states:
                mv = brd.legal_moves(occ)
                recs_e.append({"occ": occ, "k": occ.bit_count(), "nL": len(mv),
                               "L": sum(1 << u for u in mv), "g": 0, "stab": 1})
            st = hist_and_reach(0, brd, recs_e)
            st["label"] = label
            st["n_states"] = len(states)
            extra.append(st)
    except Exception as e:
        extra.append({"error": str(e)})
    b495["extra_boards"] = extra

    # theoretical note: hist_full does not determine reach in general
    # tiny DP counterexample (not necessarily realizable):
    # M={a,b,c}, w=1/nL: nL(empty)=1; nL singletons (1,1,100); nL pairs (1,1,100) vs (100,1,1)
    def toy_reach(nLmap):
        # nLmap: frozenset -> nL
        M = frozenset([0, 1, 2])
        # r = sum over perms of prod 1/nL(prefix)
        from itertools import permutations
        acc = 0.0
        for perm in permutations(M):
            pref = frozenset()
            prod = 1.0
            for x in perm:
                prod /= nLmap[pref]
                pref = pref | {x}
            acc += prod
        return acc

    # wait: last step is from |S|=2 to |S|=3 which is terminal; product should include
    # 1/nL(empty) * 1/nL(singleton) only (2 divisions for 3 stones)? Paths of length 3:
    # moves at states of size 0,1,2. So 3 divisions, nL(size2) too.
    def toy_reach2(nLmap):
        from itertools import permutations
        M = frozenset([0, 1, 2])
        acc = 0.0
        for perm in permutations(M):
            pref = frozenset()
            prod = 1.0
            for x in perm:
                prod /= nLmap[pref]
                pref = pref | {x}
            acc += prod
        return acc

    # Build two assignments with same multiset of (k,nL)
    # size0: nL=1 for both
    # size1: nL in {1,1,100}
    # size2: nL in {1,1,100}
    A = {
        frozenset(): 1,
        frozenset([0]): 1, frozenset([1]): 1, frozenset([2]): 100,
        frozenset([0, 1]): 1, frozenset([0, 2]): 1, frozenset([1, 2]): 100,
    }
    B = {
        frozenset(): 1,
        frozenset([0]): 1, frozenset([1]): 1, frozenset([2]): 100,
        frozenset([0, 1]): 100, frozenset([0, 2]): 1, frozenset([1, 2]): 1,
    }
    rA = toy_reach2(A)
    rB = toy_reach2(B)
    b495["toy_counterexample"] = {
        "reach_A": rA, "reach_B": rB,
        "ratio": (max(rA, rB) / min(rA, rB)) if min(rA, rB) > 0 else None,
        "same_hist_full": True,
        "note": "combinatorial DP: identical multiset of (k,nL) over subsets does not force equal reach; geometry of which subset carries which nL matters",
    }
    report["B495"] = b495

    # =================================================================
    # B496: exact ratio max in (sz,stab) cells + search for ratio>=10
    # =================================================================
    print("=== B496 ===", flush=True)
    b496 = {}
    for n in (4, 5):
        feats = feats_all[n]
        reach = reach_all_map[n]
        maximals = [f for f in feats.values() if f["nL"] == 0]
        by_ss = defaultdict(list)
        for f in maximals:
            by_ss[(f["k"], f["stab"])].append(f)
        cells = []
        best_pair = None
        best_ratio = 1.0
        for key, gs in sorted(by_ss.items()):
            if len(gs) < 2:
                continue
            rs = [reach.get(g["occ"], 0.0) for g in gs]
            if min(rs) <= 0:
                ratio = float("inf") if max(rs) > 0 else 1.0
            else:
                ratio = max(rs) / min(rs)
            if ratio > best_ratio:
                best_ratio = ratio
                # find the pair
                imax = rs.index(max(rs))
                imin = rs.index(min(rs))
                best_pair = {
                    "sz": key[0], "stab": key[1], "n": len(gs),
                    "max_r": max(rs), "min_r": min(rs),
                    "ratio": ratio if ratio != float("inf") else "inf",
                    "max_occ": gs[imax]["occ"], "min_occ": gs[imin]["occ"],
                }
            cells.append({
                "sz": key[0], "stab": key[1], "n": len(gs),
                "ratio": ratio if ratio != float("inf") else "inf",
            })
        b496[str(n)] = {
            "max_ratio": best_ratio if best_ratio != float("inf") else "inf",
            "best_pair": best_pair,
            "cells": cells,
            "ratio_ge_9": best_ratio >= 9.0,
            "ratio_ge_10": best_ratio >= 10.0,
        }
    report["B496"] = b496

    # =================================================================
    # B499: P_min=0 vs close E[X]; widen window
    # =================================================================
    print("=== B499 ===", flush=True)
    b499 = {}
    for n in (4, 5):
        feats = feats_all[n]
        reach = reach_all_map[n]
        board = boards[n]
        by_occ = {r["occ"]: r for r in recs[n]}
        min_sz = min(f["k"] for f in feats.values() if f["nL"] == 0)
        first_stats = []
        for p in range(board.V):
            occ0 = 1 << p
            creach = {occ0: 1.0}
            sub = [r for r in recs[n] if (r["occ"] >> p) & 1]
            sub_asc = sorted(sub, key=lambda r: r["k"])
            for r in sub_asc:
                occ = r["occ"]
                if occ == occ0:
                    continue
                pr = 0.0
                bits = [i for i in range(board.V) if (occ >> i) & 1]
                for i in bits:
                    if i == p:
                        continue
                    par = occ ^ (1 << i)
                    if par not in creach:
                        continue
                    pra = by_occ.get(par)
                    if pra is None:
                        continue
                    pr += creach[par] / pra["nL"]
                if pr:
                    creach[occ] = pr
            pmin = 0.0
            ex = 0.0
            for r in sub:
                if r["nL"] != 0:
                    continue
                pr = creach.get(r["occ"], 0.0)
                ex += pr * r["k"]
                if r["k"] == min_sz:
                    pmin += pr
            first_stats.append({"p": p, "x": p % n, "y": p // n, "E_X": ex, "P_min": pmin})

        zeros = [s for s in first_stats if s["P_min"] == 0.0]
        pos = [s for s in first_stats if s["P_min"] > 0.0]
        # min |dE| between zero and positive
        min_dE = None
        pair0 = None
        for a in zeros:
            for c in pos:
                d = abs(a["E_X"] - c["E_X"])
                if min_dE is None or d < min_dE:
                    min_dE = d
                    pair0 = {"zero": [a["x"], a["y"], round(a["E_X"], 6)],
                             "pos": [c["x"], c["y"], round(c["E_X"], 6), c["P_min"]],
                             "dE": d}
        # pairs with |dE|<=0.05 and also <=0.1, <=0.2
        def max_ratio_in(window):
            best = 1.0
            bp = None
            inf = 0
            for i in range(len(first_stats)):
                for j in range(i + 1, len(first_stats)):
                    a, c = first_stats[i], first_stats[j]
                    if abs(a["E_X"] - c["E_X"]) > window:
                        continue
                    pa, pc = a["P_min"], c["P_min"]
                    if pa <= 0 and pc <= 0:
                        continue
                    if min(pa, pc) <= 0:
                        inf += 1
                        continue
                    ratio = max(pa, pc) / min(pa, pc)
                    if ratio > best:
                        best = ratio
                        bp = {"p": [a["x"], a["y"]], "q": [c["x"], c["y"]],
                              "dE": abs(a["E_X"] - c["E_X"]), "P_min": [pa, pc], "ratio": ratio}
            return {"max_ratio": best, "best_pair": bp, "inf_pairs": inf}

        b499[str(n)] = {
            "min_sz": min_sz,
            "n_zero_pmin": len(zeros),
            "n_pos_pmin": len(pos),
            "E_range": [min(s["E_X"] for s in first_stats), max(s["E_X"] for s in first_stats)],
            "Pmin_range": [min(s["P_min"] for s in first_stats), max(s["P_min"] for s in first_stats)],
            "closest_zero_pos": pair0,
            "w0.05": max_ratio_in(0.05),
            "w0.10": max_ratio_in(0.10),
            "w0.20": max_ratio_in(0.20),
            "first": first_stats,
        }
    report["B499"] = b499

    # =================================================================
    # B500: bottleneck sharpness — layer ratios + last-layer survival
    # =================================================================
    print("=== B500 ===", flush=True)
    b500 = {}
    for n in (4, 5):
        feats = feats_all[n]
        reach = reach_all_map[n]
        board = boards[n]
        maximals = [f for f in feats.values() if f["nL"] == 0]
        # compute layer_hi for all maximals is expensive (2^sz); do extremes + sample
        mfeat_sorted = sorted(maximals, key=lambda f: reach.get(f["occ"], 0.0))
        targets = mfeat_sorted[:5] + mfeat_sorted[len(mfeat_sorted) // 2:len(mfeat_sorted) // 2 + 3] + mfeat_sorted[-5:]
        rows = []
        for f in targets:
            m = f["occ"]
            bits = [i for i in range(board.V) if (m >> i) & 1]
            sz = len(bits)
            layer_hi = defaultdict(float)
            full = 1 << sz
            for sub in range(full):
                occ = 0
                bb = sub
                j = 0
                while bb:
                    if bb & 1:
                        occ |= 1 << bits[j]
                    bb >>= 1
                    j += 1
                layer_hi[occ.bit_count()] += reach.get(occ, 0.0)
            his = [layer_hi[t] for t in range(sz + 1)]
            ratios = [his[t + 1] / his[t] for t in range(sz) if his[t] > 0]
            last_surv = his[sz] / his[sz - 1] if sz >= 1 and his[sz - 1] > 0 else None
            med = sorted(ratios)[len(ratios) // 2] if ratios else None
            min_r = min(ratios) if ratios else None
            rows.append({
                "sz": sz, "reach": reach.get(m, 0.0),
                "layer_hi": his,
                "layer_ratios": ratios,
                "last_surv": last_surv,
                "min_ratio": min_r, "med_ratio": med,
                "sharpness": (min_r / med) if (min_r is not None and med) else None,
            })
        # sharpness criterion: min_ratio <= 0.5 * med => sharp bottleneck
        n_sharp = sum(1 for r in rows if r["sharpness"] is not None and r["sharpness"] <= 0.5)
        b500[str(n)] = {
            "n_targets": len(rows),
            "n_sharp_bottleneck": n_sharp,
            "rows": rows,
            "note": "sharpness = min layer_ratio / median layer_ratio; <=0.5 counts as single sharp bottleneck",
        }
    report["B500"] = b500

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

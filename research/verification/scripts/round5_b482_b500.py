#!/usr/bin/env python3
"""Round5 B482-B500 residual stats + greedy reach on n=3,4,5.

Uses batch03_cache.pkl recs (occ,k,g,L,Rhash,...) + board quads.
Outputs research/verification/round5_b482b500.json
"""
from __future__ import annotations

import json
import math
import pickle
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round5_b482b500.json"
CACHE = ROOT / "research" / "verification" / "batch03_cache.pkl"
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


def p_graph(nv_empty: int, edges: list[tuple[int, int]]):
    adj = [set() for _ in range(nv_empty)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def count_triangles(adj) -> int:
    t = 0
    for a in range(len(adj)):
        for b in adj[a]:
            if b <= a:
                continue
            t += len(adj[a] & adj[b])
    return t


def comp_sizes(adj) -> list[int]:
    n = len(adj)
    seen = [False] * n
    sizes = []
    for i in range(n):
        if seen[i]:
            continue
        stack = [i]
        seen[i] = True
        sz = 0
        while stack:
            u = stack.pop()
            sz += 1
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
        sizes.append(sz)
    return sizes


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


def extract_features(board: Board, occ: int) -> dict:
    """Bit-optimized tri / n_comp_ge3 / b / u features."""
    V = board.V
    empty = _empties_of(occ, V)
    epos = {e: idx for idx, e in enumerate(empty)}
    ne = len(empty)
    adj = [0] * ne
    n_bridge3 = 0
    for q in board.quads:
        pc = (q & occ).bit_count()
        if pc == 2:
            em2 = q & ~occ
            a = (em2 & -em2).bit_length() - 1
            b = (em2 & (em2 - 1)).bit_length() - 1
            ia, ib = epos[a], epos[b]
            adj[ia] |= 1 << ib
            adj[ib] |= 1 << ia
        elif pc == 3:
            n_bridge3 += 1

    # triangles
    tri = 0
    for a in range(ne):
        aa = adj[a]
        x = aa
        while x:
            bb = (x & -x).bit_length() - 1
            if bb > a:
                tri += (adj[a] & adj[bb]).bit_count()
            x &= x - 1

    # components
    seen = 0
    sizes = []
    for i in range(ne):
        if (seen >> i) & 1:
            continue
        stack = [i]
        seen |= 1 << i
        sz = 0
        while stack:
            u = stack.pop()
            sz += 1
            x = adj[u]
            while x:
                v = (x & -x).bit_length() - 1
                if not (seen >> v) & 1:
                    seen |= 1 << v
                    stack.append(v)
                x &= x - 1
        sizes.append(sz)
    n_comp = len(sizes)
    n_comp_ge3 = sum(1 for s in sizes if s >= 3)

    # b stats
    qbp = board.quads_by_pt
    bs = []
    n_b1 = 0
    pts_b1 = []
    for p in empty:
        bit = 1 << p
        bp = 0
        for q in qbp[p]:
            if (q & bit) == bit and (q & occ).bit_count() == 3:
                bp += 1
        bs.append(bp)
        if bp == 1:
            n_b1 += 1
            pts_b1.append(p)
    if not bs:
        bres = dict(b_mean=0.0, b_var=0.0, b_max=0, b_frac0=1.0, n_empty=0,
                    b_var_pos=0.0, b_mean_pos=0.0, n_b1=0, n_bpos=0,
                    spread_b1=0.0, b_hist={})
    else:
        m = sum(bs) / len(bs)
        var = sum((x - m) ** 2 for x in bs) / len(bs)
        pos = [x for x in bs if x > 0]
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
        bres = dict(
            b_mean=m, b_var=var, b_max=max(bs),
            b_frac0=sum(1 for x in bs if x == 0) / len(bs),
            n_empty=len(bs),
            b_var_pos=(sum((x - sum(pos) / len(pos)) ** 2 for x in pos) / len(pos)) if pos else 0.0,
            b_mean_pos=(sum(pos) / len(pos)) if pos else 0.0,
            n_b1=n_b1,
            n_bpos=len(pos),
            spread_b1=spread,
            b_hist={str(v): bs.count(v) for v in sorted(set(bs))},
        )

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
        ures = dict(n_legal=0, u_mean=0.0, u_max=0, u_min=0, n_distinct_u=0, u_hist={})
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
        ures = dict(
            n_legal=len(us),
            u_mean=sum(us) / len(us),
            u_max=max(us),
            u_min=min(us),
            n_distinct_u=len(set(us)),
            u_hist={str(v): us.count(v) for v in sorted(set(us))},
        )

    return {
        "tri": tri,
        "n_comp": n_comp,
        "n_comp_ge3": n_comp_ge3,
        "n_bridge3": n_bridge3,
        "n_legal_extract": len(legal),
        **bres,
        **ures,
    }


def analyze_n(n: int, boards, recs) -> dict:
    b = boards[n]
    rows = recs[n]
    print(f"n={n}: {len(rows)} states, tree DP", flush=True)

    by_occ = {r["occ"]: r for r in rows}
    rows_sorted = sorted(rows, key=lambda r: -r["k"])
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

    feats = []
    for i, r in enumerate(rows):
        if i % 20000 == 0:
            print(f"  feats {i}/{len(rows)}", flush=True)
        occ = r["occ"]
        fx = extract_features(b, occ)
        feats.append({
            "occ": occ,
            "k": r["k"],
            "g": r["g"],
            "P": 1 if r["g"] == 0 else 0,
            "nL": r["nL"],
            "stab": r["stab"],
            "Rhash": r["Rhash"],
            "tri": fx["tri"],
            "n_comp": fx["n_comp"],
            "n_comp_ge3": fx["n_comp_ge3"],
            "n_bridge3": fx["n_bridge3"],
            "b_var": fx["b_var"],
            "b_var_pos": fx["b_var_pos"],
            "b_mean": fx["b_mean"],
            "b_frac0": fx["b_frac0"],
            "b_max": fx["b_max"],
            "n_b1": fx["n_b1"],
            "n_bpos": fx["n_bpos"],
            "spread_b1": fx["spread_b1"],
            "b_hist": fx["b_hist"],
            "u_mean": fx["u_mean"],
            "u_max": fx["u_max"],
            "u_min": fx["u_min"],
            "n_distinct_u": fx["n_distinct_u"],
            "u_hist": fx["u_hist"],
            "mu": mu[occ],
            "hmax": hmax[occ],
            "win_ratio": win_ratio[occ],
            "n_win": n_win[occ],
            "rand_odd": rand_odd[occ],
            "illusion": rand_odd[occ] if r["g"] == 0 else (1.0 - rand_odd[occ]),
        })
    return {"feats": feats, "mu": mu, "rand_odd": rand_odd, "by_occ": by_occ}


def cell_rows(feats, keyfn, min_n=8):
    by = defaultdict(list)
    for r in feats:
        by[keyfn(r)].append(r)
    return {k: v for k, v in by.items() if len(v) >= min_n}


def main():
    with open(CACHE, "rb") as f:
        cache = pickle.load(f)
    boards = {n: board_square(n) for n in (3, 4, 5)}
    recs = {n: cache[n]["recs"] for n in (3, 4, 5)}
    report = {}

    for n in (3, 4, 5):
        pack = analyze_n(n, boards, recs)
        feats = pack["feats"]
        print(f"n={n} features done", flush=True)

        # ---- B482: same (k,|L|), continuous n_comp_ge3 vs g after tri ----
        b482 = {"cells_cont": [], "cell_tri_l": {}}
        for key, rs in sorted(cell_rows(feats, lambda r: (r["k"], r["nL"]), 10).items()):
            xs_comp = [r["n_comp_ge3"] for r in rs]
            ys_g = [r["g"] for r in rs]
            xs_tri = [r["tri"] for r in rs]
            rho_comp = spearman(xs_comp, ys_g)
            rho_tri = spearman(xs_tri, ys_g)
            # residualize g on tri rank, then corr with n_comp_ge3
            # simple: within tri strata (top/bottom half)
            med_tri = sorted(xs_tri)[len(xs_tri) // 2]
            lo = [r for r in rs if r["tri"] <= med_tri]
            hi = [r for r in rs if r["tri"] > med_tri]
            rho_comp_lo = spearman([r["n_comp_ge3"] for r in lo], [r["g"] for r in lo])
            rho_comp_hi = spearman([r["n_comp_ge3"] for r in hi], [r["g"] for r in hi])
            # g-kind richness when n_comp_ge3 high vs low
            med_c = sorted(xs_comp)[len(xs_comp) // 2]
            c_lo = [r for r in rs if r["n_comp_ge3"] <= med_c]
            c_hi = [r for r in rs if r["n_comp_ge3"] > med_c]
            kinds_lo = len(set(r["g"] for r in c_lo)) if c_lo else 0
            kinds_hi = len(set(r["g"] for r in c_hi)) if c_hi else 0
            b482["cells_cont"].append({
                "k": key[0], "nL": key[1], "n": len(rs),
                "rho_comp_g": rho_comp, "rho_tri_g": rho_tri,
                "rho_comp_g_tri_lo": rho_comp_lo, "rho_comp_g_tri_hi": rho_comp_hi,
                "g_kinds_comp_lo": kinds_lo, "g_kinds_comp_hi": kinds_hi,
                "mean_g_comp_lo": sum(r["g"] for r in c_lo) / len(c_lo) if c_lo else None,
                "mean_g_comp_hi": sum(r["g"] for r in c_hi) / len(c_hi) if c_hi else None,
            })
        # exact (k,tri,|L|) cells
        exact = cell_rows(feats, lambda r: (r["k"], r["tri"], r["nL"]), 4)
        b482["cell_tri_l"] = {"n_cells": len(exact), "keys": [str(k) for k in list(exact)[:8]]}
        report.setdefault("B482", {})[str(n)] = b482

        # ---- B484: b_var vs win_ratio, split by including b=0 ----
        b484 = []
        for key, rs in sorted(cell_rows(feats, lambda r: (r["k"], r["nL"]), 8).items()):
            # N positions only for win_ratio variance
            ns = [r for r in rs if r["g"] != 0]
            if len(ns) < 6:
                continue
            rho_all = spearman([r["b_var"] for r in ns], [r["win_ratio"] for r in ns])
            rho_pos = spearman([r["b_var_pos"] for r in ns], [r["win_ratio"] for r in ns])
            rho_frac = spearman([r["b_frac0"] for r in ns], [r["win_ratio"] for r in ns])
            var_pos_vals = [r["b_var_pos"] for r in ns]
            b484.append({
                "k": key[0], "nL": key[1], "n": len(ns),
                "rho_bvar_win": rho_all,
                "rho_bvarpos_win": rho_pos,
                "rho_bfrac0_win": rho_frac,
                "var_of_bvarpos": (sum((x - sum(var_pos_vals)/len(var_pos_vals))**2 for x in var_pos_vals) / len(var_pos_vals)) if var_pos_vals else 0,
                "mean_n_b1": sum(r["n_b1"] for r in ns) / len(ns),
                "mean_n_bpos": sum(r["n_bpos"] for r in ns) / len(ns),
            })
        report.setdefault("B484", {})[str(n)] = b484

        # ---- B485: spread of b=1 vs win_ratio ----
        b485 = []
        for key, rs in sorted(cell_rows(feats, lambda r: (r["k"], r["nL"]), 8).items()):
            ns = [r for r in rs if r["g"] != 0 and r["n_b1"] >= 2]
            if len(ns) < 6:
                continue
            rho = spearman([r["spread_b1"] for r in ns], [r["win_ratio"] for r in ns])
            b485.append({
                "k": key[0], "nL": key[1], "n": len(ns),
                "rho_spread_win": rho,
                "mean_n_b1": sum(r["n_b1"] for r in ns) / len(ns),
                "mean_spread": sum(r["spread_b1"] for r in ns) / len(ns),
            })
        report.setdefault("B485", {})[str(n)] = b485

        # ---- B486: mu>=3, rand_odd separates P/N ----
        b486 = {"n_mu_ge3": 0, "cells": [], "overall": None}
        mu3 = [r for r in feats if r["mu"] >= 3]
        b486["n_mu_ge3"] = len(mu3)
        if mu3:
            ps = [r["rand_odd"] for r in mu3 if r["g"] == 0]
            ns = [r["rand_odd"] for r in mu3 if r["g"] != 0]
            b486["overall"] = {
                "n_P": len(ps), "n_N": len(ns),
                "mean_rand_P": sum(ps) / len(ps) if ps else None,
                "mean_rand_N": sum(ns) / len(ns) if ns else None,
                "gap": (sum(ps) / len(ps) - sum(ns) / len(ns)) if ps and ns else None,
            }
        for key, rs in sorted(cell_rows(mu3, lambda r: (r["k"], r["nL"]), 8).items()):
            ps = [r for r in rs if r["g"] == 0]
            ns = [r for r in rs if r["g"] != 0]
            if len(ps) < 3 or len(ns) < 3:
                continue
            b486["cells"].append({
                "k": key[0], "nL": key[1], "n": len(rs),
                "n_P": len(ps), "n_N": len(ns),
                "mean_rand_P": sum(r["rand_odd"] for r in ps) / len(ps),
                "mean_rand_N": sum(r["rand_odd"] for r in ns) / len(ns),
                "gap": sum(r["rand_odd"] for r in ps) / len(ps) - sum(r["rand_odd"] for r in ns) / len(ns),
            })
        report.setdefault("B486", {})[str(n)] = b486

        # ---- B487: n_distinct_u vs g, controlling u_max/u_min ----
        b487 = []
        for key, rs in sorted(cell_rows(feats, lambda r: r["k"], 20).items()):
            rho_nd = spearman([r["n_distinct_u"] for r in rs], [r["g"] for r in rs])
            rho_um = spearman([r["u_max"] for r in rs], [r["g"] for r in rs])
            within = []
            by_um = defaultdict(list)
            for r in rs:
                by_um[(r["u_max"], r["u_min"])].append(r)
            for uk, urs in by_um.items():
                if len(urs) < 8:
                    continue
                if len(set(r["g"] for r in urs)) < 2 or len(set(r["n_distinct_u"] for r in urs)) < 2:
                    continue
                within.append({
                    "u_max": uk[0], "u_min": uk[1], "n": len(urs),
                    "rho_ndistinct_g": spearman([r["n_distinct_u"] for r in urs], [r["g"] for r in urs]),
                    "g_range": [min(r["g"] for r in urs), max(r["g"] for r in urs)],
                })
            b487.append({"k": key, "n": len(rs), "rho_ndistinct_g": rho_nd, "rho_umax_g": rho_um,
                         "within_uminmax": within})
        report.setdefault("B487", {})[str(n)] = b487

        # ---- B488: Rhash dedup vs signature dedup, tri-g sign ----
        b488 = []
        for key, rs in sorted(cell_rows(feats, lambda r: r["k"], 16).items()):
            rho_raw = spearman([r["tri"] for r in rs], [r["g"] for r in rs])
            # signature dedup (tri,|L|,g,n_comp,b_var)
            sig = {}
            for r in rs:
                sk = (r["tri"], r["nL"], r["g"], r["n_comp"], round(r["b_var"], 6))
                sig.setdefault(sk, r)
            sig_rows = list(sig.values())
            rho_sig = spearman([r["tri"] for r in sig_rows], [r["g"] for r in sig_rows])
            # true residual iso dedup via Rhash (approx)
            rhash = {}
            for r in rs:
                rhash.setdefault(r["Rhash"], r)
            rh_rows = list(rhash.values())
            rho_rh = spearman([r["tri"] for r in rh_rows], [r["g"] for r in rh_rows])
            # also u_hist signature
            usig = {}
            for r in rs:
                sk = (r["tri"], r["nL"], r["g"], tuple(sorted(r["u_hist"].items())))
                usig.setdefault(sk, r)
            u_rows = list(usig.values())
            rho_u = spearman([r["tri"] for r in u_rows], [r["g"] for r in u_rows])
            b488.append({
                "k": key, "n": len(rs),
                "rho_raw": rho_raw,
                "n_sig": len(sig_rows), "rho_sig": rho_sig,
                "n_rhash": len(rh_rows), "rho_rhash": rho_rh,
                "n_usig": len(u_rows), "rho_usig": rho_u,
                "sign_flip_sig": (rho_raw is not None and rho_sig is not None and rho_raw * rho_sig < 0),
                "sign_flip_rhash": (rho_raw is not None and rho_rh is not None and rho_raw * rho_rh < 0),
            })
        report.setdefault("B488", {})[str(n)] = b488

        # ---- B489: illusion vs n_distinct_u / mu uncertainty ----
        b489 = []
        for key, rs in sorted(cell_rows(feats, lambda r: (r["k"], r["nL"]), 8).items()):
            rho_nd = spearman([r["n_distinct_u"] for r in rs], [r["illusion"] for r in rs])
            rho_bv = spearman([r["b_var"] for r in rs], [r["illusion"] for r in rs])
            rho_h = spearman([r["hmax"] for r in rs], [r["illusion"] for r in rs])
            # T* proxy: n_win spread / hmax
            rho_wr = spearman([r["win_ratio"] for r in rs], [r["illusion"] for r in rs])
            b489.append({
                "k": key[0], "nL": key[1], "n": len(rs),
                "rho_ndistinct_u_illusion": rho_nd,
                "rho_bvar_illusion": rho_bv,
                "rho_hmax_illusion": rho_h,
                "rho_winratio_illusion": rho_wr,
            })
        report.setdefault("B489", {})[str(n)] = b489

        # ---- B490: feature collisions on g / P / mu ----
        feat_keys = [
            lambda r: (r["tri"], r["nL"], r["n_comp"], r["n_comp_ge3"], round(r["b_var"], 6),
                       round(r["b_mean"], 6), r["u_max"], round(r["u_mean"], 6), r["n_distinct_u"]),
            lambda r: (r["tri"], r["nL"], r["n_comp_ge3"], r["n_b1"], r["n_bpos"], r["u_max"], r["u_min"], r["n_distinct_u"]),
            lambda r: (r["tri"], r["nL"], r["n_comp"], round(r["b_var"], 6), r["u_max"], round(r["u_mean"], 6),
                       r["n_distinct_u"], r["mu"], r["hmax"]),
        ]
        b490 = {"n_states": len(feats)}
        for fi, fk in enumerate(feat_keys):
            by = defaultdict(list)
            for r in feats:
                by[fk(r)].append(r)
            multi_g = sum(1 for rs in by.values() if len(set(r["g"] for r in rs)) > 1)
            multi_P = sum(1 for rs in by.values() if len(set(r["P"] for r in rs)) > 1)
            multi_mu = sum(1 for rs in by.values() if len(set(r["mu"] for r in rs)) > 1)
            multi_h = sum(1 for rs in by.values() if len(set(r["hmax"] for r in rs)) > 1)
            b490[f"set{fi}"] = {
                "n_keys": len(by), "multi_g": multi_g, "multi_P": multi_P,
                "multi_mu": multi_mu, "multi_h": multi_h,
            }
        report.setdefault("B490", {})[str(n)] = b490

    # ---- B494-B500: greedy reach on n=4,5 ----
    for n in (4, 5):
        b = boards[n]
        rows = recs[n]
        by_occ = {r["occ"]: r for r in rows}
        rows_asc = sorted(rows, key=lambda r: r["k"])
        reach = {0: 1.0}
        for r in rows_asc:
            occ = r["occ"]
            if occ == 0:
                continue
            p = 0.0
            bits = [i for i in range(b.V) if (occ >> i) & 1]
            for i in bits:
                par = occ ^ (1 << i)
                if par not in reach:
                    continue
                pr = by_occ.get(par)
                if pr is None:
                    continue
                p += reach[par] / pr["nL"]
            reach[occ] = p

        maximals = [r for r in rows if r["nL"] == 0]
        mfeat = []
        for mi, r in enumerate(maximals):
            if mi % 3000 == 0 and mi:
                print(f"  n={n} maximal feats {mi}/{len(maximals)}", flush=True)
            m = r["occ"]
            bits = [i for i in range(b.V) if (m >> i) & 1]
            sz = len(bits)
            L_list = []
            off_list = []
            byk_L = defaultdict(list)
            byk_off = defaultdict(list)
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
                nL = pr["nL"]
                Lmask = pr["L"]
                off = 0
                lm = Lmask
                vi = 0
                while lm:
                    if lm & 1:
                        if not (m >> vi & 1):
                            off += 1
                    lm >>= 1
                    vi += 1
                k = pr["k"]
                L_list.append(nL)
                off_list.append(off)
                byk_L[k].append(nL)
                byk_off[k].append(off)
            mid_L = [v for k, vs in byk_L.items() if 0 < k < sz for v in vs]
            mid_off = [v for k, vs in byk_off.items() if 0 < k < sz for v in vs]
            mean_logL = sum(math.log(v) for v in mid_L) / len(mid_L) if mid_L else None
            mean_off = sum(mid_off) / len(mid_off) if mid_off else None
            # |L| histogram by subset size (coarse: sorted tuple of (k, sorted Ls) too big;
            # use multiset of (k, nL) counts)
            hist = tuple(sorted((k, nL) for k, vs in byk_L.items() for nL in vs))
            hist_stats = (
                round(sum(L_list) / len(L_list), 6) if L_list else 0,
                round(sum((x - sum(L_list)/len(L_list))**2 for x in L_list) / len(L_list), 6) if L_list else 0,
                len(L_list),
            )
            mfeat.append({
                "occ": m, "sz": sz, "stab": r["stab"], "g": r["g"],
                "reach": reach.get(m, 0.0),
                "mean_logL": mean_logL,
                "mean_off": mean_off,
                "n_sub": len(L_list),
                "hist_key": hist_stats,  # coarse
                "hist_full": hist,  # exact multiset
                "byk_off_mean": {k: (sum(vs)/len(vs) if vs else 0) for k, vs in byk_off.items()},
            })

        # B494: stab -> off -> reach
        stab_vals = [m["stab"] for m in mfeat]
        off_vals = [m["mean_off"] for m in mfeat if m["mean_off"] is not None]
        reach_vals = [m["reach"] for m in mfeat]
        valid = [m for m in mfeat if m["mean_off"] is not None and m["mean_logL"] is not None]
        b494 = {
            "n_max": len(mfeat),
            "stab_hist": {str(s): stab_vals.count(s) for s in sorted(set(stab_vals))},
            "rho_stab_off": spearman([m["stab"] for m in valid], [m["mean_off"] for m in valid]),
            "rho_off_reach": spearman([m["mean_off"] for m in valid], [m["reach"] for m in valid]),
            "rho_stab_reach": spearman([m["stab"] for m in valid], [m["reach"] for m in valid]),
            "rho_logL_reach": spearman([m["mean_logL"] for m in valid], [m["reach"] for m in valid]),
        }
        report.setdefault("B494", {})[str(n)] = b494

        # B495: same hist_key or same hist_full, different reach
        by_full = defaultdict(list)
        by_coarse = defaultdict(list)
        for m in mfeat:
            by_full[m["hist_full"]].append(m)
            by_coarse[m["hist_key"]].append(m)
        def max_ratio(groups):
            best = 0.0
            pair = None
            n_groups = 0
            n_pairs = 0
            for gk, gs in groups.items():
                if len(gs) < 2:
                    continue
                n_groups += 1
                rs = [g["reach"] for g in gs]
                if min(rs) > 0:
                    ratio = max(rs) / min(rs)
                else:
                    ratio = float("inf") if max(rs) > 0 else 1.0
                n_pairs += len(gs) * (len(gs) - 1) // 2
                if ratio > best:
                    best = ratio
                    pair = (len(gs), best if best != float("inf") else "inf")
            return {"n_groups": n_groups, "n_pairs": n_pairs, "max_ratio": pair}
        report.setdefault("B495", {})[str(n)] = {
            "full": max_ratio(by_full),
            "coarse": max_ratio(by_coarse),
            "note": "hist_full = multiset of (k,|L|) over proper safe subsets; coarse = (mean,var,n_sub)",
        }

        # B496: (sz,stab) cell max/min reach ratio
        by_ss = defaultdict(list)
        for m in mfeat:
            by_ss[(m["sz"], m["stab"])].append(m)
        cells = []
        for key, gs in sorted(by_ss.items()):
            if len(gs) < 4:
                continue
            rs = [g["reach"] for g in gs]
            if min(rs) <= 0:
                ratio = float("inf") if max(rs) > 0 else 1.0
                ratio_s = "inf"
            else:
                ratio = max(rs) / min(rs)
                ratio_s = round(ratio, 4)
            cells.append({
                "sz": key[0], "stab": key[1], "n": len(gs),
                "min_r": min(rs), "max_r": max(rs), "ratio": ratio_s,
            })
        report.setdefault("B496", {})[str(n)] = cells

        # B499: first-move conditional P(min terminal) and E[X]
        first_stats = []
        min_sz = min(m["sz"] for m in mfeat)
        # for each first move p, P(reach min | first p) and E[X | first p]
        # compute via conditional reach
        for p in range(b.V):
            occ0 = 1 << p
            if occ0 not in reach and occ0 not in by_occ:
                continue
            # conditional reach from occ0
            creach = {occ0: 1.0}
            # only states containing p
            sub = [r for r in rows if (r["occ"] >> p) & 1]
            sub_asc = sorted(sub, key=lambda r: r["k"])
            for r in sub_asc:
                occ = r["occ"]
                if occ == occ0:
                    continue
                pr = 0.0
                bits = [i for i in range(b.V) if (occ >> i) & 1]
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
            first_stats.append({
                "p": p, "x": p % n, "y": p // n,
                "E_X": ex, "P_min": pmin,
            })
        # pair search: |dE|<=0.05, P_min ratio
        pairs = []
        for i in range(len(first_stats)):
            for j in range(i + 1, len(first_stats)):
                a, c = first_stats[i], first_stats[j]
                if abs(a["E_X"] - c["E_X"]) > 0.05:
                    continue
                pa, pc = a["P_min"], c["P_min"]
                if pa <= 0 and pc <= 0:
                    continue
                if min(pa, pc) <= 0:
                    ratio = "inf" if max(pa, pc) > 0 else 1
                else:
                    ratio = round(max(pa, pc) / min(pa, pc), 4)
                pairs.append({
                    "p": [a["x"], a["y"]], "q": [c["x"], c["y"]],
                    "dE": round(abs(a["E_X"] - c["E_X"]), 6),
                    "P_min": [pa, pc], "ratio": ratio,
                })
        pairs.sort(key=lambda z: (0 if z["ratio"] == "inf" else -z["ratio"] if isinstance(z["ratio"], (int, float)) else 0))
        report.setdefault("B499", {})[str(n)] = {
            "min_sz": min_sz,
            "first": first_stats,
            "top_pairs": pairs[:12],
            "n_pairs": len(pairs),
        }

        # B500: bottleneck cut bounds
        # For each size layer t, cut = sum over S with |S|=t of reach(S)*P(S does not go to target)
        # Bound: P(hit T) <= sum_{S on path layers} ...
        # Practical: compare exact reach of top/bottom maximals with product of mid-layer survival
        # survival_i = fraction of children that stay "on track" toward a given target is hard;
        # instead compute the geometric cut bound:
        #   reach(T) <= min over layers t of  sum_{S: |S|=t, S subset T} reach(S) / 1
        # which is exact if T is the unique maximal through those subsets.
        # We compute for each target maximal M:
        #   hi_t = sum_{S subset M, |S|=t} reach(S)   (prob of being inside M's downset at layer t)
        #   reach(M) <= min_t hi_t  and  reach(M) = hi_{|M|} exactly
        cut_results = []
        # pick extreme maximals by reach
        mfeat_sorted = sorted(mfeat, key=lambda m: m["reach"])
        targets = mfeat_sorted[:3] + mfeat_sorted[-3:]
        for m in targets:
            bits = [i for i in range(b.V) if (m["occ"] >> i) & 1]
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
            his = {t: layer_hi[t] for t in sorted(layer_hi)}
            hi_bound = min(his.values()) if his else None
            exact = reach.get(m["occ"], 0.0)
            cut_results.append({
                "sz": sz, "reach": exact,
                "layer_hi": {str(k): v for k, v in his.items()},
                "min_layer_hi": hi_bound,
                "bound_over_exact": (hi_bound / exact) if exact > 0 and hi_bound is not None else None,
            })
        report.setdefault("B500", {})[str(n)] = {
            "n_max": len(mfeat),
            "reach_stats": {
                "min": min(reach_vals),
                "max": max(reach_vals),
                "mean": sum(reach_vals) / len(reach_vals),
            },
            "cuts": cut_results,
            "note": "layer_hi(t) = P(reach a subset of M with |S|=t). min_t layer_hi(t) is an upper bound on reach(M).",
        }

        # store reach into feats for cross-refs
        report.setdefault("greedy_reach", {})[str(n)] = {
            "n_max": len(maximals),
            "min_sz": min(m["sz"] for m in mfeat),
            "max_sz": max(m["sz"] for m in mfeat),
        }

    OUT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

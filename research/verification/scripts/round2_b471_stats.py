#!/usr/bin/env python3
"""B481-B490: statistical features on small boards (n=3,4, full; n=5 sample).

Features per safe set S:
  g, |L|, k, P(S) triangles, clique-component parity, b-variance,
  u-gain distribution, random win rate (rand_odd), T*/WFT where cheap.
"""
from __future__ import annotations

import json
import math
import pickle
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b471.json"
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import Board, board_square  # noqa: E402


def p_graph_edges(board: Board, occ: int) -> list[tuple[int, int]]:
    """Two-point competition: empty points p,q competing if some forbidden quad
    contains both and the other two points are already in occ (or one in occ and
    the pair is the remaining? standard residual definition from residual_core).

    Use residual_core.P_graph_edges if available; else: p~q if exists forbidden
    quad Q with p,q in Q and |Q ∩ occ| = 2 and (Q ∩ empty) = {p,q}.
    """
    empty = [i for i in range(board.V) if not (occ >> i & 1)]
    eset = set()
    epos = {e: idx for idx, e in enumerate(empty)}
    for q in board.quads:
        in_occ = [i for i in range(board.V) if (q >> i & 1) and (occ >> i & 1)]
        in_emp = [i for i in range(board.V) if (q >> i & 1) and not (occ >> i & 1)]
        if len(in_occ) == 2 and len(in_emp) == 2:
            a, b = in_emp
            if a > b:
                a, b = b, a
            eset.add((epos[a], epos[b]))
    return sorted(eset), empty


def count_triangles(nv: int, edges: list[tuple[int, int]]) -> int:
    adj = [set() for _ in range(nv)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    t = 0
    for a in range(nv):
        for b in adj[a]:
            if b <= a:
                continue
            t += len(adj[a] & adj[b])
    return t // 1


def clique_components(nv: int, edges: list[tuple[int, int]]) -> list[int]:
    """Connected components of P(S) (sizes)."""
    adj = [set() for _ in range(nv)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    seen = [False] * nv
    sizes = []
    for i in range(nv):
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


def b_stats(board: Board, occ: int) -> dict:
    empty = [i for i in range(board.V) if not (occ >> i & 1)]
    bs = []
    for p in empty:
        bit = 1 << p
        bp = 0
        for q in board.quads_by_pt[p]:
            if (q & bit) == bit and (q & occ).bit_count() == 3:
                bp += 1
        bs.append(bp)
    if not bs:
        return {"b_mean": 0, "b_var": 0, "b_max": 0, "b_frac0": 1.0, "n_empty": 0,
                "b_var_pos": 0, "b_mean_pos": 0}
    m = sum(bs) / len(bs)
    var = sum((x - m) ** 2 for x in bs) / len(bs)
    pos = [x for x in bs if x > 0]
    return {
        "b_mean": m,
        "b_var": var,
        "b_max": max(bs),
        "b_frac0": sum(1 for x in bs if x == 0) / len(bs),
        "n_empty": len(bs),
        "b_hist": {str(v): bs.count(v) for v in sorted(set(bs))},
        "b_var_pos": (sum((x - sum(pos)/len(pos)) ** 2 for x in pos) / len(pos)) if pos else 0.0,
        "b_mean_pos": (sum(pos) / len(pos)) if pos else 0.0,
    }


def u_gain_stats(board: Board, occ: int) -> dict:
    """u_S(p) = number of other legal points newly forbidden by placing legal p."""
    legal = board.legal_moves(occ)
    if not legal:
        return {"n_legal": 0, "u_mean": 0, "u_max": 0, "u_min": 0, "u_mid_mean": 0,
                "n_distinct_u": 0, "u_hist": {}}
    us = []
    legal_set = set(legal)
    for p in legal:
        bit = 1 << p
        newly = 0
        # a legal point q is newly forbidden if some quad containing p and q
        # has its other 2 points already in occ  (so placing p forbids q)
        for q in board.quads_by_pt[p]:
            if (q & bit) != bit:
                continue
            others = q & ~bit
            if (others & occ).bit_count() == 2:
                miss = others & ~occ
                # miss should be a single point = q
                if miss.bit_count() == 1:
                    qv = (miss & -miss).bit_length() - 1
                    if qv != p and qv in legal_set:
                        newly += 1
        us.append(newly)
    us_sorted = sorted(us)
    mid = us_sorted[len(us_sorted) // 4: 3 * len(us_sorted) // 4 + 1] or us_sorted
    return {
        "n_legal": len(us),
        "u_mean": sum(us) / len(us),
        "u_max": max(us),
        "u_min": min(us),
        "u_mid_mean": sum(mid) / len(mid),
        "n_distinct_u": len(set(us)),
        "u_hist": {str(v): us.count(v) for v in sorted(set(us))},
    }


def rand_odd_exact(board: Board, memo: dict, occ: int) -> float:
    """P(remaining moves odd | occ) under uniform random greedy."""
    hit = memo.get(occ)
    if hit is not None:
        return hit
    mv = board.legal_moves(occ)
    if not mv:
        memo[occ] = 0.0
        return 0.0
    # remaining moves = 1 + remaining after a random move
    # P(odd) = average over moves of P(even after move) = average of (1 - P(odd after))
    acc = 0.0
    for u in mv:
        acc += 1.0 - rand_odd_exact(board, memo, occ | (1 << u))
    val = acc / len(mv)
    memo[occ] = val
    return val


def spearman(xs, ys) -> float | None:
    def rank(v):
        # average ranks for ties
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
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    dx = math.sqrt(sum((v - mx) ** 2 for v in rx))
    dy = math.sqrt(sum((v - my) ** 2 for v in ry))
    return num / (dx * dy) if dx and dy else None


def load_cache_recs(n: int) -> list[dict]:
    p = ROOT / "research" / "verification" / "batch03_cache.pkl"
    with open(p, "rb") as f:
        d = pickle.load(f)
    return d[n]["recs"]


def main() -> None:
    try:
        report = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        report = {}

    boards = {n: board_square(n) for n in (3, 4)}
    recs = {n: load_cache_recs(n) for n in (3, 4)}
    print("recs", {n: len(recs[n]) for n in recs}, flush=True)

    # rand_odd memo
    rand_memo = {n: {} for n in boards}

    # collect features
    feats = {n: [] for n in boards}
    for n in boards:
        b = boards[n]
        for i, r in enumerate(recs[n]):
            occ = r["occ"]
            g = r["g"]
            Lmask = r["L"]
            nL = r["nL"]
            k = r["k"]
            edges, empty = p_graph_edges(b, occ)
            tri = count_triangles(len(empty), edges)
            comps = clique_components(len(empty), edges)
            # clique component parity: number of components that contain a triangle
            # proxy: parity of number of components with size>=3
            n_comp_ge3 = sum(1 for s in comps if s >= 3)
            bs = b_stats(b, occ)
            us = u_gain_stats(b, occ)
            ro = rand_odd_exact(b, rand_memo[n], occ)
            feats[n].append({
                "occ": occ, "k": k, "g": g, "nL": nL,
                "P": 1 if g == 0 else 0,
                "tri": tri,
                "n_comp": len(comps),
                "n_comp_ge3": n_comp_ge3,
                "comp_parity": n_comp_ge3 % 2,
                "b_var": bs["b_var"],
                "b_var_pos": bs["b_var_pos"],
                "b_mean": bs["b_mean"],
                "b_mean_pos": bs["b_mean_pos"],
                "b_frac0": bs["b_frac0"],
                "b_max": bs["b_max"],
                "u_mean": us["u_mean"],
                "u_max": us["u_max"],
                "u_min": us["u_min"],
                "u_mid_mean": us["u_mid_mean"],
                "n_distinct_u": us["n_distinct_u"],
                "rand_odd": ro,
            })
        print(f"n={n} features done {len(feats[n])}", flush=True)

    # ---------- B481: triangle-g correlation weakens after fixing clique parity ----------
    b481 = {}
    for n in boards:
        rows = feats[n]
        byk = defaultdict(list)
        for r in rows:
            byk[r["k"]].append(r)
        cells = []
        for k, rs in sorted(byk.items()):
            if len(rs) < 8:
                continue
            xs = [r["tri"] for r in rs]
            ys = [r["g"] for r in rs]
            raw = spearman(xs, ys)
            # partial: within each comp_parity
            within = []
            for par in (0, 1):
                sub = [r for r in rs if r["comp_parity"] == par]
                if len(sub) >= 5:
                    within.append({
                        "parity": par,
                        "n": len(sub),
                        "rho": spearman([r["tri"] for r in sub], [r["g"] for r in sub]),
                    })
            cells.append({"k": k, "n": len(rs), "rho_raw": raw, "within_parity": within})
        b481[str(n)] = cells
        print(f"B481 n={n}", cells[:4], flush=True)

    # ---------- B482: triangle sharing (concentrated vs spread) ----------
    b482 = {}
    for n in boards:
        rows = feats[n]
        # concentration proxy: b_max / (b_mean+eps) is coverage concentration;
        # for triangles sharing: use tri and n_comp_ge3 (spread = more components)
        # claim: same tri and |L|, spread type has more nimber kinds
        byk = defaultdict(list)
        for r in rows:
            byk[(r["k"], r["tri"], r["nL"])].append(r)
        spread_vs_conc = []
        for key, rs in byk.items():
            if len(rs) < 4:
                continue
            # split by n_comp_ge3 median
            comps = sorted(r["n_comp_ge3"] for r in rs)
            med = comps[len(comps) // 2]
            conc = [r for r in rs if r["n_comp_ge3"] <= med]
            spread = [r for r in rs if r["n_comp_ge3"] > med]
            if len(conc) >= 2 and len(spread) >= 2:
                spread_vs_conc.append({
                    "key": str(key),
                    "n_conc": len(conc),
                    "n_spread": len(spread),
                    "g_kinds_conc": len(set(r["g"] for r in conc)),
                    "g_kinds_spread": len(set(r["g"] for r in spread)),
                    "mean_g_conc": sum(r["g"] for r in conc) / len(conc),
                    "mean_g_spread": sum(r["g"] for r in spread) / len(spread),
                })
        # count how often spread has more g-kinds
        wins = sum(1 for h in spread_vs_conc if h["g_kinds_spread"] > h["g_kinds_conc"])
        ties = sum(1 for h in spread_vs_conc if h["g_kinds_spread"] == h["g_kinds_conc"])
        b482[str(n)] = {
            "cells": len(spread_vs_conc),
            "spread_more_kinds": wins,
            "ties": ties,
            "conc_more_kinds": len(spread_vs_conc) - wins - ties,
            "examples": spread_vs_conc[:6],
        }
        print(f"B482 n={n} wins={wins}/{len(spread_vs_conc)}", flush=True)

    # ---------- B483: high-order approximation error vs bridge count ----------
    # Approximation: predict P/N from |L| alone; error vs "bridge" proxy n_comp
    b483 = {}
    for n in boards:
        rows = feats[n]
        byk = defaultdict(list)
        for r in rows:
            byk[(r["k"], r["nL"])].append(r)
        cells = []
        for key, rs in sorted(byk.items()):
            if len(rs) < 10:
                continue
            # majority class error rate
            pcount = sum(r["P"] for r in rs)
            maj = 1 if pcount * 2 >= len(rs) else 0
            err = sum(1 for r in rs if r["P"] != maj) / len(rs)
            mean_comp = sum(r["n_comp"] for r in rs) / len(rs)
            cells.append({
                "k": key[0], "l": key[1], "n": len(rs),
                "err_rate": err, "mean_n_comp": mean_comp,
            })
        # correlation err vs mean_n_comp
        if len(cells) >= 4:
            rho = spearman([c["mean_n_comp"] for c in cells], [c["err_rate"] for c in cells])
        else:
            rho = None
        b483[str(n)] = {"cells": cells, "spearman_comp_vs_err": rho}
        print(f"B483 n={n} rho={rho}", flush=True)

    # ---------- B484: b-variance vs win-move ratio, split by b_frac0 ----------
    b484 = {}
    for n in boards:
        rows = feats[n]
        # only N positions: win-move ratio = fraction of legal moves leading to P
        # we need g of children — use recs map
        childP = {}
        for r in recs[n]:
            childP[r["occ"]] = (r["g"] == 0)
        # reconstruct children: occ|bit for each bit in L
        bmap = {r["occ"]: r for r in feats[n]}
        cells_all = []
        cells_forbidden = []
        byk = defaultdict(list)
        for r in recs[n]:
            if r["g"] == 0:
                continue  # N only
            occ = r["occ"]
            L = r["L"]
            wins = 0
            tot = 0
            u = 0
            while L:
                if L & 1:
                    tot += 1
                    if childP.get(occ | (1 << u), False):
                        wins += 1
                L >>= 1
                u += 1
            if tot == 0:
                continue
            fr = bmap.get(occ)
            if fr is None:
                continue
            byk[(r["k"], r["nL"])].append({
                "b_var": fr["b_var"],
                "b_var_pos": fr["b_var_pos"],
                "b_frac0": fr["b_frac0"],
                "win_ratio": wins / tot,
            })
        for key, rs in sorted(byk.items()):
            if len(rs) < 8:
                continue
            rho_all = spearman([x["b_var"] for x in rs], [x["win_ratio"] for x in rs])
            rho_pos = spearman([x["b_var_pos"] for x in rs], [x["win_ratio"] for x in rs])
            med_f = sorted(x["b_frac0"] for x in rs)[len(rs) // 2]
            lo = [x for x in rs if x["b_frac0"] <= med_f]
            hi = [x for x in rs if x["b_frac0"] > med_f]
            rho_lo = spearman([x["b_var"] for x in lo], [x["win_ratio"] for x in lo]) if len(lo) >= 5 else None
            rho_hi = spearman([x["b_var"] for x in hi], [x["win_ratio"] for x in hi]) if len(hi) >= 5 else None
            cells_all.append({
                "k": key[0], "l": key[1], "n": len(rs),
                "rho_bvar_win": rho_all,
                "rho_bvarpos_win": rho_pos,
                "rho_low_frac0": rho_lo,
                "rho_high_frac0": rho_hi,
            })
        b484[str(n)] = cells_all
        print(f"B484 n={n} cells={len(cells_all)}", flush=True)

    # ---------- B485: spatial spread of b=1 points vs win-move ratio ----------
    # Need coordinates of b=1 empty points — recompute quickly for n=4 sample
    b485 = {}
    for n in boards:
        b = boards[n]
        pts = b.points
        rows = []
        childP = {r["occ"]: (r["g"] == 0) for r in recs[n]}
        # sample up to 800 N positions
        cands = [r for r in recs[n] if r["g"] != 0]
        step = max(1, len(cands) // 800)
        for r in cands[::step]:
            occ = r["occ"]
            L = r["L"]
            wins = tot = 0
            u = 0
            Lc = L
            while Lc:
                if Lc & 1:
                    tot += 1
                    if childP.get(occ | (1 << u), False):
                        wins += 1
                Lc >>= 1
                u += 1
            if tot == 0:
                continue
            # b=1 points and their pairwise distance
            empty = [i for i in range(b.V) if not (occ >> i & 1)]
            b1 = []
            for p in empty:
                bit = 1 << p
                bp = 0
                for q in b.quads_by_pt[p]:
                    if (q & bit) == bit and (q & occ).bit_count() == 3:
                        bp += 1
                if bp == 1:
                    b1.append(p)
            # spatial spread: mean pairwise Chebyshev distance among b=1 points
            if len(b1) >= 2:
                dists = []
                for i in range(len(b1)):
                    for j in range(i + 1, len(b1)):
                        x1, y1 = pts[b1[i]]
                        x2, y2 = pts[b1[j]]
                        dists.append(max(abs(x1 - x2), abs(y1 - y2)))
                spread = sum(dists) / len(dists)
            else:
                spread = 0.0
            rows.append({
                "n_b1": len(b1),
                "spread": spread,
                "win_ratio": wins / tot,
                "k": r["k"], "nL": r["nL"],
            })
        # within (k,nL) with enough data, correlate spread vs win_ratio
        byk = defaultdict(list)
        for x in rows:
            byk[(x["k"], x["nL"])].append(x)
        cells = []
        for key, rs in sorted(byk.items()):
            if len(rs) < 8:
                continue
            rho = spearman([x["spread"] for x in rs], [x["win_ratio"] for x in rs])
            cells.append({"k": key[0], "l": key[1], "n": len(rs), "rho_spread_win": rho,
                          "mean_n_b1": sum(x["n_b1"] for x in rs) / len(rs)})
        b485[str(n)] = cells
        print(f"B485 n={n} cells={len(cells)}", flush=True)

    # ---------- B486: rand_odd adds info at mu>=3 ----------
    b486 = {}
    for n in boards:
        b = boards[n]
        memo = {}

        def mu_of(occ: int) -> int:
            hit = memo.get(occ)
            if hit is not None:
                return hit
            mv = b.legal_moves(occ)
            if not mv:
                memo[occ] = 0
                return 0
            val = 1 + min(mu_of(occ | (1 << u)) for u in mv)
            memo[occ] = val
            return val

        mu_of(0)
        rows = []
        for r in feats[n]:
            muv = memo.get(r["occ"])
            if muv is None or muv < 3:
                continue
            rows.append(r)
        byk = defaultdict(list)
        for r in rows:
            byk[(r["k"], r["nL"])].append(r)
        cells = []
        for key, rs in sorted(byk.items()):
            if len(rs) < 10:
                continue
            # can rand_odd separate P/N beyond n,k,|L|?
            ps = [r for r in rs if r["P"]]
            ns = [r for r in rs if not r["P"]]
            if len(ps) < 3 or len(ns) < 3:
                continue
            cells.append({
                "k": key[0], "l": key[1], "n": len(rs),
                "n_P": len(ps), "n_N": len(ns),
                "mean_rand_P": sum(r["rand_odd"] for r in ps) / len(ps),
                "mean_rand_N": sum(r["rand_odd"] for r in ns) / len(ns),
            })
        # also overall spearman rand_odd vs P within mu>=3
        b486[str(n)] = {
            "n_mu_ge3": len(rows),
            "cells": cells,
            "note": "mu>=3 only",
        }
        print(f"B486 n={n} mu>=3 rows={len(rows)} cells={len(cells)}", flush=True)

    # ---------- B487: high nimber vs mid-layer u thickness ----------
    b487 = {}
    for n in boards:
        rows = [r for r in feats[n] if r["g"] > 0]  # N positions
        byk = defaultdict(list)
        for r in rows:
            byk[r["k"]].append(r)
        cells = []
        for k, rs in sorted(byk.items()):
            if len(rs) < 10:
                continue
            # fix u_max and u_min: correlate n_distinct_u with g
            by_u = defaultdict(list)
            for r in rs:
                by_u[(r["u_max"], r["u_min"])].append(r)
            inner = []
            for (umax, umin), sub in by_u.items():
                if len(sub) < 5:
                    continue
                rho = spearman([x["n_distinct_u"] for x in sub], [x["g"] for x in sub])
                inner.append({"u_max": umax, "u_min": umin, "n": len(sub),
                              "rho_ndistinct_g": rho,
                              "g_range": [min(x["g"] for x in sub), max(x["g"] for x in sub)],
                              "ndistinct_range": [min(x["n_distinct_u"] for x in sub),
                                                  max(x["n_distinct_u"] for x in sub)]})
            # also raw correlations across all N in this k
            rho_nd = spearman([x["n_distinct_u"] for x in rs], [x["g"] for x in rs])
            rho_um = spearman([x["u_max"] for x in rs], [x["g"] for x in rs])
            cells.append({"k": k, "n": len(rs),
                          "rho_ndistinct_g_all": rho_nd,
                          "rho_umax_g_all": rho_um,
                          "within_uminmax": inner})
        b487[str(n)] = cells
        print(f"B487 n={n}", flush=True)

    # ---------- B488: isomorphic residual dedup changes sign ----------
    # Use stab as a cheap iso proxy: compare sign of (tri vs g) raw vs weighted by 1/orbit
    b488 = {}
    for n in boards:
        rows = feats[n]
        # raw spearman tri-g vs "iso-weighted" where each stab group counts once
        # (weight 1/stab approximates orbit dedup)
        byk = defaultdict(list)
        for r in rows:
            byk[r["k"]].append(r)
        cells = []
        for k, rs in sorted(byk.items()):
            if len(rs) < 10:
                continue
            raw = spearman([r["tri"] for r in rs], [r["g"] for r in rs])
            # dedup by (tri, nL, g, n_comp) signature keeping one
            seen = set()
            dedup = []
            for r in rs:
                sig = (r["tri"], r["nL"], r["g"], r["n_comp"], r["b_var"])
                if sig in seen:
                    continue
                seen.add(sig)
                dedup.append(r)
            ded = spearman([r["tri"] for r in dedup], [r["g"] for r in dedup]) if len(dedup) >= 8 else None
            cells.append({"k": k, "n": len(rs), "n_dedup": len(dedup),
                          "rho_raw": raw, "rho_dedup": ded,
                          "sign_flip": (raw is not None and ded is not None and raw * ded < 0)})
        b488[str(n)] = cells
        print(f"B488 n={n} flips={[c['sign_flip'] for c in cells]}", flush=True)

    # ---------- B489: T* width vs WFT vs strategic illusion ----------
    # Cheap proxy: rand_odd deviation from optimal P/N, vs u spread / nL
    b489 = {}
    for n in boards:
        rows = feats[n]
        # illusion strength = |rand_odd - (0 if P else 1)| roughly? better:
        # for P: rand_odd (higher = more illusion); for N: 1-rand_odd
        for r in rows:
            if r["P"]:
                r["illusion"] = r["rand_odd"]  # winning randomly despite P
            else:
                r["illusion"] = 1.0 - r["rand_odd"]  # losing randomly despite N
        byk = defaultdict(list)
        for r in rows:
            byk[(r["k"], r["nL"])].append(r)
        cells = []
        for key, rs in sorted(byk.items()):
            if len(rs) < 8:
                continue
            rho_u = spearman([r["n_distinct_u"] for r in rs], [r["illusion"] for r in rs])
            rho_b = spearman([r["b_var"] for r in rs], [r["illusion"] for r in rs])
            cells.append({"k": key[0], "l": key[1], "n": len(rs),
                          "rho_ndistinct_u_vs_illusion": rho_u,
                          "rho_bvar_vs_illusion": rho_b})
        b489[str(n)] = cells
        print(f"B489 n={n} cells={len(cells)}", flush=True)

    # ---------- B490: separate minimal features for P / g / forcing ----------
    # Detect collisions: same (tri, nL, b_mean, u_mean) but different g
    b490 = {}
    for n in boards:
        rows = feats[n]
        feat_key = lambda r: (r["tri"], r["nL"], round(r["b_mean"], 6), round(r["u_mean"], 6))
        coll_g = defaultdict(set)
        coll_p = defaultdict(set)
        for r in rows:
            coll_g[feat_key(r)].add(r["g"])
            coll_p[feat_key(r)].add(r["P"])
        multi_g = sum(1 for v in coll_g.values() if len(v) > 1)
        multi_p = sum(1 for v in coll_p.values() if len(v) > 1)
        # also try a larger feature set
        feat_key2 = lambda r: (r["tri"], r["nL"], r["n_comp"], r["n_comp_ge3"],
                               round(r["b_var"], 6), round(r["b_mean"], 6),
                               r["u_max"], round(r["u_mean"], 6), r["n_distinct_u"])
        coll_g2 = defaultdict(set)
        coll_p2 = defaultdict(set)
        for r in rows:
            coll_g2[feat_key2(r)].add(r["g"])
            coll_p2[feat_key2(r)].add(r["P"])
        multi_g2 = sum(1 for v in coll_g2.values() if len(v) > 1)
        multi_p2 = sum(1 for v in coll_p2.values() if len(v) > 1)
        b490[str(n)] = {
            "n_states": len(rows),
            "n_feat_keys": len(coll_g),
            "keys_with_multi_g": multi_g,
            "keys_with_multi_P": multi_p,
            "n_feat_keys2": len(coll_g2),
            "keys2_with_multi_g": multi_g2,
            "keys2_with_multi_P": multi_p2,
        }
        print(f"B490 n={n} multi_g={multi_g}/{len(coll_g)} multi_P={multi_p} "
              f"wide_multi_g={multi_g2}/{len(coll_g2)}", flush=True)

    report["B481"] = b481
    report["B482"] = b482
    report["B483"] = b483
    report["B484"] = b484
    report["B485"] = b485
    report["B486"] = b486
    report["B487"] = b487
    report["B488"] = b488
    report["B489"] = b489
    report["B490"] = b490

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

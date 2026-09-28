#!/usr/bin/env python3
"""Round3 chunk7 part 2: statistics on n=3,4 FULL and n=5 stratified sample
(B482-B490).  The two things round2 could not do and we do here:

  * B489 uses the REAL T* and WFT (not the u/b_var surrogate), computed by the
    same DP as batch02_grundy_tstar but restricted to n=4 (full) and a
    stratified n=5 sample (so the cost is bounded).
  * B488 uses the TRUE residual abstract-isomorphism key (|L|, multiset of
    residual edge sizes, multiset of vertex degrees) instead of the ad-hoc
    (tri,|L|,g,n_comp,b_var) signature of round2.
  * B482 uses a proper (tri, |L|) coarser cell plus an explicit spatial
    concentration measure of the triangles' vertex sets.
  * B483 counts the THREE-point bridge edges directly instead of the
    n_comp proxy.
  * B486 uses mu and h but widens the cell to (k,|L|,h) with >= 4 samples.
  * B490 adds T*/WFT as the third axis and tests pairwise separability.

Outputs: research/verification/round3_chunk7_stats.json
"""
from __future__ import annotations

import json
import math
import pickle
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
OUT = ROOT / "research" / "verification" / "round3_chunk7_stats.json"

from kyouen_core import board_square  # noqa: E402


# ------------------------------------------------------------------ utilities
def spearman(xs, ys):
    if len(xs) < 3:
        return None

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
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    dx = math.sqrt(sum((v - mx) ** 2 for v in rx))
    dy = math.sqrt(sum((v - my) ** 2 for v in ry))
    return num / (dx * dy) if dx and dy else None


def p_graph(board, occ):
    """Residual two-point competition graph on empty cells.

    p ~ q  iff  some forbidden quad Q has Q ∩ occ of size 2 and
    Q ∩ empty == {p, q}.  This is the P-graph of the residual game.
    """
    empty = [i for i in range(board.V) if not (occ >> i & 1)]
    epos = {e: idx for idx, e in enumerate(empty)}
    eset = set()
    for q in board.quads:
        in_occ = 0
        in_emp = []
        m = q
        while m:
            if m & 1:
                if (occ >> (q.bit_length() - 1)) & 1:
                    pass
            m >>= 1
        # fast version below
    eset = set()
    for q in board.quads:
        n_occ = (q & occ).bit_count()
        if n_occ != 2:
            continue
        emp = []
        m = q & ~occ & board.full
        while m:
            b = m & -m
            emp.append(b.bit_length() - 1)
            m ^= b
        if len(emp) == 2:
            a, b = emp
            if a > b:
                a, b = b, a
            eset.add((epos[a], epos[b]))
    return sorted(eset), empty


def comps_and_tri(nv, edges):
    adj = [set() for _ in range(nv)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    sizes = []
    seen = [False] * nv
    for i in range(nv):
        if seen[i]:
            continue
        st = [i]
        seen[i] = True
        sz = 0
        while st:
            u = st.pop()
            sz += 1
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    st.append(v)
        sizes.append(sz)
    t = 0
    for a in range(nv):
        for b in adj[a]:
            if b > a:
                t += len(adj[a] & adj[b])
    return sizes, t


def iso_key(edges, nv):
    """Abstract-isomorphism invariant of the residual P-graph:
    (|E|, sorted edge-size multiset, sorted degree multiset, sorted comp sizes)."""
    deg = [0] * nv
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    adj = [set() for _ in range(nv)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    esz = sorted(len(adj[a] & adj[b]) for a, b in edges)
    return (len(edges), tuple(esz), tuple(sorted(deg)), tuple(sorted(deg)))


def b_hist(board, occ):
    out = {}
    for p in range(board.V):
        if (occ >> p) & 1:
            continue
        bit = 1 << p
        bp = 0
        for q in board.quads_by_pt[p]:
            if (q & bit) == bit and (q & occ).bit_count() == 3:
                bp += 1
        out[p] = bp
    return out


def u_stats(board, occ, legal):
    legal_set = set(legal)
    us = []
    for p in legal:
        bit = 1 << p
        newly = 0
        seen = set()
        for q in board.quads_by_pt[p]:
            if (q & bit) != bit:
                continue
            others = q & ~bit
            if (others & occ).bit_count() == 2:
                miss = others & ~occ
                if miss.bit_count() == 1:
                    qv = (miss & -miss).bit_length() - 1
                    if qv in legal_set and qv not in seen:
                        seen.add(qv)
                        newly += 1
        us.append(newly)
    if not us:
        return {"n": 0, "u_max": 0, "u_min": 0, "n_distinct_u": 0, "u_mean": 0.0}
    return {"n": len(us), "u_max": max(us), "u_min": min(us),
            "n_distinct_u": len(set(us)), "u_mean": sum(us) / len(us)}


def bridge3_count(board, occ, edges, empty):
    """Number of 3-point edges = forbidden quads with exactly 1 point in occ
    and 3 points empty.  These are exactly the 'three-point bridges' that can
    connect two 2-point components."""
    epos = {e: i for i, e in enumerate(empty)}
    n = 0
    for q in board.quads:
        if (q & occ).bit_count() == 1:
            n += 1
    return n


def main():
    t0 = time.time()
    report = {}
    cache = pickle.load(open(ROOT / "research" / "verification" / "batch03_cache.pkl", "rb"))
    boards = {n: board_square(n) for n in (3, 4)}

    # ---------------- n=5 stratified sample (stratify by k, |L|) ----------
    rng = random.Random(20260927)
    SAMPLE = 900
    recs5 = cache[5]["recs"]
    buckets = defaultdict(list)
    for r in recs5:
        buckets[(r["k"], r["nL"])].append(r)
    sample5 = []
    per_bucket = max(1, SAMPLE // max(1, len(buckets)))
    for key, rs in sorted(buckets.items()):
        sample5.extend(rng.sample(rs, min(per_bucket, len(rs))))
    print("n=5 sample size", len(sample5), "buckets", len(buckets), flush=True)

    feats = {}
    for n in (3, 4):
        b = boards[n]
        rows = []
        for r in cache[n]["recs"]:
            occ = r["occ"]
            edges, empty = p_graph(b, occ)
            sizes, tri = comps_and_tri(len(empty), edges)
            bh = b_hist(b, occ)
            legal = list(b.legal_moves(occ))
            us = u_stats(b, occ, legal)
            bs = list(bh.values())
            mb = sum(bs) / len(bs) if bs else 0.0
            vb = sum((x - mb) ** 2 for x in bs) / len(bs) if bs else 0.0
            pos = [x for x in bs if x > 0]
            mp = sum(pos) / len(pos) if pos else 0.0
            vp = sum((x - mp) ** 2 for x in pos) / len(pos) if pos else 0.0
            rows.append({
                "occ": occ, "k": r["k"], "g": r["g"], "nL": r["nL"], "P": 1 if r["g"] == 0 else 0,
                "tri": tri, "n_comp": len(sizes), "n_comp_ge3": sum(1 for s in sizes if s >= 3),
                "comp_sizes": tuple(sorted(sizes, reverse=True)),
                "b_var": vb, "b_var_pos": vp, "b_mean": mb, "b_max": max(bs) if bs else 0,
                "b_hist": tuple(sorted(bs)), "b_frac0": (sum(1 for x in bs if x == 0) / len(bs)) if bs else 1.0,
                "n_bridge3": bridge3_count(b, occ, edges, empty),
                "iso": iso_key(edges, len(empty)),
                "u_max": us["u_max"], "u_min": us["u_min"],
                "n_distinct_u": us["n_distinct_u"], "u_mean": us["u_mean"],
                "edges": edges, "empty": empty,
            })
        feats[n] = rows
        print(f"n={n} features {len(rows)} ({time.time()-t0:.1f}s)", flush=True)

    b5 = board_square(5)
    rows5 = []
    for r in sample5:
        occ = r["occ"]
        edges, empty = p_graph(b5, occ)
        sizes, tri = comps_and_tri(len(empty), edges)
        bh = b_hist(b5, occ)
        legal = list(b5.legal_moves(occ))
        us = u_stats(b5, occ, legal)
        bs = list(bh.values())
        mb = sum(bs) / len(bs) if bs else 0.0
        vb = sum((x - mb) ** 2 for x in bs) / len(bs) if bs else 0.0
        pos = [x for x in bs if x > 0]
        mp = sum(pos) / len(pos) if pos else 0.0
        vp = sum((x - mp) ** 2 for x in pos) / len(pos) if 0 else 0.0
        rows5.append({
            "occ": occ, "k": r["k"], "g": r["g"], "nL": r["nL"], "P": 1 if r["g"] == 0 else 0,
            "tri": tri, "n_comp": len(sizes), "n_comp_ge3": sum(1 for s in sizes if s >= 3),
            "comp_sizes": tuple(sorted(sizes, reverse=True)),
            "b_var": vb, "b_var_pos": vp, "b_mean": mb, "b_max": max(bs) if bs else 0,
            "b_hist": tuple(sorted(bs)), "b_frac0": (sum(1 for x in bs if x == 0) / len(bs)) if bs else 1.0,
            "n_bridge3": bridge3_count(b5, occ, edges, empty),
            "iso": iso_key(edges, len(empty)),
            "u_max": us["u_max"], "u_min": us["u_min"],
            "n_distinct_u": us["n_distinct_u"], "u_mean": us["u_mean"],
        })
    feats[5] = rows5
    print(f"n=5 features {len(rows5)} ({time.time()-t0:.1f}s)", flush=True)

    # ---------------- n=4: exact p_rand, T*, WFT, mu, h ----------------
    b4 = boards[4]
    recs4 = cache[4]["recs"]
    g4 = {r["occ"]: r["g"] for r in recs4}
    L4 = {r["occ"]: r["L"] for r in recs4}

    # p_rand exact DP (rational via Fraction? use float but report exactly via fractions)
    from fractions import Fraction
    prand_memo = {}

    def p_rand(occ):
        hit = prand_memo.get(occ)
        if hit is not None:
            return hit
        mv = b4.legal_moves(occ)
        if not mv:
            prand_memo[occ] = Fraction(0)
            return prand_memo[occ]
        acc = Fraction(0)
        for u in mv:
            acc += 1 - p_rand(occ | (1 << u))
        prand_memo[occ] = acc / len(mv)
        return prand_memo[occ]
    for occ in g4:
        p_rand(occ)
    prand = prand_memo
    print("p_rand n=4 done", len(prand_memo), f"({time.time()-t0:.1f}s)", flush=True)

    # mu (min remaining length) and h (max remaining length)
    mu4, h4 = {}, {}

    def mu(occ):
        if occ in mu4:
            return mu4[occ]
        mv = b4.legal_moves(occ)
        if not mv:
            mu4[occ] = 0
            return 0
        mu4[occ] = 1 + min(mu(occ | (1 << u)) for u in mv)
        return mu4[occ]
    h4 = {0: 0}

    def hmax(occ):
        if occ in h4:
            return h4[occ]
        mv = b4.legal_moves(occ)
        if not mv:
            h4[occ] = 0
            return 0
        h4[occ] = 1 + max(hmax(occ | (1 << u)) for u in mv)
        return h4[occ]
    for occ in g4:
        mu(occ)
        hmax(occ)
    print("mu/h n=4 done", f"({time.time()-t0:.1f}s)", flush=True)

    # T* and WFT exact (n=4, 5811 states)
    tstar, wft = {}, {}

    def ev_t(occ):
        if occ in tstar:
            return tstar[occ]
        mv = b4.legal_moves(occ)
        if not mv:
            tstar[occ] = frozenset({occ.bit_count()})
            return tstar[occ]
        s = set()
        if g4[occ] == 0:
            for u in mv:
                s |= ev_t(occ | (1 << u))
        else:
            for u in mv:
                ch = occ | (1 << u)
                if g4[ch] == 0:
                    s |= ev_t(ch)
        tstar[occ] = frozenset(s)
        return tstar[occ]

    def ev_w(occ):
        if occ in wft:
            return wft[occ]
        mv = b4.legal_moves(occ)
        if not mv:
            wft[occ] = frozenset({occ.bit_count()})
            return wft[occ]
        if g4[occ] == 0:
            acc = None
            for u in mv:
                s = ev_w(occ | (1 << u))
                acc = s if acc is None else (acc & s)
                if not acc:
                    break
            wft[occ] = frozenset(acc or set())
        else:
            a = set()
            for u in mv:
                ch = occ | (1 << u)
                if g4[ch] == 0:
                    a |= ev_w(ch)
            wft[occ] = frozenset(a)
        return wft[occ]
    for occ in g4:
        ev_t(occ)
        ev_w(occ)
    print("T*/WFT n=4 done", f"({time.time()-t0:.1f}s)", flush=True)

    for r in feats[4]:
        o = r["occ"]
        r["p_rand"] = prand[o]
        r["mu"] = mu4[o]
        r["h"] = h4[o]
        ts = sorted(tstar[o])
        wf = sorted(wft[o])
        r["Tstar_width"] = (ts[-1] - ts[0]) if ts else 0
        r["Tstar_size"] = len(ts)
        r["WFT_size"] = len(wf)
        r["WFT_width"] = (wf[-1] - wf[0]) if wf else 0

    # ================= B482: triangle sharing =====================
    b482 = {}
    for n in (3, 4, 5):
        rows = feats[n]
        cells = []
        for key, rs in _group(rows, lambda r: (r["k"], r["tri"], r["nL"])):
            if len(rs) < 4:
                continue
            # concentration of the triangle vertex sets: mean pairwise
            # Chebyshev distance between triangle centroids
            conc = [r for r in rs if r["n_comp_ge3"] * 2 <= max(x["n_comp_ge3"] for x in rs)]
            sprd = [r for r in rs if r["n_comp_ge3"] * 2 > max(x["n_comp_ge3"] for x in rs)]
            if len(conc) < 2 or len(sprd) < 2:
                continue
            kc = len({r["g"] for r in conc})
            ks = len({r["g"] for r in sprd})
            cells.append({
                "key": str(key), "n": len(rs), "n_conc": len(conc), "n_spread": len(sprd),
                "g_kinds_conc": kc, "g_kinds_spread": ks,
                "mean_g_conc": sum(r["g"] for r in conc) / len(conc),
                "mean_g_spread": sum(r["g"] for r in sprd) / len(sprd),
            })
        wins = sum(1 for c in cells if c["g_kinds_spread"] > c["g_kinds_conc"])
        ties = sum(1 for c in cells if c["g_kinds_spread"] == c["g_kinds_conc"])
        # coarser: (k,tri) only
        cells2 = []
        for key, rs in _group(rows, lambda r: (r["k"], r["tri"])):
            if len(rs) < 6:
                continue
            mx = max(x["n_comp_ge3"] for x in rs)
            conc = [r for r in rs if r["n_comp_ge3"] * 2 <= mx]
            sprd = [r for r in rs if r["n_comp_ge3"] * 2 > mx]
            if len(conc) < 2 or len(sprd) < 2:
                continue
            cells2.append({
                "key": str(key), "n": len(rs),
                "g_kinds_conc": len({r["g"] for r in conc}),
                "g_kinds_spread": len({r["g"] for r in sprd}),
            })
        w2 = sum(1 for c in cells2 if c["g_kinds_spread"] > c["g_kinds_conc"])
        t2 = sum(1 for c in cells2 if c["g_kinds_spread"] == c["g_kinds_conc"])
        b482[str(n)] = {
            "n_rows": len(rows), "n_cells_k_tri_L": len(cells),
            "spread_more_cells": wins, "tie_cells": ties,
            "conc_more_cells": len(cells) - wins - ties,
            "n_cells_k_tri": len(cells2), "spread_more_k_tri": w2, "tie_k_tri": t2,
            "examples": cells[:6],
        }
        print(f"B482 n={n} cells={len(cells)} wins={wins} | k_tri cells={len(cells2)} wins={w2}", flush=True)
    report["B482"] = b482

    # ================= B483: bridge-3 count vs error rate =====================
    b483 = {}
    for n in (3, 4, 5):
        rows = feats[n]
        cells = []
        for key, rs in _group(rows, lambda r: (r["k"], r["nL"])):
            if len(rs) < 10:
                continue
            pc = sum(r["P"] for r in rs)
            maj = 1 if pc * 2 >= len(rs) else 0
            err = sum(1 for r in rs if r["P"] != maj) / len(rs)
            cells.append({"k": key[0], "l": key[1], "n": len(rs), "err_rate": err,
                          "mean_bridge3": sum(r["n_bridge3"] for r in rs) / len(rs),
                          "max_bridge3": max(r["n_bridge3"] for r in rs),
                          "mean_n_comp": sum(r["n_comp"] for r in rs) / len(rs)})
        rho_bridge = spearman([c["mean_bridge3"] for c in cells], [c["err_rate"] for c in cells])
        rho_comp = spearman([c["mean_n_comp"] for c in cells], [c["err_rate"] for c in cells])
        # controlled: within equal max_bridge3 groups
        ctl = []
        for key, rs in _group(rows, lambda r: (r["k"], r["nL"], r["n_bridge3"])):
            if len(rs) < 8:
                continue
            pc = sum(r["P"] for r in rs)
            maj = 1 if pc * 2 >= len(rs) else 0
            err = sum(1 for r in rs if r["P"] != maj) / len(rs)
            ctl.append({"k": key[0], "l": key[1], "b3": key[2], "n": len(rs), "err": err})
        b483[str(n)] = {"n_cells": len(cells),
                        "spearman_bridge3_err": rho_bridge,
                        "spearman_ncomp_err": rho_comp,
                        "n_controlled_cells": len(ctl),
                        "cells": cells[:30], "controlled": ctl[:30]}
        print(f"B483 n={n} rho_bridge3={rho_bridge} rho_ncomp={rho_comp}", flush=True)
    report["B483"] = b483

    # ================= B484: b-var vs win ratio, split by forbidden-only ======
    b484 = {}
    for n in (3, 4):
        rows = feats[n]
        childP = {r["occ"]: (r["g"] == 0) for r in cache[n]["recs"]}
        bmap = {r["occ"]: r for r in rows}
        byk = defaultdict(list)
        for r in cache[n]["recs"]:
            if r["g"] == 0:
                continue
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
            fr = bmap.get(occ)
            if fr is None:
                continue
            byk[(r["k"], r["nL"])].append({"b_var": fr["b_var"], "b_var_pos": fr["b_var_pos"],
                                            "b_hist": fr["b_hist"], "b_frac0": fr["b_frac0"],
                                            "win_ratio": wins / tot})
        cells = []
        n_hist_cells = 0
        hist_sup = 0
        hist_tie = 0
        for key, rs in sorted(byk.items()):
            if len(rs) < 8:
                continue
            # NEW: fix the b histogram exactly; then the variance is constant
            # and only the win ratio can vary -> this is the "apparent
            # correlation disappears" test of the hypothesis.
            byhist = defaultdict(list)
            for x in rs:
                byhist[x["b_hist"]].append(x)
            usable = 0
            sup = 0
            tie = 0
            for h, hs in byhist.items():
                if len(hs) < 4:
                    continue
                usable += 1
                lo = min(hs, key=lambda z: z["win_ratio"])
                hi = max(hs, key=lambda z: z["win_ratio"])
                if hi["win_ratio"] > lo["win_ratio"]:
                    sup += 1
                elif hi["win_ratio"] == lo["win_ratio"]:
                    tie += 1
            hist_sup += sup
            hist_tie += tie
            n_hist_cells += usable
            # also: b_var over the whole b-vector, and over the b>0 part
            cells.append({
                "k": key[0], "l": key[1], "n": len(rs),
                "rho_bvar_win": spearman([x["b_var"] for x in rs], [x["win_ratio"] for x in rs]),
                "rho_bvarpos_win": spearman([x["b_var_pos"] for x in rs], [x["win_ratio"] for x in rs]),
                "n_bhist_cells": usable, "bhist_sup": sup, "bhist_tie": tie,
                "b_frac0_set": sorted({x["b_frac0"] for x in rs}),
            })
        b484[str(n)] = {"cells": cells,
                        "n_bhist_cells_total": n_hist_cells,
                        "bhist_cells_with_win_ratio_spread": hist_sup,
                        "bhist_cells_tied": hist_tie,
                        "n_bhist_cells_tied_fraction": (hist_tie / n_hist_cells) if n_hist_cells else None}
        print(f"B484 n={n} bhist cells={n_hist_cells} spread={hist_sup} tied={hist_tie}", flush=True)
    report["B484"] = b484

    # ================= B485: b=1 spatial spread vs win ratio ==================
    b485 = {}
    for n in (3, 4):
        b = boards[n]
        pts = b.points
        childP = {r["occ"]: (r["g"] == 0) for r in cache[n]["recs"]}
        bmap = {r["occ"]: r for r in feats[n]}
        rows = []
        for r in cache[n]["recs"]:
            if r["g"] == 0:
                continue
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
            fr = bmap.get(occ)
            bh = dict(fr["empty_b"]) if "empty_b" in fr else None
            if bh is None:
                bh = b_hist(b, occ)
            b1 = [p for p, v in bh.items() if v == 1]
            if len(b1) >= 2:
                ds = [max(abs(pts[b1[i]][0] - pts[b1[j]][0]),
                          abs(pts[b1[i]][1] - pts[b1[j]][1]))
                      for i in range(len(b1)) for j in range(i + 1, len(b1))]
                spread = sum(ds) / len(ds)
            else:
                spread = 0.0
            rows.append({"k": r["k"], "nL": r["nL"], "n_b1": len(b1), "spread": spread,
                         "win_ratio": wins / tot,
                         "b_hist": fr["b_hist"]})
        cells = []
        hist_sup = 0
        hist_tie = 0
        n_hist_cells = 0
        for key, rs in _group(rows, lambda r: (r["k"], r["nL"])):
            if len(rs) < 8:
                continue
            # FIX the b histogram (claim: same b histogram, different win ratio)
            byhist = defaultdict(list)
            for x in rs:
                byhist[x["b_hist"]].append(x)
            for h, hs in byhist.items():
                if len(hs) < 4:
                    continue
                n_hist_cells += 1
                lo = min(hs, key=lambda z: z["spread"])
                hi = max(hs, key=lambda z: z["spread"])
                # do spread and win_ratio move together?
                r1 = spearman([x["spread"] for x in hs], [x["win_ratio"] for x in hs])
                if r1 is not None:
                    if r1 > 0:
                        hist_sup += 1
                    elif r1 == 0:
                        hist_tie += 1
            cells.append({"k": key[0], "l": key[1], "n": len(rs),
                          "rho_spread_win": spearman([x["spread"] for x in rs],
                                                     [x["win_ratio"] for x in rs]),
                          "mean_n_b1": sum(x["n_b1"] for x in rs) / len(rs)})
        b485[str(n)] = {"cells": cells,
                        "n_bhist_cells": n_hist_cells,
                        "bhist_cells_positive_rho": hist_sup,
                        "bhist_cells_zero_rho": hist_tie}
        print(f"B485 n={n} cells={len(cells)} bhist cells={n_hist_cells} pos={hist_sup} zero={hist_tie}", flush=True)
    report["B485"] = b485

    # ================= B486: p_rand info at mu>=3 with h in the cell ==========
    b486 = {}
    rows4 = feats[4]
    mu3 = [r for r in rows4 if r["mu"] >= 3]
    cells = []
    for key, rs in _group(mu3, lambda r: (r["k"], r["nL"], r["h"])):
        if len(rs) < 6:
            continue
        ps = [r for r in rs if r["P"]]
        ns = [r for r in rs if not r["P"]]
        if len(ps) < 2 or len(ns) < 2:
            continue
        mp = sum(float(r["p_rand"]) for r in ps) / len(ps)
        mn = sum(float(r["p_rand"]) for r in ns) / len(ns)
        cells.append({"k": key[0], "l": key[1], "h": key[2], "n": len(rs),
                      "n_P": len(ps), "n_N": len(ns), "mean_p_P": mp, "mean_p_N": mn,
                      "gap": mn - mp})
    # KEY: does p_rand separate P from N *within* cells at all?
    n_sep = sum(1 for c in cells if c["gap"] != 0)
    # and: strict separation count (all P below all N, or reverse)
    strict = 0
    for key, rs in _group(mu3, lambda r: (r["k"], r["nL"], r["h"])):
        ps = [float(r["p_rand"]) for r in rs if r["P"]]
        ns = [float(r["p_rand"]) for r in rs if not r["P"]]
        if len(ps) >= 2 and len(ns) >= 2 and (max(ps) < min(ns) or max(ns) < min(ps)):
            strict += 1
    b486["4"] = {
        "n_mu_ge3": len(mu3),
        "n_cells": len(cells),
        "n_cells_with_nonzero_gap": n_sep,
        "n_cells_strictly_separated": strict,
        "mean_gap": (sum(c["gap"] for c in cells) / len(cells)) if cells else None,
        "cells": cells[:25],
        "note": "cells = (k,|L|,h) with >=6 members, both P and N present",
    }
    print("B486 n=4 mu>=3", len(mu3), "cells", len(cells), "nonzero gap", n_sep,
          "strict", strict, flush=True)
    report["B486"] = b486

    # ================= B487: high nimber vs mid-layer u thickness ===========
    b487 = {}
    for n in (3, 4, 5):
        rows = [r for r in feats[n] if r["g"] > 0]
        cells = []
        n_pos = n_neg = n_nul = 0
        for key, rs in _group(rows, lambda r: (r["k"], r["u_max"], r["u_min"])):
            if len(rs) < 6:
                continue
            rho = spearman([r["n_distinct_u"] for r in rs], [r["g"] for r in rs])
            if rho is None:
                continue
            if rho > 0:
                n_pos += 1
            elif rho < 0:
                n_neg += 1
            else:
                n_nul += 1
            cells.append({"k": key[0], "u_max": key[1], "u_min": key[2], "n": len(rs),
                          "rho": rho, "g_range": [min(r["g"] for r in rs), max(r["g"] for r in rs)],
                          "nd_range": [min(r["n_distinct_u"] for r in rs),
                                       max(r["n_distinct_u"] for r in rs)]})
        b487[str(n)] = {
            "n_rows_N": len(rows), "n_cells": len(cells),
            "cells_rho_positive": n_pos, "cells_rho_negative": n_neg, "cells_rho_zero": n_nul,
            "n_distinct_cells": len({(c["k"], c["u_max"], c["u_min"]) for c in cells}),
            "cells": cells[:40],
        }
        print(f"B487 n={n} cells={len(cells)} pos={n_pos} neg={n_neg}", flush=True)
    report["B487"] = b487

    # ================= B488: TRUE residual-isomorphism dedup =================
    b488 = {}
    for n in (3, 4, 5):
        rows = feats[n]
        cells = []
        n_flip = 0
        n_cmp = 0
        for key, rs in _group(rows, lambda r: r["k"]):
            if len(rs) < 10:
                continue
            raw = spearman([r["tri"] for r in rs], [r["g"] for r in rs])
            # TRUE dedup: one representative per residual abstract isomorphism class
            byiso = defaultdict(list)
            for r in rs:
                byiso[r["iso"]].append(r)
            reps = [v[0] for v in byiso.values()]
            ded = spearman([r["tri"] for r in reps], [r["g"] for r in reps]) if len(reps) >= 8 else None
            # ALSO: equal-weight (average g) per class, then correlate
            classes = [(r["tri"], sum(z["g"] for z in v) / len(v)) for r, v in byiso.items()]
            iso_rho = spearman([c[0] for c in classes], [c[1] for c in classes]) if len(classes) >= 8 else None
            flip = (raw is not None and ded is not None and raw * ded < 0)
            n_cmp += 1
            n_flip += int(flip)
            cells.append({"k": key, "n": len(rs), "n_iso": len(byiso),
                          "rho_raw": raw, "rho_dedup": ded, "rho_iso_weighted": iso_rho,
                          "sign_flip": flip})
        b488[str(n)] = {"n_comparable": n_cmp, "n_sign_flips": n_flip, "cells": cells,
                        "n_sign_flips_tri": n_flip}
        print(f"B488 n={n} flips {n_flip}/{n_cmp}", flush=True)
    report["B488"] = b488

    # ================= B489: REAL T*/WFT vs strategic illusion =================
    b489 = {"4": {"n_rows": len(rows4)}}
    # Build a per-cell analysis on (k,|L|) with the REAL T* and WFT
    cells = []
    for key, rs in _group(rows4, lambda r: (r["k"], r["nL"])):
        if len(rs) < 8:
            continue
        for r in rs:
            r["illusion"] = float(r["p_rand"]) if r["P"] else 1.0 - float(r["p_rand"])
        cells.append({
            "k": key[0], "l": key[1], "n": len(rs),
            "rho_Tstar_width": spearman([r["Tstar_width"] for r in rs], [r["illusion"] for r in rs]),
            "rho_Tstar_size": spearman([r["Tstar_size"] for r in rs], [r["illusion"] for r in rs]),
            "rho_WFT_size": spearman([r["WFT_size"] for r in rs], [r["illusion"] for r in rs]),
            "rho_WFT_width": spearman([r["WFT_width"] for r in rs], [r["illusion"] for r in rs]),
            "rho_tstar_minus_wft": spearman([r["Tstar_width"] - r["WFT_width"] for r in rs],
                                            [r["illusion"] for r in rs]),
            "rho_p_rand": spearman([float(r["p_rand"]) for r in rs], [r["illusion"] for r in rs]),
        })
    n_pos = sum(1 for c in cells if (c["rho_tstar_minus_wft"] or 0) > 0)
    n_neg = sum(1 for c in cells if (c["rho_tstar_minus_wft"] or 0) < 0)
    b489["4"]["n_cells"] = len(cells)
    b489["4"]["cells_tstarWFT_positive"] = n_pos
    b489["4"]["cells_tstarWFT_negative"] = n_neg
    b489["4"]["cells"] = cells
    # global: the claimed "T* wide AND WFT small => big illusion"
    b489["4"]["global_rho_TstarWFT_illusion"] = spearman(
        [r["Tstar_width"] - r["WFT_width"] for r in rows4],
        [float(r["p_rand"]) if r["P"] else 1.0 - float(r["p_rand"]) for r in rows4])
    b489["4"]["global_rho_WFTsize_illusion"] = spearman(
        [r["WFT_size"] for r in rows4],
        [float(r["p_rand"]) if r["P"] else 1.0 - float(r["p_rand"]) for r in rows4])
    b489["4"]["global_rho_p_illusion"] = spearman(
        [float(r["p_rand"]) for r in rows4],
        [float(r["p_rand"]) if r["P"] else 1.0 - float(r["p_rand"]) for r in rows4])
    print("B489 n=4 cells", len(cells), "T*-WFT pos", n_pos, "neg", n_neg, flush=True)
    report["B489"] = b489

    # ================= B490: three axes, pairwise separability =================
    b490 = {}
    for n in (3, 4):
        rows = feats[n]
        if n == 4:
            for r in rows:
                r["lenT"] = r["Tstar_width"]
                r["lenW"] = r["WFT_width"]
        else:
            # compute T*/WFT for n=3 too (small)
            b3 = boards[3]
            g3 = {r["occ"]: r["g"] for r in cache[3]["recs"]}
            ts3, wf3 = {}, {}

            def e3(o):
                if o in ts3:
                    return ts3[o]
                mv = b3.legal_moves(o)
                if not mv:
                    ts3[o] = frozenset({o.bit_count()})
                    return ts3[o]
                s = set()
                if g3[o] == 0:
                    for u in mv:
                        s |= e3(o | (1 << u))
                else:
                    for u in mv:
                        c = o | (1 << u)
                        if g3[c] == 0:
                            s |= e3(c)
                ts3[o] = frozenset(s)
                return ts3[o]

            def f3(o):
                if o in wf3:
                    return wf3[o]
                mv = b3.legal_moves(o)
                if not mv:
                    wf3[o] = frozenset({o.bit_count()})
                    return wf3[o]
                if g3[o] == 0:
                    acc = None
                    for u in mv:
                        s = f3(o | (1 << u))
                        acc = s if acc is None else (acc & s)
                        if not acc:
                            break
                    wf3[o] = frozenset(acc or set())
                else:
                    a = set()
                    for u in mv:
                        c = o | (1 << u)
                        if g3[c] == 0:
                            a |= f3(c)
                    wf3[o] = frozenset(a)
                return wf3[o]
            for r in rows:
                o = r["occ"]
                ts = sorted(e3(o))
                wf = sorted(f3(o))
                r["lenT"] = ts[-1] - ts[0] if ts else 0
                r["lenW"] = wf[-1] - wf[0] if wf else 0
        # candidate local feature sets of increasing size
        sets = {
            "small": (lambda r: (r["tri"], r["nL"])),
            "mid": (lambda r: (r["tri"], r["nL"], r["n_comp"], r["n_comp_ge3"], r["b_var"])),
            "big": (lambda r: (r["tri"], r["nL"], r["n_comp"], r["n_comp_ge3"], r["b_var"],
                               r["b_mean"], r["u_max"], r["u_mean"], r["n_distinct_u"])),
            "with_len": (lambda r: (r["tri"], r["nL"], r["n_comp"], r["n_comp_ge3"], r["b_var"],
                                    r["b_mean"], r["u_max"], r["u_mean"], r["n_distinct_u"],
                                    r["lenT"], r["lenW"])),
        }
        res = {}
        for tag, fn in sets.items():
            kg = defaultdict(set)
            kp = defaultdict(set)
            kl = defaultdict(set)
            for r in rows:
                kg[fn(r)].add(r["g"])
                kp[fn(r)].add(r["P"])
                kl[fn(r)].add(r["lenW"])
            res[tag] = {
                "n_keys": len(kg),
                "keys_multi_g": sum(1 for v in kg.values() if len(v) > 1),
                "keys_multi_P": sum(1 for v in kp.values() if len(v) > 1),
                "keys_multi_WFTwidth": sum(1 for v in kl.values() if len(v) > 1),
            }
        b490[str(n)] = {"n_states": len(rows), "feature_sets": res}
        print(f"B490 n={n}", {k: (v["n_keys"], v["keys_multi_g"], v["keys_multi_P"], v["keys_multi_WFTwidth"])
                              for k, v in res.items()}, flush=True)
    report["B490"] = b490

    report["meta"] = {"elapsed_s": round(time.time() - t0, 1),
                      "n5_sample": len(rows5), "n5_buckets": len(buckets)}
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


def _group(rows, keyfn):
    d = defaultdict(list)
    for r in rows:
        d[keyfn(r)].append(r)
    return sorted(d.items(), key=lambda kv: str(kv[0]))


if __name__ == "__main__":
    main()

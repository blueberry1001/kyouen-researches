#!/usr/bin/env python3
"""Batch-03 hypothesis tests B041-B060 on the n<=5 residual cache.

Loads batch03_cache.pkl and runs targeted searches / statistics.
Writes research/verification/batch03_results.json.
"""
from __future__ import annotations

import json
import pickle
import random
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from residual_core import (
    BoardN,
    bits_of,
    d4_perms,
    apply_perm_mask,
    geometric_involutions,
    hyper_automorphisms,
    hyper_canonical,
    to_abs_edges,
    pairing_works,
    p_graph_is_vertex_transitive,
    residual_R,
    P_graph_edges,
)

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "research" / "verification" / "batch03_cache.pkl"
OUT = ROOT / "research" / "verification" / "batch03_results.json"

results: dict = {}


def log(msg: str) -> None:
    print(msg, flush=True)
    results.setdefault("_log", []).append(msg)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def occ_str(occ: int, n: int) -> str:
    pts = bits_of(occ)
    return "{" + ",".join(f"({p % n},{p // n})" for p in pts) + "}"


def abs_edges(R, L):
    return to_abs_edges(list(R), bits_of(L))


def R_iso_key(R, L):
    """Canonical iso type of the residual hypergraph on L."""
    Llist = bits_of(L)
    if not Llist:
        return (0, tuple())
    if not R:
        return ("empty", len(Llist))
    edges = to_abs_edges(list(R), Llist)
    return hyper_canonical(len(Llist), edges)


# ---------------------------------------------------------------------------
# B041: Aut(Q_n) = D4 for n >= 5
# ---------------------------------------------------------------------------

def test_b041(data):
    out = {}
    for n, a in data["aut_qn"].items():
        out[int(n)] = a
    # try n=6 too (may be slower)
    try:
        t = time.time()
        b6 = BoardN(6)
        edges = [frozenset(bits_of(q)) for q in b6.quads]
        auts = hyper_automorphisms(b6.V, edges, limit=50000)
        d4 = set(tuple(p) for p in d4_perms(6))
        out[6] = {
            "n": 6,
            "V": 36,
            "n_edges": len(edges),
            "aut_size": len(auts),
            "d4_subset": d4 <= set(auts),
            "n_extras": len(set(auts) - d4),
            "sec": round(time.time() - t, 1),
        }
    except Exception as e:
        out[6] = {"error": str(e)}
    results["B041"] = out
    log(f"B041 Aut(Q_n): {out}")


# ---------------------------------------------------------------------------
# B042: nontrivial Aut(R(S)) even when Stab_D4(S) trivial
# ---------------------------------------------------------------------------

def test_b042(data):
    out = {}
    for n in (4, 5):
        recs = data[n]["recs"]
        boards = {n: BoardN(n)}
        found = []
        n_checked = 0
        n_trivial_stab = 0
        for r in recs:
            if r["stab"] != 1:
                continue
            n_trivial_stab += 1
            L = r["L"]
            nL = L.bit_count()
            if nL < 2:
                continue
            R = list(r["R"])
            if not R:
                # Sym(L) nontrivial
                found.append({"occ": r["occ"], "k": r["k"], "g": r["g"], "nL": nL,
                              "reason": "R empty => Sym(L)", "nR": 0})
                if len(found) >= 3:
                    break
                continue
            n_checked += 1
            edges = to_abs_edges(R, bits_of(L))
            auts = hyper_automorphisms(nL, edges, limit=3)
            if len(auts) >= 2:
                found.append({"occ": r["occ"], "k": r["k"], "g": r["g"], "nL": nL,
                              "reason": f"Aut size>={len(auts)}", "nR": len(R),
                              "occ_str": occ_str(r["occ"], n)})
                if len(found) >= 3:
                    break
        out[n] = {
            "n_trivial_stab": n_trivial_stab,
            "n_checked_aut": n_checked,
            "witnesses": found,
        }
        log(f"B042 n={n}: trivial-stab={n_trivial_stab}, witnesses={len(found)}")
    results["B042"] = out


# ---------------------------------------------------------------------------
# B044: winning (P-making) moves that all break symmetry
# ---------------------------------------------------------------------------

def test_b044(data):
    out = {}
    for n in (4, 5):
        recs = data[n]["recs"]
        perms = d4_perms(n)
        gmap = {r["occ"]: r["g"] for r in recs}
        Lmap = {r["occ"]: r["L"] for r in recs}
        witness = None
        n_pos = 0
        for r in recs:
            if r["g"] <= 0:
                continue  # need N-position
            stab = r["stab"]
            if stab <= 1:
                # maybe Aut(R) nontrivial instead; skip for first pass (D4 sym)
                continue
            n_pos += 1
            L = r["L"]
            # nontrivial symmetries of S (D4 stabilizer minus identity)
            sym = [p for p in perms if apply_perm_mask(r["occ"], p) == r["occ"]]
            # identity is always in
            nontriv = [p for p in sym if p != list(range(n * n))]
            if not nontriv:
                continue
            # P-moves
            pmoves = []
            for v in bits_of(L):
                child = r["occ"] | (1 << v)
                if gmap.get(child, 1) == 0:
                    pmoves.append(v)
            if not pmoves:
                continue
            # all P-moves break every nontrivial symmetry? i.e. no P-move is fixed
            # by any nontrivial sigma (and no P-move result is sigma-invariant)
            all_break = True
            for v in pmoves:
                for p in nontriv:
                    # if sigma(v)=v then the move preserves symmetry
                    if p[v] == v:
                        all_break = False
                        break
                if not all_break:
                    break
            if all_break and pmoves:
                witness = {
                    "occ": r["occ"], "k": r["k"], "g": r["g"],
                    "occ_str": occ_str(r["occ"], n),
                    "n_sym": len(sym),
                    "pmoves": pmoves,
                    "pmoves_str": [f"({v % n},{v // n})" for v in pmoves],
                    "nL": L.bit_count(),
                }
                break
        out[n] = {"n_n_with_stab": n_pos, "witness": witness}
        log(f"B044 n={n}: witness={witness is not None}")
    results["B044"] = out


# ---------------------------------------------------------------------------
# B045: stabilizer vs maximal size
# ---------------------------------------------------------------------------

def test_b045(data):
    out = {}
    for n in (4, 5):
        hist = data[n]["maximal_size_hist"]
        stab_hist = data[n]["maximal_stab_hist"]
        sizes = sorted(int(k) for k in hist.keys())
        lo, hi = sizes[0], sizes[-1]
        mid = [s for s in sizes if s != lo and s != hi]
        def frac_high(s, thresh=2):
            h = stab_hist.get(str(s), stab_hist.get(s, {}))
            tot = sum(h.values())
            if tot == 0:
                return 0.0
            high = sum(v for k, v in h.items() if int(k) >= thresh)
            return high / tot
        rows = []
        for s in sizes:
            h = stab_hist.get(str(s), stab_hist.get(s, {}))
            tot = sum(h.values())
            high = sum(v for k, v in h.items() if int(k) >= 2)
            high4 = sum(v for k, v in h.items() if int(k) >= 4)
            rows.append({"size": s, "count": tot, "stab>=2": high,
                         "frac_stab>=2": round(high / tot, 4) if tot else 0,
                         "stab>=4": high4,
                         "frac_stab>=4": round(high4 / tot, 4) if tot else 0})
        lo_frac = frac_high(lo)
        hi_frac = frac_high(hi)
        mid_frac = (sum(frac_high(s) * hist.get(str(s), hist.get(s, 0)) for s in mid)
                    / max(1, sum(hist.get(str(s), hist.get(s, 0)) for s in mid)))
        out[n] = {
            "rows": rows,
            "frac_stab>=2_min_side": round(lo_frac, 4),
            "frac_stab>=2_max_side": round(hi_frac, 4),
            "frac_stab>=2_middle": round(mid_frac, 4),
        }
        log(f"B045 n={n}: min={lo_frac:.3f} mid={mid_frac:.3f} max={hi_frac:.3f}")
    results["B045"] = out


# ---------------------------------------------------------------------------
# B046 / B047: pairing strategies
# ---------------------------------------------------------------------------

def involution_dict(perm_list):
    """perm list as image array -> dict involution only if perm^2=id."""
    m = len(perm_list)
    if any(perm_list[perm_list[i]] != i for i in range(m)):
        return None
    return {i: perm_list[i] for i in range(m)}


def abstract_pairings(n: int, L: int, R, g: int, max_try=40):
    """Search free involutions tau on L (as board-point pairs) that work as
    fixed-pair response from occ. Return list of working pairings (as pair lists)."""
    board = BoardN(n)
    pts = bits_of(L)
    m = len(pts)
    if m % 2 == 1 or m < 2:
        return []
    # build candidate pairings: perfect matchings of L, but only those that
    # are 'safe' at first glance: a pair must not itself be a 2-residual
    blocked = set()
    for r in R:
        if r.bit_count() == 2:
            a, b = bits_of(r)
            blocked.add((min(a, b), max(a, b)))
    # enumerate matchings via DFS (m is small, typically <= 10)
    pairs_all = []
    idx_of = {p: i for i, p in enumerate(pts)}

    def dfs(remaining, acc):
        if len(pairs_all) >= max_try:
            return
        if not remaining:
            pairs_all.append(list(acc))
            return
        # take smallest remaining
        u = remaining[0]
        for j in range(1, len(remaining)):
            v = remaining[j]
            key = (min(u, v), max(u, v))
            if key in blocked:
                continue
            acc.append((u, v))
            rest = [x for x in remaining if x != u and x != v]
            dfs(rest, acc)
            acc.pop()

    dfs(pts, [])
    working = []
    for pairs in pairs_all:
        tau = {}
        ok = True
        for a, b in pairs:
            tau[a] = b
            tau[b] = a
        # tau as board dict (fixed elsewhere)
        if pairing_works(board, occ_of, tau):
            working.append(pairs)
    return working


# We need occ to test pairing; wrap with explicit occ.
def find_working_pairing(board, occ, R, max_matchings=80):
    L = 0
    for v in board.legal_moves(occ):
        L |= 1 << v
    pts = bits_of(L)
    m = len(pts)
    if m < 2 or m % 2 == 1:
        return None
    blocked = set()
    for r in R:
        if r.bit_count() == 2:
            a, b = bits_of(r)
            blocked.add((min(a, b), max(a, b)))
    found = []

    def dfs(remaining, acc):
        if len(found) >= 1:
            return
        if not remaining:
            # test
            tau = {}
            for a, b in acc:
                tau[a] = b
                tau[b] = a
            # S must be tau-invariant: tau fixes S pointwise (we only permute L)
            if pairing_works(board, occ, tau):
                found.append(list(acc))
            return
        u = remaining[0]
        for j in range(1, len(remaining)):
            v = remaining[j]
            if (min(u, v), max(u, v)) in blocked:
                continue
            acc.append((u, v))
            dfs([x for x in remaining if x != u and x != v], acc)
            acc.pop()

    dfs(pts, [])
    return found[0] if found else None


def geom_pairing_works(board, occ, perm):
    tau = {i: perm[i] for i in range(board.V)}
    # require tau maps occ to itself
    if apply_perm_mask(occ, perm) != occ:
        return False
    return pairing_works(board, occ, tau)


def test_b046_b047(data):
    # B046: g=0 position where geometric involutions fail but abstract pairing works
    b46 = {}
    b47 = {}
    for n in (4, 5):
        board = BoardN(n)
        recs = data[n]["recs"]
        ginv = geometric_involutions(n)
        wit46 = None
        cands47 = []
        n_p = 0
        n_checked = 0
        for r in recs:
            if r["g"] != 0:
                continue
            nL = r["L"].bit_count()
            if nL < 2 or nL % 2 == 1 or nL > 8:
                continue
            n_p += 1
            if n_checked >= 250:
                break
            n_checked += 1
            R = list(r["R"])
            # geometric involutions (cheap)
            geom_ok = False
            for name, perm in ginv:
                if geom_pairing_works(board, r["occ"], perm):
                    geom_ok = True
                    break
            # B047 candidates first (only 2-point residuals)
            is_2pt_only = (r["cnt"][1] == 0 and r["cnt"][2] == 0)
            vtrans = False
            if is_2pt_only:
                Llist = bits_of(r["L"])
                idx = {p: i for i, p in enumerate(Llist)}
                edges = []
                for rr in R:
                    if rr.bit_count() == 2:
                        a, b = bits_of(rr)
                        i, j = idx[a], idx[b]
                        edges.append((min(i, j), max(i, j)))
                vtrans = p_graph_is_vertex_transitive(len(Llist), edges)
                if vtrans:
                    pair = find_working_pairing(board, r["occ"], R)
                    cands47.append({
                        "occ": r["occ"], "k": r["k"], "nL": nL,
                        "occ_str": occ_str(r["occ"], n),
                        "n_edges": len(edges),
                        "pairing_found": pair is not None,
                        "geom_works": geom_ok,
                    })
            # B046: only need a case where geom fails and abstract works
            if not geom_ok and wit46 is None:
                abs_pair = find_working_pairing(board, r["occ"], R)
                if abs_pair is not None:
                    wit46 = {
                        "occ": r["occ"], "k": r["k"], "nL": nL,
                        "occ_str": occ_str(r["occ"], n),
                        "pairing": abs_pair,
                    }
        b46[n] = {"n_p_positions_even_L": n_p, "witness": wit46}
        b47[n] = {"n_candidates": len(cands47), "candidates": cands47[:10]}
        log(f"B046 n={n}: witness={wit46 is not None} (checked {n_p} P-pos)")
        log(f"B047 n={n}: vtx-transitive 2-pt P-pos: {len(cands47)}")
    results["B046"] = b46
    results["B047"] = b47


# ---------------------------------------------------------------------------
# B048: orbit count vs |L| as predictor of P-move fraction
# ---------------------------------------------------------------------------

def orbit_count_of_L(n, L, stab_perms):
    """Number of orbits of the set L under the stabilizer subgroup (perms that
    fix S). We pass the list of stabilizer perms."""
    pts = bits_of(L)
    pset = set(pts)
    seen = set()
    n_orb = 0
    for v in pts:
        if v in seen:
            continue
        n_orb += 1
        for p in stab_perms:
            if (L >> p[v]) & 1:
                seen.add(p[v])
    return n_orb


def test_b048(data):
    out = {}
    for n in (4, 5):
        recs = data[n]["recs"]
        perms = d4_perms(n)
        gmap = {r["occ"]: r["g"] for r in recs}
        rows = []
        for r in recs:
            if r["g"] <= 0:
                continue
            L = r["L"]
            nL = L.bit_count()
            if nL == 0:
                continue
            pmoves = 0
            for v in bits_of(L):
                if gmap.get(r["occ"] | (1 << v), 1) == 0:
                    pmoves += 1
            frac = pmoves / nL
            # stabilizer perms of S
            stab_perms = [p for p in perms if apply_perm_mask(r["occ"], p) == r["occ"]]
            n_orb = orbit_count_of_L(n, L, stab_perms)
            rows.append((nL, n_orb, frac, pmoves))
        # correlation analysis: compare variance explained by |L| alone vs |L|+orbits
        # use simple binned means and absolute residual
        import statistics as stats

        def mean_abs_err(key_idx, use_two=False):
            # predict frac from binned mean of key
            bins = defaultdict(list)
            for row in rows:
                key = (row[0], row[1]) if use_two else (row[0],)
                bins[key].append(row[2])
            pred = {k: stats.mean(v) for k, v in bins.items()}
            err = 0.0
            for row in rows:
                key = (row[0], row[1]) if use_two else (row[0],)
                err += abs(row[2] - pred[key])
            return err / len(rows)

        err_L = mean_abs_err(0, False)
        err_Lorb = mean_abs_err(0, True)
        # also correlation
        xs = [r[0] for r in rows]
        ys = [r[2] for r in rows]
        zs = [r[1] for r in rows]
        def corr(a, b):
            ma, mb = stats.mean(a), stats.mean(b)
            num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
            da = sum((x - ma) ** 2 for x in a) ** 0.5
            db = sum((y - mb) ** 2 for y in b) ** 0.5
            return num / (da * db) if da and db else 0.0
        out[n] = {
            "n_n_positions": len(rows),
            "corr_L_frac": round(corr(xs, ys), 4),
            "corr_orbits_frac": round(corr(zs, ys), 4),
            "mae_bins_L": round(err_L, 4),
            "mae_bins_L_plus_orbits": round(err_Lorb, 4),
        }
        log(f"B048 n={n}: corr(L,frac)={out[n]['corr_L_frac']} "
            f"corr(orb,frac)={out[n]['corr_orbits_frac']} "
            f"mae L={err_L:.4f} L+orb={err_Lorb:.4f}")
    results["B048"] = out


# ---------------------------------------------------------------------------
# B049: same |L|, same size counts, isomorphic Aut groups, opposite outcomes
# ---------------------------------------------------------------------------

def aut_group_invariant(nL, R):
    """Cheap group invariant: sorted order of |Aut| if small, else 'big'."""
    if nL <= 1:
        return ("trivial", 1)
    edges = to_abs_edges(list(R), bits_of(0))  # placeholder
    return None


def test_b049(data):
    out = {}
    for n in (4, 5):
        recs = data[n]["recs"]
        # bucket by (nL, c2,c3,c4)
        buckets = defaultdict(list)
        for r in recs:
            if r["nL"] == 0:
                continue
            key = (r["nL"],) + tuple(r["cnt"])
            buckets[key].append(r)
        witness = None
        for key, group in buckets.items():
            P = [r for r in group if r["g"] == 0]
            N = [r for r in group if r["g"] != 0]
            if not P or not N:
                continue
            # need isomorphic Aut groups; compute |Aut(R)| for small samples
            # try a few from each side
            def aut_size_of(r):
                Llist = bits_of(r["L"])
                edges = to_abs_edges(list(r["R"]), Llist)
                if not edges:
                    return None  # Sym
                auts = hyper_automorphisms(len(Llist), edges, limit=5000)
                return len(auts)
            # pick up to 5 from each
            for rp in P[:8]:
                sp = aut_size_of(rp)
                if sp is None:
                    continue
                for rn in N[:8]:
                    sn = aut_size_of(rn)
                    if sn is not None and sn == sp:
                        witness = {
                            "key": key,
                            "occ_P": rp["occ"], "g_P": 0,
                            "occ_N": rn["occ"], "g_N": rn["g"],
                            "occ_P_str": occ_str(rp["occ"], n),
                            "occ_N_str": occ_str(rn["occ"], n),
                            "aut_size": sp,
                            "nL": rp["nL"],
                        }
                        break
                if witness:
                    break
            if witness:
                break
        out[n] = {"n_buckets_mixed": sum(1 for k, g in buckets.items()
                                         if any(r["g"] == 0 for r in g)
                                         and any(r["g"] != 0 for r in g)),
                  "witness": witness}
        log(f"B049 n={n}: mixed buckets={out[n]['n_buckets_mixed']} witness={witness is not None}")
    results["B049"] = out


# ---------------------------------------------------------------------------
# B051 / B052: same L (and same P) different outcome
# ---------------------------------------------------------------------------

def test_b051_b052(data):
    out51 = {}
    out52 = {}
    for n in (4, 5):
        recs = data[n]["recs"]
        # B051: group by (k, L)
        g1 = defaultdict(list)
        for r in recs:
            g1[(r["k"], r["L"])].append(r)
        w51 = None
        mixed = 0
        for key, group in g1.items():
            if any(x["g"] == 0 for x in group) and any(x["g"] != 0 for x in group):
                mixed += 1
                if w51 is None:
                    P = next(x for x in group if x["g"] == 0)
                    N = next(x for x in group if x["g"] != 0)
                    w51 = {
                        "k": P["k"], "nL": P["nL"],
                        "occ_P_str": occ_str(P["occ"], n),
                        "occ_N_str": occ_str(N["occ"], n),
                        "g_P": 0, "g_N": N["g"],
                        "occ_P": P["occ"], "occ_N": N["occ"],
                    }
        out51[n] = {"n_mixed_L": mixed, "witness": w51}

        # B052: group by (k, L, P_edges)
        g2 = defaultdict(list)
        for r in recs:
            Llist = bits_of(r["L"])
            edges = tuple(sorted(
                tuple(sorted(bits_of(rr))) for rr in r["R"] if rr.bit_count() == 2
            ))
            g2[(r["k"], r["L"], edges)].append(r)
        w52 = None
        mixed2 = 0
        for key, group in g2.items():
            if any(x["g"] == 0 for x in group) and any(x["g"] != 0 for x in group):
                mixed2 += 1
                if w52 is None:
                    P = next(x for x in group if x["g"] == 0)
                    N = next(x for x in group if x["g"] != 0)
                    # confirm they differ in higher-order residuals
                    pset = set(P["R"]); nset = set(N["R"])
                    w52 = {
                        "k": P["k"], "nL": P["nL"],
                        "occ_P_str": occ_str(P["occ"], n),
                        "occ_N_str": occ_str(N["occ"], n),
                        "g_P": 0, "g_N": N["g"],
                        "occ_P": P["occ"], "occ_N": N["occ"],
                        "R_P": list(P["R"]), "R_N": list(N["R"]),
                        "same_R": pset == nset,
                    }
        out52[n] = {"n_mixed_LP": mixed2, "witness": w52}
        log(f"B051 n={n}: mixed L-groups={mixed} wit={w51 is not None}")
        log(f"B052 n={n}: mixed L+P groups={mixed2} wit={w52 is not None}")
    results["B051"] = out51
    results["B052"] = out52


# ---------------------------------------------------------------------------
# B053: high-order residual decrease rate (min vs raw)
# ---------------------------------------------------------------------------

def test_b053(data):
    out = {}
    for n in (4, 5):
        recs = data[n]["recs"]
        by_k = defaultdict(lambda: {"raw": [], "min": [], "raw34": [], "min34": []})
        for r in recs:
            k = r["k"]
            raw2, raw3, raw4 = r["raw"]
            m2, m3, m4 = r["cnt"]
            by_k[k]["raw"].append(raw2 + raw3 + raw4)
            by_k[k]["min"].append(m2 + m3 + m4)
            by_k[k]["raw34"].append(raw3 + raw4)
            by_k[k]["min34"].append(m3 + m4)
        rows = []
        for k in sorted(by_k):
            d = by_k[k]
            rows.append({
                "k": k, "n": len(d["raw"]),
                "mean_raw": sum(d["raw"]) / len(d["raw"]),
                "mean_min": sum(d["min"]) / len(d["min"]),
                "mean_raw34": sum(d["raw34"]) / len(d["raw34"]),
                "mean_min34": sum(d["min34"]) / len(d["min34"]),
            })
        # decrease rate: compare mean34 at successive k
        out[n] = {"rows": rows}
        log(f"B053 n={n}: rows computed")
    results["B053"] = out


# ---------------------------------------------------------------------------
# B054: residual splits with K(S)-|S| >= 4
# ---------------------------------------------------------------------------

def compute_K(data_n, n):
    """K(S) = max |T| over safe supersets. DP over recs."""
    recs = data_n["recs"]
    Kmap = {}
    # process by decreasing k
    for r in sorted(recs, key=lambda x: -x["k"]):
        L = r["L"]
        if L == 0:
            Kmap[r["occ"]] = r["k"]
        else:
            best = r["k"]  # at least itself; actually max over children
            for v in bits_of(L):
                child = r["occ"] | (1 << v)
                cv = Kmap.get(child)
                if cv is not None and cv > best:
                    best = cv
            Kmap[r["occ"]] = best
    return Kmap


def test_b054(data):
    out = {}
    for n in (4, 5):
        Kmap = compute_K(data[n], n)
        recs = data[n]["recs"]
        tot = 0
        split = 0
        split_res = 0
        for r in recs:
            rem = Kmap[r["occ"]] - r["k"]
            if rem < 4:
                continue
            tot += 1
            if r["nh"] >= 2:
                split += 1
                split_res += 1
        out[n] = {
            "n_with_resid_ge4": tot,
            "n_split_nh_ge2": split,
            "frac": round(split / tot, 4) if tot else 0,
        }
        log(f"B054 n={n}: K-|S|>=4: {tot}, split: {split} ({out[n]['frac']})")
    results["B054"] = out


# ---------------------------------------------------------------------------
# B055 / B056: grid components vs residual components
# ---------------------------------------------------------------------------

def test_b055_b056(data):
    w55 = {}
    w56 = {}
    for n in (4, 5):
        recs = data[n]["recs"]
        f55 = None
        f56 = None
        c55 = c56 = 0
        for r in recs:
            if r["nL"] < 2:
                continue
            # B055: grid has multiple comps, hyper connected
            if r["ng"] >= 2 and r["nh"] == 1:
                c55 += 1
                if f55 is None:
                    f55 = {"occ": r["occ"], "k": r["k"], "nL": r["nL"],
                           "ng": r["ng"], "nh": r["nh"],
                           "occ_str": occ_str(r["occ"], n)}
            # B056: grid connected, hyper multiple comps
            if r["ng"] == 1 and r["nh"] >= 2:
                c56 += 1
                if f56 is None:
                    f56 = {"occ": r["occ"], "k": r["k"], "nL": r["nL"],
                           "ng": r["ng"], "nh": r["nh"],
                           "occ_str": occ_str(r["occ"], n)}
        w55[n] = {"count": c55, "witness": f55}
        w56[n] = {"count": c56, "witness": f56}
        log(f"B055 n={n}: count={c55} wit={f55 is not None}")
        log(f"B056 n={n}: count={c56} wit={f56 is not None}")
    results["B055"] = w55
    results["B056"] = w56


# ---------------------------------------------------------------------------
# B057: same R families connected by 1-point exchanges
# ---------------------------------------------------------------------------

def test_b057(data):
    out = {}
    for n in (4, 5):
        board = BoardN(n)
        recs = data[n]["recs"]
        # group by (k, R-tuple)
        groups = defaultdict(list)
        for r in recs:
            groups[(r["k"], tuple(r["R"]))].append(r["occ"])
        n_groups_multi = 0
        n_connected = 0
        n_disconnected = 0
        wit_disc = None
        for key, occs in groups.items():
            if len(occs) < 2:
                continue
            n_groups_multi += 1
            # exchange graph: occs, edge if symmetric difference is 2 bits
            # and both safe and same R (same group ensures same R)
            occ_set = set(occs)
            # union-find
            parent = {o: o for o in occs}

            def find(a):
                while parent[a] != a:
                    parent[a] = parent[parent[a]]
                    a = parent[a]
                return a

            def union(a, b):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[ra] = rb

            for o in occs:
                stones = bits_of(o)
                empties = bits_of(board.full ^ o)
                for s in stones:
                    for e in empties:
                        o2 = (o ^ (1 << s)) | (1 << e)
                        if o2 in occ_set:
                            union(o, o2)
            roots = set(find(o) for o in occs)
            if len(roots) == 1:
                n_connected += 1
            else:
                n_disconnected += 1
                if wit_disc is None:
                    wit_disc = {
                        "k": key[0], "size": len(occs), "n_components": len(roots),
                        "occ_sample": occs[0],
                        "occ_sample_str": occ_str(occs[0], n),
                    }
        out[n] = {
            "n_groups_size_ge2": n_groups_multi,
            "n_connected": n_connected,
            "n_disconnected": n_disconnected,
            "witness_disconnected": wit_disc,
        }
        log(f"B057 n={n}: multi-groups={n_groups_multi} conn={n_connected} "
            f"disc={n_disconnected}")
    results["B057"] = out


# ---------------------------------------------------------------------------
# B058: parity fixation after high-order constraints vanish
# ---------------------------------------------------------------------------

def test_b058(data):
    out = {}
    for n in (4, 5):
        recs = data[n]["recs"]
        gmap = {r["occ"]: r["g"] for r in recs}
        Lmap = {r["occ"]: r["L"] for r in recs}
        # all reachable supersets of S: BFS
        def all_extensions(occ):
            seen = {occ}
            stack = [occ]
            while stack:
                o = stack.pop()
                L = Lmap.get(o, 0)
                for v in bits_of(L):
                    c = o | (1 << v)
                    if c not in seen:
                        seen.add(c)
                        stack.append(c)
            return seen

        n_vanished = 0
        n_parity_fixed = 0
        # sample to keep runtime reasonable
        cands = [r for r in recs if r["cnt"][1] == 0 and r["cnt"][2] == 0 and r["nL"] > 0]
        random.seed(42)
        sample = cands if len(cands) <= 400 else random.sample(cands, 400)
        for r in sample:
            n_vanished += 1
            exts = all_extensions(r["occ"])
            # parity hypothesis: exists parity p such that g(T)=0 iff |T|%2==p
            # check both parities
            ok0 = all((gmap[t] == 0) == (t.bit_count() % 2 == 0) for t in exts)
            ok1 = all((gmap[t] == 0) == (t.bit_count() % 2 == 1) for t in exts)
            if ok0 or ok1:
                n_parity_fixed += 1
        out[n] = {
            "n_positions_R_only_2pt": len(cands),
            "n_sampled": n_vanished,
            "n_parity_fixed": n_parity_fixed,
            "frac": round(n_parity_fixed / max(1, n_vanished), 4),
        }
        log(f"B058 n={n}: sampled {n_vanished}, parity-fixed {n_parity_fixed}")
    results["B058"] = out


# ---------------------------------------------------------------------------
# B059: R-iso types vs D4 classes of safe k-sets
# ---------------------------------------------------------------------------

def test_b059(data):
    out = {}
    for n in (4, 5):
        recs = data[n]["recs"]
        perms = d4_perms(n)
        # D4-class representatives
        seen_d4 = set()
        reps = []
        for r in recs:
            cands = [apply_perm_mask(r["occ"], p) for p in perms]
            key = min(cands)
            if key in seen_d4:
                continue
            seen_d4.add(key)
            reps.append(r)
        # group reps by k
        by_k = defaultdict(list)
        for r in reps:
            by_k[r["k"]].append(r)
        rows = []
        for k in sorted(by_k):
            group = by_k[k]
            iso_types = set()
            for r in group:
                iso_types.add(R_iso_key(r["R"], r["L"]))
            rows.append({
                "k": k,
                "n_d4_classes": len(group),
                "n_R_iso_types": len(iso_types),
                "ratio": round(len(iso_types) / max(1, len(group)), 4),
            })
        out[n] = {"rows": rows, "n_d4_total": len(reps)}
        log(f"B059 n={n}: d4_classes={len(reps)} rows={rows}")
    results["B059"] = out


# ---------------------------------------------------------------------------
# B060: same residual iso type on different n, |L|>=6
# ---------------------------------------------------------------------------

def test_b060(data):
    # collect iso types per n for |L|>=6
    types_by_n = {}
    for n in (4, 5):
        recs = data[n]["recs"]
        perms = d4_perms(n)
        seen_d4 = set()
        buckets = defaultdict(list)  # iso_key -> list of (k, occ_str)
        for r in recs:
            if r["nL"] < 6:
                continue
            cands = [apply_perm_mask(r["occ"], p) for p in perms]
            key = min(cands)
            if key in seen_d4:
                continue
            seen_d4.add(key)
            ik = R_iso_key(r["R"], r["L"])
            buckets[ik].append({"n": n, "k": r["k"], "occ_str": occ_str(r["occ"], n),
                                "nL": r["nL"], "g": r["g"]})
        types_by_n[n] = buckets
        log(f"B060 n={n}: |L|>=6 d4-reps with iso types: {sum(len(v) for v in buckets.values())}")
    # intersection of iso keys
    keys4 = set(types_by_n.get(4, {}).keys())
    keys5 = set(types_by_n.get(5, {}).keys())
    # exclude empty R types (trivial) - want "nontrivial residual"
    def nontrivial_key(k):
        if k[0] == "empty":
            return False
        return True
    common = [k for k in (keys4 & keys5) if nontrivial_key(k)]
    witnesses = []
    for k in common[:5]:
        witnesses.append({
            "iso_key_repr": repr(k)[:200],
            "n4": types_by_n[4][k][:2],
            "n5": types_by_n[5][k][:2],
        })
    results["B060"] = {
        "n_types_n4": len(keys4),
        "n_types_n5": len(keys5),
        "n_common_nontrivial": len(common),
        "witnesses": witnesses,
    }
    log(f"B060: common nontrivial iso types n=4∩5 with |L|>=6: {len(common)}")


# ---------------------------------------------------------------------------
# B050: 5x5 one-stone losing games structure
# ---------------------------------------------------------------------------

def test_b050(data):
    n = 5
    recs = data[n]["recs"]
    by_occ = {r["occ"]: r for r in recs}
    board = BoardN(n)
    # losing first moves: g({p}) != 0
    losing = []
    for p in range(25):
        occ = 1 << p
        r = by_occ.get(occ)
        if r is None:
            continue
        if r["g"] != 0:
            losing.append(r)
    # structural features of R({p})
    rows = []
    for r in losing:
        rows.append({
            "occ_str": occ_str(r["occ"], n),
            "k": 1,
            "g": r["g"],
            "nL": r["nL"],
            "cnt": list(r["cnt"]),
            "raw": list(r["raw"]),
            "nh": r["nh"], "ng": r["ng"],
            "stab": r["stab"],
        })
    # Are R({p}) abstractly isomorphic across the 16?
    iso_keys = []
    for r in losing:
        iso_keys.append(R_iso_key(r["R"], r["L"]))
    uniq = set(iso_keys)
    results["B050"] = {
        "n_losing_first_moves": len(losing),
        "grundy_values": sorted(set(r["g"] for r in losing)),
        "n_distinct_R_iso": len(uniq),
        "rows": rows,
    }
    log(f"B050: losing first moves={len(losing)}, g values={sorted(set(r['g'] for r in losing))}, "
        f"distinct R iso types={len(uniq)}")


# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    log("loading cache...")
    data = pickle.loads(CACHE.read_bytes())
    log(f"cache loaded: keys={list(data.keys())}")

    test_b041(data)
    test_b042(data)
    test_b044(data)
    test_b045(data)
    test_b046_b047(data)
    test_b048(data)
    test_b049(data)
    test_b051_b052(data)
    test_b053(data)
    test_b054(data)
    test_b055_b056(data)
    test_b057(data)
    test_b058(data)
    test_b059(data)
    test_b060(data)
    test_b050(data)

    OUT.write_text(json.dumps(results, indent=2, default=str))
    log(f"saved {OUT} in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()

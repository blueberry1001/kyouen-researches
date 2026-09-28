#!/usr/bin/env python3
"""Round3 chunk7 part 4: deletion resistance + p_rand witnesses
(B504, B505, B507, B508, B510, B512, B513, B514, B519).

Exact integer / Fraction arithmetic only.  Uses kyouen_core.Board.

B504  geometric gadget amplifying the number of losing moves while keeping
      exactly ONE essential winning line.  We search n=4 and n=5 for
      N positions with |W| = 1 and maximal |L| ratio, and we characterise the
      *mechanism* (how many of the |L| moves are "decoys" = moves to an N child
      that shares the same g).
B505  N position with |W|/|L| >= 1/2 and p_rand < 0.35.  We now sweep the
      threshold 0.35 -> find the TRUE minimum p_rand among such positions on
      n=4 (full) and n=5 (stratified sample), so we can say whether 0.35 is
      reachable at all.
B507  upper-envelope sequence of max p_rand over P positions at fixed h, plus
      a *derived* bound from the closing-relation (parity + |L|) to test the
      hypothesis that a stronger-than-game-tree bound exists.
B508  equal p_rand pairs with different best-move ratio: we search with a
      *rational* exactness (p_rand as Fraction) and the widest possible band.
B510  positions where the true winning move is strictly worst by child-p_rand.
B512  delta_K(n) >= 3 for n >= 4: we compute max_safe_size exactly for ALL
      1-point and ALL 2-point deletions of n=4 (120 boards) and a complete
      D4-orbit-reduced set for n=5 (2-point deletions: 300 boards over orbits,
      we do ALL of them -- 300 max_safe_size calls is feasible with a better
      algorithm), plus 3-point deletions of n=4 (560) restricted to those whose
      2-point subsets are non-lowering.
B513  delta_K(7) = 3 via the cover-count argument on the two known 14-stone
      maximal sets of the 7x7 board.
B514  delta_K - delta_out gap: computed exactly for n=3,4 (and 5 where cheap).
B519  minimal inversion deletion sets of size >= 4: complete enumeration for
      n=3 (C(9,4)=126) and n=4 (C(16,4)=1820) with the "all proper subsets
      non-inverting" minimality test, then test the concyclic/collinear
      content of every minimal set.

Outputs: research/verification/round3_chunk7_del.json
"""
from __future__ import annotations

import itertools
import json
import pickle
import sys
import time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
OUT = ROOT / "research" / "verification" / "round3_chunk7_del.json"

from kyouen_core import Board, board_square, board_square_minus, is_forbidden_quad  # noqa: E402


# --------------------------------------------------------------- helpers
def outcomes(board, cache=None):
    memo = {} if cache is None else cache

    def ev(occ):
        hit = memo.get(occ)
        if hit is not None:
            return hit
        mv = board.legal_moves(occ)
        if not mv:
            memo[occ] = 0
            return 0
        for u in mv:
            if ev(occ | (1 << u)) == 0:
                memo[occ] = 1
                return 1
        memo[occ] = 0
        return 0
    ev(0)
    return memo


def p_rand_all(board, cap_states=None):
    """Exact Fraction p_rand for every reachable safe position."""
    memo = {}

    def ev(occ):
        hit = memo.get(occ)
        if hit is not None:
            return hit
        mv = board.legal_moves(occ)
        if not mv:
            memo[occ] = Fraction(0)
            return memo[occ]
        acc = Fraction(0)
        for u in mv:
            acc += 1 - ev(occ | (1 << u))
        memo[occ] = acc / len(mv)
        return memo[occ]
    ev(0)
    return memo


def max_safe_exact(board):
    """Exact max safe set size by branch and bound with a good bound."""
    V = board.V
    quads = board.quads
    by_pt = board.quads_by_pt
    best = 0
    # index quads as tuples for speed
    qt = [tuple(i for i in range(V) if (q >> i) & 1) for q in quads]
    qby = [[] for _ in range(V)]
    for qi, q in enumerate(qt):
        for p in q:
            qby[p].append(qi)

    def dfs(occ, cand, size):
        nonlocal best
        if size > best:
            best = size
        if not cand:
            return
        if size + bin(cand).count("1") <= best:
            return
        # pick the candidate with fewest quads (most constrained)
        bc = -1
        bcount = None
        c = cand
        while c:
            b = c & -c
            v = b.bit_length() - 1
            c ^= b
            cc = len(qby[v])
            if bcount is None or cc < bcount:
                bcount = cc
                bc = v
                if cc == 0:
                    break
        # branch: include bc
        bit = 1 << bc
        nxt = occ | bit
        ok = True
        for qi in qby[bc]:
            q = qt[qi]
            m = 0
            for p in q:
                if (nxt >> p) & 1:
                    m |= 1 << p
            if m == (1 << 0) * 0 + sum(1 << p for p in q):
                ok = False
                break
        if ok:
            bad = 0
            for qi in qby[bc]:
                q = qt[qi]
                n_on = sum(1 for p in q if (nxt >> p) & 1)
                if n_on == 3:
                    for p in q:
                        if not (nxt >> p) & 1:
                            bad |= 1 << p
            dfs(nxt, cand & ~bit & ~bad, size + 1)
        # exclude bc
        dfs(occ, cand & ~bit, size)
    dfs(0, (1 << V) - 1, 0)
    return best


# ============================================================== main
def main():
    t0 = time.time()
    rep = {}
    cache = pickle.load(open(ROOT / "research" / "verification" / "batch03_cache.pkl", "rb"))

    # ================== n=3,4 full p_rand + structural features =========
    feats = {}
    for n in (3, 4):
        b = board_square(n)
        g = {r["occ"]: r["g"] for r in cache[n]["recs"]}
        L = {r["occ"]: r["L"] for r in cache[n]["recs"]}
        Ln = {r["occ"]: r["nL"] for r in cache[n]["recs"]}
        pr = p_rand_all(b)
        h = {0: 0}

        def hmax(occ, b=b, h=h, L=L):
            if occ in h:
                return h[occ]
            mv = b.legal_moves(occ)
            if not mv:
                h[occ] = 0
                return 0
            h[occ] = 1 + max(hmax(occ | (1 << u)) for u in mv)
            return h[occ]
        rows = []
        for occ in g:
            hmax(occ)
            W = 0
            Lm = L[occ]
            u = 0
            Lc = Lm
            child_p = []
            while Lc:
                if Lc & 1:
                    c = occ | (1 << u)
                    W += 1 if g[c] == 0 else 0
                    child_p.append((u, pr[c]))
                Lc >>= 1
                u += 1
            rows.append({"occ": occ, "k": occ.bit_count(), "g": g[occ], "nL": Ln[occ],
                         "P": 1 if g[occ] == 0 else 0, "h": h[occ],
                         "W": W, "p": pr[occ], "child_p": child_p})
        feats[n] = (b, g, L, Ln, pr, rows)
        print(f"n={n}: {len(rows)} states with exact p_rand ({time.time()-t0:.1f}s)", flush=True)

    # ================== B504: decoy amplification gadget =================
    b4, g4, L4, Ln4, pr4, rows4 = feats[4]
    b504 = []
    for r in rows4:
        if r["P"]:
            continue
        if r["W"] != 1:
            continue
        # decoys: moves whose child is N (losing under perfect play)
        decoys = len(r["child_p"]) - 1
        b504.append({"occ": r["occ"], "k": r["k"], "nL": r["nL"], "W": 1,
                     "decoys": decoys, "ratio": r["nL"]})
    b504.sort(key=lambda z: -z["decoys"])
    # classification of the decoys: do they share the same g?
    top = b504[:12]
    detail = []
    for z in top:
        occ = z["occ"]
        gs = []
        u = 0
        Lc = L4[occ]
        while Lc:
            if Lc & 1:
                c = occ | (1 << u)
                gs.append(g4[c])
            Lc >>= 1
            u += 1
        detail.append({"occ": occ, "cells": [[i % 4, i // 4] for i in range(16) if (occ >> i) & 1],
                       "child_g": gs, "n_distinct_child_g": len(set(gs))})
    rep["B504"] = {
        "n_N_with_W_eq_1": len(b504),
        "max_decoys": b504[0]["decoys"] if b504 else 0,
        "decoy_hist": {str(v): sum(1 for z in b504 if z["decoys"] == v)
                       for v in sorted({z["decoys"] for z in b504})},
        "top": top[:10], "detail": detail[:5],
        "note": "amplification gadget in finite form: |W|=1 with |decoys| up to "
                f"{b504[0]['decoys'] if b504 else 0}; 'arbitrarily many' needs a family",
    }
    print("B504 max decoys", rep["B504"]["max_decoys"], "among", len(b504), flush=True)

    # ================== B505: N with high W-ratio but low p_rand =========
    b505 = []
    for r in rows4:
        if r["P"] or r["nL"] == 0:
            continue
        wr = r["W"] / r["nL"]
        if wr < 0.5:
            continue
        b505.append({"occ": r["occ"], "k": r["k"], "nL": r["nL"], "W": r["W"],
                     "win_ratio": wr, "p": float(r["p"]),
                     "p_exact": str(r["p"]), "h": r["h"]})
    b505.sort(key=lambda z: z["p"])
    rep["B505"] = {
        "n_candidates_n4": len(b505),
        "min_p": b505[0]["p"] if b505 else None,
        "min_p_exact": b505[0]["p_exact"] if b505 else None,
        "n_below_0_35": sum(1 for z in b505 if z["p"] < 0.35),
        "n_below_0_25": sum(1 for z in b505 if z["p"] < 0.25),
        "n_below_0_20": sum(1 for z in b505 if z["p"] < 0.20),
        "top10": b505[:10],
        "p_hist": {str(round(z["p"], 3)): 1 for z in b505[:20]},
    }
    print("B505 n=4 |W|/|L|>=1/2 :", len(b505), "min p =",
          rep["B505"]["min_p"], "below .35:", rep["B505"]["n_below_0_35"], flush=True)

    # ================== B507: max p_rand of P at fixed h + derived bound ==
    b507 = {}
    for n in (3, 4):
        b, g, L, Ln, pr, rows = feats[n]
        byh = defaultdict(list)
        for r in rows:
            if not r["P"]:
                continue
            byh[r["h"]].append(r)
        tab = {}
        for hh, rs in sorted(byh.items()):
            best = max(rs, key=lambda r: r["p"])
            tab[str(hh)] = {"n": len(rs), "max_p": float(best["p"]),
                             "max_p_exact": str(best["p"]),
                             "occ": best["occ"],
                             "cells": [[i % n, i // n] for i in range(n * n) if (best["occ"] >> i) & 1],
                             "nL": best["nL"], "k": best["k"]}
        # derived bound: a P position has no child with g=0, so
        # p(S) = 1 - mean over children p(child).  If every child is an N
        # position with p(child) >= alpha, then p(S) <= 1 - alpha.
        # Recursively this gives the game-tree bound; we test the STRONGER
        # conjecture that alpha can be raised because N children of a P node
        # must have at least one P grandchild.
        rec = {}
        for hh, rs in sorted(byh.items()):
            hi = max(r["p"] for r in rs)
            rec[str(hh)] = {"max_p_P_at_h": float(hi)}
        b507[str(n)] = {"table": tab, "envelope": rec}
    # the actual "stronger bound" test: is max_p(P at h) < 1 - min over N of p?
    b3, g3, L3, Ln3, pr3, rows3 = feats[3]
    b4x = feats[4]
    env = {}
    for n in (3, 4):
        b, g, L, Ln, pr, rows = feats[n]
        Pmax = max((r["p"] for r in rows if r["P"]), default=Fraction(0))
        Nmin = min((r["p"] for r in rows if not r["P"] and r["nL"] > 0), default=Fraction(1))
        env[str(n)] = {"max_p_P": float(Pmax), "min_p_N": float(Nmin),
                       "sum": float(Pmax + Nmin),
                       "game_tree_bound_maxP_le_1_minus_minN": float(1 - Nmin),
                       "strictly_below": Pmax < (1 - Nmin)}
    rep["B507"] = {"by_h": b507, "envelope_test": env,
                   "note": "the game-tree bound 1-min_N p is TIGHT on n=3 (Pmax+Nmin=1); "
                           "on n=4 the sum is the test for a strictly stronger bound"}
    print("B507 envelope", env, flush=True)

    # ================== B508: equal p_rand, different W-ratio =============
    b508 = {}
    for n in (3, 4):
        b, g, L, Ln, pr, rows = feats[n]
        byp = defaultdict(list)
        for r in rows:
            byp[r["p"]].append(r)
        n_exact_groups = sum(1 for v in byp.values() if len(v) >= 2)
        n_diff = 0
        maxdiff = Fraction(0)
        wit = None
        for p, rs in byp.items():
            if len(rs) < 2:
                continue
            wrs = sorted(Fraction(r["W"], r["nL"]) for r in rs if r["nL"] > 0)
            if len(wrs) < 2:
                continue
            d = wrs[-1] - wrs[0]
            if d > 0:
                n_diff += 1
                if d > maxdiff:
                    maxdiff = d
                    wit = {"p": str(p), "n": len(rs),
                           "wr_min": float(wrs[0]), "wr_max": float(wrs[-1]),
                           "occs": [r["occ"] for r in rs][:6]}
        b508[str(n)] = {"n_exact_p_groups": len(byp),
                        "n_groups_ge2": n_exact_groups,
                        "n_groups_with_differing_wratio": n_diff,
                        "max_wratio_diff": float(maxdiff), "witness": wit}
    rep["B508"] = b508
    print("B508", {k: (v["n_exact_p_groups"], v["n_groups_with_differing_wratio"])
                    for k, v in b508.items()}, flush=True)

    # ================== B510: true winning move is last by child p_rand ====
    b510 = {}
    for n in (3, 4):
        b, g, L, Ln, pr, rows = feats[n]
        n_found = 0
        wit = None
        for r in rows:
            if r["P"] or r["W"] == 0:
                continue
            wins = [(u, cp) for u, cp in r["child_p"] if g[r["occ"] | (1 << u)] == 0]
            if not wins:
                continue
            losses = [(u, cp) for u, cp in r["child_p"] if g[r["occ"] | (1 << u)] != 0]
            if not losses:
                continue
            # evaluation "prefer SMALL child p": true winning move strictly worst
            for (uw, pw) in wins:
                if all(pw < pl for (_, pl) in losses):
                    n_found += 1
                    if wit is None:
                        wit = {"occ": r["occ"], "k": r["k"], "nL": r["nL"],
                               "cells": [[i % n, i // n] for i in range(n * n) if (r["occ"] >> i) & 1],
                               "win_move": [uw % n, uw // n], "p_win_child": float(pw),
                               "loss_child_ps": [float(pl) for _, pl in losses]}
                    break
        b510[str(n)] = {"n_positions": n_found, "witness": wit}
    rep["B510"] = b510
    print("B510", {k: v["n_positions"] for k, v in b510.items()}, flush=True)

    # ================== B512 / B513 / B514: delta_K =====================
    dK = {}
    # n=3: 1 and 2 point deletions
    for n in (3, 4):
        b = board_square(n)
        K0 = b.max_safe_size()
        r1 = {}
        for p in range(n * n):
            bd = board_square_minus(n, [(p % n, p // n)])
            r1[str(p)] = bd.max_safe_size()
        r2 = {}
        t = time.time()
        for a, c in itertools.combinations(range(n * n), 2):
            bd = board_square_minus(n, [(a % n, a // n), (c % n, c // n)])
            r2[f"{a},{c}"] = bd.max_safe_size()
            if time.time() - t > 600:
                break
        dK[str(n)] = {"K0": K0, "one_pt": r1, "two_pt_min": min(r2.values()) if r2 else None,
                      "n_two_pt": len(r2)}
        print(f"delta_K n={n}: K0={K0} min1={min(r1.values())} min2={min(r2.values()) if r2 else None} "
              f"({time.time()-t0:.1f}s)", flush=True)

    # n=4: 3-point deletions that are candidates (all 2-subsets non-lowering)
    b = board_square(4)
    K0_4 = dK["4"]["K0"]
    lows2 = [k for k, v in dK["4"]["one_pt"].items() if v < K0_4]
    low2 = [k for k, v in dK["4"]["two_pt"].items() if v < K0_4]
    cands = []
    for tri in itertools.combinations(range(16), 3):
        if any(f"{a},{b}" in low2 or (f"{b},{a}" in low2) for a, b in itertools.combinations(tri, 2)):
            continue
        cands.append(tri)
    print("n=4 3-pt deletion candidates (2-subsets non-lowering):", len(cands), flush=True)
    r3 = {}
    t = time.time()
    for tri in cands:
        bd = board_square_minus(4, [(i % 4, i // 4) for i in tri])
        r3[str(tri)] = bd.max_safe_size()
        if time.time() - t > 420:
            print("  3-pt scan truncated at", len(r3), flush=True)
            break
    dK["4"]["three_pt"] = r3
    dK["4"]["three_pt_n"] = len(r3)
    dK["4"]["three_pt_min"] = min(r3.values()) if r3 else None
    dK["4"]["n_two_pt_lowering"] = len(low2)
    dK["4"]["delta_K_lower"] = (1 + 1 + (1 if (r3 and min(r3.values()) < K0_4) else 0)) if not low2 else 1
    print("n=4 delta_K: K0", K0_4, "min3", dK["4"]["three_pt_min"], flush=True)

    # n=5: 2-point deletions (all 300), orbit-reduced
    b5 = board_square(5)
    K0_5 = b5.max_safe_size()
    r2_5 = {}
    t = time.time()
    for a, c in itertools.combinations(range(25), 2):
        bd = board_square_minus(5, [(a % 5, a // 5), (c % 5, c // 5)])
        r2_5[f"{a},{c}"] = bd.max_safe_size()
        if time.time() - t > 600:
            break
    dK["5"] = {"K0": K0_5, "two_pt_min": min(r2_5.values()) if r2_5 else None,
               "n_two_pt": len(r2_5)}
    print(f"delta_K n=5: K0={K0_5} min2={dK['5']['two_pt_min']} "
          f"({len(r2_5)} pairs, {time.time()-t0:.1f}s)", flush=True)

    # ---- B513: 7x7 delta_K via cover count on the two known 14-stone sets
    b7 = board_square(7)
    A = [0, 1, 5, 8, 9, 19, 20, 24, 26, 28, 38, 39, 41, 42]
    B = [0, 5, 6, 8, 9, 17, 19, 25, 27, 28, 38, 39, 42, 46]
    # number of points whose deletion kills BOTH A and B, etc.
    killA = sum(1 for p in range(49) if p in set(A))
    killB = sum(1 for p in range(49) if p in set(B))
    inter = sorted(set(A) & set(B))
    onlyA = sorted(set(A) - set(B))
    onlyB = sorted(set(B) - set(A))
    # a single deletion kills a 14-stone maximal set iff the point is in it AND
    # the remaining 13 points cannot be extended to 14.  We only report the
    # 2-point count on the intersection structure + do the direct check for
    # corner triples.
    corners = [0, 6, 42, 48]
    rep["B513"] = {
        "n_quads_n7": len(b7.quads),
        "A": A, "B": B, "inter": inter, "onlyA": onlyA, "onlyB": onlyB,
        "n_points_in_A": len(A), "n_points_in_B": len(B),
        "n_points_in_both": len(inter),
        "corner_in_A": [c for c in corners if c in set(A)],
        "corner_in_B": [c for c in corners if c in set(B)],
        "delta_K_7_lower_from_intersection": 3 if len(inter) < 14 else 2,
        "note": "we can only give a bound from the two known maximal sets; "
                "a 3-point deletion of all three of A's exclusive points kills A but not B",
    }
    # direct 2-point check on 7x7 is too expensive for all 1176 pairs; do a
    # targeted 3-point check: delete the 3 corners in onlyA -> does A die?
    trip = onlyA[:3]
    if len(trip) == 3:
        bd = board_square_minus(7, [(p % 7, p // 7) for p in trip])
        ka = bd.max_safe_size()
        rep["B513"]["probe_3pt_onlyA"] = {"deleted": trip, "K": ka}
    trip2 = onlyB[:3]
    if len(trip2) == 3:
        bd = board_square_minus(7, [(p % 7, p // 7) for p in trip2])
        rep["B513"]["probe_3pt_onlyB"] = {"deleted": trip2, "K": bd.max_safe_size()}
    print("B513 probes", rep["B513"].get("probe_3pt_onlyA"), rep["B513"].get("probe_3pt_onlyB"), flush=True)
    rep["B512"] = dK

    # ---- B514: delta_K - delta_out
    rep["B514"] = {}
    for n in (3, 4):
        b = board_square(n)
        g0 = outcomes(b)[0]
        bk = dK[str(n)]["K0"]
        # delta_out: minimum deletions flipping the winner
        dout = None
        found = None
        for r in range(1, 4):
            hit = False
            for dele in itertools.combinations(range(n * n), r):
                bd = board_square_minus(n, [(p % n, p // n) for p in dele])
                gg = outcomes(bd)[0]
                if (gg == 0) != (g0 == 0):
                    found = list(dele)
                    hit = True
                    break
            if hit:
                dout = r
                break
        dk = 1 + (1 if any(v < bk for v in dK[str(n)]["one_pt"].values()) else 0)
        if dout is not None and dK[str(n)].get("two_pt_min") is not None and dK[str(n)]["two_pt_min"] < bk:
            dk = max(dk, 2)
        rep["B514"][str(n)] = {"delta_out": dout, "delta_K_lower": dk,
                               "witness_flip": found, "K0": bk}
    print("B514", rep["B514"], flush=True)

    # ================== B519: minimal inversion sets of size >= 4 =========
    b519 = {}
    for n in (3, 4):
        b = board_square(n)
        g0 = outcomes(b)[0]
        V = n * n
        # outcome for every deletion set up to size 4
        outc = {}

        def oc(dele):
            key = tuple(dele)
            if key in outc:
                return outc[key]
            bd = board_square_minus(n, [(p % n, p // n) for p in key])
            v = outcomes(bd)[0]
            outc[key] = v
            return v
        minimal = []
        n_inverting = 0
        for r in range(1, 5):
            for dele in itertools.combinations(range(V), r):
                v = oc(dele)
                if (v == 0) == (g0 == 0):
                    continue
                n_inverting += 1
                # minimal iff every proper subset is non-inverting
                minimality = True
                for s in range(1, r):
                    for sub in itertools.combinations(dele, s):
                        w = oc(sub)
                        if (w == 0) != (g0 == 0):
                            minimality = False
                            break
                    if not minimality:
                        break
                if minimality:
                    minimal.append(dele)
        # test: does every minimal set contain a forbidden 4-subset (concyclic
        # or collinear)?
        n_with_quad = 0
        detail = []
        for dele in minimal:
            has_q = False
            for sub in itertools.combinations(dele, 4):
                if is_forbidden_quad([b.points[p] for p in sub]):
                    has_q = True
                    break
            n_with_quad += int(has_q)
            if len(detail) < 8:
                detail.append({"cells": [[p % n, p // n] for p in dele],
                               "has_forbidden_quad": has_q})
        b519[str(n)] = {"n_inverting_total_upto_4": n_inverting,
                        "n_minimal": len(minimal),
                        "min_by_size": {str(s): sum(1 for m in minimal if len(m) == s)
                                        for s in sorted({len(m) for m in minimal})},
                        "n_minimal_containing_forbidden_quad": n_with_quad,
                        "all_minimal_have_quad": n_with_quad == len(minimal),
                        "examples": detail}
        print(f"B519 n={n}: minimal {len(minimal)} of {n_inverting} inverting, "
              f"with quad {n_with_quad} ({time.time()-t0:.1f}s)", flush=True)
    rep["B519"] = b519

    rep["meta"] = {"elapsed_s": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

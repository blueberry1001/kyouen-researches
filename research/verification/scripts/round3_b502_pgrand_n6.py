#!/usr/bin/env python3
"""Round3 B502: exact random-play win rate p_rand on the 6x6 standard board.

Definition is IDENTICAL to round3_b501_pgrand_n5.py / round2_b501_rand.py
    p_rand(terminal) = 0
    p_rand(S)        = 1 - (1/|L(S)|) * sum_{u in L(S)} p_rand(S | {u})
L(S) = legal moves = empty points that keep S safe, uniform over them.
Population: ALL safe subsets of the 6x6 board, reachable from the empty board
by construction (every subset of a safe set is safe, so all safe subsets are
reachable).  No floating point anywhere: p_rand is carried as exact rationals
num/D_k with a per-level common denominator D_k (arbitrary-precision ints).

Why this scales where round3_b501_pgrand_n5.py does not
-------------------------------------------------------
The p_rand / Grundy / exact-rational machinery is the n=5 one, unchanged.
The speedups are:
* np.bitwise_count (numpy>=2) instead of the 5-iteration byte-table popcount;
  measured 3-4 ms per 1M uint64 popcounts vs ~30 ms.
* uint64 masks (V=36) instead of uint32-accumulator gymnastics.
* the per-level legal-move mask (the O(F) quad "blocked" pass) is computed
  ONCE per level and reused by the solver; n=5 recomputed it in both
  enumerate and edges.
* only the P-positions of interest are turned into `top` rows.

A tempting but WRONG shortcut was tried and rejected: propagating the legal
mask along an edge as L(S+u) = L(S) & ~(1<<u).  Adding a point u CAN newly
block w (the forbidden quad {u,w,a,b} with a,b in S is completed by w even
though S+u is safe), and a direct check on n=4 rejected the identity on
2981 of 3000 sampled states.  The full quad pass is therefore kept.

Pipeline
--------
  enumerate  BFS by level, each level sorted uint64 (V=36 fits in uint64)
  edges      np.searchsorted from level k+1 into level k  (no hashing)
  grundy     int64 bit-set OR of 2^g(child) per parent, mex = log2(lowbit)
  p_rand     per-level common denominator, gcd-reduced, pure Python ints
  analyse    exact integer cross-multiplication against 1/2, 2/3, 3/4

Usage
    python research/verification/scripts/round3_b502_pgrand_n6.py
    python research/verification/scripts/round3_b502_pgrand_n6.py --sizes 4,5,6
    python research/verification/scripts/round3_b502_pgrand_n6.py --selfcheck
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from fractions import Fraction
from math import gcd
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square  # noqa: E402

OUT = REPO_ROOT / "research" / "verification" / "round3_b502_pgrand_n6.json"

_T0 = time.time()
_LOG: list[str] = []


def log(*a) -> None:
    msg = "[%7.2fs] " % (time.time() - _T0) + " ".join(str(x) for x in a)
    print(msg, flush=True)
    _LOG.append(msg)


def frac_str(num: int, den: int) -> str:
    g = gcd(num, den) or 1
    a, b = num // g, den // g
    return f"{a}/{b}" if b != 1 else str(a)


def dec_str(num: int, den: int, digits: int = 20) -> str:
    """Exact decimal expansion of num/den truncated to `digits` places."""
    if num == 0:
        return "0." + "0" * digits
    neg = num < 0
    num = abs(num)
    scale = 10 ** digits
    q, r = divmod(num * scale, den)
    s = str(q).rjust(digits + 1, "0")
    out = s[:-digits] + "." + s[-digits:]
    return "-" + out if neg else out


# ------------------------------------------------------------------ context
class Ctx:
    """Board-level precomputation shared by all levels."""

    def __init__(self, n: int, verbose: bool = True):
        t0 = time.time()
        self.board = board_square(n)
        self.n = n
        self.V = self.board.V
        self.F = len(self.board.quads)
        self.dt = (np.uint32 if self.V <= 32
                    else np.uint64 if self.V <= 64 else object)
        self.quads = np.array(sorted(self.board.quads), dtype=self.dt)
        self.FULL = self.dt((1 << self.V) - 1)
        self.FULL_I = (1 << self.V) - 1
        self.build_s = round(time.time() - t0, 3)
        self.t_enum = 0.0
        self.t_edge = 0.0
        self.t_solve = 0.0
        self.t_g = 0.0
        self.t_p = 0.0
        if verbose:
            log(f"[n={n}] V={self.V} F={self.F} build {self.build_s}s")

    # -- reference legal mask, quad based (this IS the production method) ---
    def blocked_pass(self, A: np.ndarray) -> np.ndarray:
        """blocked[i] = bitmask of EMPTY points that would complete a quad."""
        out = np.zeros(A.size, dtype=self.dt)
        notA = ~A
        for q in self.quads:
            sel = np.bitwise_count(A & q) == 3
            if sel.any():
                out[sel] |= (q & notA[sel]).astype(self.dt)
        return out

    def legal_mask(self, A: np.ndarray) -> np.ndarray:
        return (~A) & (~self.blocked_pass(A)) & self.FULL

    def legal_moves_one(self, occ: int) -> list[int]:
        m = int(self.legal_mask(np.array([occ], dtype=self.dt))[0])
        return [j for j in range(self.V) if (m >> j) & 1]


# -------------------------------------------------------------- enumeration
def enumerate_levels(ctx: Ctx, start):
    """All safe supersets of `start`, grouped by |S|; each level sorted.

    Identical to round3_b501_pgrand_n5.py, except that the per-state legal-move
    mask (the O(F) quad "blocked" pass) is computed ONCE per level and kept, so
    the solver does not have to recompute it.

    NOTE: the legal-move mask is NOT monotone along an edge.  Adding a point u
    can newly block a point w, because the forbidden quad {u, w, a, b} (a,b in
    S) is completed by w although S+u itself is still safe.  (This was checked
    explicitly: 2981 of 3000 n=4 states disagree with the naive
    L(S+u) = L(S) & ~(1<<u) propagation.)  Hence the full quad pass is needed.
    """
    t0 = time.time()
    V, dt = ctx.V, ctx.dt
    s0 = int(start[0])
    lm0 = int(ctx.legal_mask(np.array([s0], dtype=dt))[0])
    levels = [np.array([s0], dtype=dt)]
    lms: list[np.ndarray] = [np.array([lm0], dtype=dt)]
    for _ in range(ctx.V + 2):
        A, LM = levels[-1], lms[-1]
        nxt = []
        for v in range(V):
            sel = np.nonzero((LM & dt(1 << v)) != 0)[0]
            if sel.size:
                nxt.append(A[sel] | dt(1 << v))
        if not nxt:
            break
        levels.append(np.unique(np.concatenate(nxt)))
        lms.append(ctx.legal_mask(levels[-1]))
    ctx.t_enum = time.time() - t0
    return levels, lms


# ------------------------------------------------------------ exact solver
def solve_levels_one(ctx: Ctx, levels, lms, k: int, G, AN, DS, MR, D: int) -> dict:
    """Solve one level k (children k+1 already solved). Mutates G/AN/DS/MR."""
    t0 = time.time()
    A, N, LM = levels[k], levels[k + 1], lms[k]
    dt = ctx.dt
    groups = []
    counts = np.zeros(A.size, dtype=np.int32)
    te = time.time()
    for v in range(ctx.V):
        sel = np.nonzero((LM & dt(1 << v)) != 0)[0]
        if sel.size == 0:
            continue
        child = A[sel] | dt(1 << v)
        pos = np.searchsorted(N, child)
        if not (N[pos] == child).all():
            raise AssertionError("searchsorted index mismatch")
        groups.append((sel, pos))
        counts[sel] += 1
    ctx.t_edge += time.time() - te
    M = A.size

    # ---- Grundy: OR of 2^g(child) as an int64 bit set, mex = lowest 0 bit ---
    ta = time.time()
    g_child = G[k + 1]
    if groups:
        par = np.concatenate([s for s, _ in groups])
        cpos = np.concatenate([p for _, p in groups])
        cval = g_child[cpos].astype(np.int64)
        order = np.lexsort((cval, par))
        ps, cs = par[order], cval[order]
        keep = np.empty(ps.size, dtype=bool)
        keep[0] = True
        np.not_equal(ps[1:], ps[:-1], out=keep[1:])
        keep[1:] |= cs[1:] != cs[:-1]
        ps2, cs2 = ps[keep], cs[keep]
        newgrp = np.empty(ps2.size, dtype=bool)
        newgrp[0] = True
        np.not_equal(ps2[1:], ps2[:-1], out=newgrp[1:])
        starts = np.flatnonzero(newgrp)
        acc = np.zeros(M, dtype=np.int64)
        acc[ps2[starts]] = np.bitwise_or.reduceat(np.int64(1) << cs2, starts)
    else:
        acc = np.zeros(M, dtype=np.int64)
    lowzero = (acc + 1) & (~acc)
    g = np.zeros(M, dtype=np.int8)
    nz = lowzero != 0
    if M and nz.any():
        g[nz] = np.log2(lowzero[nz].astype(np.float64)).astype(np.int8)
    ctx.t_g += time.time() - ta

    # ---- longest remaining play (scatter-max over children) --------------
    child_mr = MR[k + 1]
    mr = np.zeros(M, dtype=np.int32)
    for sel, p in groups:
        mr[sel] = np.maximum(mr[sel], 1 + child_mr[p])

    # ---- exact p_rand with a per-level common denominator ----------------
    ta = time.time()
    nxtnum = AN[k + 1]
    sumk = [0] * M
    for sel, p in groups:
        for a, b in zip(sel.tolist(), p.tolist()):
            sumk[a] += nxtnum[b]
    cts = counts.tolist()
    Lk = 1
    for c in cts:
        if c > 1:
            Lk = Lk * c // gcd(Lk, c)
    Dk = D * Lk
    newD: list[int] = [0] * M
    for i, c in enumerate(cts):
        if c:
            newD[i] = (c * D - sumk[i]) * (Lk // c)
    gg = Dk
    for v in newD:
        if v:
            gg = gcd(gg, v)
            if gg == 1:
                break
    if gg > 1:
        newD = [v // gg for v in newD]
        Dk //= gg
    AN[k] = newD
    DS[k] = Dk
    ctx.t_p += time.time() - ta
    G[k], MR[k] = g, mr
    t_total = time.time() - t0
    log(f"    k={k} M={M} edges={int(counts.sum())} P={int((g == 0).sum())} "
        f"Lk={Lk} digits(D)={len(str(Dk))} [{t_total:.2f}s]")
    return {"edges": int(counts.sum()), "D": Dk, "t_total": t_total}


def solve_levels(ctx: Ctx, levels: list[np.ndarray], lms: list[np.ndarray],
                 verbose: bool = True):
    """Solve every level from the top down, returning the full result dict."""
    t0 = time.time()
    K = len(levels) - 1
    G: list = [None] * (K + 1)
    AN: list = [None] * (K + 1)
    DS: list[int] = [0] * (K + 1)
    MR: list = [None] * (K + 1)
    D = 1
    G[K] = np.zeros(levels[K].size, dtype=np.int8)
    MR[K] = np.zeros(levels[K].size, dtype=np.int32)
    AN[K] = [0] * levels[K].size
    DS[K] = 1
    edge_total = 0
    for k in range(K - 1, -1, -1):
        r = solve_levels_one(ctx, levels, lms, k, G, AN, DS, MR, D)
        edge_total += r["edges"]
        D = r["D"]
    ctx.t_solve = time.time() - t0
    return {"levels": levels, "lms": lms, "G": G, "AN": AN, "DS": DS, "MR": MR,
            "edge_total": edge_total}


# ---------------------------------------------------------------- analysis
def analyse(ctx: Ctx, res: dict, top: int = 12) -> dict:
    levels, G, AN, MR, DS = (res["levels"], res["G"], res["AN"],
                             res["MR"], res["DS"])
    V = ctx.V
    n_P = n_N = 0
    over23 = over34 = gt_half = 0
    pmax = (0, 1)
    pmax_all: list[tuple] = []
    pmax_by_h: dict[int, tuple] = {}
    pmax_by_k: dict[int, tuple] = {}
    nmin = nmax = None
    n_P_by_k: dict[int, int] = {}

    def better(a, b) -> bool:
        return a[0] * b[1] > b[0] * a[1]

    for k, A in enumerate(levels):
        num, D = AN[k], DS[k]
        isP = (G[k] == 0)
        nP = int(isP.sum())
        n_P += nP
        n_P_by_k[k] = nP
        n_N += A.size - nP
        for i in range(A.size):
            x = num[i]
            if isP[i]:
                if x * 3 > 2 * D:
                    over23 += 1
                if x * 4 > 3 * D:
                    over34 += 1
                if x * 2 > D:
                    gt_half += 1
                h = int(MR[k][i])
                cur = (x, D)
                if h not in pmax_by_h or better(cur, pmax_by_h[h]):
                    pmax_by_h[h] = cur
                if k not in pmax_by_k or better(cur, pmax_by_k[k]):
                    pmax_by_k[k] = cur
                if x and (pmax == (0, 1) or better(cur, pmax)):
                    pmax = cur
            else:
                cur = (x, D)
                if nmin is None or better(nmin, cur):
                    nmin = cur
                if nmax is None or better(cur, nmax):
                    nmax = cur
        for i in range(A.size):
            if isP[i] and num[i] == pmax[0] and D == pmax[1]:
                pmax_all.append((num[i], D, int(A[i]), k, int(MR[k][i])))

    seen: set[int] = set()
    rows: list[dict] = []
    for numv, dv, occ, k, mr in sorted(pmax_all,
                                       key=lambda t: -Fraction(t[0], t[1])):
        if occ in seen:
            continue
        seen.add(occ)
        kids: list[tuple] = []
        if k + 1 < len(levels):
            N, Dk, ANk = levels[k + 1], DS[k + 1], AN[k + 1]
            # legal mask of `occ` itself: it lives in level k, not level k+1
            lm = int(res["lms"][k][int(np.searchsorted(levels[k], ctx.dt(occ)))])
            for j in range(V):
                if (lm >> j) & 1:
                    c = occ | (1 << j)
                    p = int(np.searchsorted(N, ctx.dt(c)))
                    kids.append((Fraction(ANk[p], Dk), frac_str(ANk[p], Dk)))
        kids.sort(key=lambda t: -t[0])
        kmean = (sum(f[0] for f in kids) / len(kids)) if kids else None
        rows.append({"occ": occ, "k": k, "g": 0,
                     "p_rand": frac_str(numv, dv),
                     "p_rand_dec": dec_str(numv, dv),
                     "L": len(kids), "max_rem": mr,
                     "child_p_rand_sorted": [f[1] for f in kids],
                     "child_p_rand_mean_dec": (dec_str(kmean.numerator,
                                                       kmean.denominator)
                                               if kmean else None),
                     "points": [[j % V, j // V] for j in range(V)
                                if (occ >> j) & 1]})
        if len(rows) >= top:
            break

    empt = {"g": int(G[0][0]), "p_rand": frac_str(AN[0][0], DS[0]),
            "p_rand_dec": dec_str(AN[0][0], DS[0]),
            "max_rem": int(MR[0][0]), "L": ctx.V}
    return {
        "n": ctx.n, "V": V, "F": ctx.F,
        "n_safe_subsets": int(sum(l.size for l in levels)),
        "level_sizes": [int(l.size) for l in levels],
        "max_safe_size": len(levels) - 1,
        "edge_total": res["edge_total"],
        "per_level_denominator_digits": [len(str(d)) for d in DS],
        "n_P": n_P, "n_N": n_N, "n_P_by_level": n_P_by_k,
        "empty": empt,
        "P_max": frac_str(pmax[0], pmax[1]),
        "P_max_dec": dec_str(pmax[0], pmax[1]),
        "P_max_level": next((k for k in range(len(levels)) if DS[k] == pmax[1]),
                            None),
        "P_max_n_attaining": len(pmax_all),
        "P_gt_1_2": gt_half, "P_gt_2_3": over23, "P_gt_3_4": over34,
        "P_max_by_maxrem": {str(h): frac_str(v[0], v[1])
                            for h, v in sorted(pmax_by_h.items())},
        "P_max_by_level": {str(k): frac_str(v[0], v[1])
                           for k, v in sorted(pmax_by_k.items())},
        "N_min": frac_str(nmin[0], nmin[1]) if nmin else None,
        "N_max": frac_str(nmax[0], nmax[1]) if nmax else None,
        "top": rows,
    }


# -------------------------------------------------------------- self-check
def selfcheck(n: int = 4, trials: int = 2000) -> dict:
    """Cross-check the level-0 chain against kyouen_core.Board.legal_moves.

    For every state of a random sample of levels, the mask this script computed
    (the O(F) quad pass, as in round3_b501_pgrand_n5.py) is compared with
    Board.legal_moves, an independent slow implementation that tests every
    candidate move against every quad through that point.
    """
    ctx = Ctx(n)
    levels, lms = enumerate_levels(ctx, np.array([0], dtype=ctx.dt))
    rng = np.random.default_rng(12345)
    bad = 0
    checked = 0
    for k, A in enumerate(levels):
        m = min(int(A.size), max(1, trials // max(1, len(levels))))
        if m == 0:
            continue
        idx = rng.permutation(A.size)[:m]
        Aa = A[idx]
        mine = lms[k][idx]
        ref = np.array([sum(1 << j for j in ctx.board.legal_moves(int(a)))
                        for a in Aa.tolist()], dtype=ctx.dt)
        bad += int((mine != ref).sum())
        checked += int(Aa.size)
    return {"n": n, "n_states": int(sum(int(l.size) for l in levels)),
            "levels": len(levels), "sampled": checked, "mismatches": bad}


# -------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="4,5,6")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    data = {
        "definition":
            "p_rand(terminal)=0; p_rand(S)=(1/|L|)*sum_{u in L}(1-p_rand(S+u)); "
            "L = legal moves, uniform over them (identical to round2_b501_rand.py "
            "and round3_b501_pgrand_n5.py)",
        "population": "ALL safe subsets reachable from the empty board "
                      "(exact enumeration, not sampled)",
        "arithmetic": "exact rationals; per-level common denominator with "
                      "arbitrary-precision integers; no floating point in the DP",
        "method_note":
            "n=5 method (per-level common denominator, arbitrary-precision ints) "
            "with np.bitwise_count popcounts, uint64 masks and one cached "
            "per-level legal-move mask; the O(F) quad pass is retained because "
            "the legal mask is NOT monotone along an edge",
        "log": list(_LOG),
    }
    if args.selfcheck:
        data["selfcheck"] = {str(n): selfcheck(n) for n in (4, 5)}
    for n in [int(x) for x in args.sizes.split(",") if x]:
        ctx = Ctx(n)
        levels, lms = enumerate_levels(ctx, np.array([0], dtype=ctx.dt))
        log(f"[n={n}] safe subsets = {sum(int(l.size) for l in levels)} "
            f"levels={[int(l.size) for l in levels]} ({ctx.t_enum:.2f}s)")
        data.setdefault("timings", {})[f"n{n}_enumerate"] = round(ctx.t_enum, 2)
        res = solve_levels(ctx, levels, lms)
        out = analyse(ctx, res)
        out["timing_s"] = {"build": ctx.build_s, "enumerate": round(ctx.t_enum, 2),
                           "grundy": round(ctx.t_g, 2),
                           "prand": round(ctx.t_p, 2),
                           "total": round(ctx.t_solve + ctx.t_enum, 2)}
        log(f"[n={n}] edges={res['edge_total']} P={out['n_P']} N={out['n_N']} "
            f"P_max={out['P_max_dec']} >2/3:{out['P_gt_2_3']} "
            f">3/4:{out['P_gt_3_4']} {out['timing_s']}")
        data[f"n{n}"] = out
        data["log"] = list(_LOG)
        Path(args.out).write_text(json.dumps(data, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
    data["log"] = list(_LOG)
    Path(args.out).write_text(json.dumps(data, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    log("wrote", args.out)


if __name__ == "__main__":
    main()

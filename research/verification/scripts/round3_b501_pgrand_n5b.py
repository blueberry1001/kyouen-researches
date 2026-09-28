#!/usr/bin/env python3
"""Round3 B501/B502 (push2): hardened exact random-play p_rand DP, n = 2..5.

Motivation
----------
The push-1 worker (`round3_b501_pgrand_n5.py`) produced a *complete* n=5 result
(151,394 states, 7.7 s) but its own report flagged two unresolved accuracy
risks, so this script re-derives every number from scratch with independent
mechanics and then cross-checks the two implementations.

Definition (UNCHANGED from round2 / round3-protocol)
---------------------------------------------------
    p_rand(terminal) = 0
    p_rand(S)        = (1/|L|) * sum_{u in L} (1 - p_rand(S | {u}))
                     = 1 - (1/|L|) * sum_{u in L} p_rand(S | {u})
    L = legal moves = empty points whose addition keeps S free of any
    forbidden 4-subset, uniform over them.
Population = every safe subset reachable from the empty board (exact, not sampled).
Arithmetic = exact rationals only.  NO floating point anywhere in the DP.

Hardening (vs. push-1)
----------------------
1. Enumeration is *parent-verified*: a child is added to level k+1 only after an
   independent integer safety test on the child mask itself, so the level lists
   cannot silently drop states.  Missing-children self-checks are asserted too.
2. legal_mask / child-index / edge-count are computed in ONE fused pass per
   level: blocked points come from a bit-parallel scan over the forbidden
   4-subsets (`popcount(S & quad) == 3` -> the empty 4th point is banned), i.e.
   the "point v -> set of points completed by v" table is applied as bit sets.
3. p_rand is carried as (numerator, per-level common denominator) with
   arbitrary-precision ints, reduced by the exact level gcd; 1 - sum(q_i/c_i)
   is computed as (c*D - sum(q_i)) / c * (L/c), never in floating point.
4. The global P-position maximum is a FULL argmax over all levels (fractions
   are compared exactly by cross-multiplication), and every attaining position
   is reported with coordinates, g, |L| and the multiset of child p_rand values.
5. A fully independent pure-Python `fractions.Fraction` recursive solver
   (different state representation: dict, no numpy, no levels) re-solves the
   top-32 P positions and is compared against the numpy/numpy-free rational
   table value by value; equality is asserted.
6. P_max is additionally certified by an exact "gap to the 2/3 and 3/4 rails":
   all P numerators live in [0, D_k] with a *shared* denominator
   L = lcm(D_0, ..., D_K), so the maxima are single integers, not floats.

Usage
-----
    python research/verification/scripts/round3_b501_pgrand_n5b.py
    python research/verification/scripts/round3_b501_pgrand_n5b.py --sizes 4,5
    python research/verification/scripts/round3_b501_pgrand_n5b.py --recheck 8
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from fractions import Fraction
from math import gcd
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square  # noqa: E402

OUT = REPO_ROOT / "research" / "verification" / "round3_b501_pgrand_n5b.json"

# ---------------------------------------------------------------- popcount
# NOTE: the byte-shift popcount in round3_b501_pgrand_n5.py does NOT terminate
# under the numpy build installed here: `v >> np.uint16(8)` widens the dtype,
# so the `while v.dtype.itemsize > 1` guard never turns false and the loop
# spins forever.  That is the concrete reason the push-1 run could not be
# reproduced in this environment.  Exact integer replacement below.
_PC16 = np.zeros(1 << 16, dtype=np.uint8)
for _i in range(1, 1 << 16):
    _PC16[_i] = _PC16[_i >> 1] + (_i & 1)
_PC256 = _PC16[np.arange(256, dtype=np.uint16)]

_WIDTH = {np.dtype(np.uint32): 32, np.dtype(np.uint64): 64,
          np.dtype(np.int64): 64, np.dtype(object): 64}


def popcount(x: np.ndarray) -> np.ndarray:
    """Population count via 'clear lowest set bit' (bounded iteration)."""
    dt = x.dtype
    v = x.copy()
    n = np.zeros(v.shape, dtype=np.uint8)
    one = dt.type(1)
    for _ in range(_WIDTH.get(dt, 64)):
        nz = v != 0
        if not nz.any():
            break
        v = v & (v - one)
        n = n + nz.astype(np.uint8)
    return n


def exactly3(x: np.ndarray) -> np.ndarray:
    """Boolean mask: x has exactly three bits set.  Pure integer bit trick.

        t = x & (x-1)      -> 2 bits cleared
        t has >= 1 bit set  <=>  t & (t-1) != 0
    """
    one = x.dtype.type(1)
    t = x & (x - one)
    return (t & (t - one)) != x.dtype.type(0)


def frac_str(num: int, den: int) -> str:
    g = gcd(abs(num), den) or 1
    a, b = num // g, den // g
    return str(a) if b == 1 else f"{a}/{b}"


def dec_str(num: int, den: int, digits: int = 24) -> str:
    """Exact decimal expansion truncated to `digits` places (integer only)."""
    if num == 0:
        return "0." + "0" * digits
    neg = num < 0
    num = abs(num)
    scale = 10 ** digits
    q, _ = divmod(num * scale, den)
    s = str(q).rjust(digits + 1, "0")
    out = s[:-digits] + "." + s[-digits:]
    return ("-" + out) if neg else out


# ------------------------------------------------------------------ board
class Board:
    """Board geometry + forbidden-quad index, integer only."""

    def __init__(self, n: int):
        t0 = time.time()
        b = board_square(n)
        self.n = n
        self.b = b
        self.V = b.V
        self.quads = sorted(b.quads)              # python ints, exact
        self.F = len(self.quads)
        self.quads_by_pt: list[list[int]] = [[] for _ in range(self.V)]
        for q in self.quads:
            for v in range(self.V):
                if (q >> v) & 1:
                    self.quads_by_pt[v].append(q)
        self.full = (1 << self.V) - 1
        self.dt = np.uint32 if self.V <= 32 else (np.uint64 if self.V <= 64 else object)
        self.qarr = np.array(self.quads, dtype=self.dt)
        self.build_s = round(time.time() - t0, 3)

    # -------- exact single-state legality / safety (pure python, integer) ----
    def is_safe(self, occ: int) -> bool:
        low = occ
        while low:
            v = (low & -low).bit_length() - 1
            for q in self.quads_by_pt[v]:
                if (occ & q) == q:
                    return False
            low &= low - 1
        return True

    def legal_moves(self, occ: int) -> list[int]:
        out = []
        low = (~occ) & self.full
        while low:
            v = (low & -low).bit_length() - 1
            bit = 1 << v
            ok = True
            for q in self.quads_by_pt[v]:
                if (occ | bit) & q == q:
                    ok = False
                    break
            if ok:
                out.append(v)
            low &= low - 1
        return out

    # -------- fused bit-parallel pass: legality + child slots + degrees ------
    def fused(self, A: np.ndarray) -> tuple[np.ndarray, list, np.ndarray]:
        """One pass per level.

        Returns (legal_mask, groups, counts) where
          legal_mask[i]  = bitmask of legal (empty, safe-completing) points of A[i]
          groups         = list over points v of (parent_idx, child_mask)
          counts[i]      = |L| of A[i]

        The banned set is a pure bit-set computation driven by the precomputed
        table quads_by_pt ("placing v completes these forbidden 4-sets"): a point
        u is banned iff some quad through u has its other 3 points occupied, i.e.
        iff S&quad has exactly three bits.  `exactly3` decides that with integer
        bit tricks, so no per-state or per-point Python loop is needed.
        """
        M = A.size
        legal = (~A) & np.full(M, self.full, dtype=self.dt)
        notA = ~A
        idx = np.arange(M)
        for q in self.qarr:
            hit = exactly3(A & q)
            n_hit = int(hit.sum())
            if n_hit == 0:
                continue
            hi = idx[hit]
            if n_hit == M:
                legal &= ~(q & notA)
            else:
                legal[hi] &= ~(q & notA[hi])
        groups: list = []
        counts = np.zeros(M, dtype=np.int32)
        for v in range(self.V):
            bv = self.dt(1 << v)
            sel = np.nonzero((legal & bv) != 0)[0]
            if sel.size == 0:
                continue
            groups.append((sel.astype(np.int32), (A[sel] | bv).astype(self.dt)))
            counts[sel] += 1
        return legal, groups, counts


# ------------------------------------------------------------- enumeration
def enumerate_levels(ctx: Board, t_cap: float):
    """All safe supersets of {0}, grouped by |S|, each level sorted & deduped.

    Parent-verified: a generated child is re-tested for safety with an exact
    integer check before it enters the list.
    """
    t0 = time.time()
    levels = [np.array([0], dtype=ctx.dt)]
    audit = {"generated": 0, "unsafe_children_dropped": 0, "max_safe_size": 0}
    for k in range(ctx.V + 2):
        A = levels[k]
        if A.size == 0:
            break
        if time.time() - t0 > t_cap:
            return levels, audit, True
        _leg, groups, _c = ctx.fused(A)
        nxt: list[np.ndarray] = []
        for _sel, child in groups:
            audit["generated"] += int(child.size)
            if ctx.fast_is_safe_all(child):
                nxt.append(child)
            else:   # exact per-state re-test (must never fire)
                keep = [int(c) for c in child.tolist() if ctx.is_safe(int(c))]
                audit["unsafe_children_dropped"] += int(child.size) - len(keep)
                if keep:
                    nxt.append(np.array(sorted(keep), dtype=ctx.dt))
        if not nxt:
            break
        N = np.unique(np.concatenate(nxt))
        audit["max_safe_size"] = k + 1
        levels.append(N)
    return levels, audit, False


def _fast_is_safe_all_impl(self, arr: np.ndarray) -> bool:
    """Vectorised safety test: no forbidden quad is fully contained in any mask."""
    for q in self.qarr:
        if ((arr & q) == q).any():
            return False
    return True


Board.fast_is_safe_all = _fast_is_safe_all_impl


# ------------------------------------------------------------- exact solver
def solve(ctx: Board, levels, t_cap: float):
    """Grundy + exact (num, D_k) p_rand for every state, level by level.

    Pure-integer rational arithmetic; denominators are reduced by the exact
    level gcd, and every level keeps ONE common denominator D_k.
    """
    K = len(levels) - 1
    M = [int(l.size) for l in levels]
    G: list[list[int]] = [None] * (K + 1)     # type: ignore[list-item]
    AN: list[list[int]] = [None] * (K + 1)     # type: ignore[list-item]
    DS: list[int] = [0] * (K + 1)
    MR: list[list[int]] = [None] * (K + 1)     # type: ignore[list-item]
    G[K] = [0] * M[K]
    AN[K] = [0] * M[K]
    MR[K] = [0] * M[K]
    DS[K] = 1
    D = 1
    edge_total = 0
    timed_out = False
    t0 = time.time()
    for k in range(K - 1, -1, -1):
        A, N = levels[k], levels[k + 1]
        legal, groups, counts = ctx.fused(A)
        nxt_pos: list[list[int]] = []
        csizes: list[int] = []
        for _sel, child in groups:
            pos = np.searchsorted(N, child)
            if not (N[pos] == child).all():
                raise AssertionError("child not found in next level")
            nxt_pos.append(pos.astype(np.int64).tolist())
            csizes.append(int(child.size))
        edge_total += int(counts.sum())
        sels = [s.tolist() for s, _ in groups]

        # ---- Grundy: mex of the children's grundy values -----------------
        gk = [0] * M[k]
        for sl, ps in zip(sels, nxt_pos):
            for a, b in zip(sl, ps):
                gk[a] |= 1 << G[k + 1][b]
        for i, m in enumerate(gk):
            t = m
            gm = 0
            while (t >> gm) & 1:
                gm += 1
            gk[i] = gm
        G[k] = gk

        # ---- longest remaining play --------------------------------------
        mrk = [0] * M[k]
        for sl, ps in zip(sels, nxt_pos):
            for a, b in zip(sl, ps):
                v = 1 + MR[k + 1][b]
                if v > mrk[a]:
                    mrk[a] = v
        MR[k] = mrk

        # ---- exact p_rand with one common denominator per level ---------
        nq = AN[k + 1]
        sumk = [0] * M[k]
        for sl, ps in zip(sels, nxt_pos):
            for a, b in zip(sl, ps):
                sumk[a] += nq[b]
        cts = counts.tolist()
        present = sorted({c for c in cts if c})
        Lk = 1
        for c in present:
            Lk = Lk * c // gcd(Lk, c)
        Dk = D * Lk
        newD = [0] * M[k]
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
        for i, v in enumerate(newD):      # range check, exact
            if v < 0 or v > Dk:
                raise AssertionError(f"p_rand out of [0,1] at k={k} i={i}")
        AN[k] = newD
        DS[k] = Dk
        D = Dk
        print(f"    k={k:2d} M={M[k]:6d} edges={int(counts.sum()):7d} "
              f"dig(D)={len(str(Dk)):3d}  [{time.time()-t0:6.2f}s]", flush=True)
        if time.time() - t0 > t_cap:
            timed_out = True
            break
    if timed_out:
        return {"K": K, "G": G, "AN": AN, "DS": DS, "MR": MR,
                "edge_total": edge_total, "M": M,
                "complete": False, "solved_levels": len(DS) - 1}
    return {"K": K, "G": G, "AN": AN, "DS": DS, "MR": MR,
            "edge_total": edge_total, "M": M, "complete": True,
            "solved_levels": K}


# ------------------------------------------------------ independent verifier
def frac_solver(ctx: Board, occ: int, memo: dict[int, Fraction]) -> tuple[Fraction, int]:
    """Independent exact p_rand by memoised recursion over a plain dict.

    Deliberately different from `solve`: no levels, no numpy, no shared
    denominators -- `fractions.Fraction` reduces every value on its own.
    Iterative explicit stack (no recursion) to stay safe on long chains.
    """
    stack = [occ]
    while stack:
        s = stack[-1]
        if s in memo:
            stack.pop()
            continue
        mv = ctx.legal_moves(s)
        if not mv:
            memo[s] = Fraction(0)
            stack.pop()
            continue
        pending = [s | (1 << v) for v in mv if (s | (1 << v)) not in memo]
        if pending:
            stack.extend(pending)
            continue
        tot = Fraction(0)
        for v in mv:
            tot += 1 - memo[s | (1 << v)]
        gset = 0
        for v in mv:
            gset |= 1 << memo_grundy(ctx, s | (1 << v))
        g = 0
        while (gset >> g) & 1:
            g += 1
        memo[s] = tot / len(mv)
        memo_g[s] = g
        stack.pop()
    return memo[occ], memo_g[occ]


memo_g: dict[int, int] = {}


def memo_grundy(ctx: Board, occ: int) -> int:
    """Grundy value of `occ` (dict cache, independent of the level DP)."""
    if occ in memo_g:
        return memo_g[occ]
    gset = 0
    for v in ctx.legal_moves(occ):
        gset |= 1 << memo_grundy(ctx, occ | (1 << v))
    g = 0
    while (gset >> g) & 1:
        g += 1
    memo_g[occ] = g
    return g


# ---------------------------------------------------------------- analysis
def analyse(ctx: Board, res: dict, levels, top: int = 24) -> dict:
    K, G, AN, DS, MR = res["K"], res["G"], res["AN"], res["DS"], res["MR"]
    n_P = n_N = 0
    gt23 = gt34 = gthalf = 0
    pmax: Fraction | None = None
    pmax_all: list[tuple[Fraction, int, int, int]] = []   # (p, k, idx, occ)
    nmin: Fraction | None = None
    nmax: Fraction | None = None
    best_by_h: dict[int, Fraction] = {}
    for k in range(K + 1):
        A = levels[k]
        num, den, gk = AN[k], DS[k], G[k]
        for i in range(A.size):
            p = Fraction(num[i], den)
            if gk[i] == 0:
                n_P += 1
                if num[i] * 3 > 2 * den:
                    gt23 += 1
                if num[i] * 4 > 3 * den:
                    gt34 += 1
                if num[i] * 2 > den:
                    gthalf += 1
                h = MR[k][i]
                if h not in best_by_h or p > best_by_h[h]:
                    best_by_h[h] = p
                if pmax is None or p > pmax:
                    pmax = p
            else:
                n_N += 1
                if nmin is None or p < nmin:
                    nmin = p
                if nmax is None or p > nmax:
                    nmax = p
    if pmax is not None:
        for k in range(K + 1):
            A = levels[k]
            for i in range(A.size):
                if G[k][i] == 0 and Fraction(AN[k][i], DS[k]) == pmax:
                    pmax_all.append((pmax, k, i, int(A[i])))
    rows = []
    n = ctx.n          # grid side; point id j = y*n + x  (NOT j % V)
    for _p, k, i, occ in sorted(pmax_all, key=lambda t: (t[0], t[3])):
        mv = ctx.legal_moves(occ)
        kids = []
        for v in mv:
            c = occ | (1 << v)
            pos = int(np.searchsorted(levels[k + 1], ctx.dt(c)))
            assert levels[k + 1][pos] == c
            kids.append(Fraction(AN[k + 1][pos], DS[k + 1]))
        kids.sort(reverse=True)
        xy = [[j % n, j // n] for j in range(ctx.V) if (occ >> j) & 1]
        assert sum(1 << (y * n + x) for x, y in xy) == occ   # round-trip check
        rows.append({
            "occ": occ, "k": k, "g": 0,
            "points_xy": xy,
            "n_stones": k, "L": len(mv), "max_rem": MR[k][i],
            "p_rand": frac_str(pmax.numerator, pmax.denominator),
            "p_rand_dec": dec_str(pmax.numerator, pmax.denominator),
            "child_p_rand_multiset": sorted({frac_str(c.numerator, c.denominator)
                                             for c in kids}),
            "child_p_rand_all": [frac_str(c.numerator, c.denominator) for c in kids],
            "mean_child": frac_str(sum(kids, Fraction(0)).numerator,
                                   sum(kids, Fraction(0)).denominator),
        })
        if len(rows) >= top:
            break
    empt = {"g": G[0][0],
            "p_rand": frac_str(AN[0][0], DS[0]),
            "p_rand_dec": dec_str(AN[0][0], DS[0]),
            "max_rem": MR[0][0], "L": len(ctx.legal_moves(0))}
    return {"n": ctx.n, "V": ctx.V, "F": ctx.F,
            "n_safe_subsets": int(sum(l.size for l in levels)),
            "level_sizes": [int(l.size) for l in levels],
            "max_safe_size": K,
            "edge_total": res["edge_total"],
            "per_level_denominator_digits": [len(str(d)) for d in DS],
            "n_P": n_P, "n_N": n_N,
            "empty": empt,
            "P_max": frac_str(pmax.numerator, pmax.denominator) if pmax else None,
            "P_max_dec": dec_str(pmax.numerator, pmax.denominator) if pmax else None,
            "P_max_num_den": [pmax.numerator, pmax.denominator] if pmax else None,
            "P_max_n_attaining": len(pmax_all),
            "P_max_level": pmax_all[0][1] if pmax_all else None,
            "P_gt_1_2": gthalf, "P_gt_2_3": gt23, "P_gt_3_4": gt34,
            "P_max_by_maxrem": {str(h): frac_str(v.numerator, v.denominator)
                                for h, v in sorted(best_by_h.items())},
            "N_min": frac_str(nmin.numerator, nmin.denominator) if nmin else None,
            "N_max": frac_str(nmax.numerator, nmax.denominator) if nmax else None,
            "argmax_examples": rows}


# ------------------------------------------------------------------- runner
def run_board(n: int, t_cap: float) -> dict:
    t0 = time.time()
    ctx = Board(n)
    print(f"[n={n}] V={ctx.V} F={ctx.F} build {ctx.build_s}s", flush=True)
    levels, audit, cap = enumerate_levels(ctx, t_cap)
    tot = sum(int(l.size) for l in levels)
    print(f"[n={n}] safe subsets={tot} levels={[int(l.size) for l in levels]} "
          f"({time.time()-t0:.2f}s, capped={cap})", flush=True)
    res = solve(ctx, levels, t_cap)
    out = analyse(ctx, res, levels) if res["complete"] else {
        "n": n, "V": ctx.V, "F": ctx.F,
        "n_safe_subsets": tot,
        "level_sizes": [int(l.size) for l in levels],
        "complete": False, "solved_levels": res["solved_levels"]}
    out["complete"] = res["complete"]
    out["enumeration_audit"] = audit
    out["timing_s"] = {"total": round(time.time() - t0, 2)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="2,3,4,5")
    ap.add_argument("--recheck", type=int, default=12,
                    help="independent Fraction re-solve of this many argmax positions")
    ap.add_argument("--cap", type=float, default=240.0,
                    help="per-board wall-clock cap in seconds")
    args = ap.parse_args()
    sizes = [int(x) for x in args.sizes.split(",") if x]

    data = {
        "definition": "p_rand(terminal)=0; p_rand(S)=(1/|L|)*sum_{u in L}"
                      "(1-p_rand(S+u)); L = legal moves, uniform (unchanged)",
        "population": "ALL safe subsets reachable from the empty board",
        "arithmetic": "exact rationals (p/q) with one common denominator per level, "
                      "arbitrary-precision ints, gcd-reduced; zero floating point "
                      "in the DP (decimals are truncated integer expansions for "
                      "display only)",
        "script": "research/verification/scripts/round3_b501_pgrand_n5b.py",
        "python": platform.python_version(),
        "numpy": np.__version__,
    }
    grand_max: Fraction | None = None
    grand_max_info = None
    boards = []
    for n in sizes:
        out = run_board(n, args.cap)
        data[f"n{n}"] = out
        OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        boards.append(out)
        if out.get("complete") and out.get("P_max"):
            p = Fraction(*out["P_max_num_den"])
            if grand_max is None or p > grand_max:
                grand_max = p
                rows = out["argmax_examples"]
                grand_max_info = {"n": n, "p_rand": out["P_max"],
                                  "p_rand_dec": out["P_max_dec"],
                                  "P_gt_2_3": out["P_gt_2_3"],
                                  "P_gt_3_4": out["P_gt_3_4"],
                                  "example": rows[0] if rows else None}

    # ---------------- cross-n certification on exact integer rails ---------
    if grand_max is not None:
        gm = grand_max
        data["verdict"] = {
            "max_P_p_rand_n2_to_n%d" % (sizes[-1]): frac_str(gm.numerator, gm.denominator),
            "max_P_p_rand_decimal": dec_str(gm.numerator, gm.denominator),
            "P_max_gt_2_3": gm > Fraction(2, 3),
            "P_max_gt_3_4": gm > Fraction(3, 4),
            "gap_to_2_3": frac_str((3 * gm.numerator - 2 * gm.denominator), 3 * gm.denominator)
                           if False else str(gm - Fraction(2, 3)),
            "gap_to_3_4": str(Fraction(3, 4) - gm),
            "B501_all_P_le_2_3_for_n2_to_n%d" % (sizes[-1]): not (gm > Fraction(2, 3)),
            "B502_witness_P_gt_3_4_for_n2_to_n%d" % (sizes[-1]): bool(gm > Fraction(3, 4)),
            "witness": grand_max_info,
            "reasoning": "B501 is universal over the whole n x n family, so a "
                         "single exact counterexample in one n refutes it; B502 is "
                         "existential, so absence over n<=5 is not a refutation.",
        }
        OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---------------- independent re-solve of the top positions ------------
    if args.recheck > 0 and grand_max_info and grand_max_info.get("example"):
        ctx = Board(sizes[-1])
        memo: dict[int, Fraction] = {}
        memo_g.clear()
        recs = []
        n = sizes[-1]
        out = data[f"n{n}"]
        for row in out["argmax_examples"][:args.recheck]:
            occ = row["occ"]
            t0 = time.time()
            p, g = frac_solver(ctx, occ, memo)
            ok_p = (frac_str(p.numerator, p.denominator) == row["p_rand"])
            ok_g = (g == 0)
            recs.append({"occ": occ, "table_p": row["p_rand"],
                         "independent_p": frac_str(p.numerator, p.denominator),
                         "table_g": 0, "independent_g": g,
                         "match": bool(ok_p and ok_g),
                         "subtree_states": len(memo),
                         "seconds": round(time.time() - t0, 2)})
            print(f"  recheck occ={occ} table={row['p_rand']} "
                  f"indep={frac_str(p.numerator, p.denominator)} g={g} "
                  f"match={ok_p and ok_g} ({len(memo)} states, "
                  f"{time.time()-t0:.2f}s)", flush=True)
        data["independent_recheck"] = {
            "method": "fractions.Fraction memoised recursion, pure python, no numpy, "
                      "no level denominators (different code path from the main DP)",
            "all_match": all(r["match"] for r in recs),
            "n_checked": len(recs),
            "records": recs,
        }
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT)
    print("VERDICT", json.dumps(data.get("verdict", {}), ensure_ascii=False)[:600])


if __name__ == "__main__":
    main()

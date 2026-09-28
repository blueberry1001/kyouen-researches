#!/usr/bin/env python3
"""Round3 B501/B502: exact random-play win rate p_rand on standard boards.

Same definition as round2 (research/verification/scripts/round2_b501_rand.py):

    p_rand(terminal) = 0
    p_rand(S)        = (1/|L|) * sum_{u in L} (1 - p_rand(S | {u}))
                     = 1 - (1/|L|) * sum_{u in L} p_rand(S | {u})

L = set of legal moves (empty points that keep S safe), uniform over them.
Population: ALL safe subsets reachable from the empty board (exact, not sampled).

Method
  * level-by-level enumeration of every safe subset (uint32 masks, numpy)
  * per-level `blocked` pass: for every state at once, the bitmask of empty
    points that would complete a forbidden quad (bit parallel over states)
  * edges level k -> level k+1 found by searchsorted into the sorted next
    level; no hashing, no recursion
  * p_rand carried as EXACT rationals: per-level common denominator D_k with
    integer numerators, reduced by the level gcd at every step
    (D grows past 2^63 for n=5, so arbitrary-precision ints are mandatory)
  * Grundy by the same level loop (OR of 2^g over children, then mex)
  * optional n=6 random-play sampling of reachable safe sets

Usage
    python research/verification/scripts/round3_b501_pgrand_n5.py
    python research/verification/scripts/round3_b501_pgrand_n5.py --sizes 4,5
    python research/verification/scripts/round3_b501_pgrand_n5.py --sizes 5 --n6 40
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import random
import sys
import time
from fractions import Fraction
from math import gcd
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square  # noqa: E402

OUT = REPO_ROOT / "research" / "verification" / "round3_b501_pgrand_n5.json"

_PC16 = np.zeros(1 << 16, dtype=np.uint8)
for _i in range(1, 1 << 16):
    _PC16[_i] = _PC16[_i >> 1] + (_i & 1)
_PC256 = _PC16[np.arange(256, dtype=np.uint16)]


def popcount(x: np.ndarray) -> np.ndarray:
    """Population count of an unsigned integer array (any width)."""
    v = x
    acc = np.zeros(v.shape, dtype=np.uint16)
    while v.dtype.itemsize > 1:
        acc = acc + _PC256[(v & np.uint16(0xFF)).astype(np.uint16)]
        v = v >> np.uint16(8)
    return acc + _PC16[v]


def frac_str(num: int, den: int) -> str:
    g = gcd(num, den) or 1
    a, b = num // g, den // g
    return f"{a}/{b}" if b != 1 else str(a)


def dec_str(num: int, den: int, digits: int = 20) -> str:
    """Exact decimal expansion truncated to `digits` places (integer only)."""
    if num == 0:
        return "0." + "0" * digits
    neg = num < 0
    num = abs(num)
    scale = 10 ** digits
    q, r = divmod(num * scale, den)
    s = str(q).rjust(digits + 1, "0")
    out = s[:-digits] + "." + s[-digits:]
    if neg:
        out = "-" + out
    return out


# ----------------------------------------------------------------- context
class Ctx:
    """Board-level precomputation shared by all levels."""

    def __init__(self, n: int):
        t0 = time.time()
        self.board = board_square(n)
        self.n = n
        self.V = self.board.V
        self.F = len(self.board.quads)
        # n<=5 needs 25 bits; n=6 needs 36 -> wider masks
        self.dt = np.uint32 if self.V <= 32 else (np.uint64 if self.V <= 64
                                                  else object)
        self.quads = np.array(sorted(self.board.quads), dtype=self.dt)
        self.FULL = self.dt((1 << self.V) - 1)
        self.build_s = round(time.time() - t0, 3)
        self.t_enum = 0.0
        self.t_edge = 0.0
        self.t_p = 0.0
        self.t_g = 0.0

    def blocked_pass(self, A: np.ndarray) -> np.ndarray:
        """blocked[i] = bitmask of EMPTY points that would complete a quad."""
        out = np.zeros(A.size, dtype=self.dt)
        notA = ~A
        for q in self.quads:
            sel = popcount(A & q) == 3
            if sel.any():
                out[sel] |= (q & notA[sel]).astype(self.dt)
        return out

    def legal_mask(self, A: np.ndarray) -> np.ndarray:
        return (~A) & (~self.blocked_pass(A)) & self.FULL

    def legal_moves_one(self, occ: int) -> list[int]:
        lm = self.legal_mask(np.array([occ], dtype=self.dt))
        m = int(lm[0])
        return [j for j in range(self.V) if (m >> j) & 1]


# ------------------------------------------------------------- enumeration
def enumerate_levels(ctx: Ctx, start) -> list[np.ndarray]:
    """All safe supersets of `start`, grouped by |S|; each level sorted."""
    t0 = time.time()
    levels = [np.unique(np.asarray(start, dtype=ctx.dt))]
    V, dt = ctx.V, ctx.dt
    for _ in range(ctx.V + 2):
        A = levels[-1]
        legal = ctx.legal_mask(A)
        nxt = []
        for v in range(V):
            sel = np.nonzero((legal & dt(1 << v)) != 0)[0]
            if sel.size:
                nxt.append(A[sel] | dt(1 << v))
        if not nxt:
            break
        levels.append(np.unique(np.concatenate(nxt)))
    ctx.t_enum += time.time() - t0
    return levels


def level_edges(ctx: Ctx, A: np.ndarray, N: np.ndarray):
    """groups_np = [(parent idx, child idx in level k+1), ...]; counts, flat lists."""
    t0 = time.time()
    legal = ctx.legal_mask(A)
    groups_np, groups_py = [], []
    counts = np.zeros(A.size, dtype=np.int32)
    for v in range(ctx.V):
        sel = np.nonzero((legal & ctx.dt(1 << v)) != 0)[0]
        if sel.size == 0:
            continue
        child = A[sel] | ctx.dt(1 << v)
        pos = np.searchsorted(N, child)
        if not (N[pos] == child).all():          # must never fire
            raise AssertionError("searchsorted index mismatch")
        groups_np.append((sel.astype(np.int64), pos.astype(np.int64)))
        groups_py.append((sel.tolist(), pos.tolist()))
        counts[sel] += 1
    ctx.t_edge += time.time() - t0
    return groups_np, groups_py, counts


# ------------------------------------------------------------- exact solver
def solve_levels(ctx: Ctx, levels: list[np.ndarray], verbose: bool = True):
    """Grundy + exact (num, den) p_rand + max-rem for every state."""
    K = len(levels) - 1
    G: list[np.ndarray] = [None] * (K + 1)
    AN: list[list[int]] = [None] * (K + 1)
    DS: list[int] = [0] * (K + 1)
    MR: list[np.ndarray] = [None] * (K + 1)
    D = 1
    g = np.zeros(levels[K].size, dtype=np.int8)
    mr = np.zeros(levels[K].size, dtype=np.int32)
    G[K], AN[K], MR[K], DS[K] = g, [0] * levels[K].size, mr, 1
    edge_total = 0
    for k in range(K - 1, -1, -1):
        A, N = levels[k], levels[k + 1]
        gn, gp, counts = level_edges(ctx, A, N)
        edge_total += int(counts.sum())
        M = A.size

        # ---- Grundy: bit-set OR of 2^g(child), then mex = log2(lowest 0) ----
        t0 = time.time()
        if gp:
            par = np.concatenate([s for s, _ in gn])
            cpos = np.concatenate([p for _, p in gn])
            cval = g[cpos].astype(np.int64)
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
        if M and lowzero.any():
            g[lowzero != 0] = np.log2(lowzero[lowzero != 0]
                                       .astype(np.float64)).astype(np.int8)
        ctx.t_g += time.time() - t0

        # ---- longest remaining play ----
        child_mr = MR[k + 1]
        newmr = np.zeros(M, dtype=np.int32)
        for sel, p in gn:
            newmr[sel] = np.maximum(newmr[sel], 1 + child_mr[p])
        mr = newmr

        # ---- exact p_rand, per-level common denominator ----
        t0 = time.time()
        nxtnum = AN[k + 1]
        sumk = [0] * M
        for sel_t, pos_t in gp:
            for a, b in zip(sel_t, pos_t):
                sumk[a] += nxtnum[b]
        cts = counts.tolist()
        present = sorted({c for c in cts if c})
        Lk = 1
        for c in present:
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
        D = Dk
        DS[k] = D
        ctx.t_p += time.time() - t0
        G[k], MR[k] = g, mr
        if verbose:
            print(f"    k={k} M={M} Lk={Lk} digits(D)={len(str(D))}", flush=True)

    return {"levels": levels, "G": G, "AN": AN, "D": D, "DS": DS, "MR": MR,
            "edge_total": edge_total}


def solve_quiet(ctx: Ctx, levels):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return solve_levels(ctx, levels, verbose=False)


# ----------------------------------------------------------------- analysis
def analyse(ctx: Ctx, res: dict, top: int = 10) -> dict:
    """All comparisons use exact integer cross-products x/D_k vs a/b."""
    levels, G, AN, MR, DS = (res["levels"], res["G"], res["AN"],
                             res["MR"], res["DS"])
    V, n = ctx.V, ctx.n
    n_P = n_N = 0
    over23 = over34 = gt_half = 0
    pmax = (0, 1)                 # best P value as an exact (num, den) pair
    pmax_all: list[tuple] = []    # (num, den, occ, k, max_rem)
    n_pr_gt_0 = 0
    pmax_by_h: dict[int, tuple] = {}
    nmin = nmax = None

    def better(a, b) -> bool:    # a > b for exact (num, den)
        return a[0] * b[1] > b[0] * a[1]

    for k, A in enumerate(levels):
        num = AN[k]
        D = DS[k]
        n_pr_gt_0 += sum(1 for x in num if x)
        isP = (G[k] == 0)
        nP = int(isP.sum())
        n_P += nP
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
            for j in ctx.legal_moves_one(occ):
                c = occ | (1 << j)
                pos = int(np.searchsorted(N, ctx.dt(c)))
                if N[pos] == c:
                    kids.append((Fraction(ANk[pos], Dk), frac_str(ANk[pos], Dk)))
        kids.sort(key=lambda t: -t[0])
        kmean = (sum(f[0] for f in kids) / len(kids)) if kids else None
        rows.append({"occ": occ, "k": k, "g": 0,
                     "p_rand": frac_str(numv, dv),
                     "p_rand_dec": dec_str(numv, dv),
                     "L": len(ctx.legal_moves_one(occ)), "max_rem": mr,
                     "child_p_rand_sorted": [f[1] for f in kids],
                     "child_p_rand_mean_dec": (dec_str(kmean.numerator,
                                                        kmean.denominator)
                                               if kmean else None),
                     "points": [[j % V, j // V] for j in range(V) if (occ >> j) & 1]})
        if len(rows) >= top:
            break
    empt = {"g": int(G[0][0]), "p_rand": frac_str(AN[0][0], DS[0]),
            "p_rand_dec": dec_str(AN[0][0], DS[0]),
            "max_rem": int(MR[0][0]), "L": len(ctx.legal_moves_one(0))}
    return {
        "n": n, "V": V, "F": ctx.F,
        "n_safe_subsets": int(sum(l.size for l in levels)),
        "level_sizes": [int(l.size) for l in levels],
        "max_safe_size": len(levels) - 1,
        "edge_total": res["edge_total"],
        "per_level_denominator_digits": [len(str(d)) for d in DS],
        "n_P": n_P, "n_N": n_N,
        "empty": empt,
        "P_max": frac_str(pmax[0], pmax[1]),
        "P_max_dec": dec_str(pmax[0], pmax[1]),
        "P_max_level": next((k for k in range(len(levels))
                             if DS[k] == pmax[1]), None),
        "P_max_n_attaining": len(pmax_all),
        "P_gt_1_2": gt_half,
        "P_gt_2_3": over23, "P_gt_3_4": over34,
        "P_max_by_maxrem": {str(h): frac_str(v[0], v[1])
                            for h, v in sorted(pmax_by_h.items())},
        "N_min": frac_str(nmin[0], nmin[1]) if nmin else None,
        "N_max": frac_str(nmax[0], nmax[1]) if nmax else None,
        "top": rows,
    }


def run_board(n: int) -> dict:
    t0 = time.time()
    ctx = Ctx(n)
    print(f"[n={n}] V={ctx.V} F={ctx.F} build {ctx.build_s}s", flush=True)
    levels = enumerate_levels(ctx, np.array([0], dtype=ctx.dt))
    print(f"[n={n}] safe subsets = {sum(int(l.size) for l in levels)} "
          f"levels={[int(l.size) for l in levels]} ({ctx.t_enum:.2f}s)", flush=True)
    res = solve_levels(ctx, levels)
    out = analyse(ctx, res)
    out["timing_s"] = {"build": ctx.build_s, "enumerate": round(ctx.t_enum, 2),
                       "edges": round(ctx.t_edge, 2), "grundy": round(ctx.t_g, 2),
                       "prand": round(ctx.t_p, 2), "total": round(time.time() - t0, 2)}
    print(f"[n={n}] edges={res['edge_total']} P={out['n_P']} N={out['n_N']} "
          f"P_max={out['P_max_dec']} >2/3:{out['P_gt_2_3']} >3/4:{out['P_gt_3_4']} "
          f"{out['timing_s']}", flush=True)
    return out


# -------------------------------------------------------------------- n = 6
def sample_n6(nsamples: int, seed: int, depths=(2, 3, 4, 5, 6, 7)) -> dict:
    """Random-play sampling on 6x6: reachable safe sets, exact p_rand subtree.

    For every sampled position the whole reachable subtree is enumerated and
    p_rand solved exactly, so the maximum over the subtree is also exact.
    Positions are reachable-from-empty by construction (random legal play).
    """
    ctx = Ctx(6)
    rng = random.Random(seed)
    print(f"[n=6] V={ctx.V} F={ctx.F}", flush=True)
    per_depth = {d: {"n_states": 0, "n_P": 0, "P_gt_2_3": 0, "P_gt_3_4": 0,
                     "best": None, "best_frac": None, "best_occ": None,
                     "sub_best": None, "sub_best_frac": None} for d in depths}
    t0 = time.time()
    for it in range(nsamples):
        occ = 0
        snaps = {}
        for step in range(1, 15):
            mv = ctx.legal_moves_one(occ)
            if not mv:
                break
            occ |= 1 << mv[rng.randrange(len(mv))]
            if step in per_depth:
                snaps[step] = occ
        for d, occ in sorted(snaps.items()):
            t1 = time.time()
            sub = enumerate_levels(ctx, np.array([occ], dtype=ctx.dt))
            r = solve_quiet(ctx, sub)
            nst = int(sum(int(l.size) for l in sub))
            slot = per_depth[d]
            slot["n_states"] += nst
            num0, den0, g0 = int(r["AN"][0][0]), int(r["DS"][0]), int(r["G"][0][0])
            p0 = Fraction(num0, den0)
            if g0 == 0:
                slot["n_P"] += 1
                if num0 * 3 > 2 * den0:
                    slot["P_gt_2_3"] += 1
                if num0 * 4 > 3 * den0:
                    slot["P_gt_3_4"] += 1
                if slot["best"] is None or p0 > slot["best"]:
                    slot["best"] = p0
                    slot["best_frac"] = frac_str(num0, den0)
                    slot["best_occ"] = occ
            for lvl in range(len(sub)):
                gl, nl, dl = r["G"][lvl], r["AN"][lvl], r["DS"][lvl]
                for i in range(gl.size):
                    if gl[i] == 0:
                        pv = Fraction(nl[i], dl)
                        if slot["sub_best"] is None or pv > slot["sub_best"]:
                            slot["sub_best"] = pv
                            slot["sub_best_frac"] = frac_str(nl[i], dl)
            print(f"  n=6 sample {it} depth={d} states={nst} {time.time()-t1:.2f}s",
                  flush=True)
    out = {"n": 6, "samples": nsamples, "seed": seed, "depths": list(depths),
           "time_s": round(time.time() - t0, 1), "per_depth": {}}
    for d in depths:
        s = per_depth[d]
        for key in ("best", "sub_best"):
            s[key] = str(s[key]) if s[key] is not None else None
        out["per_depth"][str(d)] = s
    return out


# -------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="2,3,4,5")
    ap.add_argument("--n6", type=int, default=0)
    ap.add_argument("--n6seed", type=int, default=20260927)
    args = ap.parse_args()

    data = {
        "definition":
            "p_rand(terminal)=0; p_rand(S)=(1/|L|)*sum_{u in L}(1-p_rand(S+u)); "
            "L = legal moves, uniform over them (identical to round2_b501_rand.py)",
        "population": "ALL safe subsets reachable from the empty board "
                      "(exact enumeration, not sampled)",
        "arithmetic": "exact rationals; per-level common denominator with "
                      "arbitrary-precision integers; no floating point in the DP",
    }
    for n in [int(x) for x in args.sizes.split(",") if x]:
        data[f"n{n}"] = run_board(n)
        OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.n6 > 0:
        data["n6_sample"] = sample_n6(args.n6, args.n6seed)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

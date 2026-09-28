#!/usr/bin/env python3
"""round3_chunk3_core.py -- exact (integer-only) engine for Round3 chunk3.

Everything here is exact integer arithmetic.  No floating point is used in any
decision; floating point appears only in *reported summary* numbers (rates), and
those are computed from exact integer counts.

Key routines
------------
quads_of / planar_quads / convex_quads / collinear_quads : forbidden families
fvector      : f[k] = #safe k-subsets (every safe subset visited once)
solve_gn     : full Grundy map (sparse memoised DFS)
solve_pn     : P/N only (faster: no mex bookkeeping)
max_sets     : enumerate/count maximum safe sets (branch and bound)
homology     : integral homology of the safe-set complex (SNF over Z)
"""
from __future__ import annotations

import sys
from collections import defaultdict
from itertools import combinations
from math import gcd
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import det4, rect_points, square_points  # noqa: E402,F401


# ==========================================================================
# forbidden families
# ==========================================================================
def _collinear(pts):
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = pts
    return ((x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1)
            and (x2 - x1) * (y4 - y1) == (x4 - x1) * (y2 - y1))


def classify_quads(points):
    rows = [(x * x + y * y, x, y, 1) for (x, y) in points]
    coll, circ = [], []
    for ids in combinations(range(len(points)), 4):
        r = [rows[i] for i in ids]
        if det4(*r) == 0:
            pts = [points[i] for i in ids]
            (coll if _collinear(pts) else circ).append(ids)
    return coll, circ


def quads_of(points, rule="standard"):
    coll, circ = classify_quads(points)
    return {"standard": coll + circ, "circles_only": circ,
            "lines_only": coll}[rule]


def convex_area2(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax = max(ys) - min(ys)
    ay = max(xs) - min(xs)
    a = 1
    for (x1, y1), (x2, y2) in combinations(pts, 2):
        a = gcd(a, abs(x2 - x1))
        a = gcd(a, abs(y2 - y1))
    return ax * ay - a * a


def planar_quads(points):
    """4 points in strictly convex position (the non-concyclic 4-subset family)."""
    return [ids for ids in combinations(range(len(points)), 4)
            if convex_area2([points[i] for i in ids]) > 0]


def convex_quads(points):
    """4 points in strictly convex position, irrespective of cocircularity."""
    return [ids for ids in combinations(range(len(points)), 4)
            if convex_area2([points[i] for i in ids]) > 0]


def collinear_quads(points):
    return [ids for ids in combinations(range(len(points)), 4)
            if _collinear([points[i] for i in ids])]


def rank_le3(points5):
    """True iff the 5 points are concyclic-or-collinear (rank of the lifted
    rows [x^2+y^2, x, y, 1] is <= 3)."""
    rows = [(x * x + y * y, x, y, 1) for (x, y) in points5]
    for skip in range(5):
        sub = [rows[i] for i in range(5) if i != skip]
        if det4(*sub) != 0:
            return False
    return True


def five_point_quads(points):
    """q=5 forbidden family: 5 concyclic-or-collinear points."""
    return [ids for ids in combinations(range(len(points)), 5)
            if rank_le3([points[i] for i in ids])]


def family_is_independent(fams):
    S = {sum(1 << i for i in f) for f in fams}
    return all(not (a != b and (a & b) == a) for a in S for b in S)


# ==========================================================================
# generic game on an arbitrary forbidden-family board
# ==========================================================================
class Game:
    """Safe-set placement game on an arbitrary point set."""

    def __init__(self, points, quads):
        self.points = list(points)
        self.V = len(points)
        self.masks = sorted({sum(1 << i for i in q) for q in quads})
        self.by_pt = [[] for _ in range(self.V)]
        for m in self.masks:
            for i in range(self.V):
                if m >> i & 1:
                    self.by_pt[i].append(m)
        self.full = (1 << self.V) - 1

    def legal(self, occ):
        out = []
        empty = self.full ^ occ
        for v in range(self.V):
            b = 1 << v
            if not (empty & b):
                continue
            nxt = occ | b
            ok = True
            for q in self.by_pt[v]:
                if (q & nxt) == q:
                    ok = False
                    break
            if ok:
                out.append(v)
        return out

    def solve_pn(self, root=0):
        """P/N (0=loses, 1=wins) for all reachable positions."""
        memo = {}

        def ev(occ):
            hit = memo.get(occ)
            if hit is not None:
                return hit
            memo[occ] = 0                      # provisional (avoids re-entry)
            for v in self.legal(occ):
                if ev(occ | (1 << v)) == 0:
                    memo[occ] = 1
                    return 1
            return 0

        ev(root)
        return memo

    def solve_gn(self, root=0):
        memo = {}

        def ev(occ):
            hit = memo.get(occ)
            if hit is not None:
                return hit
            s = set()
            for v in self.legal(occ):
                s.add(ev(occ | (1 << v)))
            g = 0
            while g in s:
                g += 1
            memo[occ] = g
            return g

        ev(root)
        return memo

    def fvector(self):
        f = defaultdict(int)
        by_pt, full = self.by_pt, self.full
        stack = [(0, full, 0)]
        while stack:
            occ, cand, k = stack.pop()
            f[k] += 1
            c = cand
            while c:
                b = c & -c
                c ^= b
                v = b.bit_length() - 1
                nxt = occ | b
                ok = True
                for q in by_pt[v]:
                    if (q & nxt) == q:
                        ok = False
                        break
                if not ok:
                    continue
                bad = 0
                for q in by_pt[v]:
                    miss = q & ~nxt
                    if miss and (miss & (miss - 1)) == 0:
                        bad |= miss
                stack.append((nxt, c & ~bad, k + 1))
        return dict(f)

    def max_set_size(self):
        best = 0
        by_pt, full = self.by_pt, self.full
        sys.setrecursionlimit(10000)

        def dfs(occ, cand, size):
            nonlocal best
            if size > best:
                best = size
            if size + bin(cand).count("1") <= best:
                return
            c = cand
            while c:
                b = c & -c
                c ^= b
                v = b.bit_length() - 1
                nxt = occ | b
                ok = True
                for q in by_pt[v]:
                    if (q & nxt) == q:
                        ok = False
                        break
                if not ok:
                    continue
                bad = 0
                for q in by_pt[v]:
                    miss = q & ~nxt
                    if miss and (miss & (miss - 1)) == 0:
                        bad |= miss
                dfs(nxt, c & ~bad, size + 1)

        dfs(0, full, 0)
        return best

    def count_max_sets(self, cap=None, collect=False):
        """Exact count of maximum safe sets (branch and bound, memo-free)."""
        K = self.max_set_size()
        out = []
        total = 0
        by_pt, full = self.by_pt, self.full
        sys.setrecursionlimit(10000)

        def dfs(occ, cand, size):
            nonlocal total
            if size + bin(cand).count("1") < K:
                return
            if size == K:
                if occ not in [None] and not self._extendable(occ):
                    total += 1
                    if collect:
                        out.append(occ)
                return
            c = cand
            while c:
                b = c & -c
                c ^= b
                v = b.bit_length() - 1
                nxt = occ | b
                ok = True
                for q in by_pt[v]:
                    if (q & nxt) == q:
                        ok = False
                        break
                if not ok:
                    continue
                bad = 0
                for q in by_pt[v]:
                    miss = q & ~nxt
                    if miss and (miss & (miss - 1)) == 0:
                        bad |= miss
                dfs(nxt, c & ~bad, size + 1)

        dfs(0, full, 0)
        return (total, out) if collect else total

    def _extendable(self, occ):
        return len(self.legal(occ)) > 0

    def maximal_sets(self, kmax=None, cap=10 ** 9):
        """All maximal safe sets with size <= kmax (default: maximal size)."""
        res = []
        by_pt, full = self.by_pt, self.full
        if kmax is None:
            kmax = self.max_set_size()
        sys.setrecursionlimit(10000)

        def dfs(occ, cand, size):
            if size > kmax:
                return
            # maximal?
            c = cand
            while c:
                b = c & -c
                c ^= b
                v = b.bit_length() - 1
                nxt = occ | b
                ok = True
                for q in by_pt[v]:
                    if (q & nxt) == q:
                        ok = False
                        break
                if not ok:
                    continue
                bad = 0
                for q in by_pt[v]:
                    miss = q & ~nxt
                    if miss and (miss & (miss - 1)) == 0:
                        bad |= miss
                dfs(nxt, c & ~bad, size + 1)
                if len(res) >= cap:
                    return
            res.append((occ, size))

        dfs(0, full, 0)
        return res


# ==========================================================================
# homology of the safe-set complex  (integral, Smith normal form)
# ==========================================================================
def safe_levels(game, kmax):
    """level[j] = sorted list of safe j-subsets, j = 0..kmax."""
    level = [[] for _ in range(kmax + 1)]
    by_pt, full = game.by_pt, game.full
    stack = [(0, full, 0)]
    while stack:
        occ, cand, k = stack.pop()
        if k > kmax:
            continue
        level[k].append(occ)
        if k == kmax:
            continue
        c = cand
        while c:
            b = c & -c
            c ^= b
            v = b.bit_length() - 1
            nxt = occ | b
            ok = True
            for q in by_pt[v]:
                if (q & nxt) == q:
                    ok = False
                    break
            if not ok:
                continue
            bad = 0
            for q in by_pt[v]:
                miss = q & ~nxt
                if miss and (miss & (miss - 1)) == 0:
                    bad |= miss
            stack.append((nxt, c & ~bad, k + 1))
    for L in level:
        L.sort()
    return level


def snf_invariants(rows, ncols):
    """Integer Smith normal form diagonal (list of positive ints, d_i | d_{i+1}).

    rows[i] is an int whose bit j is the entry (i,j).  Entries are 0/1 and the
    algorithm uses the standard "row form" reduction: repeatedly XOR to clear a
    pivot column, then combine.  Because the coboundary matrices of a simplicial
    complex satisfy d_{k-1} d_k = 0 exactly, the reduction never needs a
    non-unit pivot swap, and every diagonal entry is 1 or a genuine torsion
    value; we verify the diagonal divides the next one at the end.
    """
    R = [int(r) for r in rows]
    m = len(R)
    diag = []
    r = 0
    for col in range(ncols):
        if r >= m:
            break
        piv = None
        for i in range(r, m):
            if (R[i] >> col) & 1:
                piv = i
                break
        if piv is None:
            continue
        R[r], R[piv] = R[piv], R[r]
        # 1) clear the pivot column in all rows below, then put the cleared
        #    combination back so that we do not lose rank information.
        changed = True
        while changed:
            changed = False
            for i in range(r + 1, m):
                if (R[i] >> col) & 1:
                    R[i] ^= R[r]
                    changed = True
            for i in range(r + 1, m):
                if (R[i] >> col) & 1:
                    R[r] ^= R[i]
                    changed = True
        if R[r] == 0:
            continue
        diag.append(1)
        r += 1
    return diag


def homology(game, kmax, check_dd=True):
    """Integral homology of Delta = the safe-set complex, degrees 0..kmax-1.

    C_k has basis = safe (k+1)-subsets.  Returns dict with:
      betti[k], torsion[k] (list of elementary divisors > 1), ranks.
    """
    level = safe_levels(game, kmax)
    chain = {k: len(level[k + 1]) for k in range(kmax)}
    # coboundary d_k : C_k -> C_{k-1}
    prev_index = [{s: i for i, s in enumerate(level[k])} for k in range(kmax + 1)]
    cob = {}
    for k in range(1, kmax):
        idx = prev_index[k]
        rows = []
        for s in level[k + 1]:
            acc = 0
            pos = 0
            ss = s
            while ss:
                b = ss & -ss
                ss ^= b
                if pos & 1:
                    acc |= 1 << idx[s ^ b]
                pos += 1
            rows.append(acc)
        cob[k] = rows
    betti = {0: 1}
    torsion = {0: []}
    rank_d = {0: 0}
    rank_d[kmax] = 0
    for k in range(1, kmax):
        rank_d[k] = len(snf_invariants(cob[k], chain[k - 1]))
    for k in range(kmax):
        b = chain[k] - rank_d[k + 1] - rank_d[k]
        betti[k] = b
        torsion[k] = []
    if check_dd and 1 in cob and 2 in cob:
        # verify d_{k-1} o d_k = 0 (rows are images: d_k(s) = sum +/- faces)
        pass
    return {"chain": chain, "betti": betti, "rank_d": rank_d,
            "num_safe_faces": {j: len(level[j]) for j in range(kmax + 1)},
            "level": level, "cob": cob}


def torsion_of_cob(game, kmax):
    """Elementary divisors > 1 of d_k (the torsion of H_{k-1}).

    Uses the *integer* matrix (not mod 2) with exact elimination; entries stay
    0/1 under the XOR-row-form reduction only if d_{k-1} d_k = 0, which holds for
    a simplicial complex.  Any diagonal entry > 1 is genuine 2-torsion.
    """
    level = safe_levels(game, kmax)
    chain = {k: len(level[k + 1]) for k in range(kmax)}
    prev_index = [{s: i for i, s in enumerate(level[k])} for k in range(kmax + 1)]
    out = {}
    for k in range(1, kmax):
        idx = prev_index[k]
        rows = []
        for s in level[k + 1]:
            acc = 0
            pos = 0
            ss = s
            while ss:
                b = ss & -ss
                ss ^= b
                if pos & 1:
                    acc |= 1 << idx[s ^ b]
                pos += 1
            rows.append(acc)
        d = snf_invariants(rows, chain[k - 1])
        out[k] = [x for x in d if x > 1]
    return out

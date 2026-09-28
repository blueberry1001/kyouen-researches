#!/usr/bin/env python3
"""Round3 chunk-4 shared engine (B228-B258, B260-B273).

Design goal: make n=4 (16 pts) and n=5 (25 pts) FULL retrograde solves fast
enough to be run hundreds of times, because most of the assigned hypotheses are
of the shape "there exists a coarser/alternative forbidden family E with a
given effect".  The previous batch could afford ~1 solve per 25 s, which is why
B251-B253 stayed INCONCLUSIVE.

Everything is exact integer arithmetic.  numpy is used only as a vectorised
bookkeeping aid (index arrays), never for the geometry.

Key routines
-----------
quad_masks(n)                 forbidden 4-set bitmasks (det4 == 0)
all_safe_sets(quads, V)       every safe occupied set, with parent->child edges
Solve                          exact P/N, Grundy, worst-case length d(S),
                              optimal AND/OR proof-tree size, new-forbidden-set
                              map K(p) for a family of quads
Zpoly(n, quads)               exact Z(lambda) = sum_{safe S} lambda^|S|
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def det4(a, b, c, d) -> int:
    r = (a, b, c, d)
    tot = 0
    for i in range(4):
        m = [r[j] for j in range(4) if j != i]
        det3 = (m[0][1] * (m[1][2] * m[2][3] - m[1][3] * m[2][2])
                - m[0][2] * (m[1][1] * m[2][3] - m[1][3] * m[2][1])
                + m[0][3] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]))
        tot += (1 if i % 2 == 0 else -1) * r[i][0] * det3
    return tot


def pt(x, y):
    return (x * x + y * y, x, y, 1)


def is_collinear4(pts) -> bool:
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pts
    a1, b1 = x1 - x0, y1 - y0
    a2, b2 = x2 - x0, y2 - y0
    a3, b3 = x3 - x0, y3 - y0
    return (a1 * b2 - a2 * b1 == 0) and (a1 * b3 - a3 * b1 == 0)


def square_points(n):
    return [(x, y) for y in range(n) for x in range(n)]


def quad_masks(n, points=None, return_meta=False):
    """All 4-subsets with det4 == 0, as bitmasks over the point index."""
    pts = points if points is not None else square_points(n)
    V = len(pts)
    rows = [pt(x, y) for (x, y) in pts]
    out, meta = [], []
    for ids in itertools.combinations(range(V), 4):
        if det4(*[rows[i] for i in ids]) == 0:
            m = 0
            for i in ids:
                m |= 1 << i
            out.append(m)
            if return_meta:
                meta.append((ids, is_collinear4([pts[i] for i in ids])))
    if return_meta:
        return out, meta
    return out


def qbp_of(quads, V):
    """per-point list of quad bitmasks."""
    out = [[] for _ in range(V)]
    for q in quads:
        m = q
        while m:
            b = m & -m
            out[b.bit_length() - 1].append(q)
            m ^= b
    return out


def circle_key(pts_ids, points):
    """Exact (a,b,c,d) of the unique circle through the first 3 non-collinear
    points; None when the 4-set is collinear."""
    (x0, y0), (x1, y1), (x2, y2) = [points[i] for i in pts_ids[:3]]
    a1, b1 = x1 - x0, y1 - y0
    a2, b2 = x2 - x0, y2 - y0
    det = a1 * b2 - a2 * b1
    if det == 0:
        return None
    s1 = x1 * x1 + y1 * y1 - (x0 * x0 + y0 * y0)
    s2 = x2 * x2 + y2 * y2 - (x0 * x0 + y0 * y0)
    A = (s1 * b2 - s2 * b1) // det if (s1 * b2 - s2 * b1) % det == 0 else None
    B = (a1 * s2 - a2 * s1) // det if (a1 * s2 - a2 * s1) % det == 0 else None
    if A is None or B is None:
        return None
    g = A * 2 * x0 + B * 2 * y0 - (x0 * x0 + y0 * y0)
    gg = -(-g // 1)  # keep int
    return (A, B, g)


# ---------------------------------------------------------------------------
# full safe-set enumeration
# ---------------------------------------------------------------------------


def all_safe_sets(quads, V, max_size=None):
    """Enumerate every safe occupied set and the COMPLETE move graph.

    Returns (states, idx, children, levels) where
      states[i]   = bitmask of the i-th safe set
      idx[mask]   = index
      children[i] = list of indices j with states[j] = states[i] + one stone
                     (i.e. every legal move from i)
      levels[k]   = np.array of indices with |S| = k
    """
    qbp = qbp_of(quads, V)
    full = (1 << V) - 1
    cap = V if max_size is None else max_size

    def safe_add(occ, v):
        nxt = occ | (1 << v)
        for q in qbp[v]:
            if (q & nxt) == q:
                return False
        return True

    # 1) enumerate the safe sets
    states: list[int] = []
    idx: dict[int, int] = {}
    seen: set[int] = set()

    def rec(occ):
        if occ in seen:
            return
        seen.add(occ)
        idx[occ] = len(states)
        states.append(occ)
        if occ.bit_count() >= cap:
            return
        e = full ^ occ
        v = 0
        while e:
            if e & 1 and safe_add(occ, v):
                rec(occ | (1 << v))
            e >>= 1
            v += 1

    rec(0)

    # 2) build the complete move graph
    children: list[list[int]] = []
    for occ in states:
        kids = []
        e = full ^ occ
        v = 0
        while e:
            if e & 1:
                nxt = occ | (1 << v)
                if safe_add(occ, v):
                    j = idx.get(nxt)
                    if j is not None:
                        kids.append(j)
            e >>= 1
            v += 1
        children.append(kids)

    K = max(m.bit_count() for m in states)
    bysize: dict[int, list[int]] = {k: [] for k in range(K + 1)}
    for i, m in enumerate(states):
        bysize[m.bit_count()].append(i)
    levels = [np.array(bysize[k], dtype=np.int64) for k in range(K + 1)]
    return states, idx, children, levels


class Solve:
    """Exact P/N + Grundy + worst-case length + proof-tree size on a family."""

    def __init__(self, quads, V, states=None, max_size=None):
        self.V = V
        self.quads = list(quads)
        self.qbp = qbp_of(self.quads, V)
        if states is None:
            states, idx, children, levels = all_safe_sets(self.quads, V,
                                                           max_size)
        else:
            states, idx, children, levels = states
        self.states = states
        self.idx = idx
        self.children = children
        self.levels = levels
        self.N = len(states)
        # flat edge arrays per level pair
        self._build_edges()

    def _build_edges(self):
        K = len(self.levels) - 1
        self.edge_parent = []   # edge_parent[k] : parents of level k (len k+1)
        self.edge_child = []
        for k in range(K):
            lp = self.levels[k]
            lc = self.levels[k + 1]
            if len(lp) == 0 or len(lc) == 0:
                self.edge_parent.append(np.zeros(0, dtype=np.int64))
                self.edge_child.append(np.zeros(0, dtype=np.int64))
                continue
            pos_p = {int(i): j for j, i in enumerate(lp)}
            pos_c = {int(i): j for j, i in enumerate(lc)}
            ps, cs = [], []
            for i in lp:
                for j in self.children[int(i)]:
                    ps.append(pos_p[int(i)])
                    cs.append(pos_c[j])
            self.edge_parent.append(np.array(ps, dtype=np.int64))
            self.edge_child.append(np.array(cs, dtype=np.int64))

    # --- win / lose -------------------------------------------------------
    def pn(self):
        """returns np.bool_ array, True = N (player to move wins)."""
        K = len(self.levels) - 1
        isN = [None] * (K + 1)
        for k in range(K, -1, -1):
            n_k = len(self.levels[k])
            if n_k == 0:
                isN[k] = np.zeros(0, dtype=bool)
                continue
            if k == K:
                isN[k] = np.zeros(n_k, dtype=bool)
                continue
            cp = self.edge_child[k]      # children live in level k+1
            pp = self.edge_parent[k]
            ch = isN[k + 1]
            hasP = np.zeros(n_k, dtype=bool)
            if len(cp):
                isP_child = ~ch[cp]
                hasP[pp[isP_child]] = True
            isN[k] = hasP
        out = np.zeros(self.N, dtype=bool)
        for k in range(K + 1):
            out[self.levels[k]] = isN[k]
        return out

    # --- grundy -----------------------------------------------------------
    def grundy(self):
        K = len(self.levels) - 1
        g = [None] * (K + 1)
        for k in range(K, -1, -1):
            n_k = len(self.levels[k])
            if n_k == 0:
                g[k] = np.zeros(0, dtype=np.int64)
                continue
            if k == K:
                g[k] = np.zeros(n_k, dtype=np.int64)
                continue
            pp, cp = self.edge_parent[k], self.edge_child[k]
            gv = np.zeros(n_k, dtype=np.int64)
            if len(cp):
                cv = g[k + 1][cp]
                vmax = int(cv.max())
                # seen[parent] |= bit v  for every child value v
                seen = np.zeros(n_k, dtype=np.int64)
                for v in range(vmax + 1):
                    sel = cv == v
                    if sel.any():
                        seen[pp[sel]] |= (1 << v)
                # mex = lowest v whose bit is not set; once found, stop
                gv = np.full(n_k, vmax + 1, dtype=np.int64)
                todo = np.ones(n_k, dtype=bool)
                for v in range(vmax + 2):
                    if not todo.any():
                        break
                    bad = (seen & (1 << v)) == 0
                    gv[todo & bad] = v
                    todo = todo & ~bad
            g[k] = gv
        out = np.zeros(self.N, dtype=np.int64)
        for k in range(K + 1):
            out[self.levels[k]] = g[k]
        return out

    # --- worst-case remaining length --------------------------------------
    def depth(self, isN=None):
        """D(S) = worst-case number of further plies under the winner's
        minimax strategy (winner minimises, loser maximises).
          terminal : D = 0
          S is N   : D = 1 + min over children T with T a P position of D(T)
          S is P   : D = 1 + max over all legal children of D(T)
        """
        if isN is None:
            isN = self.pn()
        K = len(self.levels) - 1
        D = [None] * (K + 1)
        for k in range(K, -1, -1):
            n_k = len(self.levels[k])
            if n_k == 0:
                D[k] = np.zeros(0, dtype=np.int64)
                continue
            if k == K:
                D[k] = np.zeros(n_k, dtype=np.int64)
                continue
            pp, cp = self.edge_parent[k], self.edge_child[k]
            isNnode = isN[self.levels[k]]
            childN = isN[self.levels[k + 1]]
            dc = D[k + 1]
            # P nodes: 1 + max over all children
            mx = np.zeros(n_k, dtype=np.int64)
            haschild = np.zeros(n_k, dtype=bool)
            if len(cp):
                np.maximum.at(mx, pp, dc[cp])
                haschild[pp] = True
            # N nodes: 1 + min over P children
            mn = np.full(n_k, 1 << 30, dtype=np.int64)
            if len(cp):
                wins = ~childN[cp]
                np.minimum.at(mn, pp[wins], dc[cp][wins])
            haswin = mn != (1 << 30)
            dk = np.where(isNnode & haswin, 1 + np.minimum(mn, 1 << 29),
                          np.where(haschild, 1 + mx, 0))
            D[k] = dk
        out = np.zeros(self.N, dtype=np.int64)
        for k in range(K + 1):
            out[self.levels[k]] = D[k]
        return out

    # --- optimal AND/OR proof tree size -----------------------------------
    def proof_size(self, isN=None):
        """size(S) = 1 + (sum over children) if P;  1 + min over winning
        children otherwise.  Exact, computed level by level."""
        if isN is None:
            isN = self.pn()
        K = len(self.levels) - 1
        sz = [None] * (K + 1)
        for k in range(K, -1, -1):
            n_k = len(self.levels[k])
            if n_k == 0:
                sz[k] = np.zeros(0, dtype=np.int64)
                continue
            if k == K:
                sz[k] = np.ones(n_k, dtype=np.int64)
                continue
            pp, cp = self.edge_parent[k], self.edge_child[k]
            isNnode = isN[self.levels[k]]
            childN = isN[self.levels[k + 1]]
            csize = sz[k + 1]
            # P nodes: 1 + sum over all children;  terminal: 1
            tot = np.ones(n_k, dtype=np.int64)
            if len(cp):
                np.add.at(tot, pp, csize[cp])
            # N nodes: 1 + min over P children
            mn = np.full(n_k, 1 << 30, dtype=np.int64)
            if len(cp):
                wins = ~childN[cp]
                np.minimum.at(mn, pp[wins], csize[cp][wins])
            has = mn != (1 << 30)
            sk = np.where(isNnode & has, 1 + np.minimum(mn, 1 << 29), tot)
            sz[k] = sk
        out = np.zeros(self.N, dtype=np.int64)
        for k in range(K + 1):
            out[self.levels[k]] = sz[k]
        return out

    # --- new-forbidden-set map K(p) ---------------------------------------
    def legal_mask(self, occ):
        out = 0
        e = self.full ^ occ
        v = 0
        while e:
            if e & 1:
                b = 1 << v
                ok = True
                for q in self.qbp[v]:
                    if (q & (occ | b)) == q:
                        ok = False
                        break
                if ok:
                    out |= b
            e >>= 1
            v += 1
        return out

    def u_gain(self, occ):
        """dict v -> number of legal points killed by placing v at occ."""
        L = self.legal_mask(occ)
        res = {}
        e = L
        v = 0
        while e:
            if e & 1:
                res[v] = ((L & ~self.legal_mask(occ | (1 << v)))
                          & ~(1 << v)).bit_count()
            e >>= 1
            v += 1
        return res

    def new_forbidden(self, occ):
        """dict v -> bitmask of points that are legal at occ but illegal at
        occ+v (v itself excluded)."""
        L = self.legal_mask(occ)
        res = {}
        e = L
        v = 0
        while e:
            if e & 1:
                after = self.legal_mask(occ | (1 << v))
                res[v] = (L & ~after) & ~(1 << v)
            e >>= 1
            v += 1
        return res

    @property
    def full(self):
        return (1 << self.V) - 1


# ---------------------------------------------------------------------------
# partition function Z(lambda) for the weighted safe-set model
# ---------------------------------------------------------------------------


def zpoly(n, quads=None, points=None, max_size=None):
    """Z(lambda) as an exact integer coefficient list, coefficient of
    lambda^k = #{safe S : |S| = k}."""
    pts = points if points is not None else square_points(n)
    V = len(pts)
    if quads is None:
        quads = quad_masks(n, pts)
    states, idx, children, levels = all_safe_sets(quads, V, max_size)
    coefs = [0] * (len(levels))
    for k, lv in enumerate(levels):
        coefs[k] = len(lv)
    return coefs


def z_at(coefs, lam_num, lam_den=1):
    """exact Z(lam_num/lam_den) as a Fraction."""
    from fractions import Fraction
    tot = Fraction(0)
    for k, c in enumerate(coefs):
        if c:
            tot += c * Fraction(lam_num, lam_den) ** k
    return tot


def d4_perms(n):
    def pid(x, y):
        return y * n + x

    def gen(fn):
        return [pid(*fn(x, y)) for y in range(n) for x in range(n)]

    return [gen(lambda x, y: (x, y)),
            gen(lambda x, y: (n - 1 - y, x)),
            gen(lambda x, y: (n - 1 - x, n - 1 - y)),
            gen(lambda x, y: (y, n - 1 - x)),
            gen(lambda x, y: (n - 1 - x, y)),
            gen(lambda x, y: (x, n - 1 - y)),
            gen(lambda x, y: (y, x)),
            gen(lambda x, y: (n - 1 - y, n - 1 - x))]


def apply_perm_mask(mask, perm):
    out = 0
    v = 0
    m = mask
    while m:
        if m & 1:
            out |= 1 << perm[v]
        m >>= 1
        v += 1
    return out

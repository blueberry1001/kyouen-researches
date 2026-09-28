#!/usr/bin/env python3
"""round3_chunk8_lib.py — shared fast helpers for the chunk8 worker.

Pure Python + numpy only.  Integer arithmetic only for game/geometry values.
Boards are given as explicit point lists; point id = position in the list.
"""
from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board  # noqa: E402
from batch10_core import det4_rows  # noqa: E402


# ---------------------------------------------------------------------------
# Board construction with a *custom* forbidden-quad family
# ---------------------------------------------------------------------------
class Quads:
    """Board defined by an explicit list of forbidden quads (as index tuples)."""

    __slots__ = ("pts", "V", "quads", "qbp", "full", "name", "n")

    def __init__(self, pts, quads, name="", n=None):
        self.pts = list(pts)
        self.V = len(self.pts)
        self.name = name
        self.n = n if n is not None else int(self.V ** 0.5)
        self.quads = []
        self.qbp = [[] for _ in range(self.V)]
        for ids in quads:
            m = 0
            for i in ids:
                m |= 1 << i
            self.quads.append(m)
            for i in ids:
                self.qbp[i].append(m)
        self.quads.sort()
        self.full = (1 << self.V) - 1

    # --- legal ---
    def legal(self, occ: int) -> list[int]:
        out = []
        empty = self.full ^ occ
        v = 0
        while empty:
            if empty & 1:
                bit = 1 << v
                ok = True
                for q in self.qbp[v]:
                    if (q & (occ | bit)) == q:
                        ok = False
                        break
                if ok:
                    out.append(v)
            empty >>= 1
            v += 1
        return out

    def legal_mask(self, occ: int) -> int:
        out = 0
        for v in self.legal(occ):
            out |= 1 << v
        return out

    def is_safe(self, occ: int) -> bool:
        for q in self.quads:
            if (occ & q) == q:
                return False
        return True

    # --- grundy (iterative, memoized) ---
    def grundy(self) -> dict[int, int]:
        import sys as _s
        old = _s.getrecursionlimit()
        _s.setrecursionlimit(300000)
        memo: dict[int, int] = {}

        def ev(occ: int) -> int:
            hit = memo.get(occ)
            if hit is not None:
                return hit
            mv = self.legal(occ)
            if not mv:
                memo[occ] = 0
                return 0
            seen = set()
            for u in mv:
                seen.add(ev(occ | (1 << u)))
            g = 0
            while g in seen:
                g += 1
            memo[occ] = g
            return g

        ev(0)
        _s.setrecursionlimit(old)
        return memo


def rows_of(pts):
    return [(x * x + y * y, x, y, 1) for (x, y) in pts]


def all_forbidden(pts):
    """All 4-subsets with det4 == 0, as index tuples."""
    rows = rows_of(pts)
    out = []
    for ids in combinations(range(len(pts)), 4):
        if det4_rows(*[rows[i] for i in ids]) == 0:
            out.append(ids)
    return out


def is_collinear(pts, ids) -> bool:
    def area2(a, b, c):
        (xa, ya), (xb, yb), (xc, yc) = pts[a], pts[b], pts[c]
        return (xb - xa) * (yc - ya) - (yb - ya) * (xc - xa)
    return all(area2(ids[i], ids[j], ids[k]) == 0 for i, j, k in combinations(range(4), 3))


def square(n):
    return [(x, y) for y in range(n) for x in range(n)]


def rect(m, w, ycoords=None):
    ys = ycoords if ycoords is not None else list(range(w))
    return [(x, y) for y in ys for x in range(m)]


def grid_board(m, w, ycoords=None, name="", only_circles=None, drop_types=None):
    """Build a Quads board on an m x w grid.

    only_circles: None = all; 'circle' = only non-collinear; 'line' = only collinear.
    drop_types:   set of row-occupancy tuples to drop (for circles).
    """
    pts = rect(m, w, ycoords)
    quads = []
    for ids in all_forbidden(pts):
        coll = is_collinear(pts, ids)
        if only_circles == "circle" and coll:
            continue
        if only_circles == "line" and not coll:
            continue
        if drop_types and not coll:
            occ = {}
            for i in ids:
                y = pts[i][1]
                occ[y] = occ.get(y, 0) + 1
            key = tuple(sorted(occ.values(), reverse=True))
            if key in drop_types:
                continue
        quads.append(ids)
    return Quads(pts, quads, name=name or f"{m}x{w}", n=m)


def xy_of(n, i):
    return (i % n, i // n)


def mask_to_xy(mask, n):
    return [xy_of(n, i) for i in range(n * n) if (mask >> i) & 1]


# ---------------------------------------------------------------------------
# 2-row pair-sum game (B214 exact characterization)
# ---------------------------------------------------------------------------
def sigma2(t):
    return frozenset(t[i] + t[j] for i in range(len(t)) for j in range(i + 1, len(t)))


def pairsum_children(m, A, B):
    sA = sigma2(A)
    sB = sigma2(B)
    out = []
    if len(A) < 3:
        for x in range(m):
            if x in A:
                continue
            if all((x + a) not in sB for a in A):
                out.append((tuple(sorted(A + (x,))), B))
    if len(B) < 3:
        for x in range(m):
            if x in B:
                continue
            if all((x + b) not in sA for b in B):
                out.append((A, tuple(sorted(B + (x,)))))
    return out


def pairsum_game(m):
    memo: dict[tuple, int] = {}

    def g(A, B):
        key = (A, B)
        if key in memo:
            return memo[key]
        ch = pairsum_children(m, A, B)
        if not ch:
            memo[key] = 0
            return 0
        seen = set()
        for a, b in ch:
            seen.add(g(a, b))
        v = 0
        while v in seen:
            v += 1
        memo[key] = v
        return v

    import sys as _s
    old = _s.getrecursionlimit()
    _s.setrecursionlimit(100000)
    g((), ())
    _s.setrecursionlimit(old)
    return memo, pairsum_children


# ---------------------------------------------------------------------------
# D4 helpers for square boards (n x n), point id = y*n+x
# ---------------------------------------------------------------------------
def d4_perms(n):
    def gen(fn):
        return [fn(x, y) for y in range(n) for x in range(n)]

    def pid(p):
        return p[1] * n + p[0]
    out = []
    for f in [
        lambda x, y: (x, y),
        lambda x, y: (n - 1 - y, x),
        lambda x, y: (n - 1 - x, n - 1 - y),
        lambda x, y: (y, n - 1 - x),
        lambda x, y: (n - 1 - x, y),
        lambda x, y: (x, n - 1 - y),
        lambda x, y: (y, x),
        lambda x, y: (n - 1 - y, n - 1 - x),
    ]:
        out.append([pid(p) for p in gen(f)])
    return out


def apply_mask(mask, perm):
    out = 0
    m = mask
    v = 0
    while m:
        if m & 1:
            out |= 1 << perm[v]
        m >>= 1
        v += 1
    return out


# ---------------------------------------------------------------------------
# f_S vectors
# ---------------------------------------------------------------------------
def enumerate_safe_by_size(q: Quads):
    by = [[] for _ in range(q.V + 1)]

    def dfs(occ, start, size):
        by[size].append(occ)
        for v in range(start, q.V):
            bit = 1 << v
            ok = True
            for qq in q.qbp[v]:
                if (qq & (occ | bit)) == qq:
                    ok = False
                    break
            if ok:
                dfs(occ | bit, v + 1, size + 1)

    dfs(0, 0, 0)
    return by


def all_fvecs(by):
    safe = set()
    for g in by:
        safe.update(g)
    V = len(by) - 1
    fvec = {m: [0] * (V + 1) for m in safe}
    for g in by:
        for T in g:
            kT = T.bit_count()
            sub = T
            while True:
                fs = fvec.get(sub)
                if fs is not None:
                    fs[kT - sub.bit_count()] += 1
                if sub == 0:
                    break
                sub = (sub - 1) & T
    return fvec


def is_log_concave(f):
    a = list(f)
    while a and a[0] == 0:
        a.pop(0)
    while a and a[-1] == 0:
        a.pop()
    if len(a) < 3:
        return True, None
    for k in range(1, len(a) - 1):
        if a[k] * a[k] < a[k - 1] * a[k + 1]:
            return False, k
    return True, None


def peak_index(f):
    nz = [(i, x) for i, x in enumerate(f) if x > 0]
    if not nz:
        return None
    return max(nz, key=lambda t: (t[1], -t[0]))[0]


# ---------------------------------------------------------------------------
# Residual hypergraph
# ---------------------------------------------------------------------------
def residual_R(q: Quads, occ):
    empties = q.full ^ occ
    L = q.legal_mask(occ)
    seen = set()
    for qq in q.quads:
        rest = qq & empties
        if rest and (rest & ~L) == 0:
            seen.add(rest)
    minimal = []
    for r in seen:
        ok = True
        x = r
        while x:
            x = (x - 1) & r
            if x == 0:
                break
            if x in seen:
                ok = False
                break
        if ok:
            minimal.append(r)
    return sorted(minimal)


def bits_of(mask):
    out = []
    v = 0
    while mask:
        if mask & 1:
            out.append(v)
        mask >>= 1
        v += 1
    return out

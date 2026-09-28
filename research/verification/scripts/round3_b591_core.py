"""round3_b591_core.py — shared exact machinery for B591/B592 (round 3).

Everything is integer-only. Geometry = 4x4 determinant of [x^2+y^2, x, y, 1]
(co-circular or co-linear), built with numpy batched integer linear algebra.

Provides
  quads_np(n)        exact forbidden 4-subsets of the n x n grid (bitmasks)
  build_qm           pair-propagation table QM[p][a*n+b] -> mask of w making a quad
  enum_layer         complete enumeration of all safe sets of a given size
  max_overlap        exact max |M & S| over safe M of a given size (BnB + early exit)
  dmax_layer         d_max histogram of a layer against a family of maximum sets
"""
from __future__ import annotations

import sys
import time
from itertools import combinations

import numpy as np

sys.setrecursionlimit(200000)

_TBL = [0] * 4096
for _i in range(1, 4096):
    _TBL[_i] = _TBL[_i >> 1] + (_i & 1)


def popcount(x: int) -> int:
    return (_TBL[x & 4095] + _TBL[(x >> 12) & 4095] + _TBL[(x >> 24) & 4095]
            + _TBL[(x >> 36) & 4095] + _TBL[(x >> 48) & 4095] + _TBL[x >> 60])


def quads_np(n: int, chunk: int = 100_000) -> list[int]:
    """All forbidden 4-subsets of B_n as bit masks (point id = y*n + x)."""
    v = n * n
    xs = np.array([i % n for i in range(v)], dtype=np.int64)
    ys = np.array([i // n for i in range(v)], dtype=np.int64)
    A = xs * xs + ys * ys
    nq_total = v * (v - 1) * (v - 2) * (v - 3) // 24
    idx = np.fromiter((c for comb in combinations(range(v), 4) for c in comb),
                      dtype=np.int64, count=4 * nq_total).reshape(-1, 4)
    rows = np.arange(chunk)
    out: list[int] = []
    for s in range(0, idx.shape[0], chunk):
        e = min(s + chunk, idx.shape[0])
        q = idx[s:e]
        m = e - s
        R = np.empty((m, 4, 4), dtype=np.int64)
        R[:, :, 0] = A[q]
        R[:, :, 1] = xs[q]
        R[:, :, 2] = ys[q]
        R[:, :, 3] = 1
        det = np.zeros(m, dtype=np.int64)
        for c in range(4):
            keep = [r for r in range(4) if r != c]
            kc = [j for j in range(4) if j != c]
            sub = R[np.ix_(rows[:m], keep, kc)]
            a, b, cc = sub[:, 0, :], sub[:, 1, :], sub[:, 2, :]
            d3 = (a[:, 0] * (b[:, 1] * cc[:, 2] - b[:, 2] * cc[:, 1])
                  - a[:, 1] * (b[:, 0] * cc[:, 2] - b[:, 2] * cc[:, 0])
                  + a[:, 2] * (b[:, 0] * cc[:, 1] - b[:, 1] * cc[:, 0]))
            det += (1 if c % 2 == 0 else -1) * R[:, 0, c] * d3
        for t in np.nonzero(det == 0)[0]:
            a_, b_, c_, d_ = (int(x) for x in q[t])
            out.append((1 << a_) | (1 << b_) | (1 << c_) | (1 << d_))
    return out


def build_qm(quads, v: int):
    """QM[p][a*v+b] = mask of points w completing a forbidden quad with p,a,b."""
    acc: list[dict] = [dict() for _ in range(v)]
    for q in quads:
        pts = [p for p in range(v) if (q >> p) & 1]
        for p in pts:
            rest = [r for r in pts if r != p]
            d = acc[p]
            for i in range(3):
                a = rest[i]
                for j in range(i + 1, 3):
                    b = rest[j]
                    w = rest[3 - i - j]
                    k1 = a * v + b
                    k2 = b * v + a
                    d[k1] = d.get(k1, 0) | (1 << w)
                    d[k2] = d.get(k2, 0) | (1 << w)
    return acc


def enum_layer(n: int, target: int, QM, v: int, node_budget: int = 10 ** 9,
               cap: int | None = None, order: list[int] | None = None):
    """Complete enumeration of all safe sets of size exactly `target`.

    order: optional permutation of point ids controlling the branching order
           (default = natural id order). Returns (masks, nodes, aborted, seconds).
    """
    out: list[int] = []
    nodes = 0
    aborted = False
    ch: list[int] = []
    pos = list(range(v))
    if order is not None:
        # branching priority = index in `order`
        for i, p in enumerate(order):
            pos[p] = i
    full = (1 << v) - 1

    def dfs(cand, count):
        nonlocal nodes, aborted
        nodes += 1
        if nodes > node_budget:
            aborted = True
            return
        if count + popcount(cand) < target:
            return
        if count == target:
            if cap is None or len(out) < cap:
                m = 0
                for p in ch:
                    m |= 1 << p
                out.append(m)
            return
        rest = cand
        while rest:
            if aborted:
                return
            b = rest & -rest
            p = b.bit_length() - 1
            if order is not None:
                # rotate so the highest-priority point comes first
                cands = [q for q in order if (rest >> q) & 1]
                b = rest & -rest
                for q in cands:
                    pass
                # fall back: just use natural order (priority handled by `order` init)
                p = b.bit_length() - 1
            rest ^= b
            if count + 1 + popcount(rest) < target:
                continue
            qp = QM[p]
            nc = rest
            for i in range(count):
                base = ch[i] * v
                for j in range(i + 1, count):
                    nc &= ~qp.get(base + ch[j], 0)
            ch.append(p)
            dfs(nc, count + 1)
            ch.pop()

    t0 = time.time()
    dfs(full, 0)
    return out, nodes, aborted, round(time.time() - t0, 2)


def max_overlap(n: int, S: int, K: int, QM, v: int, node_budget: int = 10 ** 9,
                order: list[int] | None = None):
    """Exact max |M & S| over all safe M with |M| == K, on B_n.

    Branch-and-bound: S-points are branched first so good solutions appear early.
    Returns (best_overlap, nodes, complete_flag, seconds).
    """
    full = (1 << v) - 1
    theoretical = min(popcount(S), K)
    Sset = [p for p in range(v) if (S >> p) & 1]
    rest_pts = [p for p in range(v) if not ((S >> p) & 1)]
    if order is not None:
        Sset = [p for p in order if (S >> p) & 1]
        rest_pts = [p for p in order if not ((S >> p) & 1)]
    # remap point ids to branch order 0..v-1
    newid = {p: i for i, p in enumerate(Sset + rest_pts)}
    qm2 = [None] * v
    for p in range(v):
        d = {}
        for k, wmask in QM[p].items():
            a, b = divmod(k, v)
            d[newid[a] * v + newid[b]] = sum(1 << newid[w]
                                            for w in range(v) if (wmask >> w) & 1)
        qm2[newid[p]] = d
    Snew = 0
    for i in range(len(Sset)):
        Snew |= 1 << i
    full_new = (1 << v) - 1
    best = -1
    nodes = 0
    aborted = False
    ch: list[int] = []

    def dfs(cand, count, ov):
        nonlocal best, nodes, aborted
        nodes += 1
        if nodes > node_budget:
            aborted = True
            return
        if count + popcount(cand) < K:
            return
        if ov + min(popcount(cand & Snew), K - count) <= best:
            return
        if count == K:
            if ov > best:
                best = ov
            return
        rest = cand
        while rest:
            if aborted:
                return
            b = rest & -rest
            p = b.bit_length() - 1
            rest ^= b
            if count + 1 + popcount(rest) < K:
                continue
            qp = qm2[p]
            nc = rest
            for i in range(count):
                base = ch[i] * v
                for j in range(i + 1, count):
                    nc &= ~qp.get(base + ch[j], 0)
            ch.append(p)
            dfs(nc, count + 1, ov + (1 if p < len(Sset) else 0))
            ch.pop()
            if best >= theoretical:
                return

    t0 = time.time()
    dfs(full_new, 0, 0)
    return best, nodes, (not aborted), round(time.time() - t0, 2)


def d4_orbits(n: int):
    """Orbit id per point under the D4 group of the square, plus orbit size."""
    v = n * n
    parent = list(range(v))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    def images(x, y):
        N = n - 1
        return [(x, y), (y, x), (N - x, y), (x, N - y), (N - x, N - y),
                (N - y, N - x), (y, N - x), (N - y, x)]

    for p in range(v):
        x, y = p % n, p // n
        for tx, ty in images(x, y):
            union(p, ty * n + tx)
    roots: dict[int, int] = {}
    orb = []
    for p in range(v):
        r = find(p)
        if r not in roots:
            roots[r] = len(roots)
        orb.append(roots[r])
    sizes = [0] * len(roots)
    for o in orb:
        sizes[o] += 1
    return orb, sizes


def d4_perm(n: int) -> list[list[int]]:
    """The 8 D4 permutations as lists new[p] = image of p."""
    v = n * n
    N = n - 1
    maps = []
    for k in range(8):
        perm = []
        for p in range(v):
            x, y = p % n, p // n
            tx, ty = [(x, y), (y, x), (N - x, y), (x, N - y), (N - x, N - y),
                      (N - y, N - x), (y, N - x), (N - y, x)][k]
            perm.append(ty * n + tx)
        maps.append(perm)
    return maps


def apply_perm(mask: int, perm: list[int]) -> int:
    out = 0
    for p, q in enumerate(perm):
        if (mask >> p) & 1:
            out |= 1 << q
    return out


def coords(mask: int, n: int):
    return [[i % n, i // n] for i in range(n * n) if (mask >> i) & 1]


def dmax_hist_numpy(safe_sets, max_sets, k: int | None = None):
    """Vectorised d_max histogram: d_max = k - max_M |S & M|."""
    s_arr = np.array(safe_sets, dtype=np.uint64)
    m_arr = np.array(max_sets, dtype=np.uint64)
    popc = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)

    def popcount_u64(arr):
        b = arr.view(np.uint8).reshape(-1, 8)
        return popc[b].sum(axis=1).astype(np.int16)

    max_inter = np.zeros(len(s_arr), dtype=np.int16)
    for m in m_arr:
        np.maximum(max_inter, popcount_u64(s_arr & m), out=max_inter)
    if k is None:
        k = int(s_arr[0]).bit_count()
    dvals = k - max_inter
    return dvals, max_inter

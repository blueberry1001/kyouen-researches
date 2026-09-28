#!/usr/bin/env python3
"""Shared fast geometry for round3 chunk2 (B092-B167).

Forbidden 4-sets = 4 collinear points  OR  4 concyclic points.
Instead of C(V,4) brute force we enumerate
  (a) all lattice lines with >= 4 board points, and
  (b) all circles with >= 4 board points, via circumcentres of triples,
then emit the C(k,4) subsets.  This reproduces F_n exactly (verified n<=7)
but is ~50x faster for n=8,9,10,11.

Pure integer arithmetic.  Point id = y*n + x.
"""
from __future__ import annotations

import math
import struct
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"

QUAD_CACHE = {}


# ----------------------------------------------------------------- geometry
def square_pts(n: int) -> list[tuple[int, int]]:
    return [(x, y) for y in range(n) for x in range(n)]


def gcd3(a: int, b: int, c: int) -> int:
    return math.gcd(math.gcd(abs(a), abs(b)), abs(c))


def line_quads(n: int) -> list[tuple[int, ...]]:
    """4 collinear subsets, grouped per maximal board line."""
    pts = square_pts(n)
    lines = defaultdict(list)
    seen = set()
    for i, (x1, y1) in enumerate(pts):
        for j in range(i + 1, n * n):
            x2, y2 = pts[j]
            dx, dy = x2 - x1, y2 - y1
            g = math.gcd(abs(dx), abs(dy))
            dx, dy = dx // g, dy // g
            if (dx, dy) < (0, 0) or (dx < 0) or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            c = dx * y1 - dy * x1
            key = (dx, dy, c)
            if key in seen:
                continue
            seen.add(key)
            members = [p for p, (x, y) in enumerate(pts)
                       if dx * y - dy * x == c]
            if len(members) >= 4:
                lines[key] = members
    out = []
    for key, members in lines.items():
        for comb in combinations(members, 4):
            out.append(comb)
    return out


def circ(pts, p, q, r):
    """Exact circumcircle: returns (qden, cx, cy, rho) reduced, or None."""
    (x1, y1), (x2, y2), (x3, y3) = p, q, r
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if d == 0:
        return None
    s1 = x1 * x1 + y1 * y1
    s2 = x2 * x2 + y2 * y2
    s3 = x3 * x3 + y3 * y3
    ux = s1 * (y2 - y3) + s2 * (y3 - y1) + s3 * (y1 - y2)
    uy = s1 * (x3 - x2) + s2 * (x1 - x3) + s3 * (x2 - x1)
    g = gcd3(ux, uy, d)
    ux, uy, d = ux // g, uy // g, d // g
    if d < 0:
        ux, uy, d = -ux, -uy, -d
    rho = (x1 * d - ux) ** 2 + (y1 * d - uy) ** 2
    return (d, ux, uy, rho)


def circle_quads(n: int, max_n_full: int = 8) -> tuple[list[tuple[int, ...]], dict]:
    """Non-collinear (concyclic) 4-subsets.  Full for n <= max_n_full."""
    pts = square_pts(n)
    V = n * n
    circles = {}
    for i in range(V):
        for j in range(i + 1, V):
            for k in range(j + 1, V):
                c = circ(pts, pts[i], pts[j], pts[k])
                if c is None:
                    continue
                if c not in circles:
                    circles[c] = 0
    out = []
    for (q, cx, cy, rho) in circles:
        members = []
        for p, (x, y) in enumerate(pts):
            a = q * x - cx
            b = q * y - cy
            if a * a + b * b == rho:
                members.append(p)
        if len(members) >= 4:
            for comb in combinations(members, 4):
                out.append(comb)
    stats = {"n_circles_ge4": len(circles)}
    return out, stats


def det4(n, ids):
    rows = [(0, 0)]
    m = []
    for i in ids:
        x, y = i % n, i // n
        m.append((x * x + y * y, x, y, 1))
    tot = 0
    for i in range(4):
        mm = [m[r] for r in range(4) if r != i]
        d3 = (mm[0][1] * (mm[1][2] * mm[2][3] - mm[1][3] * mm[2][2])
              - mm[0][2] * (mm[1][1] * mm[2][3] - mm[1][3] * mm[2][1])
              + mm[0][3] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1]))
        tot += (1 if i % 2 == 0 else -1) * m[i][0] * d3
    return tot


def all_quads(n: int, verify: bool = False):
    """All forbidden 4-subsets as sorted tuples of point ids.  Cached."""
    if n in QUAD_CACHE:
        return QUAD_CACHE[n]
    lq = line_quads(n)
    cq, st = circle_quads(n)
    quads = sorted(set(lq) | set(cq))
    if verify:
        # brute-force cross-check on small n
        ref = set()
        for ids in combinations(range(n * n), 4):
            if det4(n, ids) == 0:
                ref.add(ids)
        assert set(quads) == ref, (n, len(quads), len(ref),
                                   list(set(quads) ^ ref)[:5])
    QUAD_CACHE[n] = (quads, {"n_line_quads": len(lq), "n_circ_quads": len(cq),
                            "n_quads": len(quads), **st})
    return QUAD_CACHE[n]


def quad_masks(n: int) -> list[int]:
    quads, _ = all_quads(n)
    return [sum(1 << i for i in q) for q in quads]


def triples_by_point(n: int) -> list[list[int]]:
    quads, _ = all_quads(n)
    V = n * n
    tbp = [[] for _ in range(V)]
    for q in quads:
        m = sum(1 << i for i in q)
        for t in q:
            tbp[t].append(m & ~(1 << t))
    return tbp


def is_safe_mask(m: int, qm: list[int]) -> bool:
    for q in qm:
        if (m & q) == q:
            return False
    return True


def legal_moves(m: int, n: int, tbp: list[list[int]]) -> list[int]:
    V = n * n
    out = []
    for v in range(V):
        b = 1 << v
        if m & b:
            continue
        mm = m | b
        ok = True
        for t in tbp[v]:
            if (mm & t) == t:
                ok = False
                break
        if ok:
            out.append(v)
    return out


def is_maximal(m: int, n: int, tbp: list[list[int]]) -> bool:
    return not legal_moves(m, n, tbp)


# ------------------------------------------------------------------- data io
def load_bin(path) -> list[int]:
    raw = Path(path).read_bytes()
    k = len(raw) // 8
    return list(struct.unpack(f"<{k}Q", raw))


def d4_perms(n: int) -> list[list[int]]:
    P = []
    for m in range(8):
        fx, fy, tr = bool(m & 1), bool(m & 2), bool(m & 4)
        p = []
        for y in range(n):
            for x in range(n):
                sx = (n - 1 - x) if fx else x
                sy = (n - 1 - y) if fy else y
                nx, ny = (sy, sx) if tr else (sx, sy)
                p.append(ny * n + nx)
        P.append(p)
    return P


def apply_perm(mask: int, p: list[int]) -> int:
    o = 0
    w = mask
    while w:
        b = w & -w
        i = b.bit_length() - 1
        w ^= b
        o |= 1 << p[i]
    return o


def canon(mask: int, perms) -> int:
    return min(apply_perm(mask, p) for p in perms)


def xy(pid_: int, n: int) -> tuple[int, int]:
    return pid_ % n, pid_ // n


def bitl(m: int) -> list[int]:
    out = []
    w = m
    while w:
        b = w & -w
        out.append(b.bit_length() - 1)
        w ^= b
    return out


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        p = self.p
        if x not in p:
            p[x] = x
            return x
        r = x
        while p[r] != r:
            r = p[r]
        while p[x] != r:
            p[x], x = r, p[x]
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb

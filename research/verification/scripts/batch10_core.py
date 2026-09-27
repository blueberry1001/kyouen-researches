"""Shared exact-integer core for batch-10 verification (B221-B300).

Board B_n = {0,...,n-1}^2, point id = y*n+x.
Row for det4: [x^2+y^2, x, y, 1].
det4 == 0  <=>  concyclic OR collinear (degenerate circle).
Collinear  <=>  every 3-subset has det3([x,y,1]) == 0.
"""

from __future__ import annotations

from itertools import combinations, permutations
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# Determinants
# ---------------------------------------------------------------------------


def det3_rows(r0, r1, r2) -> int:
    return (
        r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
        - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
        + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0])
    )


def det4_rows(r0, r1, r2, r3) -> int:
    rows = (r0, r1, r2, r3)
    det = 0
    for c0 in range(4):
        sign = 1 if c0 % 2 == 0 else -1
        cols = [c for c in range(4) if c != c0]
        m = [[rows[i][c] for c in cols] for i in (1, 2, 3)]
        minor = det3_rows(m[0], m[1], m[2])
        det += sign * rows[0][c0] * minor
    return det


def xy(n: int, pid: int) -> Tuple[int, int]:
    return (pid % n, pid // n)


def point_row(n: int, pid: int) -> Tuple[int, int, int, int]:
    x, y = xy(n, pid)
    return (x * x + y * y, x, y, 1)


def area2(n: int, a: int, b: int, c: int) -> int:
    """Twice signed area of triangle (collinearity test)."""
    xa, ya = xy(n, a)
    xb, yb = xy(n, b)
    xc, yc = xy(n, c)
    return (xb - xa) * (yc - ya) - (yb - ya) * (xc - xa)


def is_collinear4(n: int, ids: Sequence[int]) -> bool:
    return all(area2(n, ids[i], ids[j], ids[k]) == 0
               for i, j, k in combinations(range(4), 3))


# ---------------------------------------------------------------------------
# Forbidden families
# ---------------------------------------------------------------------------


def classify_quads(n: int) -> Tuple[List[Tuple[int, int, int, int]],
                                    List[Tuple[int, int, int, int]]]:
    """Return (collinear_quads, proper_circle_quads)."""
    rows = [point_row(n, i) for i in range(n * n)]
    coll: List[Tuple[int, int, int, int]] = []
    circ: List[Tuple[int, int, int, int]] = []
    for ids in combinations(range(n * n), 4):
        if det4_rows(*[rows[i] for i in ids]) == 0:
            if is_collinear4(n, ids):
                coll.append(ids)
            else:
                circ.append(ids)
    return coll, circ


def forbidden_quads(n: int) -> List[Tuple[int, int, int, int]]:
    coll, circ = classify_quads(n)
    return coll + circ


def quads_by_point(n: int, quads: Iterable[Sequence[int]]) -> List[List[int]]:
    """For each point, list of quad bitmasks containing it."""
    out: List[List[int]] = [[] for _ in range(n * n)]
    for ids in quads:
        m = 0
        for i in ids:
            m |= 1 << i
        for i in ids:
            out[i].append(m)
    return out


# ---------------------------------------------------------------------------
# Game evaluation over a forbidden family
# ---------------------------------------------------------------------------


class Game:
    def __init__(self, n: int, quads: Iterable[Sequence[int]]):
        self.n = n
        self.V = n * n
        self.quads = list(quads)
        self.qbp = quads_by_point(n, self.quads)

    def safe_add(self, occ: int, v: int) -> bool:
        mask = occ | (1 << v)
        for q in self.qbp[v]:
            if (q & mask) == q:
                return False
        return True

    def legal(self, occ: int) -> List[int]:
        empty = ((1 << self.V) - 1) ^ occ
        out = []
        v = 0
        while empty:
            if empty & 1 and self.safe_add(occ, v):
                out.append(v)
            empty >>= 1
            v += 1
        return out

    def legal_mask(self, occ: int) -> int:
        empty = ((1 << self.V) - 1) ^ occ
        out = 0
        v = 0
        while empty:
            if empty & 1 and self.safe_add(occ, v):
                out |= 1 << v
            empty >>= 1
            v += 1
        return out


def grundy_map(game: Game, root: int = 0,
               max_stones: Optional[int] = None) -> Dict[int, int]:
    """DFS memo of exact g(S) for all states reachable from `root`."""
    sys_limit = 10 ** 7
    import sys
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, sys_limit))
    memo: Dict[int, int] = {}

    def go(occ: int) -> int:
        if occ in memo:
            return memo[occ]
        if max_stones is not None and occ.bit_count() >= max_stones:
            memo[occ] = 0
            return 0
        moves = game.legal(occ)
        if not moves:
            memo[occ] = 0
            return 0
        seen = set()
        for u in moves:
            seen.add(go(occ | (1 << u)))
        g = 0
        while g in seen:
            g += 1
        memo[occ] = g
        return g

    go(root)
    sys.setrecursionlimit(old)
    return memo


def winner_from_grundy(g0: int) -> str:
    """P-position (g=0) => previous player wins => Second (後手)."""
    return "Second" if g0 == 0 else "First"


def first_move_labels(game: Game, memo: Dict[int, int]) -> Dict[int, str]:
    """For each single-stone start p: 'Win' if opponent is P after p."""
    out = {}
    for p in range(game.V):
        key = 1 << p
        if not game.safe_add(0, p):
            out[p] = "Illegal"
            continue
        if key not in memo:
            # compute on demand
            grundy_map(game, root=key)
        g = memo.get(key, None)
        if g is None:
            gmap = grundy_map(game, root=key)
            g = gmap[key]
        out[p] = "Win" if g == 0 else "Lose"
    return out


# ---------------------------------------------------------------------------
# Utilities for statistics (B291-B300)
# ---------------------------------------------------------------------------


def u_gain(game: Game, occ: int, p: int) -> int:
    """u_S(p) = |L(S) \\ ({p} u L(S+p))| = newly-illegal legal points."""
    before = game.legal_mask(occ)
    after = game.legal_mask(occ | (1 << p))
    removed = before & ~after & ~(1 << p)
    return removed.bit_count()


def pair_synergy(game: Game, occ: int, p: int, q: int) -> int:
    """Points legal at S, blocked by {p,q} jointly beyond those blocked by
    neither alone (counting p,q themselves out)."""
    L = game.legal_mask(occ)
    Lp = game.legal_mask(occ | (1 << p))
    Lq = game.legal_mask(occ | (1 << q))
    Lpq = game.legal_mask(occ | (1 << p) | (1 << q))
    only_joint = L & ~Lp & ~Lq & ~Lpq & ~(1 << p) & ~(1 << q)
    return only_joint.bit_count()


def dist_pairs(n: int, S: Sequence[int]) -> Tuple[int, ...]:
    pts = [xy(n, i) for i in S]
    ds = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            dx = pts[i][0] - pts[j][0]
            dy = pts[i][1] - pts[j][1]
            ds.append(dx * dx + dy * dy)
    return tuple(sorted(ds))


def boundary_dists(n: int, S: Sequence[int]) -> Tuple[int, ...]:
    """For each point, distance to nearest board edge (in lattice steps)."""
    out = []
    for i in S:
        x, y = xy(n, i)
        out.append(min(x, y, n - 1 - x, n - 1 - y))
    return tuple(sorted(out))

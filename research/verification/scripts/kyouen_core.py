#!/usr/bin/env python3
"""Shared integer-geometry kyouen engine for verification batches.

Boards are arbitrary finite subsets of Z^2. Point index is position in
self.points. Forbidden 4-set iff det[x^2+y^2, x, y, 1] rows are 0
(concyclic or collinear). Safe set = bitmask with no forbidden 4-subset.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Iterable


def det4(p0, p1, p2, p3) -> int:
    rows = (p0, p1, p2, p3)
    total = 0
    for i in range(4):
        mm = [rows[r] for r in range(4) if r != i]
        det3 = (
            mm[0][1] * (mm[1][2] * mm[2][3] - mm[1][3] * mm[2][2])
            - mm[0][2] * (mm[1][1] * mm[2][3] - mm[1][3] * mm[2][1])
            + mm[0][3] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
        )
        # expand along column 0: row i, col 0
        total += (1 if i % 2 == 0 else -1) * rows[i][0] * det3
    return total


def is_forbidden_quad(pts4) -> bool:
    a, b, c, d = pts4
    return det4((a[0] * a[0] + a[1] * a[1], a[0], a[1], 1),
                (b[0] * b[0] + b[1] * b[1], b[0], b[1], 1),
                (c[0] * c[0] + c[1] * c[1], c[0], c[1], 1),
                (d[0] * d[0] + d[1] * d[1], d[0], d[1], 1)) == 0


def square_points(n: int) -> list[tuple[int, int]]:
    return [(x, y) for y in range(n) for x in range(n)]


def rect_points(w: int, h: int) -> list[tuple[int, int]]:
    """w columns (x=0..w-1), h rows (y=0..h-1)."""
    return [(x, y) for y in range(h) for x in range(w)]


class Board:
    """Point set + forbidden-quad index + legal-move / game solvers."""

    def __init__(self, points: list[tuple[int, int]], name: str = ""):
        self.points = list(points)
        self.V = len(points)
        self.name = name or f"board[{self.V}]"
        self.rows = [(x * x + y * y, x, y, 1) for (x, y) in self.points]
        self.quads: list[int] = []
        self.quads_by_pt: list[list[int]] = [[] for _ in range(self.V)]
        for ids in combinations(range(self.V), 4):
            r = [self.rows[i] for i in ids]
            if det4(*r) == 0:
                m = (1 << ids[0]) | (1 << ids[1]) | (1 << ids[2]) | (1 << ids[3])
                self.quads.append(m)
                for i in ids:
                    self.quads_by_pt[i].append(m)
        self.full = (1 << self.V) - 1

    # --- legality ---
    def is_safe(self, occ: int) -> bool:
        for q in self.quads:
            if (occ & q) == q:
                return False
        return True

    def legal_moves(self, occ: int) -> list[int]:
        out = []
        empty = self.full ^ occ
        v = 0
        while empty:
            if empty & 1:
                bit = 1 << v
                ok = True
                for q in self.quads_by_pt[v]:
                    if (q & (occ | bit)) == q:
                        ok = False
                        break
                if ok:
                    out.append(v)
            empty >>= 1
            v += 1
        return out

    def is_maximal(self, occ: int) -> bool:
        return self.is_safe(occ) and not self.legal_moves(occ)

    # --- random greedy ---
    def random_greedy_terminal(self, rng, first_move: int | None = None) -> tuple[int, int]:
        """Return (terminal_mask, terminal_size). rng needs .randrange."""
        occ = 0
        if first_move is not None:
            occ = 1 << first_move
        while True:
            mv = self.legal_moves(occ)
            if not mv:
                return occ, occ.bit_count()
            occ |= 1 << mv[rng.randrange(len(mv))]

    # --- full retrograde solve (outcomes only) ---
    def solve_outcomes(self) -> dict[int, int]:
        """Memo: occ -> 1 if player-to-move wins, 0 if loses. All reachable."""
        memo: dict[int, int] = {}
        stack = [0]
        order: list[int] = []
        seen = {0}
        # iterative DFS to get children evaluated first would need post-order;
        # instead memoized recursion via explicit stack with state.
        # Simple approach: recursive with high limit (depth <= V <= ~40).
        import sys
        sys.setrecursionlimit(100000)

        def ev(occ: int) -> int:
            hit = memo.get(occ)
            if hit is not None:
                return hit
            mv = self.legal_moves(occ)
            if not mv:
                memo[occ] = 0
                return 0
            win = False
            for u in mv:
                if ev(occ | (1 << u)) == 0:
                    win = True
            memo[occ] = 1 if win else 0
            return memo[occ]

        ev(0)
        return memo

    def solve_grundy(self) -> dict[int, int]:
        import sys
        sys.setrecursionlimit(100000)
        memo: dict[int, int] = {}

        def ev(occ: int) -> int:
            hit = memo.get(occ)
            if hit is not None:
                return hit
            mv = self.legal_moves(occ)
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
        return memo

    # --- random-greedy terminal size distribution (exact DP) ---
    def exact_terminal_dist(self) -> dict[int, float]:
        """Distribution of terminal |S| under uniform random legal-move greedy.

        P(X=t | occ) averaged over legal moves; memoized.
        """
        import sys
        sys.setrecursionlimit(100000)
        memo: dict[int, dict[int, float]] = {}

        def dist(occ: int) -> dict[int, float]:
            hit = memo.get(occ)
            if hit is not None:
                return hit
            mv = self.legal_moves(occ)
            if not mv:
                d = {occ.bit_count(): 1.0}
                memo[occ] = d
                return d
            acc: dict[int, float] = defaultdict(float)
            w = 1.0 / len(mv)
            for u in mv:
                for t, p in dist(occ | (1 << u)).items():
                    acc[t] += p * w
            d = dict(acc)
            memo[occ] = d
            return d

        return dist(0)

    def max_safe_size(self) -> int:
        """DFS branch-and-bound maximum safe set size."""
        best = 0
        quads = self.quads
        V = self.V

        def dfs(occ: int, candidates: int, size: int) -> None:
            nonlocal best
            if size > best:
                best = size
            if not candidates:
                return
            # simple bound
            if size + candidates.bit_count() <= best:
                return
            # pick lowest candidate
            while candidates:
                b = candidates & -candidates
                v = b.bit_length() - 1
                candidates ^= b
                # try including v
                nxt_occ = occ | b
                if self.is_safe(nxt_occ):
                    # remaining candidates excluding those that complete a quad
                    remain = candidates
                    bad = 0
                    for q in self.quads_by_pt[v]:
                        if (q & nxt_occ) == q:
                            pass
                        elif (q & ~nxt_occ & self.full).bit_count() == 1:
                            miss = q & ~nxt_occ
                            bad |= miss
                    dfs(nxt_occ, remain & ~bad, size + 1)
                # excluding v already handled by looping

        dfs(0, self.full, 0)
        return best


def board_square(n: int) -> Board:
    return Board(square_points(n), name=f"{n}x{n}")


def board_rect(w: int, h: int) -> Board:
    return Board(rect_points(w, h), name=f"{w}x{h}")


def board_square_minus(n: int, deleted: Iterable[int]) -> Board:
    """Square n×n with points removed. deleted are (x,y) coords."""
    dead = set(deleted)
    pts = [(x, y) for y in range(n) for x in range(n) if (x, y) not in dead]
    return Board(pts, name=f"{n}x{n}-del{len(dead)}")

#!/usr/bin/env python3
"""Round5 B482-B500 residual stats + greedy reach on n=3,4,5.

Uses batch03_cache.pkl recs (occ,k,g,L,Rhash,...) + board quads.
Outputs research/verification/round5_b482b500.json
"""
from __future__ import annotations

import json
import math
import pickle
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round5_b482b500.json"
CACHE = ROOT / "research" / "verification" / "batch03_cache.pkl"
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import Board, board_square  # noqa: E402


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0
            for t in range(i, j + 1):
                rk[order[t]] = avg
            i = j + 1
        return rk

    if len(xs) < 3:
        return None
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    dx = math.sqrt(sum((v - mx) ** 2 for v in rx))
    dy = math.sqrt(sum((v - my) ** 2 for v in ry))
    return num / (dx * dy) if dx and dy else None


def p_graph(nv_empty: int, edges: list[tuple[int, int]]):
    adj = [set() for _ in range(nv_empty)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def count_triangles(adj) -> int:
    t = 0
    for a in range(len(adj)):
        for b in adj[a]:
            if b <= a:
                continue
            t += len(adj[a] & adj[b])
    return t


def comp_sizes(adj) -> list[int]:
    n = len(adj)
    seen = [False] * n
    sizes = []
    for i in range(n):
        if seen[i]:
            continue
        stack = [i]
        seen[i] = True
        sz = 0
        while stack:
            u = stack.pop()
            sz += 1
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
        sizes.append(sz)
    return sizes



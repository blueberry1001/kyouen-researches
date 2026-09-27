#!/usr/bin/env python3
"""Round2 B422: longest induced cycle in the 311-vertex non-max G_12 component.

Fixes the induced-cycle DFS: the start vertex is allowed as the closing
neighbor; intermediate vertices may not touch earlier path vertices.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches")
sys.path.insert(0, str(ROOT / "research/verification/scripts"))
from kyouen_core import Board, square_points  # noqa: E402

OUT = ROOT / "research/verification/round2_b411.json"


def bits(x: int) -> list[int]:
    return [i for i in range(49) if (x >> i) & 1]


def legal_adds(board: Board, occ: int) -> list[int]:
    out = []
    v = 0
    e = board.full ^ occ
    while e:
        if e & 1:
            bit = 1 << v
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & (occ | bit)) == q:
                    ok = False
                    break
            if ok:
                out.append(v)
        e >>= 1
        v += 1
    return out


def is_safe(board: Board, occ: int) -> bool:
    for q in board.quads:
        if (occ & q) == q:
            return False
    return True


def grow_component(board: Board, seed: int, max_states: int = 5000):
    seen = {seed}
    q = deque([seed])
    while q and len(seen) < max_states:
        u = q.popleft()
        if bin(u).count("1") > 12:
            for i in bits(u):
                v = u ^ (1 << i)
                if v not in seen and is_safe(board, v):
                    seen.add(v)
                    q.append(v)
        for i in legal_adds(board, u):
            v = u | (1 << i)
            if v not in seen and bin(v).count("1") >= 12:
                seen.add(v)
                q.append(v)
    return seen


def longest_induced(adj, nodes, limit=16):
    idx = {u: i for i, u in enumerate(nodes)}
    n = len(nodes)
    a = [set() for _ in range(n)]
    for u in nodes:
        for v in adj[u]:
            a[idx[u]].add(idx[v])
    best = 0
    best_path = []
    for s in range(n):
        # DFS: path from s, cannot revisit; induced: no edge between
        # non-consecutive path vertices except the closing edge to s.
        stack = [(s, [s], {s})]
        while stack:
            u, path, pset = stack.pop()
            L = len(path)
            if L >= 3 and s in a[u]:
                # already induced by construction
                if L > best:
                    best = L
                    best_path = [nodes[x] for x in path]
            if L >= limit:
                continue
            for v in a[u]:
                if v in pset:
                    continue
                if v == s:
                    continue  # only close, do not extend through s
                # v must not touch path except u (and may touch s for closing)
                bad = False
                for w in path[1:-1]:
                    if v in a[w]:
                        bad = True
                        break
                if bad:
                    continue
                # also v not adjacent to s unless we will close later —
                # adjacency to s is allowed (it becomes the closing edge),
                # but then we cannot add more vertices after; handle by
                # allowing it (closing check uses s in a[u]).
                stack.append((v, path + [v], pset | {v}))
    return best, best_path


def main():
    board = Board(square_points(7), "n7")
    data = json.loads(OUT.read_text())
    m = sum(1 << c for c in [0, 2, 7, 11, 14, 15, 25, 27, 33, 38, 43, 44, 48])
    states = grow_component(board, m, max_states=5000)
    adj = defaultdict(set)
    for s in states:
        for i in range(49):
            t = s ^ (1 << i)
            if t in states and t > s:
                adj[s].add(t)
                adj[t].add(s)
    nodes = sorted(states)
    print("n", len(nodes), "e", sum(len(v) for v in adj.values()) // 2, flush=True)
    best, path = longest_induced(adj, nodes, limit=16)
    print("longest induced", best, flush=True)
    if path:
        print("path", [bits(x) for x in path], flush=True)
    # also report shortest cycle (girth-ish): BFS from each node
    girth = 99
    for s in nodes:
        dist = {s: 0}
        par = {s: None}
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v not in dist:
                    dist[v] = dist[u] + 1
                    par[v] = u
                    q.append(v)
                elif par[u] != v:
                    girth = min(girth, dist[u] + dist[v] + 1)
    print("girth", girth)
    data["B422_cycle"] = {
        "n": len(nodes),
        "longest_induced_cycle": best,
        "cycle_example": [bits(x) for x in path] if path else None,
        "girth": girth if girth < 99 else None,
    }
    OUT.write_text(json.dumps(data, indent=2, default=str))
    print("wrote")


if __name__ == "__main__":
    main()

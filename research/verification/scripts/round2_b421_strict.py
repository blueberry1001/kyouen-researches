#!/usr/bin/env python3
"""Round2 B421-B424: tree/cycle structure of non-isolated non-max G_12 components."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path

ROOT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches")
sys.path.insert(0, str(ROOT / "research/verification/scripts"))
from kyouen_core import Board, square_points  # noqa: E402

RES = ROOT / "results"
OUT = ROOT / "research/verification/round2_b411.json"


def bits(x: int) -> list[int]:
    return [i for i in range(49) if (x >> i) & 1]


def d4_cell(c, k):
    x, y = c % 7, c // 7
    for _ in range(k % 4):
        x, y = y, 6 - x
    if k >= 4:
        x = 6 - x
    return y * 7 + x


def d4_mask(s, k):
    out = 0
    for i in bits(s):
        out |= 1 << d4_cell(i, k)
    return out


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


def analyze_tree_cycle(board: Board, states: set[int]):
    sset = states
    adj = defaultdict(set)
    ne = 0
    for s in sset:
        for i in range(49):
            t = s ^ (1 << i)
            if t in sset and t > s:
                adj[s].add(t)
                adj[t].add(s)
                ne += 1
    nv = len(sset)
    # connected
    start = next(iter(sset))
    seen = {start}
    q = deque([start])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    connected = len(seen) == nv
    cyclomatic = ne - nv + 1 if connected else ne - nv + "multi"
    # longest induced cycle (exact DFS) if nv small enough
    nodes = sorted(sset)
    idx = {u: i for i, u in enumerate(nodes)}
    a = [set() for _ in range(nv)]
    for u in nodes:
        for v in adj[u]:
            a[idx[u]].add(idx[v])
    best = 0
    best_path = []
    if nv <= 400:
        for s in range(nv):
            stack = [(s, [s], {s})]
            while stack:
                u, path, pset = stack.pop()
                if len(path) >= 3 and s in a[u]:
                    ok = True
                    L = len(path)
                    for i in range(L):
                        for j in range(i + 2, L):
                            if j == L - 1 and i == 0:
                                continue
                            if path[j] in a[path[i]]:
                                ok = False
                                break
                        if not ok:
                            break
                    if ok and len(path) > best:
                        best = len(path)
                        best_path = [nodes[x] for x in path]
                if len(path) >= 12:
                    continue
                for v in a[u]:
                    if v in pset:
                        continue
                    if v == s and len(path) < 3:
                        continue
                    bad = False
                    for w in path[:-1]:
                        if v in a[w]:
                            bad = True
                            break
                    if bad:
                        continue
                    stack.append((v, path + [v], pset | {v}))
    return {
        "n_vertices": nv,
        "n_edges": ne,
        "connected": connected,
        "is_tree": connected and ne == nv - 1,
        "cyclomatic": (ne - nv + 1) if connected else None,
        "longest_induced_cycle": best if nv <= 400 else None,
        "cycle_example": [bits(x) for x in best_path[:12]] if best_path else None,
    }


def main():
    board = Board(square_points(7), "n7")
    data = json.loads(OUT.read_text())
    nm = data["nonmax_search"]
    seeds = []
    for e in nm["examples_noniso"]:
        m = sum(1 << c for c in e["seed"])
        seeds.append(m)

    # also grow the peaks that were size-1? and the 311-component fully
    results = []
    for m in seeds:
        states = grow_component(board, m, max_states=5000)
        info = analyze_tree_cycle(board, states)
        info["seed"] = bits(m)
        info["layers"] = dict(Counter(bin(s).count("1") for s in states))
        info["n13"] = sum(1 for s in states if bin(s).count("1") == 13)
        info["has14"] = any(bin(s).count("1") == 14 for s in states)
        results.append(info)
        print(info["seed"], info["n_vertices"], info["n_edges"], info["is_tree"], info["cyclomatic"], info["longest_induced_cycle"], info["n13"], flush=True)

    data["B421_B424_strict"] = {
        "n_components": len(results),
        "all_lt_903": all(r["n_vertices"] < 903 for r in results),
        "max_n": max(r["n_vertices"] for r in results),
        "max_n13": max(r["n13"] for r in results),
        "all_n13_le_8": all(r["n13"] <= 8 for r in results),
        "n_trees": sum(1 for r in results if r["is_tree"]),
        "n_with_cycle": sum(1 for r in results if (r["cyclomatic"] or 0) > 0),
        "max_induced_cycle": max((r["longest_induced_cycle"] or 0) for r in results),
        "details": results,
    }
    OUT.write_text(json.dumps(data, indent=2, default=str))
    print(json.dumps(data["B421_B424_strict"], indent=2, default=str)[:2500])


if __name__ == "__main__":
    main()

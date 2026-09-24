#!/usr/bin/env python3
"""探索10: 極大安全配置のサイズスペクトル全数と、n=5 の勝ち初手後の終局集合。"""
from __future__ import annotations

import json
import random
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"


def det3(m):
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )


def det4_pts(p, q, r, s):
    A = [
        [p[0] ** 2 + p[1] ** 2, p[0], p[1], 1],
        [q[0] ** 2 + q[1] ** 2, q[0], q[1], 1],
        [r[0] ** 2 + r[1] ** 2, r[0], r[1], 1],
        [s[0] ** 2 + s[1] ** 2, s[0], s[1], 1],
    ]
    return (
        A[0][0] * det3([row[1:] for row in A[1:]])
        - A[0][1] * det3([[A[i][j] for j in (0, 2, 3)] for i in (1, 2, 3)])
        + A[0][2] * det3([[A[i][j] for j in (0, 1, 3)] for i in (1, 2, 3)])
        - A[0][3] * det3([row[:3] for row in A[1:]])
    )


class Hypergraph:
    def __init__(self, n: int):
        self.n = n
        self.V = n * n
        self.pts = [(i % n, i // n) for i in range(self.V)]
        self.complete = {i: [] for i in range(self.V)}
        self.n_bad = 0
        for idx in combinations(range(self.V), 4):
            q = [self.pts[i] for i in idx]
            if det4_pts(*q) == 0:
                self.n_bad += 1
                for t in combinations(idx, 3):
                    p = next(x for x in idx if x not in t)
                    self.complete[p].append(frozenset(t))

    def is_safe_with(self, chosen: frozenset, p: int) -> bool:
        if p in chosen:
            return False
        for triple in self.complete[p]:
            if triple <= chosen:
                return False
        return True

    def legal_moves(self, chosen: frozenset):
        out = []
        for p in range(self.V):
            if p in chosen:
                continue
            if self.is_safe_with(chosen, p):
                out.append(p)
        return out

    def maximal_size_hist_dfs(self, limit_nodes: int = 5_000_000):
        """全極大安全配置を構成順 (id 増加) で一意に数える。"""
        hist = Counter()
        nodes = 0
        complete_flag = True

        def rec(chosen: frozenset, start: int):
            nonlocal nodes, complete_flag
            nodes += 1
            if nodes > limit_nodes:
                complete_flag = False
                return
            can_extend = False
            for p in range(self.V):
                if p in chosen:
                    continue
                if not self.is_safe_with(chosen, p):
                    continue
                can_extend = True
                if p >= start:
                    rec(chosen | {p}, p + 1)
                    if not complete_flag:
                        return
            if not can_extend:
                hist[len(chosen)] += 1

        rec(frozenset(), 0)
        return hist, complete_flag, nodes

    def greedy_samples(self, trials: int = 3000, seed: int = 0):
        rng = random.Random(seed)
        hist = Counter()
        for _ in range(trials):
            order = list(range(self.V))
            rng.shuffle(order)
            S = frozenset()
            for p in order:
                if self.is_safe_with(S, p):
                    S = S | {p}
            hist[len(S)] += 1
        return hist


def main():
    report = {}
    for n in (4, 5, 6):
        print(f"=== n={n} ===", flush=True)
        hg = Hypergraph(n)
        print(f"  forbidden quads: {hg.n_bad}", flush=True)
        if n <= 4:
            hist, complete, nodes = hg.maximal_size_hist_dfs()
            report[n] = {
                "forbidden": hg.n_bad,
                "maximal_size_hist": dict(sorted(hist.items())),
                "complete": complete,
                "dfs_nodes": nodes,
            }
            print(f"  COMPLETE maximal hist: {report[n]['maximal_size_hist']} nodes={nodes}", flush=True)
        else:
            hist, complete, nodes = hg.maximal_size_hist_dfs(limit_nodes=8_000_000)
            g = hg.greedy_samples(4000)
            report[n] = {
                "forbidden": hg.n_bad,
                "dfs_partial_hist": dict(sorted(hist.items())),
                "dfs_complete": complete,
                "dfs_nodes": nodes,
                "greedy_hist": dict(sorted(g.items())),
            }
            print(f"  DFS complete={complete} hist={report[n]['dfs_partial_hist']} nodes={nodes}", flush=True)
            print(f"  greedy hist: {report[n]['greedy_hist']}", flush=True)

    out = OUT / "exploration_report_10.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

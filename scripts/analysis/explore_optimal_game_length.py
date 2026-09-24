#!/usr/bin/env python3
"""探索7b: 合法手を厳密判定した最適対局長と終局石数。"""
from __future__ import annotations

import json
import struct
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
CERTS = ROOT / "night-research"


def det3(m):
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )


def det4_pts(p, q, r, s):
    A = [[p[0] * p[0] + p[1] * p[1], p[0], p[1], 1],
         [q[0] * q[0] + q[1] * q[1], q[0], q[1], 1],
         [r[0] * r[0] + r[1] * r[1], r[0], r[1], 1],
         [s[0] * s[0] + s[1] * s[1], s[0], s[1], 1]]
    return (
        A[0][0] * det3([row[1:] for row in A[1:]])
        - A[0][1] * det3([[A[i][j] for j in (0, 2, 3)] for i in (1, 2, 3)])
        + A[0][2] * det3([[A[i][j] for j in (0, 1, 3)] for i in (1, 2, 3)])
        - A[0][3] * det3([row[:3] for row in A[1:]])
    )


class Geometry:
    def __init__(self, n: int):
        self.n = n
        self.pts = [(i % n, i // n) for i in range(n * n)]
        self.bad = set()
        # triple -> list of points completing a forbidden quad
        self.complete = defaultdict(list)
        for idx in combinations(range(n * n), 4):
            q = [self.pts[i] for i in idx]
            if det4_pts(*q) == 0:
                self.bad.add(idx)
                for t in combinations(idx, 3):
                    s = frozenset(t)
                    p = next(x for x in idx if x not in t)
                    self.complete[s].append(p)

    def legal_add(self, occupied: frozenset, p: int) -> bool:
        if p in occupied:
            return False
        if len(occupied) < 3:
            return True
        for triple in combinations(occupied, 3):
            s = frozenset(triple)
            if p in self.complete.get(s, ()):
                return False
        return True


def parse_cert(path: Path):
    with path.open("rb") as f:
        f.read(8)
        version, board = struct.unpack("<II", f.read(8))
        node_count = struct.unpack("<Q", f.read(8))[0]
        root_lo = struct.unpack("<Q", f.read(8))[0]
        root_hi, forbidden = struct.unpack("<II", f.read(8))
        nodes = {}
        for _ in range(node_count):
            data = f.read(16)
            lo, hi, outcome, witness, rank, reserved = struct.unpack("<QIBBBB", data)
            nodes[(lo, hi)] = {
                "outcome": outcome,
                "witness": witness,
                "rank": rank,
                "lo": lo,
                "hi": hi,
            }
    return board, node_count, (root_lo, root_hi), nodes


def bits_to_set(lo, hi, V):
    s = set()
    for i in range(min(64, V)):
        if lo & (1 << i):
            s.add(i)
    for i in range(64, V):
        if hi & (1 << (i - 64)):
            s.add(i)
    return frozenset(s)


def set_to_key(s, V):
    lo = hi = 0
    for i in s:
        if i < 64:
            lo |= 1 << i
        else:
            hi |= 1 << (i - 64)
    return (lo, hi)


def analyze(path: Path):
    board, ncount, root, nodes = parse_cert(path)
    V = board * board
    geo = Geometry(board)
    sets = {k: bits_to_set(k[0], k[1], V) for k in nodes}

    loss_children = defaultdict(list)
    win_witness_child = {}
    for key, node in nodes.items():
        S = sets[key]
        if node["outcome"] == 2:
            w = node["witness"]
            if w < V and w not in S:
                win_witness_child[key] = set_to_key(S | {w}, V)
        else:
            for p in range(V):
                if p in S:
                    continue
                if geo.legal_add(S, p):
                    ck = set_to_key(S | {p}, V)
                    if ck in nodes:
                        loss_children[key].append(ck)

    memo_min, memo_max, memo_reach = {}, {}, {}

    def stones_of(key):
        return len(sets[key])

    def calc(key):
        if key in memo_min:
            return
        node = nodes[key]
        if node["outcome"] == 1:
            ch = loss_children.get(key, [])
            if not ch:
                memo_min[key] = 0
                memo_max[key] = 0
                memo_reach[key] = {stones_of(key)}
                return
            mins, maxs, st = [], [], set()
            for c in ch:
                calc(c)
                mins.append(memo_min[c])
                maxs.append(memo_max[c])
                st |= memo_reach[c]
            memo_min[key] = 1 + min(mins)
            memo_max[key] = 1 + max(maxs)
            memo_reach[key] = st
        else:
            c = win_witness_child.get(key)
            if c is None or c not in nodes:
                memo_min[key] = 0
                memo_max[key] = 0
                memo_reach[key] = {stones_of(key)}
                return
            calc(c)
            memo_min[key] = 1 + memo_min[c]
            memo_max[key] = 1 + memo_max[c]
            memo_reach[key] = memo_reach[c]

    calc(root)

    # true terminals
    terms = {
        k: stones_of(k)
        for k, n in nodes.items()
        if n["outcome"] == 1 and not loss_children.get(k)
    }
    # verify terminals really have no legal moves
    false_terms = 0
    for k, S in sets.items():
        if nodes[k]["outcome"] != 1:
            continue
        if loss_children.get(k):
            continue
        for p in range(V):
            if geo.legal_add(S, p):
                false_terms += 1
                break

    return {
        "n": board,
        "nodes": ncount,
        "root_outcome": "LOSS" if nodes[root]["outcome"] == 1 else "WIN",
        "min_moves_from_empty": memo_min[root],
        "max_moves_from_empty": memo_max[root],
        "terminal_stones_reachable": sorted(memo_reach[root]),
        "terminal_stone_hist": dict(sorted(Counter(terms.values()).items())),
        "n_terminals": len(terms),
        "false_terminals": false_terms,
        "n_bad_quads": len(geo.bad),
    }


def main():
    report = {}
    print("=== 合法手厳密判定つき最適対局長 ===")
    for n in range(1, 8):
        path = CERTS / f"kyouen-{n}x{n}.cert"
        if not path.exists():
            continue
        print(f"  n={n} analyzing...")
        r = analyze(path)
        report[n] = r
        print(f"    root={r['root_outcome']} moves=[{r['min_moves_from_empty']},{r['max_moves_from_empty']}] "
              f"reach_stones={r['terminal_stones_reachable']} term_hist={r['terminal_stone_hist']} "
              f"n_term={r['n_terminals']} false_term={r['false_terminals']}")

    out = OUT / "exploration_report_7b.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

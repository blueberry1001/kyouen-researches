#!/usr/bin/env python3
"""探索9: D4 正規化を考慮した証明書 DAG の最適対局長。"""
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
    A = [[p[0] ** 2 + p[1] ** 2, p[0], p[1], 1],
         [q[0] ** 2 + q[1] ** 2, q[0], q[1], 1],
         [r[0] ** 2 + r[1] ** 2, r[0], r[1], 1],
         [s[0] ** 2 + s[1] ** 2, s[0], s[1], 1]]
    return (
        A[0][0] * det3([row[1:] for row in A[1:]])
        - A[0][1] * det3([[A[i][j] for j in (0, 2, 3)] for i in (1, 2, 3)])
        + A[0][2] * det3([[A[i][j] for j in (0, 1, 3)] for i in (1, 2, 3)])
        - A[0][3] * det3([row[:3] for row in A[1:]])
    )


def d4_maps(n):
    """8 つの D4 変換 (x,y) -> (x',y')。"""
    def ident(x, y):
        return x, y

    def rot90(x, y):
        return y, n - 1 - x

    def rot180(x, y):
        return n - 1 - x, n - 1 - y

    def rot270(x, y):
        return n - 1 - y, x

    def refl_x(x, y):
        return n - 1 - x, y

    def refl_y(x, y):
        return x, n - 1 - y

    def refl_diag(x, y):
        return y, x

    def refl_antidiag(x, y):
        return n - 1 - y, n - 1 - x

    return [ident, rot90, rot180, rot270, refl_x, refl_y, refl_diag, refl_antidiag]


class Board:
    def __init__(self, n: int):
        self.n = n
        self.V = n * n
        self.pts = [(i % n, i // n) for i in range(self.V)]
        self.id_of = {(i % n, i // n): i for i in range(self.V)}
        self.maps = d4_maps(n)
        self.complete = defaultdict(list)
        self.bad = set()
        for idx in combinations(range(self.V), 4):
            q = [self.pts[i] for i in idx]
            if det4_pts(*q) == 0:
                self.bad.add(frozenset(idx))
                for t in combinations(idx, 3):
                    p = next(x for x in idx if x not in t)
                    self.complete[frozenset(t)].append(p)

    def legal_add(self, occ: frozenset, p: int) -> bool:
        if p in occ or len(occ) < 3:
            return p not in occ
        for triple in combinations(occ, 3):
            if p in self.complete.get(frozenset(triple), ()):
                return False
        return True

    def transform_set(self, occ: frozenset, f) -> frozenset:
        return frozenset(self.id_of[f(*self.pts[i])] for i in occ)

    def canon_key(self, occ: frozenset):
        best = None
        for f in self.maps:
            lo = hi = 0
            for i in self.transform_set(occ, f):
                if i < 64:
                    lo |= 1 << i
                else:
                    hi |= 1 << (i - 64)
            key = (hi, lo)  # compare hi first like KYOENC4
            if best is None or key < best:
                best = key
        return best

    def key_to_occ(self, lo, hi) -> frozenset:
        s = set()
        for i in range(min(64, self.V)):
            if lo & (1 << i):
                s.add(i)
        for i in range(64, self.V):
            if hi & (1 << (i - 64)):
                s.add(i)
        return frozenset(s)


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
            nodes[(hi, lo)] = {
                "outcome": outcome,
                "witness": witness,
                "rank": rank,
                "lo": lo,
                "hi": hi,
            }
        return board, node_count, (root_hi, root_lo), nodes


def analyze(path: Path, max_n: int = 6):
    board, ncount, root, nodes = parse_cert(path)
    if board > max_n:
        return {"n": board, "skipped": True}
    geo = Board(board)
    # verify all nodes are in canonical form
    noncanon = 0
    occ_of = {}
    for key, node in nodes.items():
        occ = geo.key_to_occ(node["lo"], node["hi"])
        occ_of[key] = occ
        if geo.canon_key(occ) != key:
            noncanon += 1

    # children
    loss_children = defaultdict(list)
    win_child = {}
    missing_win_child = 0
    for key, node in nodes.items():
        S = occ_of[key]
        if node["outcome"] == 2:
            w = node["witness"]
            if w >= geo.V or w in S:
                missing_win_child += 1
                continue
            child_occ = S | {w}
            ck = geo.canon_key(child_occ)
            if ck in nodes:
                win_child[key] = ck
            else:
                missing_win_child += 1
        else:
            for p in range(geo.V):
                if geo.legal_add(S, p):
                    ck = geo.canon_key(S | {p})
                    if ck in nodes:
                        loss_children[key].append(ck)

    memo_min, memo_max, memo_reach = {}, {}, {}

    def stones_of(key):
        return len(occ_of[key])

    def calc(key):
        if key in memo_min:
            return
        node = nodes[key]
        if node["outcome"] == 1:
            ch = loss_children.get(key, [])
            # unique children
            ch = list(dict.fromkeys(ch))
            if not ch:
                memo_min[key] = memo_max[key] = 0
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
            c = win_child.get(key)
            if c is None:
                memo_min[key] = memo_max[key] = 0
                memo_reach[key] = {stones_of(key)}
                return
            calc(c)
            memo_min[key] = 1 + memo_min[c]
            memo_max[key] = 1 + memo_max[c]
            memo_reach[key] = memo_reach[c]

    calc(root)
    terms = [stones_of(k) for k, n in nodes.items() if n["outcome"] == 1 and not loss_children.get(k)]

    return {
        "n": board,
        "nodes": ncount,
        "noncanonical_nodes": noncanon,
        "states_are_canonical": noncanon == 0,
        "missing_win_child": missing_win_child,
        "root_outcome": "LOSS" if nodes[root]["outcome"] == 1 else "WIN",
        "min_moves_from_empty": memo_min[root],
        "max_moves_from_empty": memo_max[root],
        "terminal_stones_reachable": sorted(memo_reach[root]),
        "terminal_stone_hist": dict(sorted(Counter(terms).items())),
        "n_terminals": len(terms),
    }


def main():
    report = {}
    for n in range(1, 8):
        path = CERTS / f"kyouen-{n}x{n}.cert"
        if not path.exists():
            continue
        print(f"n={n} ...", flush=True)
        r = analyze(path, max_n=6)
        report[n] = r
        print(json.dumps(r, ensure_ascii=False), flush=True)
    out = OUT / "exploration_report_9.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

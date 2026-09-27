#!/usr/bin/env python3
"""n×n の極小極大安全配置サイズ K_min を小さい n で列挙する。"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"


def forbidden_quads(n: int):
    pts = [(x, y) for y in range(n) for x in range(n)]
    quads = []

    def det3(r0, r1, r2):
        return (
            r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
            - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
            + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0])
        )

    for a, b, c, d in itertools.combinations(range(n * n), 4):
        coords = [pts[a], pts[b], pts[c], pts[d]]
        A = [(x * x + y * y, x, y, 1) for x, y in coords]
        det = (
            A[0][0] * det3(A[1][1:], A[2][1:], A[3][1:])
            - A[0][1] * det3((A[1][0], A[1][2], A[1][3]), (A[2][0], A[2][2], A[2][3]), (A[3][0], A[3][2], A[3][3]))
            + A[0][2] * det3((A[1][0], A[1][1], A[1][3]), (A[2][0], A[2][1], A[2][3]), (A[3][0], A[3][1], A[3][3]))
            - A[0][3] * det3((A[1][0], A[1][1], A[1][2]), (A[2][0], A[2][1], A[2][2]), (A[3][0], A[3][1], A[3][2]))
        )
        if det == 0:
            quads.append((a, b, c, d))
    return quads


def k_min_for_board(n: int, max_k: int = 12) -> dict:
    quads = forbidden_quads(n)
    pts = n * n
    pair_blocks = {}
    for q in quads:
        for i in range(4):
            for j in range(i + 1, 4):
                a, b = q[i], q[j]
                key = (a, b) if a < b else (b, a)
                others = tuple(p for p in q if p not in (a, b))
                pair_blocks.setdefault(key, []).append(others)

    def safe_add(occ, p):
        s = set(occ)
        for x in occ:
            key = (x, p) if x < p else (p, x)
            for u, v in pair_blocks.get(key, ()):
                if u in s and v in s:
                    return False
        return True

    def is_maximal(occ):
        s = set(occ)
        for p in range(pts):
            if p not in s and safe_add(occ, p):
                return False
        return True

    for k in range(4, max_k + 1):
        found = None
        nodes = 0

        def dfs(occ, from_i):
            nonlocal found, nodes
            if found is not None:
                return
            nodes += 1
            if len(occ) == k:
                if is_maximal(occ):
                    found = list(occ)
                return
            need = k - len(occ)
            for p in range(from_i, pts - need + 1):
                if not safe_add(occ, p):
                    continue
                occ.append(p)
                dfs(occ, p + 1)
                occ.pop()
                if found is not None:
                    return

        dfs([], 0)
        if found is not None:
            return {
                "n": n,
                "forbidden": len(quads),
                "k_min": k,
                "example": found,
                "nodes_at_hit": nodes,
            }
    return {"n": n, "forbidden": len(quads), "k_min": None, "note": f"not found k<={max_k}"}


def main() -> None:
    rows = []
    for n in range(3, 8):
        print(f"n={n}...", flush=True)
        r = k_min_for_board(n)
        print(r, flush=True)
        rows.append(r)
    path = OUT / "fact_kmin_by_board.json"
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()

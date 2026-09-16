#!/usr/bin/env python3
"""H4: geometric pair-witness count vs depth-indexed pair cores on the 10x10 medium LOSS root.

R = {90,61,2,73,69,66,13,91}, id = y*10+x
w(a,b) = #{ forbidden 4-sets F : {a,b} subset F and |F ∩ R| >= 2 }
Does w predict the empirical LOSS cores C_3,C_4,C_5,C_6?
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
N = 10
R = [90, 61, 2, 73, 69, 66, 13, 91]


def coords(i: int) -> tuple[int, int]:
    return (i % N, i // N)


def is_forbidden(pts: tuple[int, int, int, int]) -> bool:
    x = []
    y = []
    for p in pts:
        xi, yi = coords(p)
        x.append(xi)
        y.append(yi)
    # det of [[x^2+y^2, x, y, 1], ...]
    m = [
        [x[i] * x[i] + y[i] * y[i], x[i], y[i], 1] for i in range(4)
    ]
    # 4x4 determinant via cofactor expansion / integer elimination
    a = [row[:] for row in m]
    det = 1
    for col in range(4):
        pivot = None
        for r in range(col, 4):
            if a[r][col] != 0:
                pivot = r
                break
        if pivot is None:
            return True
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            det = -det
        piv = a[col][col]
        det *= piv
        for r in range(col + 1, 4):
            if a[r][col] == 0:
                continue
            # eliminate using integer row ops: row_r = piv*row_r - a[r][col]*row_col
            factor = a[r][col]
            for c in range(col, 4):
                a[r][c] = piv * a[r][c] - factor * a[col][c]
        # divide previous rows implicitly; after elimination remaining det accumulates piv
        # Because we didn't scale previous rows when multiplying later, rebuild carefully:
    # The above is wrong for exact det with mixed scales. Use recursive integer det instead.
    return det4(m) == 0


def det4(m: list[list[int]]) -> int:
    def det3(a: list[list[int]]) -> int:
        return (
            a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
            - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
        )

    s = 0
    for c in range(4):
        minor = [[m[r][cc] for cc in range(4) if cc != c] for r in range(1, 4)]
        s += ((-1) ** c) * m[0][c] * det3(minor)
    return s


def forbidden_4sets() -> list[tuple[int, int, int, int]]:
    pts = list(range(N * N))
    out = []
    for combo in combinations(pts, 4):
        if is_forbidden(combo):
            out.append(combo)
    return out


def load_states(name: str) -> list[tuple[list[int], str]]:
    path = ROOT / "results" / "10x10" / name
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            state = [int(x) for x in r["state"].strip('"').split(",")]
            rows.append((state, r["outcome"]))
    return rows


def pair_core(rows: list[tuple[list[int], str]]) -> list[tuple[tuple[int, int], int]]:
    cnt: dict[tuple[int, int], int] = defaultdict(int)
    for state, outcome in rows:
        if outcome != "LOSS":
            continue
        for a, b in combinations(sorted(state), 2):
            cnt[(a, b)] += 1
    return sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))


def main() -> None:
    forb = forbidden_4sets()
    print(f"forbidden_4sets={len(forb)}", flush=True)
    Rset = set(R)
    # pair-witness count restricted as stated
    w_all: dict[tuple[int, int], int] = defaultdict(int)
    w_loss_eligible: dict[tuple[int, int], int] = defaultdict(int)
    for F in forb:
        inter = Rset.intersection(F)
        if len(inter) < 2:
            continue
        for a, b in combinations(sorted(inter), 2):
            w_all[(a, b)] += 1

    # Also unrestricted: forbidden sets containing the pair anywhere on board (not just inside R)
    w_board: dict[tuple[int, int], int] = defaultdict(int)
    for F in forb:
        for a, b in combinations(F, 2):
            if a in Rset and b in Rset:
                w_board[(a, b)] += 1

    cores = {}
    for k, fname in [
        (3, "three-stone-subsets-of-medium-loss.csv"),
        (4, "four-stone-subsets-of-medium-loss.csv"),
        (5, "five-stone-subsets-of-medium-loss.csv"),
        (6, "six-stone-subsets-of-medium-loss.csv"),
    ]:
        rows = load_states(fname)
        cores[k] = {
            "n_rows": len(rows),
            "n_loss": sum(1 for _, o in rows if o == "LOSS"),
            "top_pairs": pair_core(rows)[:8],
        }

    pairs = list(combinations(sorted(R), 2))
    ranked_w = sorted(pairs, key=lambda p: (-w_all[p], p))
    ranked_board = sorted(pairs, key=lambda p: (-w_board[p], p))

    result = {
        "R": R,
        "n_forbidden": len(forb),
        "w_definition": "forbidden 4-sets F with pair in R and |F∩R|>=2",
        "w_all_ranked": [(list(p), w_all[p]) for p in ranked_w],
        "w_board_ranked": [(list(p), w_board[p]) for p in ranked_board],
        "cores": {str(k): cores[k] for k in cores},
    }

    # Test H4 claims
    top_w_pair = ranked_w[0]
    top_board_pair = ranked_board[0]
    claims = {}
    claims["w_max_is_61_66"] = top_w_pair == (61, 66)
    claims["board_w_max_is_61_66"] = top_board_pair == (61, 66)

    for k in (3, 4, 5, 6):
        loss_pairs = [tuple(p) for p, _ in cores[k]["top_pairs"]]
        if not loss_pairs:
            continue
        best_support = cores[k]["top_pairs"][0][1]
        core_pairs = [p for p, c in cores[k]["top_pairs"] if c == best_support]
        # among pairs appearing in >=1 LOSS k-subset, is a core pair maximizing w?
        appearing = set()
        rows = load_states(
            {
                3: "three-stone-subsets-of-medium-loss.csv",
                4: "four-stone-subsets-of-medium-loss.csv",
                5: "five-stone-subsets-of-medium-loss.csv",
                6: "six-stone-subsets-of-medium-loss.csv",
            }[k]
        )
        for state, outcome in rows:
            if outcome != "LOSS":
                continue
            for a, b in combinations(sorted(state), 2):
                appearing.add((a, b))
        w_on_appearing = sorted(appearing, key=lambda p: (-w_all[p], p))
        best_w_val = w_all[w_on_appearing[0]] if w_on_appearing else None
        core_max_w = max((w_all[p] for p in core_pairs), default=None)
        claims[f"k{k}_core_maximizes_w_among_loss_pairs"] = core_max_w == best_w_val
        claims[f"k{k}_core_pairs"] = [list(p) for p in core_pairs]
        claims[f"k{k}_best_w_pair"] = list(w_on_appearing[0]) if w_on_appearing else None
        claims[f"k{k}_best_w_val"] = best_w_val
        claims[f"k{k}_core_max_w"] = core_max_w

    result["claims"] = claims
    (OUT / "h4-pair-witness.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"claims": claims, "w_top10": result["w_all_ranked"][:10],
                      "board_top10": result["w_board_ranked"][:10],
                      "cores": {k: cores[k]["top_pairs"][:5] for k in cores}}, indent=2))


if __name__ == "__main__":
    main()

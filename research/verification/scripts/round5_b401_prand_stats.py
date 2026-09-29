#!/usr/bin/env python3
"""Round5 B504/B505/B508/B510: per-position p_rand / |W| statistics on n<=5.

Population: ALL safe subsets reachable from empty board (exact).
p_rand: exact Fractions. p(terminal)=0; p(S)=1-(1/|L|)*sum p(child).

Outputs research/verification/round5_b401_prand_stats.json
"""
from __future__ import annotations

import json
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square  # noqa: E402

OUT = REPO_ROOT / "research" / "verification" / "round5_b401_prand_stats.json"


def analyze_board(n: int) -> dict:
    t0 = time.time()
    bd = board_square(n)
    V = bd.V
    full = (1 << V) - 1

    levels: list[list[int]] = [[0]]
    seen = {0}
    for _k in range(V):
        nxt_set = set()
        for occ in levels[-1]:
            empty = full ^ occ
            v = 0
            e = empty
            while e:
                if e & 1:
                    child = occ | (1 << v)
                    if bd.is_safe(child):
                        nxt_set.add(child)
                e >>= 1
                v += 1
        if not nxt_set:
            break
        nxt = sorted(nxt_set)
        levels.append(nxt)
        seen |= nxt_set

    sizes = [len(L) for L in levels]
    F = sum(sizes)
    idx_of = [{s: i for i, s in enumerate(L)} for L in levels]

    children: list[list[list[int]]] = []
    legal_cnt: list[list[int]] = []
    for k, L in enumerate(levels):
        ch = []
        lc = []
        for occ in L:
            empty = full ^ occ
            kids = []
            v = 0
            e = empty
            while e:
                if e & 1:
                    child = occ | (1 << v)
                    if bd.is_safe(child):
                        kids.append(idx_of[k + 1][child])
                e >>= 1
                v += 1
            ch.append(kids)
            lc.append(len(kids))
        children.append(ch)
        legal_cnt.append(lc)

    # grundy bottom-up
    g_of: list[list[int]] = [None] * len(levels)  # type: ignore
    for k in range(len(levels) - 1, -1, -1):
        row = [0] * len(levels[k])
        for i in range(len(levels[k])):
            kids = children[k][i]
            if not kids:
                continue
            seen_g = 0
            for j in kids:
                seen_g |= 1 << g_of[k + 1][j]
            mex = 0
            while seen_g & (1 << mex):
                mex += 1
            row[i] = mex
        g_of[k] = row

    # p_rand exact Fractions bottom-up
    pr: list[list[Fraction]] = [None] * len(levels)  # type: ignore
    for k in range(len(levels) - 1, -1, -1):
        row = [Fraction(0, 1)] * len(levels[k])
        if k + 1 < len(levels):
            child_pr = pr[k + 1]
            for i in range(len(levels[k])):
                kids = children[k][i]
                m = legal_cnt[k][i]
                if m == 0:
                    continue
                s = Fraction(0, 1)
                for j in kids:
                    s += child_pr[j]
                row[i] = 1 - s / m
        pr[k] = row

    max_safe = len(levels) - 1
    max_decoys = -1
    max_decoys_ex = None
    b504_count = 0
    b505_hits = []
    b505_min_pr = None
    b505_count_half = 0
    b510_hits = []
    b510_count = 0
    by_pr: dict[str, list] = {}
    n_P = n_N = 0
    P_max = Fraction(0, 1)
    N_min = None
    P_max_by_maxrem: dict[str, Fraction] = {}
    # also N_min by maxrem for contrast
    N_stats_by_maxrem: dict[str, dict] = {}

    def coords(occ: int) -> list:
        return [(bx, by) for by in range(n) for bx in range(n) if occ & (1 << (by * n + bx))]

    for k, L in enumerate(levels):
        for i, occ in enumerate(L):
            g = g_of[k][i]
            m = legal_cnt[k][i]
            p = pr[k][i]
            max_rem = max_safe - k
            kids = children[k][i]
            if g == 0:
                n_P += 1
                if p > P_max:
                    P_max = p
                key = str(max_rem)
                if key not in P_max_by_maxrem or p > P_max_by_maxrem[key]:
                    P_max_by_maxrem[key] = p
            else:
                n_N += 1
                if N_min is None or p < N_min:
                    N_min = p
                key = str(max_rem)
                st = N_stats_by_maxrem.setdefault(key, {"n": 0, "min_pr": None, "max_pr": None})
                st["n"] += 1
                if st["min_pr"] is None or p < st["min_pr"]:
                    st["min_pr"] = p
                if st["max_pr"] is None or p > st["max_pr"]:
                    st["max_pr"] = p

            win_kids = [j for j in kids if g_of[k + 1][j] == 0]
            lose_kids = [j for j in kids if g_of[k + 1][j] != 0]
            W = len(win_kids)

            if g > 0 and W == 1:
                b504_count += 1
                decoys = m - 1
                if decoys > max_decoys:
                    max_decoys = decoys
                    max_decoys_ex = {
                        "occ": occ, "k": k, "L": m, "W": W, "decoys": decoys,
                        "p_rand": str(p), "g": g, "points": coords(occ),
                        "win_child_p": [str(pr[k + 1][j]) for j in win_kids],
                        "lose_child_p_sorted": sorted(str(pr[k + 1][j]) for j in lose_kids),
                    }

            if g > 0 and m > 0:
                wr = Fraction(W, m)
                if wr >= Fraction(1, 2):
                    b505_count_half += 1
                    if b505_min_pr is None or p < b505_min_pr:
                        b505_min_pr = p
                    if p < Fraction(2, 5) and len(b505_hits) < 8:
                        b505_hits.append({
                            "occ": occ, "k": k, "L": m, "W": W,
                            "win_ratio": f"{W}/{m}", "p_rand": str(p), "g": g,
                            "points": coords(occ),
                        })

            if g > 0 and W >= 1 and lose_kids:
                win_ps = [pr[k + 1][j] for j in win_kids]
                lose_ps = [pr[k + 1][j] for j in lose_kids]
                if min(win_ps) > max(lose_ps):
                    b510_count += 1
                    if len(b510_hits) < 5:
                        b510_hits.append({
                            "occ": occ, "k": k, "L": m, "W": W, "p_rand": str(p),
                            "win_child_p": [str(x) for x in win_ps],
                            "lose_child_p_max": str(max(lose_ps)),
                            "points": coords(occ),
                        })

            wr_s = f"{W}/{m}" if m else "0"
            by_pr.setdefault(str(p), []).append((Fraction(W, m) if m else Fraction(0), W, m, occ, k))

    b508_max_gap = Fraction(0, 1)
    b508_example = None
    b508_pairs = []
    for pstr, items in by_pr.items():
        if len(items) < 2:
            continue
        ratios = sorted(items, key=lambda t: t[0])
        gap = ratios[-1][0] - ratios[0][0]
        if gap > b508_max_gap:
            b508_max_gap = gap
            lo, hi = ratios[0], ratios[-1]
            b508_example = {
                "p_rand": pstr, "gap": str(gap),
                "min_ratio": f"{lo[1]}/{lo[2]}", "min_occ": lo[3], "min_k": lo[4],
                "max_ratio": f"{hi[1]}/{hi[2]}", "max_occ": hi[3], "max_k": hi[4],
                "n_same_pr": len(items),
            }
        if gap >= Fraction(2, 5) and len(b508_pairs) < 5:
            lo, hi = ratios[0], ratios[-1]
            b508_pairs.append({
                "p_rand": pstr, "gap": str(gap),
                "min_ratio": f"{lo[1]}/{lo[2]}", "max_ratio": f"{hi[1]}/{hi[2]}",
                "min_occ": lo[3], "max_occ": hi[3],
            })

    return {
        "n": n,
        "V": V,
        "level_sizes": sizes,
        "F": F,
        "max_safe_size": max_safe,
        "empty_g": g_of[0][0],
        "empty_p_rand": str(pr[0][0]),
        "n_P": n_P,
        "n_N": n_N,
        "P_max": str(P_max),
        "N_min": str(N_min) if N_min is not None else None,
        "P_max_by_maxrem": {k: str(v) for k, v in sorted(P_max_by_maxrem.items(), key=lambda kv: int(kv[0]))},
        "N_by_maxrem": {k: {"n": v["n"], "min_pr": str(v["min_pr"]), "max_pr": str(v["max_pr"])}
                        for k, v in sorted(N_stats_by_maxrem.items(), key=lambda kv: int(kv[0]))},
        "B504": {"N_with_W1": b504_count, "max_decoys": max_decoys, "example": max_decoys_ex},
        "B505": {
            "n_N_win_ratio_ge_half": b505_count_half,
            "min_pr_when_win_ratio_ge_half": str(b505_min_pr) if b505_min_pr is not None else None,
            "n_hits_pr_lt_0_4": len(b505_hits),
            "hits": b505_hits,
        },
        "B508": {
            "max_same_pr_ratio_gap": str(b508_max_gap),
            "example": b508_example,
            "pairs_gap_ge_0_4": b508_pairs,
        },
        "B510": {"n_hits": b510_count, "hits": b510_hits},
        "timing_s": round(time.time() - t0, 2),
    }


def main():
    sizes = [4, 5]
    if len(sys.argv) > 1:
        sizes = [int(x) for x in sys.argv[1].split(",")]
    out = {}
    for n in sizes:
        print(f"=== n={n} ===", flush=True)
        st = analyze_board(n)
        out[f"n{n}"] = st
        brief = {k: st[k] for k in ("level_sizes", "n_P", "n_N", "P_max", "N_min", "P_max_by_maxrem", "B504", "B505", "B508", "B510") if k in st}
        print(json.dumps(brief, ensure_ascii=False, indent=1)[:2500], flush=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

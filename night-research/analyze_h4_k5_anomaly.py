#!/usr/bin/env python3
"""Why does depth-5 pair core {13,91} ignore high-w pairs? Characterize the k=5 failure of H4."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
N = 10
R = [90, 61, 2, 73, 69, 66, 13, 91]


def coords(i: int) -> tuple[int, int]:
    return (i % N, i // N)


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


def is_forbidden(pts) -> bool:
    xs = [coords(p)[0] for p in pts]
    ys = [coords(p)[1] for p in pts]
    m = [[xs[i] * xs[i] + ys[i] * ys[i], xs[i], ys[i], 1] for i in range(4)]
    return det4(m) == 0


def load(name: str):
    path = ROOT / "results" / "10x10" / name
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    rows5 = load("five-stone-subsets-of-medium-loss.csv")
    loss = [ [int(x) for x in r["state"].strip('"').split(",")] for r in rows5 if r["outcome"]=="LOSS" ]
    win = [ [int(x) for x in r["state"].strip('"').split(",")] for r in rows5 if r["outcome"]=="WIN" ]

    # pair support among LOSS vs WIN
    def pair_freq(states):
        c = Counter()
        for s in states:
            for a,b in combinations(sorted(s),2):
                c[(a,b)] += 1
        return c

    fL, fW = pair_freq(loss), pair_freq(win)
    pairs = list(combinations(sorted(R),2))

    # enrichment = P(pair|LOSS)/P(pair|WIN) with Laplace
    enr = {}
    for p in pairs:
        pl = (fL[p]+0.5)/(len(loss)+1)
        pw = (fW[p]+0.5)/(len(win)+1)
        enr[p] = pl/pw

    ranked = sorted(pairs, key=lambda p: -enr[p])

    # w from previous run
    w = json.loads((OUT/"h4-pair-witness.json").read_text(encoding="utf-8"))
    wmap = {(a,b): val for (a,b), val in w["w_all_ranked"]}

    # For each LOSS 5-set, which pairs does it contain; is {13,91} special in composition?
    contains_1391 = [s for s in loss if 13 in s and 91 in s]
    not_1391 = [s for s in loss if not (13 in s and 91 in s)]

    # co-occurrence: does high-w pair imply presence of low-w core via other stones?
    # measure how often {66,73} appears with {13,91}
    both = sum(1 for s in loss if {66,73} <= set(s) and {13,91} <= set(s))
    only_6673 = sum(1 for s in loss if {66,73} <= set(s) and not ({13,91} <= set(s)))
    only_1391 = sum(1 for s in loss if {13,91} <= set(s) and not ({66,73} <= set(s)))

    # stone-level: which stones appear in LOSS 5-sets
    stoneL = Counter()
    for s in loss:
        for p in s:
            stoneL[p]+=1
    stoneW = Counter()
    for s in win:
        for p in s:
            stoneW[p]+=1

    result = {
        "n_loss": len(loss),
        "n_win": len(win),
        "top_enrichment_pairs": [(list(p), round(enr[p],3), fL[p], fW[p], wmap.get(p)) for p in ranked[:12]],
        "w_vs_enrichment_rank_corr_spearman_approx": None,
        "loss_5sets_containing_1391": len(contains_1391),
        "loss_5sets_without_1391": [[int(x) for x in s] for s in not_1391],
        "pair_66_73_in_loss": only_6673 + both,
        "pair_13_91_in_loss": only_1391 + both,
        "both_pairs": both,
        "stone_freq_loss": stoneL.most_common(),
        "stone_freq_win": stoneW.most_common(),
        "note": "If high-w pairs appear equally in WIN, w is not LOSS-selective at k=5",
    }

    # rank correlation between w and enrichment
    import math
    def spearman(xs, ys):
        def rank(v):
            order = sorted(range(len(v)), key=lambda i: v[i])
            r = [0]*len(v)
            for i,idx in enumerate(order):
                r[idx]=i
            return r
        rx, ry = rank(xs), rank(ys)
        n=len(xs)
        mx=sum(rx)/n; my=sum(ry)/n
        num=sum((rx[i]-mx)*(ry[i]-my) for i in range(n))
        denx=math.sqrt(sum((rx[i]-mx)**2 for i in range(n)))
        deny=math.sqrt(sum((ry[i]-my)**2 for i in range(n)))
        return num/(denx*deny) if denx and deny else None

    result["w_vs_enrichment_rank_corr_spearman_approx"] = spearman(
        [wmap[p] for p in pairs], [enr[p] for p in pairs]
    )

    (OUT/"h4-k5-anomaly.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in [
        "n_loss","n_win","top_enrichment_pairs","loss_5sets_containing_1391",
        "loss_5sets_without_1391","pair_66_73_in_loss","pair_13_91_in_loss",
        "w_vs_enrichment_rank_corr_spearman_approx","stone_freq_loss","stone_freq_win"
    ]}, indent=2)[:6000])


if __name__ == "__main__":
    main()

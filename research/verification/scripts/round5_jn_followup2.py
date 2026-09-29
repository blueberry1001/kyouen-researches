#!/usr/bin/env python3
"""Round5 J_n follow-up #2: lock B312 n_inter classifier, one-stone~J iso theorem,
n6 sigma holes, B320 mixed-key has1 rule. Writes round5_jn_followup2.json."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square  # noqa: E402

VER = Path(__file__).resolve().parents[1]
OUT = VER / "round5_jn_followup2.json"


def load_grundy(n: int) -> dict[int, int]:
    if n == 5:
        cache = json.load(open(VER / "round5_b231_n5_grundy.json", encoding="utf-8"))
        return {int(k): v for k, v in cache.items()}
    return board_square(n).solve_grundy()


def main() -> None:
    result = {}

    # ---- B312: n_inter / n_union perfect separators on J_4 ----
    n = 4
    b = board_square(n)
    V = b.V
    gr = b.solve_grundy()
    adj = [0] * V
    p_pairs = []
    for i, j in combinations(range(V), 2):
        occ = (1 << i) | (1 << j)
        if gr[occ] == 0:
            adj[i] |= 1 << j
            adj[j] |= 1 << i
            p_pairs.append((i, j))

    def is_td(a, bpt):
        for v in range(V):
            if ((adj[v] >> a) & 1) == 0 and ((adj[v] >> bpt) & 1) == 0:
                return False
        return True

    def n_inter(a, bpt):
        return bin(adj[a] & adj[bpt]).count("1")

    def n_union(a, bpt):
        return bin(adj[a] | adj[bpt]).count("1")

    td_rows, ntd_rows = [], []
    for a, bpt in p_pairs:
        row = {
            "pair": [a, bpt],
            "n_inter": n_inter(a, bpt),
            "n_union": n_union(a, bpt),
            "d2": (a % n - bpt % n) ** 2 + (a // n - bpt // n) ** 2,
            "deg_a": bin(adj[a]).count("1"),
            "deg_b": bin(adj[bpt]).count("1"),
        }
        (td_rows if is_td(a, bpt) else ntd_rows).append(row)

    td_inter = Counter(r["n_inter"] for r in td_rows)
    ntd_inter = Counter(r["n_inter"] for r in ntd_rows)
    td_union = Counter(r["n_union"] for r in td_rows)
    ntd_union = Counter(r["n_union"] for r in ntd_rows)

    result["b312"] = {
        "n": 4,
        "n_P": len(p_pairs),
        "n_TD": len(td_rows),
        "n_nonTD": len(ntd_rows),
        "td_n_inter_hist": dict(sorted(td_inter.items())),
        "nontd_n_inter_hist": dict(sorted(ntd_inter.items())),
        "n_inter_perfect": set(td_inter).isdisjoint(set(ntd_inter)),
        "td_n_union_hist": dict(sorted(td_union.items())),
        "nontd_n_union_hist": dict(sorted(ntd_union.items())),
        "n_union_perfect": set(td_union).isdisjoint(set(ntd_union)),
        "td_examples": td_rows[:4],
        "nontd_examples": ntd_rows[:4],
    }

    # ---- one-stone g <=> J isolation, uniform-h theorem ----
    oneJ = {}
    for nn in (2, 3, 4, 5):
        gr_n = load_grundy(nn)
        Vn = board_square(nn).V
        one, two = {}, {}
        for occ, g in gr_n.items():
            c = occ.bit_count()
            if c == 1:
                one[occ] = g
            elif c == 2:
                two[occ] = g
        cells = Counter()
        for occ, g in one.items():
            p = (occ).bit_length() - 1
            hasP = any(two.get((1 << p) | (1 << q)) == 0 for q in range(Vn) if q != p)
            cells[(g, hasP)] += 1
        one_hist = dict(Counter(one.values()))
        two_hist = dict(Counter(two.values()))
        uniform = len(one_hist) == 1
        h = next(iter(one_hist)) if uniform else None
        # theorem: uniform h => h absent from all two-stone
        thm_viol = None
        if uniform:
            thm_viol = sum(1 for g in two.values() if g == h)
        # g(p)=0 iff isolated in J
        iso_iff_g0 = all(
            (one[occ] == 0)
            == (
                not any(
                    two.get((1 << (occ.bit_length() - 1)) | (1 << q)) == 0
                    for q in range(Vn)
                    if q != occ.bit_length() - 1
                )
            )
            for occ in one
        )
        oneJ[str(nn)] = {
            "one_hist": one_hist,
            "two_hist": two_hist,
            "uniform": uniform,
            "uniform_h": h,
            "thm_h_absent_in_two": thm_viol == 0 if uniform else None,
            "thm_violations": thm_viol,
            "g0_iff_J_isolated": iso_iff_g0,
            "cells_g_hasP": {f"g={k[0]},hasP={k[1]}": v for k, v in sorted(cells.items())},
            "g_empty": gr_n.get(0),
        }

    # n=6 from known: one all 0, two {1:596,3:34}, J empty
    oneJ["6"] = {
        "one_hist": {"0": 36},
        "two_hist": {"1": 596, "3": 34},
        "uniform": True,
        "uniform_h": 0,
        "thm_h_absent_in_two": True,
        "thm_violations": 0,
        "g0_iff_J_isolated": True,
        "note": "from round5_b301_j6 / prior batch; J_6 empty is a theorem consequence",
    }
    result["one_stone_J"] = oneJ

    # ---- n6 sigma holes from round2_b321 ----
    r2 = json.load(open(VER / "round2_b321.json", encoding="utf-8"))
    result["b321_b322_n6"] = {
        "holes_by_n": r2["holes_by_n"],
        "B321": r2["B321"],
        "B322": r2["B322"],
    }

    # ---- B320 mixed-key has1 rule (from existing followup) ----
    fu = json.load(open(VER / "round5_jn_followup.json", encoding="utf-8"))
    md = fu["b320"]["mixed_detail"]
    b320 = {"n": 5, "mixed_keys": fu["b320"]["mixed_keys"], "per_key": {}}
    for key, det in md.items():
        b320["per_key"][key] = {
            "n_P": det["n_P"],
            "n_nonP": det["n_nonP"],
            "has0": det["stats"]["has0"],
            "has1": det["stats"]["has1"],
            "child_sets_P": det["stats"]["child_sets_P"],
            "child_sets_nonP": det["stats"]["child_sets_nonP"],
            "R1": det["stats"]["R1_0_not_in_children_iff_P"],
            "examples_P": det["examples_P"][:2],
        }
    result["b320"] = b320

    # ---- B321/B322 all-layer vs sigma from existing followup ----
    result["b321_b322_all_layers"] = {
        "n_analyses_holes": {
            n: {
                "sigma": fu["n_analyses"][n]["sigma"],
                "K": fu["n_analyses"][n]["K"],
                "sigma_layer_holes": fu["n_analyses"][n]["sigma_layer_holes"],
                "all_layer_holes": fu["n_analyses"][n]["all_layer_holes"],
            }
            for n in ("2", "3", "4", "5")
        },
        "summary": fu["summary"],
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT)

    # console summary
    print("B312 n_inter perfect:", result["b312"]["n_inter_perfect"])
    print("  TD", result["b312"]["td_n_inter_hist"], "nonTD", result["b312"]["nontd_n_inter_hist"])
    print("B312 n_union perfect:", result["b312"]["n_union_perfect"])
    for n, d in oneJ.items():
        print(f"n={n} uniform={d['uniform']} h={d['uniform_h']} thm={d['thm_h_absent_in_two']} g0iff={d['g0_iff_J_isolated']}")


if __name__ == "__main__":
    main()

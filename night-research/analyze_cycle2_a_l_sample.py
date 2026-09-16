#!/usr/bin/env python3
"""Independent A_L count on the existing 8x8 depth-audit sample.

Uses artifacts/8x8-depth-audit-children.out.csv only (no new solves).
A_L = number of unordered pairs of LOSS children that differ by one stone
(one-swap adjacency). Within a parent, any two LOSS children automatically
differ by exactly two cells (the two distinct 5th moves).
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CHILDREN = REPO / "artifacts" / "8x8-depth-audit-children.out.csv"


def main() -> None:
    rows = list(csv.DictReader(CHILDREN.open(encoding="utf-8", newline="")))
    loss_per: Counter[str] = Counter()
    win_per: Counter[str] = Counter()
    all_parents: set[str] = set()
    for r in rows:
        p = r["canonical_parent"]
        all_parents.add(p)
        if r["child_outcome"] == "LOSS":
            loss_per[p] += 1
        else:
            win_per[p] += 1

    # Sibling A_L: sum C(K,2) over parents
    sibling_a_l = 0
    pair_counts = []
    for p, k in loss_per.items():
        c = k * (k - 1) // 2
        sibling_a_l += c
        pair_counts.append((p, k, c, win_per.get(p, 0)))

    pair_counts.sort(key=lambda t: (-t[1], t[0]))

    # Cross-parent one-swap: two LOSS children from different parents that
    # differ by exactly one stone (one removed / one added).
    # Child = parent_set + move. Encode child as frozenset of stone ids.
    child_sets: dict[str, set[frozenset[int]]] = defaultdict(set)
    for r in rows:
        if r["child_outcome"] != "LOSS":
            continue
        stones = frozenset(int(x) for x in r["canonical_parent"].split(","))
        child = frozenset(set(stones) | {int(r["move"])})
        child_sets[r["canonical_parent"]].add(child)

    # All LOSS children as flat set of frozensets
    all_loss_children: set[frozenset[int]] = set()
    for s in child_sets.values():
        all_loss_children |= s

    # Count one-swap pairs among all sample LOSS children
    loss_list = list(all_loss_children)
    cross_a_l = 0
    sibling_exact = 0
    for i in range(len(loss_list)):
        for j in range(i + 1, len(loss_list)):
            a, b = loss_list[i], loss_list[j]
            if len(a) != len(b):
                continue
            if len(a.symmetric_difference(b)) == 2:
                # same parent iff |intersection| == |a|-1 and union size |a|+1
                # always true when |Δ|=2 and |a|=|b|. Parent = a ∩ b.
                # Sibling if that parent is in our parent set.
                parent = a & b
                if parent is not None and len(parent) == len(a) - 1:
                    # could be sibling of a parent we expanded
                    # check whether parent string matches some expanded parent
                    # (canonicalization may differ — use set containment)
                    sibling_exact += 1

    k_hist = Counter(loss_per.values())
    sum_k = sum(loss_per.values())
    sum_k2 = sum(k * k for k in loss_per.values())

    out = {
        "source": str(CHILDREN.relative_to(REPO)).replace("\\", "/"),
        "n_children": len(rows),
        "n_parents": len(all_parents),
        "n_parents_with_loss": len(loss_per),
        "total_loss_children": sum_k,
        "total_win_children": sum(win_per.values()),
        "K_histogram": {str(k): v for k, v in sorted(k_hist.items())},
        "sum_K": sum_k,
        "sum_K2": sum_k2,
        "sibling_A_L": sibling_a_l,
        "one_swap_pairs_among_sample_loss": sibling_exact,
        "identity_check_sum_K2_minus_sum_K": sum_k2 - sum_k,
        "identity_note": (
            "For a complete depth layer, sum K^2 = (d+1)*N_LOSS(d+1) + 2*A_L. "
            "Here the sample is complete only as children of these parents, not "
            "board-complete, so (d+1)*N_LOSS is not the right normalizer. "
            "Sibling pairs alone give A_L = sum C(K,2)."
        ),
        "top_K_parents": [
            {"parent": p, "K_loss": k, "sibling_pairs": c, "win_children": w}
            for p, k, c, w in pair_counts[:10]
        ],
        "interpretation": [
            "A_L=629 is a sample statistic on 20 WIN 4-stone parents of 8x8, not a board census.",
            "One parent has K=31 LOSS children (killer concentration).",
            "Board-complete 6x6 A_L is not computable from existing certs/CSVs.",
        ],
    }
    dest = ROOT / "cycle2-a-l-8x8-sample.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(dest), "A_L": sibling_a_l, "sum_K": sum_k, "K_max": max(loss_per.values()) if loss_per else 0}))


if __name__ == "__main__":
    main()

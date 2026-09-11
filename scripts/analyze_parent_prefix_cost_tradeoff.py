#!/usr/bin/env python3
"""Audit whether reducing first-LOSS position actually reduces parent work.

The parent benchmark summary contains an exact-cost prefix proxy for strategies A
(native) and B (10k-probe order):

    prefix_proxy = exact cost of WIN children before first LOSS
                 + exact cost of the selected LOSS child

This script compares that cost-weighted quantity with the much cheaper structural
metric `root_entered` / first-LOSS position.  A reordering can enter fewer children
but still be worse if the remaining WIN prefix is expensive, so first-LOSS rank
must not be treated as the optimization target by itself.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path("results/10x10/parent-benchmark/loss_proof_cost_summary.json")


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    rows = data["selected_loss"]

    fewer_entered = 0
    fewer_entered_but_proxy_worse = 0
    entered_same_but_proxy_worse = 0
    entered_same_but_proxy_better = 0

    print(
        "parent,A_entered,B_entered,entered_delta,A_win_waste,B_win_waste,"
        "A_selected_loss,B_selected_loss,A_prefix_proxy,B_prefix_proxy,"
        "proxy_ratio_B_over_A,work_ratio"
    )

    for r in rows:
        a_prefix = r["a_win_waste_proxy"] + r["a_sel_proxy"]
        b_prefix = r["b_win_waste_proxy"] + r["b_sel_proxy"]
        proxy_ratio = b_prefix / a_prefix
        delta = r["b_entered"] - r["a_entered"]

        if delta < 0:
            fewer_entered += 1
            if proxy_ratio > 1:
                fewer_entered_but_proxy_worse += 1
        elif delta == 0:
            if proxy_ratio > 1:
                entered_same_but_proxy_worse += 1
            elif proxy_ratio < 1:
                entered_same_but_proxy_better += 1

        print(
            f"{r['parent']},{r['a_entered']},{r['b_entered']},{delta},"
            f"{r['a_win_waste_proxy']},{r['b_win_waste_proxy']},"
            f"{r['a_sel_proxy']},{r['b_sel_proxy']},{a_prefix},{b_prefix},"
            f"{proxy_ratio:.4f},{r['work_ratio']:.4f}"
        )

    print()
    print(f"parents={len(rows)}")
    print(f"B enters fewer children: {fewer_entered}/{len(rows)}")
    print(
        "...but exact prefix proxy is worse: "
        f"{fewer_entered_but_proxy_worse}/{fewer_entered}"
    )
    print(
        "same entered count, proxy worse/better: "
        f"{entered_same_but_proxy_worse}/{entered_same_but_proxy_better}"
    )
    print()
    print(
        "Interpretation: first-LOSS position is only a count proxy.  The next "
        "ordering experiment should score the cost-weighted prefix, and should "
        "report WIN-prefix cost separately from selected-LOSS proof cost."
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Audit an outcome-gated parent ordering strategy.

Proposed strategy:
  1. Search the native first root child exactly, without any probe.
  2. If that child is LOSS, terminate exactly as native ordering would.
  3. Only if the first child is WIN, probe/reorder the remaining siblings.

The key safety property is structural: every parent whose native first child is
LOSS is completely unaffected (including zero probe overhead).  Existing A/B
benchmark data cannot reconstruct the exact counterfactual cost on triggered
parents because B reordered the first child too, so this script deliberately
reports the trigger set and the amount of already-observed regression that the
gate would make impossible, rather than inventing a counterfactual speedup.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path("results/10x10/parent-benchmark/loss_proof_cost_summary.json")


def main() -> None:
    rows = json.loads(DATA.read_text(encoding="utf-8"))["selected_loss"]

    protected = [r for r in rows if r["a_first_loss_pos"] == 1]
    triggered = [r for r in rows if r["a_first_loss_pos"] > 1]

    print("lazy-probe gate audit")
    print(f"parents={len(rows)}")
    print(f"protected native-first-LOSS parents={len(protected)}/{len(rows)}")
    print(f"triggered after native-first-WIN={len(triggered)}/{len(rows)}")
    print()

    print("protected parents (lazy strategy is exactly native here)")
    print("parent,current_B_over_A,current_B_entered,A_entered")
    for r in protected:
        print(
            f"{r['parent']},{r['work_ratio']:.6f},"
            f"{r['b_entered']},{r['a_entered']}"
        )

    print()
    print("triggered parents (need a new residual-sibling experiment)")
    print("parent,A_first_LOSS,B_first_LOSS,current_B_over_A,A_prefix_proxy,B_prefix_proxy")
    for r in triggered:
        a_prefix = r["a_win_waste_proxy"] + r["a_sel_proxy"]
        b_prefix = r["b_win_waste_proxy"] + r["b_sel_proxy"]
        print(
            f"{r['parent']},{r['a_first_loss_pos']},{r['b_first_loss_pos']},"
            f"{r['work_ratio']:.6f},{a_prefix},{b_prefix}"
        )

    avoided = [r for r in protected if r["work_ratio"] > 1]
    avoided_max = max((r["work_ratio"] for r in avoided), default=1.0)
    print()
    print(
        "Safety result: all regressions on native-first-LOSS parents become "
        "structurally impossible, because no probe or reorder is performed "
        "before the already-decisive first child."
    )
    print(f"observed B regressions made impossible={len(avoided)}/{len(protected)}")
    print(f"largest observed B/A regression removed from this set={avoided_max:.6f}x")
    print(
        "Next experiment: for triggered parents only, keep native child #1 fixed, "
        "probe siblings #2..N, and measure the cost-weighted prefix."
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Secondary diagnostic for the invalidated cumulative-memo blind probes.

This script does NOT rehabilitate the old blind validation.  The old batch probe
used one Solver for multiple children, so `memo` is cumulative.  Here we only
ask a mechanistic question: after removing the deterministic cumulative trend by
first-differencing memo usage within the batch, do the known counterexamples
remain poor under a descending marginal-memo ranking?

The resulting delta is not a substitute for a fresh-Solver memo measurement:
cache overlap changes both search and memo growth.  It is therefore labelled
secondary/hypothesis-generating and must not alter the preregistered fresh rerun
rule (1M fresh memo descending).
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results" / "10x10"
C = R / "blind_probe_children"
RESULTS = R / "blind-probe-results.csv"


def norm(s: str) -> str:
    return "-".join(str(int(x)) for x in s.replace(",", "-").split("-") if x != "")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def first_loss_rank(order: list[str], outcomes: dict[str, str]) -> int:
    for i, state in enumerate(order, 1):
        if outcomes.get(state, "").upper() == "LOSS":
            return i
    return len(order) + 1


def rank_desc(values: list[tuple[str, int]]) -> list[str]:
    # State is the deterministic tie break; the old primary used descending memo.
    return [s for s, _ in sorted(values, key=lambda x: (-x[1], x[0]))]


def main() -> None:
    parents = []
    for r in read_rows(RESULTS):
        if r["stones"] == "3" and int(r["loss_child_count"]) > 0:
            parents.append(r["parent"])

    rows: list[dict[str, object]] = []
    for parent in parents:
        safe = parent.replace(",", "_")
        probe_path = C / f"probe_{safe}_batch0_1000000.csv"
        exact_path = C / f"exact_{safe}_batch0.csv"
        if not probe_path.exists() or not exact_path.exists():
            continue

        probe = read_rows(probe_path)
        exact = read_rows(exact_path)
        outcomes = {norm(r["state"]): r["outcome"] for r in exact}

        states = [norm(r["state"]) for r in probe]
        memos = [int(r["memo"]) for r in probe]
        deltas = [memos[0]] + [b - a for a, b in zip(memos, memos[1:])]

        cumulative_order = rank_desc(list(zip(states, memos)))
        delta_order = rank_desc(list(zip(states, deltas)))
        reverse_input_order = list(reversed(states))

        cum_rank = first_loss_rank(cumulative_order, outcomes)
        delta_rank = first_loss_rank(delta_order, outcomes)
        reverse_rank = first_loss_rank(reverse_input_order, outcomes)

        loss_deltas = [d for s, d in zip(states, deltas) if outcomes.get(s, "").upper() == "LOSS"]
        win_deltas = [d for s, d in zip(states, deltas) if outcomes.get(s, "").upper() == "WIN"]

        rows.append({
            "parent": parent,
            "children": len(states),
            "losses": len(loss_deltas),
            "old_cumulative_memo_desc_first_loss": cum_rank,
            "reverse_input_first_loss": reverse_rank,
            "marginal_memo_desc_first_loss": delta_rank,
            "marginal_minus_old_rank": delta_rank - cum_rank,
            "loss_delta_median": round(statistics.median(loss_deltas), 1) if loss_deltas else "",
            "win_delta_median": round(statistics.median(win_deltas), 1) if win_deltas else "",
            "loss_minus_win_delta_median": (
                round(statistics.median(loss_deltas) - statistics.median(win_deltas), 1)
                if loss_deltas and win_deltas else ""
            ),
            "memo_strictly_increasing": all(b > a for a, b in zip(memos, memos[1:])),
        })

    if not rows:
        raise SystemExit("no matching invalidated probe/exact pairs found")

    out = R / "confounded-probe-marginal-memo.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("parent old_rank reverse_rank marginal_rank loss_delta_med win_delta_med")
    for r in rows:
        print(r["parent"], r["old_cumulative_memo_desc_first_loss"],
              r["reverse_input_first_loss"], r["marginal_memo_desc_first_loss"],
              r["loss_delta_median"], r["win_delta_median"])
    print(f"wrote {out}")
    print("WARNING: marginal memo is secondary only; it is not a fresh-Solver estimate.")


if __name__ == "__main__":
    main()

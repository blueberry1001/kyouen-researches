#!/usr/bin/env python3
"""Verify that fresh-process probe features are independent of child order.

This is a measurement-validity test, not a game-outcome experiment. The same
small committed child set is probed in forward, reverse, and deterministic
shuffled order. Every child is launched through run_one(), which starts a new
solver process. All deterministic output fields except wall-clock seconds must
match exactly for each child across orders.
"""

import csv
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_blind_probe_batch_isolated import run_one  # noqa: E402

BUDGET = 20_000
STATES = [
    "0,1,10,13",
    "0,2,10,13",
    "0,4,10,13",
]


def probe_order(states):
    result = {}
    for state in states:
        rows, _ = run_one(state, BUDGET)
        header, row = rows
        rec = dict(zip(header, row))
        if rec.get("state") != state.replace(",", "-"):
            raise SystemExit(f"state identity mismatch: input={state} output={rec.get('state')}")
        rec.pop("seconds", None)
        result[state] = rec
    return result


def main():
    orders = {
        "forward": list(STATES),
        "reverse": list(reversed(STATES)),
    }
    shuffled = list(STATES)
    random.Random(20260909).shuffle(shuffled)
    orders["shuffle"] = shuffled

    runs = {name: probe_order(order) for name, order in orders.items()}
    baseline = runs["forward"]
    for name, run in runs.items():
        for state in STATES:
            if run[state] != baseline[state]:
                diffs = {
                    k: (baseline[state].get(k), run[state].get(k))
                    for k in baseline[state]
                    if baseline[state].get(k) != run[state].get(k)
                }
                raise SystemExit(f"order dependence: order={name} state={state} diffs={diffs}")

    print("fresh_process_order_invariance=PASS")
    print(f"budget={BUDGET}")
    print("compared_fields=all_solver_csv_fields_except_seconds")
    for name, order in orders.items():
        print(f"{name}={'|'.join(order)}")
    for state in STATES:
        r = baseline[state]
        print(
            f"state={state} outcome={r.get('outcome')} visited={r.get('visited')} "
            f"maxdepth={r.get('maxdepth')} memo={r.get('memo')}"
        )


if __name__ == "__main__":
    main()

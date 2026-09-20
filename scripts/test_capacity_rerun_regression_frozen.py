#!/usr/bin/env python3
"""Run the capacity-rerun regression using the frozen regression contract.

This wrapper exists because the earlier regression implementation selected its
parents internally and reread C2 summary.csv at runtime. The wrapper treats
regression_expected.json as the authority: it first verifies every frozen
expectation against the committed C2 source, then overrides only the regression
parent list and binary path before delegating to the existing instrumentation-
heavy gate.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "results/10x10/cache-aware-below-root-capacity-rerun/regression_expected.json"
C2_SUMMARY = ROOT / "results/10x10/cache-aware-below-root-confirmation-v2/summary_ab.csv"
DEFAULT_BIN = ROOT / "tmp-kb/order_ab_capacity"

sys.path.insert(0, str(ROOT / "scripts"))
import test_capacity_rerun_regression as gate  # noqa: E402


def verify_frozen_expectations(frozen: dict) -> list[str]:
    with C2_SUMMARY.open(newline="", encoding="utf-8") as f:
        rows = {(r["parent"], r["condition"]): r for r in csv.DictReader(f)}

    parents: list[str] = []
    for case in frozen["cases"]:
        parent = case["parent"]
        parents.append(parent)
        for condition, want in case["conditions"].items():
            got = rows.get((parent, condition))
            if got is None:
                raise SystemExit(f"missing frozen C2 source row: {(parent, condition)}")
            for field in frozen["required_fields"]:
                wv = want[field]
                gv: object = got[field]
                if isinstance(wv, int):
                    gv = int(str(gv))
                if gv != wv:
                    raise SystemExit(
                        "FROZEN REGRESSION EXPECTATION MISMATCH: "
                        f"parent={parent} condition={condition} field={field} "
                        f"frozen={wv!r} current={gv!r}"
                    )
    return parents


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", type=Path, default=DEFAULT_BIN)
    args = ap.parse_args()

    binary = args.bin if args.bin.is_absolute() else ROOT / args.bin
    frozen = json.loads(EXPECTED.read_text(encoding="utf-8"))
    parents = verify_frozen_expectations(frozen)

    gate.REGRESSION_PARENTS = parents
    gate.NEW_BIN = binary
    print("FROZEN REGRESSION CONTRACT PASS")
    print("parents=" + ";".join(parents))
    print(f"binary={binary}")
    return gate.main()


if __name__ == "__main__":
    raise SystemExit(main())

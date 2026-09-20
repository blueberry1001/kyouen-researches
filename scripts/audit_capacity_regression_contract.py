#!/usr/bin/env python3
"""Fail-closed audit of the preregistered capacity-rerun regression contract.

The regression expectation set was frozen in regression_expected.json.  This
audit prevents the executable regression gate from silently drifting to a
different parent set or to different old-C2 reference values.
"""
from __future__ import annotations

import ast
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "results/10x10/cache-aware-below-root-capacity-rerun/regression_expected.json"
REGRESSION = ROOT / "scripts/test_capacity_rerun_regression.py"
C2_SUMMARY = ROOT / "results/10x10/cache-aware-below-root-confirmation-v2/summary_ab.csv"


def literal_assignment(tree: ast.AST, name: str):
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                return ast.literal_eval(node.value)
    raise SystemExit(f"missing literal assignment {name} in {REGRESSION}")


def main() -> int:
    frozen = json.loads(EXPECTED.read_text(encoding="utf-8"))
    frozen_parents = [case["parent"] for case in frozen["cases"]]

    tree = ast.parse(REGRESSION.read_text(encoding="utf-8"), filename=str(REGRESSION))
    script_parents = literal_assignment(tree, "REGRESSION_PARENTS")
    if script_parents != frozen_parents:
        raise SystemExit(
            "REGRESSION CONTRACT DRIFT: script parents differ from frozen JSON\n"
            f"  frozen={frozen_parents}\n  script={script_parents}"
        )

    with C2_SUMMARY.open(newline="", encoding="utf-8") as f:
        rows = {(r["parent"], r["condition"]): r for r in csv.DictReader(f)}

    fields = frozen["required_fields"]
    for case in frozen["cases"]:
        parent = case["parent"]
        for condition, want in case["conditions"].items():
            got = rows.get((parent, condition))
            if got is None:
                raise SystemExit(f"missing old-C2 regression source row: {(parent, condition)}")
            for field in fields:
                gv = got[field]
                wv = want[field]
                if isinstance(wv, int):
                    try:
                        gv = int(gv)
                    except ValueError as e:
                        raise SystemExit(
                            f"non-integer old-C2 value {(parent, condition, field)}={gv!r}"
                        ) from e
                if gv != wv:
                    raise SystemExit(
                        "REGRESSION EXPECTATION DRIFT: old-C2 source no longer matches frozen JSON\n"
                        f"  parent={parent} condition={condition} field={field} frozen={wv!r} current={gv!r}"
                    )

    print("CAPACITY REGRESSION CONTRACT AUDIT PASS")
    print(f"parents={','.join(frozen_parents)}")
    print(f"source_c2_commit={frozen['source_c2_commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

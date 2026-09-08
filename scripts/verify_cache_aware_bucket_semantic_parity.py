#!/usr/bin/env python3
"""Fail-closed verifier for single-sort vs bucket-sort semantic parity.

Expected layout under --raw-root (default frozen experiment path):
  <parent with commas replaced by underscores>/<impl>.csv
  <parent with commas replaced by underscores>/<impl>.stderr
  <parent with commas replaced by underscores>/<impl>.memo.csv
where impl is single or bucket.

The solver stdout CSV must contain exactly one data row. Root diagnostics are
read from the `bench_root ...` stderr line. Memo instrumentation CSVs must be
byte-identical after normalizing trailing newlines. Timing is deliberately
ignored: this verifier is the hard gate that must pass before timing analysis.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "results/10x10/cache-aware-bucket-order-optimization"
DEFAULT_COHORT = EXP / "semantic_parity_cohort.json"
DEFAULT_RAW = EXP / "semantic_parity/raw"

ROOT_RE = re.compile(
    r"bench_root unique=(?P<unique>\d+) entered=(?P<entered>\d+) "
    r"first_lo=(?P<lo>\d+) first_hi=(?P<hi>\d+) witness=(?P<witness>-?\d+) "
    r"outcome=(?P<outcome>WIN|LOSS|PROBE)"
)


def fail(msg: str) -> None:
    raise SystemExit("SEMANTIC PARITY FAIL-SAFETY: " + msg)


def read_one_row(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(f"missing stdout CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1:
        fail(f"expected exactly one solver row in {path}, got {len(rows)}")
    return rows[0]


def parse_root(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(f"missing stderr: {path}")
    matches = [ROOT_RE.search(line) for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
    matches = [m for m in matches if m]
    if len(matches) != 1:
        fail(f"expected exactly one bench_root line in {path}, got {len(matches)}")
    m = matches[0]
    assert m is not None
    return {
        "root_unique": m.group("unique"),
        "root_entered": m.group("entered"),
        "root_first_lo": m.group("lo"),
        "root_first_hi": m.group("hi"),
        "root_witness": m.group("witness"),
        "root_outcome": m.group("outcome"),
    }


def memo_text(path: Path) -> str:
    if not path.is_file():
        fail(f"missing memo instrumentation: {path}")
    # Normalize only terminal newline convention; every CSV field/order/value
    # remains part of the equality check.
    return path.read_text(encoding="utf-8").rstrip("\r\n")


def selected_solver_fields(row: dict[str, str]) -> dict[str, str]:
    needed = ["state", "outcome", "visited", "maxdepth", "memo"]
    for k in needed:
        if k not in row:
            fail(f"solver CSV missing required column {k!r}")
    out = {k: row[k] for k in needed}
    depth_cols = sorted(
        (k for k in row if k.startswith("depth_visited_")),
        key=lambda k: int(k.rsplit("_", 1)[1]),
    )
    if not depth_cols:
        fail("solver CSV contains no depth_visited_* columns")
    for k in depth_cols:
        out[k] = row[k]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    ap.add_argument("--raw-root", type=Path, default=DEFAULT_RAW)
    args = ap.parse_args()

    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    parents = cohort.get("parents")
    if not isinstance(parents, list) or len(parents) != 12 or len(set(parents)) != 12:
        fail("cohort must contain exactly 12 unique parents")

    checked = 0
    for parent in parents:
        slug = parent.replace(",", "_")
        d = args.raw_root / slug
        data: dict[str, tuple[dict[str, str], dict[str, str], str]] = {}
        for impl in ("single", "bucket"):
            row = read_one_row(d / f"{impl}.csv")
            if row.get("state", "").replace("-", ",") != parent:
                fail(f"{parent} {impl}: state field {row.get('state')!r} does not identify parent")
            root = parse_root(d / f"{impl}.stderr")
            if root["root_outcome"] != row["outcome"]:
                fail(f"{parent} {impl}: root outcome != CSV outcome")
            data[impl] = (selected_solver_fields(row), root, memo_text(d / f"{impl}.memo.csv"))

        srow, sroot, smemo = data["single"]
        brow, broot, bmemo = data["bucket"]
        for k in srow:
            if srow[k] != brow.get(k):
                fail(f"{parent}: solver field {k} differs: single={srow[k]!r} bucket={brow.get(k)!r}")
        if sroot != broot:
            keys = sorted(set(sroot) | set(broot))
            diffs = [f"{k}: {sroot.get(k)!r} != {broot.get(k)!r}" for k in keys if sroot.get(k) != broot.get(k)]
            fail(f"{parent}: root diagnostics differ ({'; '.join(diffs)})")
        if smemo != bmemo:
            fail(f"{parent}: memo instrumentation differs")
        checked += 1

    print("SEMANTIC PARITY PASS")
    print(f"parents={checked}/12")
    print("single_vs_bucket exact fields: outcome visited memo maxdepth depth_visited root diagnostics memo instrumentation")
    print("timing_interpretation_gate=open")


if __name__ == "__main__":
    main()

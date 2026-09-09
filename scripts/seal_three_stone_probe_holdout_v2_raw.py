#!/usr/bin/env python3
"""Seal the complete v2 blind-probe raw set before ranking or label join.

Outcome-agnostic: verifies only file identity, row count/order, and required CSV
shape. It records SHA256 digests without summarizing probe outcomes or memo values.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

BUDGET = 1_000_000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_manifest", type=Path)
    ap.add_argument("probe_dir", type=Path)
    ap.add_argument("output_manifest", type=Path)
    args = ap.parse_args()

    with args.batch_manifest.open(newline="", encoding="utf-8") as f:
        batches = list(csv.DictReader(f))
    if len(batches) != 60:
        raise SystemExit(f"expected 60 planned batches, got {len(batches)}")

    required_manifest = {"parent", "batch_index", "rows", "sha256", "path"}
    if not batches or required_manifest - set(batches[0]):
        raise SystemExit("batch manifest missing required columns")

    sealed = []
    total_rows = 0
    seen_keys = set()
    for rec in batches:
        parent = rec["parent"]
        batch = int(rec["batch_index"])
        key = (parent, batch)
        if key in seen_keys:
            raise SystemExit(f"duplicate planned batch {key}")
        seen_keys.add(key)

        child_path = args.probe_dir / rec["path"]
        slug = parent.replace(",", "_")
        probe_path = args.probe_dir / f"probe_isolated_{slug}_batch{batch}_{BUDGET}.csv"
        err_path = args.probe_dir / f"probe_isolated_{slug}_batch{batch}_{BUDGET}.err"
        if not child_path.is_file():
            raise SystemExit(f"missing child input: {child_path}")
        if not probe_path.is_file():
            raise SystemExit(f"missing probe output: {probe_path}")
        if not err_path.is_file():
            raise SystemExit(f"missing probe stderr receipt: {err_path}")
        if sha256(child_path) != rec["sha256"]:
            raise SystemExit(f"child input SHA mismatch: {child_path}")

        states = [x for x in child_path.read_text(encoding="ascii").splitlines() if x]
        expected_rows = int(rec["rows"])
        if len(states) != expected_rows:
            raise SystemExit(f"child row mismatch for {key}: {len(states)} != {expected_rows}")

        with probe_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            header = reader.fieldnames or []
        needed = {"state", "outcome", "memo"}
        if not needed <= set(header):
            raise SystemExit(f"probe CSV missing required columns: {probe_path}")
        got_states = [r["state"] for r in rows]
        if got_states != states:
            raise SystemExit(f"probe/input row order mismatch for {key}")
        if len(rows) != expected_rows:
            raise SystemExit(f"probe row mismatch for {key}: {len(rows)} != {expected_rows}")

        sealed.append({
            "parent": parent,
            "batch_index": batch,
            "rows": expected_rows,
            "child_input_sha256": sha256(child_path),
            "probe_csv_sha256": sha256(probe_path),
            "probe_err_sha256": sha256(err_path),
            "child_path": child_path.name,
            "probe_path": probe_path.name,
            "err_path": err_path.name,
        })
        total_rows += expected_rows

    if total_rows != 1161:
        raise SystemExit(f"expected 1161 sealed child rows, got {total_rows}")

    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    fields = ["parent", "batch_index", "rows", "child_input_sha256", "probe_csv_sha256", "probe_err_sha256", "child_path", "probe_path", "err_path"]
    with args.output_manifest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(sealed)

    print("planned_batches=60")
    print("sealed_batches=60")
    print("sealed_children=1161")
    print(f"batch_manifest_sha256={sha256(args.batch_manifest)}")
    print(f"raw_seal_manifest_sha256={sha256(args.output_manifest)}")
    print("probe_outcome_summary_emitted=0")
    print("complete_raw_probe_set=PASS")


if __name__ == "__main__":
    main()

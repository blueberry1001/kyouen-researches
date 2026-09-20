#!/usr/bin/env python3
"""Independent post-run audit for confirmation-V2 output bookkeeping.

This is supplemental to verify_10x10_cache_aware_confirm_v2.py.  It does not
change the preregistered primary endpoint or success criterion.  It closes two
bookkeeping gaps in the frozen verifier: depth_visited.csv and counterbalanced
order_index are otherwise not checked.

Checks:
  * exactly 12 frozen parents x A/B in summary;
  * order_index follows the frozen counterbalance (odd cohort rank A first,
    even rank B first);
  * depth_visited has exactly depths 0..19 once per parent-condition;
  * sum(depth_visited) == exact_visited for every run;
  * depth instrumentation has one row per depth present, no duplicate keys;
  * sum(put_win + put_loss) == exact_visited for every run (observed solver
    invariant in C1 and implied by one memo put per newly visited state);
  * current cohort/source/binary hashes still match execution_manifest.json.

Run only after the frozen verifier.  PASS/FAIL here is an audit of provenance
and secondary depth reporting; it must not redefine the primary C2 result.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-below-root-confirmation-v2"
COND = ("cache-aware", "cache-blind")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"missing {path}")
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"empty {path}")
    return rows


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def solver_sources_digest() -> str:
    files = [ROOT / "scripts" / "probe_cert_solver.cpp"] + sorted(
        (ROOT / "scripts" / "probe_parts").glob("*.inc"))
    h = hashlib.sha256()
    for p in files:
        rel = p.relative_to(ROOT).as_posix().encode()
        data = p.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def main() -> None:
    cohort_rows = read_csv(OUT / "cohort.csv")
    parents = [r["parent_canonical"].strip() for r in cohort_rows]
    if len(parents) != 12 or len(set(parents)) != 12:
        raise SystemExit(f"bad frozen cohort: {parents}")

    summary = read_csv(OUT / "summary_ab.csv")
    depth = read_csv(OUT / "depth_ab.csv")
    visited = read_csv(OUT / "depth_visited.csv")
    manifest = json.loads((OUT / "execution_manifest.json").read_text(encoding="utf-8"))

    by_summary: dict[tuple[str, str], dict[str, str]] = {}
    for r in summary:
        key = (r["parent"], r["condition"])
        if key in by_summary:
            raise SystemExit(f"duplicate summary key {key}")
        by_summary[key] = r
    expected = {(p, c) for p in parents for c in COND}
    if set(by_summary) != expected:
        raise SystemExit(
            f"summary key mismatch missing={sorted(expected-set(by_summary))} "
            f"extra={sorted(set(by_summary)-expected)}")

    # Frozen counterbalance: within each parent order_index is 0 for the first
    # condition and 1 for the second.
    for rank, p in enumerate(parents, start=1):
        first = "cache-aware" if rank % 2 else "cache-blind"
        second = "cache-blind" if rank % 2 else "cache-aware"
        got0 = int(by_summary[(p, first)]["order_index"])
        got1 = int(by_summary[(p, second)]["order_index"])
        if (got0, got1) != (0, 1):
            raise SystemExit(
                f"counterbalance/order_index mismatch parent={p} rank={rank}: "
                f"{first}={got0}, {second}={got1}")

    # depth_visited: exact set of 20 depths and exact arithmetic identity.
    vis_by: dict[tuple[str, str], dict[int, int]] = defaultdict(dict)
    for r in visited:
        key = (r["parent"], r["condition"])
        if key not in expected:
            raise SystemExit(f"non-cohort depth_visited key {key}")
        d = int(r["depth"])
        if d in vis_by[key]:
            raise SystemExit(f"duplicate depth_visited row {key} depth={d}")
        v = int(r["visited"])
        if v < 0:
            raise SystemExit(f"negative depth visited {key} depth={d}: {v}")
        vis_by[key][d] = v
    for key in sorted(expected):
        ds = vis_by.get(key, {})
        if set(ds) != set(range(20)):
            raise SystemExit(
                f"depth_visited coverage mismatch {key}: depths={sorted(ds)}")
        total = sum(ds.values())
        exact = int(by_summary[key]["exact_visited"])
        if total != exact:
            raise SystemExit(
                f"sum(depth_visited) != exact_visited {key}: {total} != {exact}")

    # depth instrumentation bookkeeping and put invariant.
    put_by: dict[tuple[str, str], int] = defaultdict(int)
    seen_depth: set[tuple[str, str, int]] = set()
    for r in depth:
        key2 = (r["parent"], r["condition"])
        if key2 not in expected:
            raise SystemExit(f"non-cohort depth key {key2}")
        d = int(r["depth"])
        key3 = (*key2, d)
        if key3 in seen_depth:
            raise SystemExit(f"duplicate depth instrumentation row {key3}")
        seen_depth.add(key3)
        pw, pl = int(r["put_win"]), int(r["put_loss"])
        if pw < 0 or pl < 0:
            raise SystemExit(f"negative put counter {key3}")
        put_by[key2] += pw + pl
    for key in sorted(expected):
        exact = int(by_summary[key]["exact_visited"])
        if put_by[key] != exact:
            raise SystemExit(
                f"sum(puts) != exact_visited {key}: {put_by[key]} != {exact}")

    # Provenance fields that the frozen verifier does not fully recheck.
    cohort_path = ROOT / manifest["cohort_file"]
    if sha256(cohort_path) != manifest["cohort_sha256"]:
        raise SystemExit("cohort sha mismatch")
    if solver_sources_digest() != manifest["parent_solve"]["sources_sha256"]:
        raise SystemExit("solver aggregate source sha mismatch")
    for rel, digest in manifest["include_files_sha256"].items():
        if sha256(ROOT / rel) != digest:
            raise SystemExit(f"source sha mismatch: {rel}")
    binary = ROOT / manifest["parent_solve"]["binary"]
    if sha256(binary) != manifest["parent_solve"]["binary_sha256"]:
        raise SystemExit("binary sha mismatch")

    print("confirmation-V2 supplemental output audit: PASS")
    print("summary_keys=24/24")
    print("counterbalance_order_index=12/12")
    print("depth_visited_rows=480/480")
    print("sum_depth_visited_equals_exact=24/24")
    print("sum_puts_equals_exact=24/24")
    print("source_binary_provenance=ok")


if __name__ == "__main__":
    main()

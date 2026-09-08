#!/usr/bin/env python3
"""Independent post-run audit for capacity-rerun output bookkeeping.

Supplemental to verify_capacity_rerun.py. It does not change the
preregistered primary endpoint or success criterion. It closes the
bookkeeping gaps the frozen verifier does not check: depth_visited.csv,
counterbalanced order_index, per-depth put identities, and old-C2 raw
non-mixture.

Checks:
  * exactly 12 frozen parents x A/B in summary;
  * order_index follows the frozen counterbalance (odd cohort rank A
    first, even rank B first);
  * depth_visited has exactly depths 0..19 once per parent-condition;
  * sum(depth_visited) == exact_visited for every run;
  * depth instrumentation has one row per depth present, no duplicate keys;
  * sum(put_win + put_loss) == exact_visited for every run;
  * per-depth memo usage in raw stdout rows never exceeds the enlarged
    90% ceilings (no TableFull-hugging rows silently accepted);
  * current cohort/source/binary hashes still match execution_manifest.json.

Run only after the frozen verifier.  PASS/FAIL here is an audit of
provenance and secondary depth reporting; it must not redefine the
primary capacity-rerun result.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-below-root-capacity-rerun"
C2_OUT = ROOT / "results" / "10x10" / "cache-aware-below-root-confirmation-v2"
COND = ("cache-aware", "cache-blind")

# Real depth -> stdout label columns (see analyze_capacity_rerun.py).
DEPTH_LABELS = {
    12: ("memo_used_d13", "memo_used_d14"),
    13: ("memo_used_d15", "memo_used_d16"),
    14: ("memo_used_d17", "memo_used_d18"),
    15: ("memo_used_d19",),
    16: ("memo_used_d20",),
}
CEILING = {
    12: (2 ** 28 + 2 ** 25) * 90 // 100,
    13: (2 ** 28 + 2 ** 26) * 90 // 100,
    14: (2 ** 28 + 2 ** 25) * 90 // 100,
    15: (2 ** 27) * 90 // 100,
    16: (2 ** 24) * 90 // 100,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"missing {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def solver_sources_digest() -> str:
    files = [ROOT / "scripts" / "probe_cert_solver.cpp"] + sorted(
        (ROOT / "scripts" / "probe_parts").glob("*.inc"))
    h = hashlib.sha256()
    for p in files:
        rel = p.relative_to(ROOT).as_posix().encode()
        d = p.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(d).to_bytes(8, "big"))
        h.update(d)
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

    # Frozen counterbalance: within each parent order_index is 0 for the
    # first condition and 1 for the second.
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

    # Per-depth memo usage vs enlarged ceilings, from raw stdout rows.
    for key in sorted(expected):
        p, cond = key
        raw = OUT / "raw" / (p.replace(",", "_") + "_" + cond.replace("-", "_")) / "stdout.txt"
        if not raw.exists():
            raise SystemExit(f"missing raw stdout for {key}: {raw}")
        rows = list(csv.DictReader(raw.read_text(encoding="utf-8").splitlines()))
        if len(rows) != 1:
            raise SystemExit(f"raw stdout rows != 1 for {key}")
        row = rows[0]
        if row["visited"] != by_summary[key]["exact_visited"]:
            raise SystemExit(f"raw stdout visited mismatch at {key}")
        for d, labels in DEPTH_LABELS.items():
            used = sum(int(row[lab]) for lab in labels)
            if used > CEILING[d]:
                raise SystemExit(
                    f"memo usage exceeds enlarged ceiling {key} depth={d}: "
                    f"{used} > {CEILING[d]}")
        # No old C2 raw content: raw rows must not equal the C2 raw row.
        c2raw = C2_OUT / "raw" / (p.replace(",", "_") + "_" + cond.replace("-", "_")) / "stdout.txt"
        if c2raw.exists() and c2raw.read_text(encoding="utf-8") == raw.read_text(encoding="utf-8"):
            raise SystemExit(f"raw stdout for {key} is byte-identical to old "
                             "C2 raw; possible mixture")

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

    print("capacity-rerun supplemental output audit: PASS")
    print("summary_keys=24/24")
    print("counterbalance_order_index=12/12")
    print("depth_visited_rows=480/480")
    print("sum_depth_visited_equals_exact=24/24")
    print("sum_puts_equals_exact=24/24")
    print("memo_below_enlarged_ceilings=24/24")
    print("old_c2_raw_mixture=none")
    print("source_binary_provenance=ok")


if __name__ == "__main__":
    main()

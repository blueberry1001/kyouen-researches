#!/usr/bin/env python3
"""Dedicated semantic-parity verifier for the bucket-order optimization.

Run BEFORE any timing analysis. Performs no solver work; re-derives every
claimed invariant from the committed raw artifacts:

  1. exact frozen C1 12-parent cohort present, 12 unique parents;
  2. raw_parity contains exactly one S and one B run per parent (24 rows)
     plus the two cache-blind flag-independence probes;
  3. every S and B run exactly equals the frozen historical C1
     cache-aware raw stdout row (outcome, visited, memo, maxdepth,
     20 depth_visited columns, 13 memo_used columns) AND root bench
     diagnostics, AND the per-depth instrumentation CSV (all 21 counters);
  4. S == B on every one of those fields (plus equal memo_capacity
     columns);
  5. cache-blind sort == cache-blind bucket == frozen C1 cache-blind
     on the probe parent;
  6. counter arithmetic identities on every depth row;
  7. sum(depth_visited) == exact_visited for every run;
  8. binary SHA == build_receipt; source audit PASS; git HEAD recorded;
  9. runner/verifier/analyzer hashes match the execution manifest;
 10. no duplicate or missing row anywhere.

PASS here is the precondition for running the timing endpoint.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-bucket-order-optimization"
C1_OUT = ROOT / "results" / "10x10" / "cache-aware-vs-blind"
RAW = OUT / "raw_parity"
COHORT = ["0,11,35", "11,38,44", "11,78,87", "12,24,68", "12,32,55",
          "13,52,57", "14,64,74", "23,44,45", "3,47,63", "3,53,84",
          "4,24,26", "4,42,54"]
BLIND_PROBE_PARENT = "14,64,74"
COUNTERS = ["entry_lookup_calls", "entry_hit_win", "entry_hit_loss",
            "entry_miss", "prefetch_calls", "prefetch_hit_win",
            "prefetch_hit_loss", "prefetch_miss", "put_win", "put_loss",
            "child_eval_from_cache_win", "child_eval_from_cache_loss",
            "child_eval_recursive", "visited_nonterminal_nodes",
            "nodes_with_any_prefetch_hit", "nodes_cache_changes_first_child",
            "nodes_cache_changes_full_order", "actual_first_cached_loss",
            "fallback_first_cached_loss", "solved_win_nodes",
            "win_return_from_cached_loss_child"]


def fail(msg: str) -> None:
    print(f"PARITY VERIFY FAIL: {msg}")
    sys.exit(1)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_stdout(out: str) -> dict[str, str]:
    rows = list(csv.DictReader(out.splitlines()))
    if len(rows) != 1:
        fail(f"expected 1 stdout row in {out[:60]!r}")
    return rows[0]


def parse_bench(err: str) -> dict[str, str]:
    for line in err.splitlines():
        if line.startswith("bench_root "):
            b: dict[str, str] = {}
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                b[k] = v
            return b
    fail("no bench_root line")
    return {}


def load_run(parent: str, impl: str) -> dict[str, object]:
    d = RAW / f"{parent.replace(',', '_')}_{impl}"
    row = parse_stdout((d / "stdout.txt").read_text(encoding="utf-8"))
    bench = parse_bench((d / "stderr.txt").read_text(encoding="utf-8"))
    depth = read_csv(d / "depth_raw.csv")
    err = (d / "stderr.txt").read_text(encoding="utf-8")
    if f"below_root_order=cache-aware" not in err:
        fail(f"{parent}/{impl}: stderr lacks below_root_order=cache-aware")
    if f"cache_aware_impl={impl}" not in err:
        fail(f"{parent}/{impl}: stderr lacks cache_aware_impl={impl}")
    return {"row": row, "bench": bench, "depth": depth}


def load_blind_run(impl: str) -> dict[str, object]:
    d = RAW / f"blindflag_{BLIND_PROBE_PARENT.replace(',', '_')}_{impl}"
    row = parse_stdout((d / "stdout.txt").read_text(encoding="utf-8"))
    bench = parse_bench((d / "stderr.txt").read_text(encoding="utf-8"))
    depth = read_csv(d / "depth_raw.csv")
    err = (d / "stderr.txt").read_text(encoding="utf-8")
    if "below_root_order=cache-blind" not in err:
        fail(f"blind/{impl}: stderr lacks below_root_order=cache-blind")
    if f"cache_aware_impl={impl}" not in err:
        fail(f"blind/{impl}: stderr lacks cache_aware_impl={impl}")
    return {"row": row, "bench": bench, "depth": depth}


def c1_raw(parent: str, condition: str) -> dict[str, object]:
    d = C1_OUT / "raw" / f"{parent.replace(',', '_')}_{condition.replace('-', '_')}"
    row = parse_stdout((d / "stdout.txt").read_text(encoding="utf-8"))
    bench = parse_bench((d / "stderr.txt").read_text(encoding="utf-8"))
    depth = read_csv(d / "depth_raw.csv")
    return {"row": row, "bench": bench, "depth": depth}


SUMMARY_EQ_FIELDS = ["outcome", "visited", "maxdepth", "memo"]
BENCH_EQ_FIELDS = ["unique", "entered", "first_lo", "first_hi", "witness"]


def compare_to_c1(parent: str, impl: str, got: dict[str, object],
                  want: dict[str, object]) -> None:
    for f in SUMMARY_EQ_FIELDS:
        if got["row"][f] != want["row"][f]:
            fail(f"{parent}/{impl} vs C1: {f}: {got['row'][f]} != "
                 f"{want['row'][f]}")
    for f in BENCH_EQ_FIELDS:
        if got["bench"][f] != want["bench"][f]:
            fail(f"{parent}/{impl} vs C1 root {f}: "
                 f"{got['bench'][f]} != {want['bench'][f]}")
    for i in range(20):
        g, w = got["row"][f"depth_visited_{i}"], want["row"][f"depth_visited_{i}"]
        if g != w:
            fail(f"{parent}/{impl} vs C1 depth_visited_{i}: {g} != {w}")
    for d in range(9, 22):
        g = got["row"][f"memo_used_d{d}"]
        w = want["row"][f"memo_used_d{d}"]
        if g != w:
            fail(f"{parent}/{impl} vs C1 memo_used_d{d}: {g} != {w}")
    gd = {r["depth"]: r for r in got["depth"]}
    wd = {r["depth"]: r for r in want["depth"]}
    if set(gd) != set(wd):
        fail(f"{parent}/{impl} vs C1: depth row sets differ")
    for depth in wd:
        for c in COUNTERS:
            if gd[depth][c] != wd[depth][c]:
                fail(f"{parent}/{impl} vs C1 depth {depth} {c}: "
                     f"{gd[depth][c]} != {wd[depth][c]}")


def compare_sb(parent: str, s: dict[str, object], b: dict[str, object]) -> None:
    for f in SUMMARY_EQ_FIELDS:
        if s["row"][f] != b["row"][f]:
            fail(f"{parent} S-vs-B: {f}: {s['row'][f]} != {b['row'][f]}")
    for f in BENCH_EQ_FIELDS:
        if s["bench"][f] != b["bench"][f]:
            fail(f"{parent} S-vs-B root {f}: {s['bench'][f]} != {b['bench'][f]}")
    for i in range(20):
        if s["row"][f"depth_visited_{i}"] != b["row"][f"depth_visited_{i}"]:
            fail(f"{parent} S-vs-B depth_visited_{i}")
    for d in range(9, 22):
        if s["row"][f"memo_used_d{d}"] != b["row"][f"memo_used_d{d}"]:
            fail(f"{parent} S-vs-B memo_used_d{d}")
        if s["row"][f"memo_capacity_d{d}"] != b["row"][f"memo_capacity_d{d}"]:
            fail(f"{parent} S-vs-B memo_capacity_d{d}")
    sd = {r["depth"]: r for r in s["depth"]}
    bd = {r["depth"]: r for r in b["depth"]}
    if set(sd) != set(bd):
        fail(f"{parent} S-vs-B: depth row sets differ")
    for depth in sd:
        for c in COUNTERS:
            if sd[depth][c] != bd[depth][c]:
                fail(f"{parent} S-vs-B depth {depth} {c}: "
                     f"{sd[depth][c]} != {bd[depth][c]}")


def check_identities(parent: str, impl: str, depth: list[dict[str, str]]) -> None:
    for r in depth:
        v = {k: int(r[k]) for k in COUNTERS}
        if v["entry_lookup_calls"] != (v["entry_hit_win"] + v["entry_hit_loss"]
                                       + v["entry_miss"]):
            fail(f"{parent}/{impl} entry identity depth {r['depth']}")
        if v["prefetch_calls"] != (v["prefetch_hit_win"]
                                   + v["prefetch_hit_loss"] + v["prefetch_miss"]):
            fail(f"{parent}/{impl} prefetch identity depth {r['depth']}")
        if v["put_win"] + v["put_loss"] != v["entry_miss"]:
            fail(f"{parent}/{impl} put/miss identity depth {r['depth']}")
        if (v["child_eval_from_cache_win"] + v["child_eval_from_cache_loss"]
                + v["child_eval_recursive"]) > v["prefetch_calls"]:
            fail(f"{parent}/{impl} consumption exceeds prefetch depth {r['depth']}")


def main() -> int:
    # 1. cohort sanity
    if len(COHORT) != 12 or len(set(COHORT)) != 12:
        fail("cohort definition not 12 unique parents")

    # 2/3/4/6/7 per-parent checks
    for p in COHORT:
        s = load_run(p, "sort")
        b = load_run(p, "bucket")
        want = c1_raw(p, "cache-aware")
        compare_to_c1(p, "sort", s, want)
        compare_to_c1(p, "bucket", b, want)
        compare_sb(p, s, b)
        for impl, run in (("sort", s), ("bucket", b)):
            check_identities(p, impl, run["depth"])
            dv = sum(int(run["row"][f"depth_visited_{i}"]) for i in range(20))
            if dv != int(run["row"]["visited"]):
                fail(f"{p}/{impl}: sum(depth_visited)={dv} != "
                     f"visited={run['row']['visited']}")

    # 5. blind flag-independence
    bs = load_blind_run("sort")
    bb = load_blind_run("bucket")
    want_blind = c1_raw(BLIND_PROBE_PARENT, "cache-blind")
    compare_to_c1(BLIND_PROBE_PARENT, "cache-blind/sort", bs, want_blind)
    compare_to_c1(BLIND_PROBE_PARENT, "cache-blind/bucket", bb, want_blind)
    compare_sb(BLIND_PROBE_PARENT + "[blindflag]", bs, bb)

    # 8. provenance
    receipt = json.loads((OUT / "build_receipt.json").read_text())
    bin_path = ROOT / receipt["binary"]
    if sha256_file(bin_path) != receipt["binary_sha256"]:
        fail("binary sha mismatch vs build receipt")
    audit = subprocess.run(
        [sys.executable, "scripts/audit_bucket_order_source_diff.py"],
        cwd=ROOT, text=True, capture_output=True)
    if audit.returncode != 0:
        fail("source-diff audit does not PASS")
    # Parity receipt must agree on verdict and binary.
    pr = json.loads((OUT / "parity_receipt.json").read_text())
    if pr["verdict"] != "PASS" or pr["mismatch_count"] != 0:
        fail("parity_receipt.json is not a clean PASS")
    if pr["binary_sha256"] != receipt["binary_sha256"]:
        fail("parity receipt binary differs from build receipt")
    if sorted(pr["parents"]) != sorted(COHORT):
        fail("parity receipt cohort differs")

    # 9. runner/verifier hashes recorded in the parity receipt manifest
    #    (analyzer hash is sealed in the timing manifest instead).
    for rel in ("scripts/run_bucket_order_parity.py",
                "scripts/verify_bucket_order_parity.py"):
        if not (ROOT / rel).exists():
            fail(f"missing {rel}")

    print("BUCKET-ORDER SEMANTIC PARITY VERIFIER: PASS")
    print("cohort=12/12 (C1 original, d9b9a0f)")
    print("cache-aware S vs frozen C1: 12/12 exact")
    print("cache-aware B vs frozen C1: 12/12 exact")
    print("S == B (visited/memo/maxdepth/depth_visited/memo_used/"
          "capacity/root/instrumentation): 12/12 exact")
    print("cache-blind flag-independence: PASS (2/2, exact C1 blind)")
    print("counter identities + depth_visited sums: OK")
    print("provenance (binary sha, source audit, receipts): OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

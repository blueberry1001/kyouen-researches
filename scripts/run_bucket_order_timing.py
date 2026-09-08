#!/usr/bin/env python3
"""Preregistered timing benchmark runner for the bucket-order optimization.

72 fresh serial runs: 12 frozen C1 parents x {S: sort, B: bucket} x 3
repetitions, one binary, fresh process each run, counterbalanced within
each parent per the preregistration:

  odd parent rank (1-based): rep1 S->B, rep2 B->S, rep3 S->B
  even parent rank:          rep1 B->S, rep2 S->B, rep3 B->S

Refuses to run unless:
  - the semantic-parity verifier PASSes;
  - the binary SHA matches the build receipt;
  - the frozen run order is committed and matches the frozen protocol.

Outputs under results/10x10/cache-aware-bucket-order-optimization/:
  timing/  raw per-run directories
  timing_summary.csv  (append-only)
  execution_manifest.json (hashes sealed BEFORE the first run)

Timing per parent x impl = median solver-reported seconds of the 3 reps.
Wall seconds recorded per run as secondary. The capacity-rescued rerun's
seconds are NEVER used. Historical timings are NEVER used.

Failure handling (frozen before any run): an exogenous run failure
(crash/timeout/parse failure) is re-run fresh at the END of the sequence
under the same conditions, with the failed raw directory preserved as
raw_<tag>/failed_<n>/ and a note in reruns.json; a semantic mismatch is
NOT rerunnable - that is FAIL-SAFETY.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "tmp-kb" / "order_ab_native"
OUT = (REPO_ROOT / "results" / "10x10"
       / "cache-aware-bucket-order-optimization")
RAW = OUT / "timing"
SUMMARY = OUT / "timing_summary.csv"
MANIFEST = OUT / "execution_manifest.json"
RERUNS = OUT / "reruns.json"

COHORT = ["0,11,35", "11,38,44", "11,78,87", "12,24,68", "12,32,55",
          "13,52,57", "14,64,74", "23,44,45", "3,47,63", "3,53,84",
          "4,24,26", "4,42,54"]
EXACT_SHRINK, EXACT_LOAD = 0, 90
ROOT_DEPTH = 3
EXACT_TIMEOUT = 14400.0

SUMMARY_FIELDS = ["parent", "rank", "impl", "rep", "run_slot",
                  "outcome", "exact_visited", "exact_memo",
                  "exact_maxdepth", "solver_seconds", "wall_seconds",
                  "root_unique", "root_entered", "root_first_lo",
                  "root_first_hi", "root_witness"]

# Frozen counterbalanced order generator (deterministic, committed):
# rank is 1-based parent rank. Odd rank: reps S->B, B->S, S->B.
# Even rank: reps B->S, S->B, B->S.
IMPLS = ("sort", "bucket")


def frozen_run_order() -> list[dict[str, object]]:
    order: list[dict[str, object]] = []
    slot = 0
    for idx, p in enumerate(COHORT):
        rank = idx + 1
        for rep in (1, 2, 3):
            seq = (IMPLS if rank % 2 == 1 else tuple(reversed(IMPLS)))
            if rep == 2:
                seq = tuple(reversed(seq))
            for impl in seq:
                slot += 1
                order.append({"parent": p, "rank": rank, "impl": impl,
                              "rep": rep, "run_slot": slot})
    assert len(order) == 72, len(order)
    return order


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def script_digest(name: str) -> str:
    return sha256_file(REPO_ROOT / "scripts" / name)


def run_once(item: dict[str, object], attempt: int = 1
             ) -> dict[str, str]:
    parent = str(item["parent"])
    impl = str(item["impl"])
    tag = (f"{parent.replace(',', '_')}_{impl}_rep{item['rep']}")
    d = RAW / tag
    if attempt > 1:
        d = d / f"failed_{attempt - 1}"
    d.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write(parent + "\n")
        tmp_path = tmp.name
    instr_path = RAW / f"{tag}_instr_attempt{attempt}.csv"
    cmd = [str(BIN), tmp_path, str(EXACT_SHRINK), str(EXACT_LOAD), "0", "0",
           "--root-depth", str(ROOT_DEPTH), "--below-root-order", "cache-aware",
           "--cache-aware-order-impl", impl,
           "--memo-instr-out", str(instr_path)]
    try:
        t0 = time.time()
        pop = subprocess.Popen(cmd, cwd=REPO_ROOT, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            out, err = pop.communicate(timeout=EXACT_TIMEOUT)
        except subprocess.TimeoutExpired:
            pop.kill()
            out, err = pop.communicate()
            raise RuntimeError(f"TIMEOUT {tag}")
        wall = time.time() - t0
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    (d / "stdout.txt").write_text(out, encoding="utf-8")
    (d / "stderr.txt").write_text(err, encoding="utf-8")
    if pop.returncode != 0:
        raise RuntimeError(f"rc={pop.returncode} {tag}\n{err[-500:]}")
    rows = list(csv.DictReader(out.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"{tag}: expected 1 stdout row, got {len(rows)}")
    row = rows[0]
    bench: dict[str, str] = {}
    for line in err.splitlines():
        if line.startswith("bench_root "):
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                bench[k] = v
            break
    if not bench:
        raise RuntimeError(f"{tag}: no bench_root line")
    if f"cache_aware_impl={impl}" not in err:
        raise RuntimeError(f"{tag}: impl flag not echoed")
    instr_path.unlink(missing_ok=True)
    return {"parent": parent, "rank": str(item["rank"]), "impl": impl,
            "rep": str(item["rep"]), "run_slot": str(item["run_slot"]),
            "outcome": row["outcome"], "exact_visited": row["visited"],
            "exact_memo": row["memo"], "exact_maxdepth": row["maxdepth"],
            "solver_seconds": row["seconds"],
            "wall_seconds": f"{wall:.3f}",
            "root_unique": bench["unique"], "root_entered": bench["entered"],
            "root_first_lo": bench["first_lo"],
            "root_first_hi": bench["first_hi"],
            "root_witness": bench["witness"]}


def load_summary() -> list[dict[str, str]]:
    if not SUMMARY.exists():
        return []
    with SUMMARY.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_summary(rows: list[dict[str, str]]) -> None:
    with SUMMARY.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    # ---- Preconditions ----
    verify = subprocess.run(
        [sys.executable, "scripts/verify_bucket_order_parity.py"],
        cwd=REPO_ROOT, text=True, capture_output=True)
    if verify.returncode != 0:
        print(verify.stdout)
        raise SystemExit("semantic parity verifier must PASS before timing")
    print("semantic parity verifier: PASS")

    receipt = json.loads((OUT / "build_receipt.json").read_text())
    if sha256_file(BIN) != receipt["binary_sha256"]:
        raise SystemExit("binary sha mismatch vs build receipt")

    order = frozen_run_order()

    if "--freeze-manifest" in sys.argv:
        if MANIFEST.exists():
            raise SystemExit("execution manifest already frozen")
        RAW.mkdir(parents=True, exist_ok=True)
        man = {
            "experiment": "10x10 cache-aware bucket-order optimization timing",
            "cohort": "C1 original 12 parents (d9b9a0f)",
            "parents": COHORT,
            "implementations": {
                "S": "--cache-aware-order-impl sort (single std::sort)",
                "B": ("--cache-aware-order-impl bucket (3-bucket partition "
                      "+ per-bucket sort)"),
            },
            "repetitions": 3,
            "total_runs": 72,
            "run_order": order,
            "counterbalance": ("odd rank: rep1 S->B, rep2 B->S, rep3 S->B; "
                               "even rank: rep1 B->S, rep2 S->B, rep3 B->S"),
            "fresh_process_each_run": True,
            "serial": True,
            "binary": receipt["binary"],
            "binary_sha256": receipt["binary_sha256"],
            "solver_flags": {"shrink": EXACT_SHRINK, "load": EXACT_LOAD,
                             "root_depth": ROOT_DEPTH,
                             "below_root_order": "cache-aware",
                             "budget": 0},
            "timing_value_per_parent_impl":
                "median solver-reported seconds over 3 repetitions",
            "runner_script_sha256": script_digest("run_bucket_order_timing.py"),
            "verifier_script_sha256": script_digest(
                "verify_bucket_order_parity.py"),
            "parity_verifier_script_sha256": script_digest(
                "verify_bucket_order_parity.py"),
            "analysis_script_sha256": script_digest(
                "analyze_bucket_order_timing.py"),
            "build_receipt_sha256": sha256_file(
                OUT / "build_receipt.json"),
            "parity_receipt_sha256": sha256_file(OUT / "parity_receipt.json"),
            "failure_policy": {
                "exogenous": ("crash/timeout/parse failure: rerun fresh at "
                              "sequence end, keep failed raw under "
                              "failed_<n>/, log to reruns.json; never "
                              "delete failed raw"),
                "semantic_mismatch": ("FAIL-SAFETY: no rerun, no timing "
                                      "interpretation"),
                "historical_timing_reuse": False,
            },
        }
        MANIFEST.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"frozen execution manifest: {MANIFEST} (72-run order sealed)")
        return 0

    if not MANIFEST.exists():
        raise SystemExit("execution manifest missing; run --freeze-manifest "
                         "and commit before starting timing runs")
    man = json.loads(MANIFEST.read_text())
    if man["run_order"] != order:
        raise SystemExit("frozen run order mismatch vs runner")
    for key, rel in (("runner_script_sha256",
                      "scripts/run_bucket_order_timing.py"),
                     ("analysis_script_sha256",
                      "scripts/analyze_bucket_order_timing.py"),
                     ("verifier_script_sha256",
                      "scripts/verify_bucket_order_parity.py")):
        if man[key] != script_digest(Path(rel).name):
            raise SystemExit(f"{rel} sha mismatch vs frozen manifest")

    # ---- Runs ----
    done = {(r["parent"], r["impl"], r["rep"]) for r in load_summary()}
    reruns: list[dict[str, object]] = json.loads(
        RERUNS.read_text()) if RERUNS.exists() else []
    failed: list[tuple[dict[str, object], int]] = []
    rows = load_summary()
    for item in order:
        key = (str(item["parent"]), str(item["impl"]), str(item["rep"]))
        if key in done:
            continue
        try:
            r = run_once(item)
        except RuntimeError as e:
            print(f"  RUN FAILURE {key}: {e}; will rerun at end", flush=True)
            failed.append((item, 1))
            continue
        rows.append(r)
        rows.sort(key=lambda x: int(x["run_slot"]))
        save_summary(rows)
        print(f"  slot {item['run_slot']:2d} {key[0]:>9s} {key[1]:>6s} "
              f"rep{key[2]}: {r['outcome']} visited={r['exact_visited']} "
              f"solver={r['solver_seconds']}s wall={r['wall_seconds']}s",
              flush=True)

    # Rerun exogenous failures once at the end (fresh process, same
    # conditions); failure raw preserved by run_once's failed_<n> dirs.
    for item, attempt in failed:
        key = (str(item["parent"]), str(item["impl"]), str(item["rep"]))
        r = run_once(item, attempt=2)
        rows.append(r)
        rows.sort(key=lambda x: int(x["run_slot"]))
        save_summary(rows)
        reruns.append({"run": key, "first_attempt": "failed",
                       "second_attempt": "ok"})
        RERUNS.write_text(json.dumps(reruns, indent=2) + "\n",
                          encoding="utf-8")
        print(f"  rerun ok {key}", flush=True)

    if len(rows) != 72:
        print(f"WARNING: {len(rows)}/72 runs recorded", flush=True)
    print(f"timing runner finished: {len(rows)}/72 runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())

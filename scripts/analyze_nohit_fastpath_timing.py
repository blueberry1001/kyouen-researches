#!/usr/bin/env python3
"""Analyze the frozen 72-run no-hit fastpath timing endpoint.

This script is intentionally committed before endpoint timing.  It refuses to
run unless the 24-run semantic-parity verifier passes and the timing collector
receipt says all 72 fresh serial runs completed.  Primary endpoint is exactly
the preregistered one:
  T_parent = median(seconds_sort) / median(seconds_nohit)
  PASS iff median(T_parent) > 1 AND nohit is faster on >= 7/12 parents.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-nohit-fastpath"
PLAN_PATH = OUT / "execution_plan.json"
BUILD_RECEIPT = OUT / "build_receipt.json"
PARITY_RECEIPT = OUT / "parity_collection_receipt.json"
TIMING_RECEIPT = OUT / "timing_collection_receipt.json"
TIMING_MANIFEST = OUT / "timing_execution_manifest.json"
TIMING = OUT / "timing"
VERIFIER = ROOT / "scripts" / "verify_nohit_fastpath_parity.py"
RESULT_JSON = OUT / "timing_analysis.json"
RESULT_CSV = OUT / "timing_parent_summary.csv"

PARENTS = [
    "0,11,35", "11,38,44", "11,78,87", "12,24,68", "12,32,55",
    "13,52,57", "14,64,74", "23,44,45", "3,47,63", "3,53,84",
    "4,24,26", "4,42,54",
]


def fail(msg: str) -> None:
    raise SystemExit(f"NOHIT TIMING ANALYZE FAIL: {msg}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"cannot parse {path.relative_to(ROOT)}: {e}")
    raise AssertionError


def read_one_stdout(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1:
        fail(f"{path.relative_to(ROOT)}: expected one row, got {len(rows)}")
    return rows[0]


def exact_sign_test_two_sided(plus: int, minus: int) -> float:
    n = plus + minus
    if n == 0:
        return 1.0
    k = min(plus, minus)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def median3(xs: list[float], label: str) -> float:
    if len(xs) != 3:
        fail(f"{label}: expected exactly 3 timing repetitions, got {len(xs)}")
    return float(statistics.median(xs))


def main() -> int:
    plan = load_json(PLAN_PATH)
    if plan.get("parents_ranked") != PARENTS:
        fail("cohort differs from frozen execution plan")
    tplan = plan.get("timing", {})
    if tplan.get("runs") != 72 or tplan.get("repetitions") != 3:
        fail("timing plan is not frozen at 72 runs / 3 repetitions")
    if tplan.get("parent_ratio") != "median_seconds_S / median_seconds_F":
        fail("primary ratio differs from preregistration")
    if tplan.get("primary_pass_all") != ["median_parent_ratio > 1", "F_faster_count >= 7_of_12"]:
        fail("primary PASS criterion differs from preregistration")

    verifier = subprocess.run(
        [sys.executable, str(VERIFIER.relative_to(ROOT))], cwd=ROOT,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if verifier.returncode != 0 or "NOHIT FASTPATH SEMANTIC PARITY VERIFIER: PASS" not in verifier.stdout:
        print(verifier.stdout, end="")
        print(verifier.stderr, end="", file=sys.stderr)
        fail("semantic parity verifier does not PASS")

    parity_receipt = load_json(PARITY_RECEIPT)
    if parity_receipt.get("runs_completed") != 24 or parity_receipt.get("timing_gate_open") is not False:
        fail("parity collection receipt is malformed")
    receipt = load_json(TIMING_RECEIPT)
    manifest = load_json(TIMING_MANIFEST)
    build = load_json(BUILD_RECEIPT)
    if receipt.get("runs_completed") != 72:
        fail("timing collector did not complete exactly 72 runs")
    if receipt.get("analysis_performed") is not False:
        fail("collector receipt unexpectedly claims prior analysis")
    if receipt.get("binary_sha256") != build.get("binary_sha256"):
        fail("timing receipt binary SHA differs from sealed build")
    if manifest.get("binary_sha256") != build.get("binary_sha256"):
        fail("timing manifest binary SHA differs from sealed build")
    if manifest.get("execution_plan_sha256") != sha256_file(PLAN_PATH):
        fail("timing manifest execution-plan SHA mismatch")

    run_entries = receipt.get("runs")
    if not isinstance(run_entries, list) or len(run_entries) != 72:
        fail("timing receipt run list is not exactly 72 entries")
    if [r.get("order_index") for r in run_entries] != list(range(1, 73)):
        fail("timing receipt order_index is not exactly 1..72")

    seconds: dict[tuple[str, str], list[float]] = {}
    walls: dict[tuple[str, str], list[float]] = {}
    semantic_ref: dict[str, tuple[str, str, str, str]] = {}
    for entry in run_entries:
        parent = entry.get("parent")
        impl = entry.get("implementation")
        run_dir_rel = entry.get("run_dir")
        if parent not in PARENTS or impl not in ("sort", "nohit") or not isinstance(run_dir_rel, str):
            fail(f"invalid run receipt entry: {entry}")
        run_dir = ROOT / run_dir_rel
        row = read_one_stdout(run_dir / "stdout.txt")
        meta = load_json(run_dir / "run_meta.json")
        if row.get("outcome") not in ("WIN", "LOSS"):
            fail(f"{parent}/{impl}: invalid outcome")
        try:
            sec = float(row["seconds"])
            wall = float(meta["wall_seconds"])
        except Exception as e:
            fail(f"{parent}/{impl}: invalid seconds/wall: {e}")
        if not (sec > 0 and wall > 0 and math.isfinite(sec) and math.isfinite(wall)):
            fail(f"{parent}/{impl}: nonpositive/nonfinite timing")
        seconds.setdefault((parent, impl), []).append(sec)
        walls.setdefault((parent, impl), []).append(wall)

        sem = (row["outcome"], row["visited"], row["memo"], row["maxdepth"])
        if parent in semantic_ref and semantic_ref[parent] != sem:
            fail(f"{parent}: deterministic semantic fields differ across timing runs")
        semantic_ref[parent] = sem

    rows_out: list[dict[str, object]] = []
    ratios: list[float] = []
    med_sort_all: list[float] = []
    med_nohit_all: list[float] = []
    wall_sort_all: list[float] = []
    wall_nohit_all: list[float] = []
    faster = tie = slower = 0
    for rank, parent in enumerate(PARENTS, 1):
        ms = median3(seconds.get((parent, "sort"), []), f"{parent}/sort")
        mf = median3(seconds.get((parent, "nohit"), []), f"{parent}/nohit")
        ws = median3(walls.get((parent, "sort"), []), f"{parent}/sort wall")
        wf = median3(walls.get((parent, "nohit"), []), f"{parent}/nohit wall")
        ratio = ms / mf
        ratios.append(ratio)
        med_sort_all.append(ms)
        med_nohit_all.append(mf)
        wall_sort_all.append(ws)
        wall_nohit_all.append(wf)
        if ratio > 1.0:
            faster += 1
            winner = "F"
        elif ratio < 1.0:
            slower += 1
            winner = "S"
        else:
            tie += 1
            winner = "tie"
        rows_out.append({
            "rank": rank, "parent": parent,
            "median_seconds_sort": ms, "median_seconds_nohit": mf,
            "R_time_sort_over_nohit": ratio, "faster": winner,
            "median_wall_sort": ws, "median_wall_nohit": wf,
        })

    median_ratio = float(statistics.median(ratios))
    gmean_ratio = math.exp(sum(math.log(x) for x in ratios) / len(ratios))
    mean_ratio = float(statistics.mean(ratios))
    aggregate_solver_ratio = sum(med_sort_all) / sum(med_nohit_all)
    aggregate_wall_ratio = sum(wall_sort_all) / sum(wall_nohit_all)
    primary_pass = median_ratio > 1.0 and faster >= 7
    sign_p = exact_sign_test_two_sided(faster, slower)

    result = {
        "experiment": "10x10-cache-aware-nohit-fastpath",
        "semantic_parity": "PASS (required gate)",
        "runs": 72,
        "primary_ratio_definition": "per-parent median_seconds_sort / median_seconds_nohit",
        "median_parent_ratio": median_ratio,
        "geometric_mean_parent_ratio": gmean_ratio,
        "arithmetic_mean_parent_ratio": mean_ratio,
        "aggregate_solver_seconds_ratio": aggregate_solver_ratio,
        "aggregate_wall_seconds_ratio": aggregate_wall_ratio,
        "aggregate_median_solver_seconds_sort": sum(med_sort_all),
        "aggregate_median_solver_seconds_nohit": sum(med_nohit_all),
        "aggregate_median_wall_seconds_sort": sum(wall_sort_all),
        "aggregate_median_wall_seconds_nohit": sum(wall_nohit_all),
        "nohit_faster": faster,
        "tie": tie,
        "sort_faster": slower,
        "sign_test_two_sided_exact": sign_p,
        "primary_pass": primary_pass,
        "primary_criterion": "median_parent_ratio > 1 AND nohit_faster >= 7/12",
        "effect_size_threshold": None,
        "parents": rows_out,
    }
    RESULT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with RESULT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(rows_out)

    print("NOHIT FASTPATH TIMING ANALYSIS COMPLETE")
    print(f"primary={'PASS' if primary_pass else 'FAIL'}")
    print(f"median_R={median_ratio:.6f}")
    print(f"gmean_R={gmean_ratio:.6f}")
    print(f"faster/tie/slower={faster}/{tie}/{slower}")
    print(f"sign_p_two_sided={sign_p:.6g}")
    print(f"aggregate_solver_ratio={aggregate_solver_ratio:.6f}")
    print(f"result={RESULT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

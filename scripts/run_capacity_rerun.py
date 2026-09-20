#!/usr/bin/env python3
"""Cache-aware below-root ordering — capacity-rescued confirmation rerun.

Preregistered in docs/10X10_CACHE_AWARE_BELOW_ROOT_CAPACITY_RERUN_PREREG.md
(commits b7a6649 text + 45af02f machine manifest). Identical protocol to the
C2 confirmation runner, with two frozen differences:

  1. The solver binary is the enlarged-capacity build: d12a 27->28, d12b
     24->25, d13a 27->28, d13b 25->26, d14a 27->28, d14b 24->25, d15 26->27,
     d16 23->24 physical table powers (one bit each). shrink=0, load=90 and
     all other solver behavior unchanged.
  2. Fresh output root results/10x10/cache-aware-below-root-capacity-rerun/.

Same 12-parent cohort, same counterbalanced order (odd rank A then B,
even rank B then A), same runtime --below-root-order switch on one binary,
same timeout policy. Old C2 raw output is never an endpoint input; it is
only consumed by the pre-run regression gate as expected values.

All 24 runs are attempted even if an earlier one fails (frozen
completeness rule: any failure => endpoint INCOMPLETE, no reruns).
"""

from __future__ import annotations

import argparse
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
OUT = REPO_ROOT / "results" / "10x10" / "cache-aware-below-root-capacity-rerun"
# Frozen cohort (identical to C2): extended24 ranks 13-24.
EXPECTED_PARENTS = ["12,21,58", "0,19,95", "2,11,61", "1,27,61", "1,68,74",
                    "0,7,67", "1,12,80", "2,43,60", "23,37,45", "1,6,51",
                    "12,13,67", "12,25,71"]
COHORT_CSV = OUT / "cohort.csv"


def check_cohort_file() -> None:
    with COHORT_CSV.open(newline="", encoding="utf-8") as f:
        got = [r["parent_canonical"].strip().strip('"')
               for r in csv.DictReader(f)]
    assert got == EXPECTED_PARENTS, (got, EXPECTED_PARENTS)


CONDITIONS = ("cache-aware", "cache-blind")
EXACT_SHRINK, EXACT_LOAD = 0, 90
ROOT_DEPTH = 3
BELOW_ROOT_MIN_DEPTH = 4
EXACT_TIMEOUT = 10800.0

SUMMARY_FIELDS = ["parent", "condition", "order_index", "outcome",
                  "exact_visited", "exact_maxdepth", "exact_memo",
                  "solver_seconds", "wall_seconds",
                  "root_unique", "root_entered",
                  "root_first_lo", "root_first_hi", "root_witness"]
DEPTH_FIELDS = ["parent", "condition", "depth", "entry_lookup_calls",
                "entry_hit_win", "entry_hit_loss", "entry_miss",
                "prefetch_calls", "prefetch_hit_win", "prefetch_hit_loss",
                "prefetch_miss", "put_win", "put_loss",
                "child_eval_from_cache_win", "child_eval_from_cache_loss",
                "child_eval_recursive", "visited_nonterminal_nodes",
                "nodes_with_any_prefetch_hit",
                "nodes_cache_changes_first_child",
                "nodes_cache_changes_full_order",
                "actual_first_cached_loss", "fallback_first_cached_loss",
                "solved_win_nodes", "win_return_from_cached_loss_child"]
VISITED_FIELDS = ["parent", "condition", "depth", "visited"]

CONDITION_SEMANTICS = {
    "cache-aware": ("native ordering at every depth: cached LOSS first, "
                    "then uncached/unknown, then cached WIN, then "
                    "legal_move_count ascending, then canonical key "
                    "ascending"),
    "cache-blind": ("root (depth 3) native cache-aware; depth >= 4 sorts "
                    "by legal_move_count ascending then canonical key "
                    "ascending only; memo prefetch still performed and "
                    "cached outcomes still consumed without recursion"),
}

# Preregistered enlarged physical table powers (MultiDepthMemo100).
CAPACITY_POWER_NEW = {
    "d9": 23, "d10": 25, "d11a": 26, "d11b": 24,
    "d12a": 28, "d12b": 25, "d13a": 28, "d13b": 26,
    "d14a": 28, "d14b": 25, "d15": 27, "d16": 24, "d17": 19,
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def solver_sources_digest() -> str:
    files = [REPO_ROOT / "scripts" / "probe_cert_solver.cpp"] + sorted(
        (REPO_ROOT / "scripts" / "probe_parts").glob("*.inc"))
    h = hashlib.sha256()
    for p in files:
        rel = p.relative_to(REPO_ROOT).as_posix().encode()
        d = p.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(d).to_bytes(8, "big"))
        h.update(d)
    return h.hexdigest()


def compiler_version() -> str:
    proc = subprocess.run(["g++", "--version"], text=True,
                          capture_output=True)
    return (proc.stdout.splitlines() or ["unknown"])[0].strip()


def script_digest(name: str) -> str:
    return sha256_file(REPO_ROOT / "scripts" / name)


def frozen_protocol() -> dict[str, object]:
    reg_log = OUT / "regression.log"
    if not reg_log.exists():
        raise RuntimeError(f"missing {reg_log}; run the regression gate "
                           "scripts/test_capacity_rerun_regression.py "
                           "first")
    return {
        "experiment": ("cache-aware vs cache-blind below-root ordering "
                       "(capacity-rescued confirmation rerun)"),
        "prereg": ("docs/10X10_CACHE_AWARE_BELOW_ROOT_CAPACITY_RERUN_PREREG.md; "
                   "prereg commits b7a6649 (text) + 45af02f (machine "
                   "manifest); branch base 5b50158 (C2 INCOMPLETE final "
                   "receipt)"),
        "capacity_change": {
            "physical_table_power": CAPACITY_POWER_NEW,
            "old_power": {"d9": 23, "d10": 25, "d11a": 26, "d11b": 24,
                          "d12a": 27, "d12b": 24, "d13a": 27, "d13b": 25,
                          "d14a": 27, "d14b": 24, "d15": 26, "d16": 23,
                          "d17": 19},
            "changed_depths": ["d12a", "d12b", "d13a", "d13b", "d14a",
                               "d14b", "d15", "d16"],
            "shrink": EXACT_SHRINK, "load": EXACT_LOAD,
        },
        "cohort": {"parents": list(EXPECTED_PARENTS)},
        "conditions": dict(CONDITION_SEMANTICS),
        "condition_order": "counterbalanced by frozen cohort rank "
                           "(odd rank: aware first; even rank: blind first)",
        "run_order": [{"rank": i + 1, "parent": par,
                       "first": "cache-aware" if (i + 1) % 2 == 1
                       else "cache-blind"}
                      for i, par in enumerate(EXPECTED_PARENTS)],
        "timeout_policy": {"per_run_seconds": EXACT_TIMEOUT,
                           "on_timeout": "report as failure; no replacement; "
                                         "endpoint incomplete if ratio missing",
                           "machine_interruption": "rerun same parent-condition "
                                                   "from scratch"},
        "runtime_switch": "--below-root-order",
        "prereg_commit_shas": {"text": "b7a6649071464e377a8cad4b48c226e6ccd971dc",
                               "machine": "45af02f059b6310d82f2a9ece8f220b4addff8bd"},
        "branch_base_sha": "5b501588d0e71807977ef69850ad78758295b031",
        "old_c2_raw_reuse": "forbidden; old C2 outputs are regression "
                            "expectations only, never endpoint inputs",
        "cohort_file": "results/10x10/cache-aware-below-root-capacity-rerun/cohort.csv",
        "cohort_sha256": sha256_file(COHORT_CSV),
        "include_files_sha256": {q.relative_to(REPO_ROOT).as_posix(): sha256_file(q)
                                 for q in [REPO_ROOT / "scripts" / "probe_cert_solver.cpp"] +
                                 sorted((REPO_ROOT / "scripts" / "probe_parts").glob("*.inc"))},
        "parent_solve": {"binary": "tmp-kb/order_ab_native",
                         "binary_sha256": sha256_file(BIN),
                         "sources_sha256": solver_sources_digest(),
                         "build_cmd": ["g++", "-O2", "-std=c++20"],
                         "compiler": compiler_version(),
                         "shrink": EXACT_SHRINK, "load": EXACT_LOAD,
                         "budget": 0, "root_depth": ROOT_DEPTH,
                         "below_root_min_depth": BELOW_ROOT_MIN_DEPTH,
                         "root_order_override": None,
                         "instrumentation": "memo reuse counters ON in both "
                                            "conditions (same setting)",
                         "fresh_process_per_parent_condition": True},
        "command_templates": {
            "cache-aware": ["BIN", "STATES_FILE", "0", "90", "0", "0",
                            "--root-depth", "3", "--below-root-order",
                            "cache-aware", "--memo-instr-out", "DEPTH_CSV"],
            "cache-blind": ["BIN", "STATES_FILE", "0", "90", "0", "0",
                            "--root-depth", "3", "--below-root-order",
                            "cache-blind", "--memo-instr-out", "DEPTH_CSV"],
        },
        "output_schema": {"summary": list(SUMMARY_FIELDS),
                          "depth": list(DEPTH_FIELDS),
                          "depth_visited": list(VISITED_FIELDS)},
        "regression": {"script": "scripts/test_capacity_rerun_regression.py",
                       "script_sha256": script_digest(
                           "test_capacity_rerun_regression.py"),
                       "log_sha256": sha256_file(reg_log)},
        "runner_script_sha256": script_digest("run_capacity_rerun.py"),
        "analysis_script_sha256": script_digest("analyze_capacity_rerun.py"),
        "verifier_script_sha256": script_digest("verify_capacity_rerun.py"),
    }


def require_protocol(freeze: bool) -> None:
    assert BIN.exists(), f"missing {BIN}; build it first"
    check_cohort_file()
    man_path = OUT / "execution_manifest.json"
    if freeze:
        if man_path.exists():
            raise RuntimeError(f"{man_path} already frozen; refusing to "
                               "overwrite after results may exist")
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "raw").mkdir(parents=True, exist_ok=True)
        cur = frozen_protocol()
        man_path.write_text(json.dumps(cur, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"frozen {man_path}")
        return
    if not man_path.exists():
        raise RuntimeError(f"{man_path} missing; run --freeze-manifest "
                           "first (after the regression gate)")
    rec = json.loads(man_path.read_text(encoding="utf-8"))
    cur = frozen_protocol()
    if rec != cur:
        raise RuntimeError("capacity-rerun protocol mismatch; "
                           "refusing to mix runs")


def bench_from_stderr(stderr: str) -> dict[str, str]:
    for line in stderr.splitlines():
        if line.startswith("bench_root "):
            out = {}
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                out[k] = v
            return out
    raise AssertionError(f"no bench_root line:\n{stderr[-600:]}")


def solve_parent(parent: str, condition: str, order_index: int
                 ) -> tuple[dict[str, str], list[dict[str, str]],
                            list[dict[str, str]], str, str]:
    assert condition in CONDITIONS
    tag = parent.replace(",", "_") + "_" + condition.replace("-", "_")
    rawdir = OUT / "raw" / tag
    rawdir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write(parent + "\n")
        tmp_path = tmp.name
    instr_path = Path(tmp_path).with_suffix(".d2_instr.csv")
    try:
        cmd = [str(BIN), tmp_path, str(EXACT_SHRINK), str(EXACT_LOAD),
               "0", "0", "--root-depth", str(ROOT_DEPTH),
               "--below-root-order", condition,
               "--memo-instr-out", str(instr_path)]
        t0 = time.time()
        pop = subprocess.Popen(cmd, cwd=REPO_ROOT, text=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        try:
            out, err = pop.communicate(timeout=EXACT_TIMEOUT)
        except subprocess.TimeoutExpired:
            pop.kill()
            out, err = pop.communicate()
            raise RuntimeError(f"exact {parent} {condition} TIMEOUT")
        wall = time.time() - t0
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    (rawdir / "stdout.txt").write_text(out, encoding="utf-8")
    (rawdir / "stderr.txt").write_text(err, encoding="utf-8")
    if pop.returncode != 0:
        raise RuntimeError(f"exact {parent} {condition} "
                           f"rc={pop.returncode}\n{err[-600:]}")
    rows = list(csv.DictReader(out.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected 1 row for {parent} {condition}, "
                            f"got {len(rows)}")
    r = rows[0]
    b = bench_from_stderr(err)
    assert f"below_root_order={condition}" in err, err[-300:]
    summary = {"parent": parent, "condition": condition,
               "order_index": str(order_index), "outcome": r["outcome"],
               "exact_visited": r["visited"],
               "exact_maxdepth": r["maxdepth"], "exact_memo": r["memo"],
               "solver_seconds": r["seconds"], "wall_seconds": f"{wall:.3f}",
               "root_unique": b["unique"], "root_entered": b["entered"],
               "root_first_lo": b["first_lo"],
               "root_first_hi": b["first_hi"],
               "root_witness": b["witness"]}
    with instr_path.open(newline="", encoding="utf-8") as f:
        draw = list(csv.DictReader(f))
    depth_rows = [{"parent": parent, "condition": condition,
                   **{k: d[k] for k in DEPTH_FIELDS
                      if k not in ("parent", "condition")}} for d in draw]
    visited_rows = [{"parent": parent, "condition": condition,
                     "depth": str(i), "visited": r[f"depth_visited_{i}"]}
                    for i in range(20)]
    print(f"  {parent} {condition} {r['outcome']} "
          f"visited={r['visited']} maxdepth={r['maxdepth']} "
          f"memo={r['memo']} seconds={r['seconds']} wall={wall:.1f}s",
          flush=True)
    return summary, depth_rows, visited_rows, out, err


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, fields: list[str], rows: list[dict[str, str]]
             ) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze-manifest", action="store_true")
    ap.add_argument("--parents", nargs="*", default=None)
    ap.add_argument("--conditions", nargs="*", default=None)
    args = ap.parse_args()
    require_protocol(freeze=args.freeze_manifest)
    if args.freeze_manifest:
        return
    parents = args.parents or EXPECTED_PARENTS
    conditions = args.conditions or list(CONDITIONS)
    assert set(parents) <= set(EXPECTED_PARENTS), parents
    assert set(conditions) <= set(CONDITIONS), conditions

    summaries = [r for r in load_csv(OUT / "summary_ab.csv")
                 if r["parent"] in EXPECTED_PARENTS
                 and r["condition"] in CONDITIONS]
    depths = [r for r in load_csv(OUT / "depth_ab.csv")
              if r["parent"] in EXPECTED_PARENTS
              and r["condition"] in CONDITIONS]
    visited = [r for r in load_csv(OUT / "depth_visited.csv")
               if r["parent"] in EXPECTED_PARENTS
               and r["condition"] in CONDITIONS]
    done = {(r["parent"], r["condition"]) for r in summaries}
    failures: list[str] = []
    for idx, p in enumerate(EXPECTED_PARENTS):
        if p not in parents:
            continue
        rank = idx + 1  # prereg: odd rank A-first, even rank B-first
        order = list(CONDITIONS) if rank % 2 == 1 else list(
            reversed(CONDITIONS))
        for cond in order:
            if cond not in conditions:
                continue
            if (p, cond) in done:
                print(f"  {p} {cond} already done, skipping")
                continue
            try:
                s, d, v, _, _ = solve_parent(p, cond, order.index(cond))
            except RuntimeError as e:
                print(f"  {p} {cond} FAILED: {e}", flush=True)
                failures.append(f"{p} {cond}: {e}")
                continue
            summaries.append(s)
            depths.extend(d)
            visited.extend(v)
            summaries.sort(key=lambda r: (EXPECTED_PARENTS.index(
                r["parent"]), CONDITIONS.index(r["condition"])))
            save_csv(OUT / "summary_ab.csv", SUMMARY_FIELDS, summaries)
            save_csv(OUT / "depth_ab.csv", DEPTH_FIELDS, depths)
            save_csv(OUT / "depth_visited.csv", VISITED_FIELDS, visited)
    if failures:
        print(f"capacity-rerun runner finished with {len(failures)} "
              f"failure(s); frozen rule => endpoint INCOMPLETE")
        for f in failures:
            print(f"  FAIL {f}")
    else:
        print("capacity-rerun cohort runner finished: 24/24 complete")


if __name__ == "__main__":
    sys.exit(main())

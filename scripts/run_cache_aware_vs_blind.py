#!/usr/bin/env python3
"""Cache-aware vs cache-blind below-root ordering benchmark (preregistered).

Paired mechanism intervention on the frozen 12 clean-V2 parents. Both
conditions keep memo lookup/prefetch/reuse/shortcut/write identical; only
the below-root child comparator differs:

  A (cache-aware): cached LOSS < uncached < cached WIN, then legal-move
     count, then canonical key (native, every depth).
  B (cache-blind): root (depth 3) native; depth >= 4 sorts by legal-move
     count then canonical key only. Prefetched cached outcomes are still
     consumed without recursion when reached.

Outputs under results/10x10/cache-aware-vs-blind/:
  protocol.json, summary_ab.csv, depth_ab.csv, depth_visited.csv,
  regression.log, raw/<parent>_<condition>/{stdout.txt,stderr.txt,
  depth_raw.csv}

Usage:
  python3 scripts/run_cache_aware_vs_blind.py --freeze-manifest
  python3 scripts/run_cache_aware_vs_blind.py            # full 24/24 cohort
  python3 scripts/run_cache_aware_vs_blind.py --parents 0,11,35 --conditions cache-aware

The manifest must be frozen (after the regression gate passes, before the
first full B result is inspected). Any later run with a mismatched binary,
source, compiler, cohort, or script digest refuses to append.
Must run under WSL/Linux (ELF solver binary). Serial exacts, A/B order
counterbalanced per parent (even index: A first; odd index: B first).
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
OUT = REPO_ROOT / "results" / "10x10" / "cache-aware-vs-blind"
FROZEN_NATIVE_SUMMARY = (REPO_ROOT / "results" / "10x10"
                         / "memo-instrumentation" / "summary.csv")

EXPECTED_PARENTS = ["0,11,35", "11,38,44", "11,78,87", "12,24,68",
                    "12,32,55", "13,52,57", "14,64,74", "23,44,45",
                    "3,47,63", "3,53,84", "4,24,26", "4,42,54"]
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
                           "scripts/test_order_ab_regression.py first and "
                           "tee its output to regression.log before freezing")
    return {
        "experiment": "cache-aware vs cache-blind below-root ordering",
        "prereg": ("docs/10X10_CACHE_AWARE_VS_BLIND_BELOW_ROOT_PREREG.md @ "
                   "21e7bfec13f593dddbd65f81a4f58a1b5c791aa1, base 80b734b"),
        "cohort": {"parents": list(EXPECTED_PARENTS)},
        "conditions": dict(CONDITION_SEMANTICS),
        "condition_order": "counterbalanced per parent index "
                           "(even: aware first; odd: blind first)",
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
        "regression": {"script": "scripts/test_order_ab_regression.py",
                       "script_sha256": script_digest(
                           "test_order_ab_regression.py"),
                       "log_sha256": sha256_file(reg_log)},
        "analysis_script_sha256": script_digest(
            "analyze_cache_aware_vs_blind.py"),
        "verifier_script_sha256": script_digest(
            "verify_10x10_cache_aware_vs_blind.py"),
    }


def require_protocol(freeze: bool) -> None:
    assert BIN.exists(), f"missing {BIN}; build it first"
    man_path = OUT / "protocol.json"
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
        raise RuntimeError("cache-aware-vs-blind protocol mismatch; "
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
    instr_path = rawdir / "depth_raw.csv"
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
    for idx, p in enumerate(EXPECTED_PARENTS):
        if p not in parents:
            continue
        order = list(CONDITIONS) if idx % 2 == 0 else list(
            reversed(CONDITIONS))
        for cond in order:
            if cond not in conditions:
                continue
            if (p, cond) in done:
                print(f"  {p} {cond} already done, skipping")
                continue
            s, d, v, _, _ = solve_parent(p, cond, order.index(cond))
            summaries.append(s)
            depths.extend(d)
            visited.extend(v)
            summaries.sort(key=lambda r: (EXPECTED_PARENTS.index(
                r["parent"]), CONDITIONS.index(r["condition"])))
            save_csv(OUT / "summary_ab.csv", SUMMARY_FIELDS, summaries)
            save_csv(OUT / "depth_ab.csv", DEPTH_FIELDS, depths)
            save_csv(OUT / "depth_visited.csv", VISITED_FIELDS, visited)
    print("cache-aware vs cache-blind cohort runner finished")


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Exact regression gate for the 10x10 capacity-rescued A/B rerun.

Runs the six preregistered light/medium/heavy parent-condition cases and
requires exact parity with the successful historical C2 rows for all frozen
semantic/work diagnostics. Timing is intentionally ignored.

The gate also verifies mechanism invariants needed before execution sealing:
- cache-blind has zero below-root cache-order changes;
- memo reuse remains active in both conditions;
- instrumentation arithmetic identities hold;
- summed depth visited equals exact visited.

No endpoint result is produced or analyzed by this script.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "results/10x10/cache-aware-below-root-capacity-rerun/regression_expected.json"
DEFAULT_BIN = ROOT / "tmp-kb/order_ab_capacity"
CONDITIONS = ("cache-aware", "cache-blind")
SHRINK = 0
LOAD = 90
ROOT_DEPTH = 3
TIMEOUT = 10800.0

DEPTH_INT_FIELDS = [
    "entry_lookup_calls", "entry_hit_win", "entry_hit_loss", "entry_miss",
    "prefetch_calls", "prefetch_hit_win", "prefetch_hit_loss", "prefetch_miss",
    "put_win", "put_loss", "child_eval_from_cache_win",
    "child_eval_from_cache_loss", "child_eval_recursive",
    "visited_nonterminal_nodes", "nodes_with_any_prefetch_hit",
    "nodes_cache_changes_first_child", "nodes_cache_changes_full_order",
    "actual_first_cached_loss", "fallback_first_cached_loss", "solved_win_nodes",
    "win_return_from_cached_loss_child",
]


def bench_from_stderr(stderr: str) -> dict[str, str]:
    for line in stderr.splitlines():
        if line.startswith("bench_root "):
            out: dict[str, str] = {}
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                out[k] = v
            return out
    raise AssertionError("missing bench_root line")


def parse_one_csv(stdout: str) -> dict[str, str]:
    rows = list(csv.DictReader(stdout.splitlines()))
    if len(rows) != 1:
        raise AssertionError(f"expected one solver CSV row, got {len(rows)}")
    return rows[0]


def as_int(row: dict[str, str], key: str) -> int:
    try:
        return int(row[key])
    except Exception as e:
        raise AssertionError(f"bad integer field {key}={row.get(key)!r}") from e


def check_depth_invariants(rows: list[dict[str, str]], condition: str,
                           exact_visited: int) -> None:
    if not rows:
        raise AssertionError("instrumentation CSV is empty")
    depths = [as_int(r, "depth") for r in rows]
    if len(depths) != len(set(depths)):
        raise AssertionError("duplicate instrumentation depth")

    total_put = 0
    total_cached_eval = 0
    total_prefetch_hits = 0
    for r in rows:
        for f in DEPTH_INT_FIELDS:
            as_int(r, f)

        entry_calls = as_int(r, "entry_lookup_calls")
        if entry_calls != (as_int(r, "entry_hit_win") +
                           as_int(r, "entry_hit_loss") +
                           as_int(r, "entry_miss")):
            raise AssertionError(f"entry lookup identity failed at depth {r['depth']}")

        prefetch_calls = as_int(r, "prefetch_calls")
        prefetch_parts = (as_int(r, "prefetch_hit_win") +
                          as_int(r, "prefetch_hit_loss") +
                          as_int(r, "prefetch_miss"))
        if prefetch_calls != prefetch_parts:
            raise AssertionError(f"prefetch identity failed at depth {r['depth']}")

        total_put += as_int(r, "put_win") + as_int(r, "put_loss")
        total_cached_eval += (as_int(r, "child_eval_from_cache_win") +
                              as_int(r, "child_eval_from_cache_loss"))
        total_prefetch_hits += (as_int(r, "prefetch_hit_win") +
                                as_int(r, "prefetch_hit_loss"))

        if condition == "cache-blind" and as_int(r, "depth") >= 4:
            if as_int(r, "nodes_cache_changes_first_child") != 0:
                raise AssertionError(
                    f"cache-blind first-child ordering changed at depth {r['depth']}")
            if as_int(r, "nodes_cache_changes_full_order") != 0:
                raise AssertionError(
                    f"cache-blind full ordering changed at depth {r['depth']}")

    if total_put != exact_visited:
        raise AssertionError(f"sum(put_win+put_loss)={total_put} != visited={exact_visited}")
    if total_prefetch_hits <= 0 or total_cached_eval <= 0:
        raise AssertionError("memo reuse is unexpectedly inactive")


def run_case(binary: Path, parent: str, condition: str) -> tuple[dict[str, object], str]:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as sf:
        sf.write(parent + "\n")
        state_path = Path(sf.name)
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as df:
        depth_path = Path(df.name)
    try:
        cmd = [str(binary), str(state_path), str(SHRINK), str(LOAD), "0", "0",
               "--root-depth", str(ROOT_DEPTH), "--below-root-order", condition,
               "--memo-instr-out", str(depth_path)]
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                           timeout=TIMEOUT)
        if p.returncode != 0:
            raise AssertionError(
                f"solver failed parent={parent} condition={condition} rc={p.returncode}\n"
                f"stderr tail:\n{p.stderr[-1200:]}")
        if f"below_root_order={condition}" not in p.stderr:
            raise AssertionError("runtime ordering switch was not acknowledged")
        r = parse_one_csv(p.stdout)
        b = bench_from_stderr(p.stderr)
        with depth_path.open(newline="", encoding="utf-8") as f:
            depth_rows = list(csv.DictReader(f))

        exact_visited = int(r["visited"])
        check_depth_invariants(depth_rows, condition, exact_visited)

        depth_sum = sum(int(r[f"depth_visited_{i}"]) for i in range(20))
        if depth_sum != exact_visited:
            raise AssertionError(
                f"sum(depth_visited)={depth_sum} != exact_visited={exact_visited}")

        got: dict[str, object] = {
            "outcome": r["outcome"],
            "exact_visited": exact_visited,
            "exact_maxdepth": int(r["maxdepth"]),
            "exact_memo": int(r["memo"]),
            "root_unique": int(b["unique"]),
            "root_entered": int(b["entered"]),
            "root_first_lo": int(b["first_lo"]),
            "root_first_hi": int(b["first_hi"]),
            "root_witness": int(b["witness"]),
        }
        return got, p.stderr
    finally:
        state_path.unlink(missing_ok=True)
        depth_path.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", type=Path, default=DEFAULT_BIN,
                    help=f"capacity-enlarged solver binary (default: {DEFAULT_BIN})")
    args = ap.parse_args()
    binary = args.bin.resolve()
    if not binary.exists():
        raise SystemExit(f"missing solver binary: {binary}")

    spec = json.loads(EXPECTED.read_text(encoding="utf-8"))
    required = spec["required_fields"]
    passed = 0
    for case in spec["cases"]:
        parent = case["parent"]
        klass = case["class"]
        for condition in CONDITIONS:
            exp = case["conditions"][condition]
            got, _ = run_case(binary, parent, condition)
            diffs = []
            for key in required:
                if got[key] != exp[key]:
                    diffs.append(f"{key}: got={got[key]!r} expected={exp[key]!r}")
            if diffs:
                raise SystemExit(
                    f"REGRESSION FAIL {klass} {parent} {condition}\n  " +
                    "\n  ".join(diffs))
            passed += 1
            print(f"PASS {klass:6s} {parent:8s} {condition:11s} "
                  f"visited={got['exact_visited']} memo={got['exact_memo']}", flush=True)

    if passed != 6:
        raise SystemExit(f"internal error: expected 6 passes, got {passed}")
    print("REGRESSION PASS: 6/6 exact parity; memo/order invariants PASS")


if __name__ == "__main__":
    main()

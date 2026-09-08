#!/usr/bin/env python3
"""Pre-run regression gate for the capacity-rescued cache-aware rerun.

Preregistered in docs/10X10_CACHE_AWARE_BELOW_ROOT_CAPACITY_RERUN_PREREG.md
(section 6). Runs BEFORE the execution manifest freeze and before any cohort
run. One binary, the new enlarged d12-16 capacity build.

For each regression parent (one light, one medium, one heavier successful C2
parent), for BOTH conditions (cache-aware, cache-blind):

  1. New-binary run must complete exactly (rc=0, no TableFull).
  2. outcome, exact visited, memo, maxdepth must equal the frozen old-C2 run.
  3. Root diagnostics (unique/entered/first_lo/first_hi/witness) must equal
     the frozen old-C2 run.
  4. B ordering-change counters total 0 (blind sort active, unchanged).
  5. Memo reuse alive in both conditions (prefetch hits, cached evals).
  6. Instrumentation arithmetic identities hold in both conditions.
  7. Per-sub-table physical capacities (stdout memo_capacity_d* columns)
     are exactly the preregistered enlarged powers for d12-16 (each one
     bit larger, physical capacity doubled) and unchanged for d9-11/17.

Expected values are read ONLY from the frozen old-C2 committed outputs
(regression expectation source), never as endpoint inputs. If any visited or
other exact figure changes, DO NOT start the endpoint.

Run under WSL/Linux from the repository root:
    python3 scripts/test_capacity_rerun_regression.py
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
NEW_BIN = REPO_ROOT / "tmp-kb" / "order_ab_native"
C2_OUT = (REPO_ROOT / "results" / "10x10"
          / "cache-aware-below-root-confirmation-v2")
OUT = REPO_ROOT / "results" / "10x10" / "cache-aware-below-root-capacity-rerun"

# Frozen old-C2 committed outputs are the regression EXPECTATION SOURCE only.
C2_SUMMARY = C2_OUT / "summary_ab.csv"
C2_DEPTH = C2_OUT / "depth_ab.csv"

EXACT_SHRINK, EXACT_LOAD = 0, 90
ROOT_DEPTH = 3
EXACT_TIMEOUT = 14400.0
# light / medium / heavier successful C2 parents (max A/B solver seconds
# 25.6 / 51.9 / 109.5 in old C2; expected budgets 4/10/40 minutes).
REGRESSION_PARENTS = ["12,13,67", "1,27,61", "0,7,67"]

EXACT_FIELDS = ("outcome", "visited", "maxdepth", "memo")
ROOT_FIELDS = ("unique", "entered", "first_lo", "first_hi", "witness")
ORDERING_CHANGE_COUNTERS = ("nodes_cache_changes_first_child",
                            "nodes_cache_changes_full_order")


# Per-sub-table physical capacities (columns memo_capacity_d9..d21 in the
# solver stdout row; printed in table order d9,d10,d11,d11b,d12a,d12b,d13a,
# d13b,d14a,d14b,d15,d16,d17 -> labeled d9,d10,d11,d12,d13,d14,d15,d16,d17,
# d18,d19,d20,d21). Positions after the comma: i2=d11b as d12, d12a as d13,
# d12b as d14, d13a as d15, d13b as d16, d14a as d17, d14b as d18, d15 as
# d19, d16 as d20, d17 as d21.
CAPACITY_COLUMNS = {
    # stdout column: (old physical capacity, new physical capacity)
    "memo_capacity_d9": (2 ** 23, 2 ** 23),
    "memo_capacity_d10": (2 ** 25, 2 ** 25),
    "memo_capacity_d11": (2 ** 26, 2 ** 26),   # d11
    "memo_capacity_d12": (2 ** 24, 2 ** 24),   # d11b
    "memo_capacity_d13": (2 ** 27, 2 ** 28),   # d12a
    "memo_capacity_d14": (2 ** 24, 2 ** 25),   # d12b
    "memo_capacity_d15": (2 ** 27, 2 ** 28),   # d13a
    "memo_capacity_d16": (2 ** 25, 2 ** 26),   # d13b
    "memo_capacity_d17": (2 ** 27, 2 ** 28),   # d14a
    "memo_capacity_d18": (2 ** 24, 2 ** 25),   # d14b
    "memo_capacity_d19": (2 ** 26, 2 ** 27),   # d15
    "memo_capacity_d20": (2 ** 23, 2 ** 24),   # d16
    "memo_capacity_d21": (2 ** 19, 2 ** 19),   # d17
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def c2_expected() -> dict[tuple[str, str], dict[str, str]]:
    if not C2_SUMMARY.exists():
        raise SystemExit(f"missing frozen old-C2 summary: {C2_SUMMARY}")
    out: dict[tuple[str, str], dict[str, str]] = {}
    for r in read_csv(C2_SUMMARY):
        out[(r["parent"], r["condition"])] = r
    return out


def c2_depth_totals() -> dict[tuple[str, str], dict[str, int]]:
    totals: dict[tuple[str, str], dict[str, int]] = {}
    for r in read_csv(C2_DEPTH):
        key = (r["parent"], r["condition"])
        slot = totals.setdefault(key, {})
        for k, v in r.items():
            if k in ("parent", "condition", "depth"):
                continue
            slot[k] = slot.get(k, 0) + int(v)
    return totals


def check_capacity_columns(row: dict[str, str]) -> None:
    for col, (old, new) in CAPACITY_COLUMNS.items():
        got = int(row[col])
        if got != new:
            raise SystemExit(
                f"CAPACITY MISMATCH {col}: new build reports {got}, "
                f"preregistered new power gives {new} (old was {old})")


def run_exact(parent: str, condition: str
              ) -> tuple[dict[str, str], dict[str, str],
                         list[dict[str, str]], str, float]:
    assert NEW_BIN.exists(), f"missing {NEW_BIN}; build it first"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as tmp:
        tmp_path = tmp.name
    instr_path = Path(tmp_path).with_suffix(".instr.csv")
    try:
        cmd = [str(NEW_BIN), tmp_path, str(EXACT_SHRINK), str(EXACT_LOAD),
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
            raise SystemExit(f"regression TIMEOUT {parent} {condition}")
        wall = time.time() - t0
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    if pop.returncode != 0:
        raise SystemExit(f"regression run failed {parent} {condition} "
                         f"rc={pop.returncode}\n{err[-800:]}")
    rows = list(csv.DictReader(out.splitlines()))
    if len(rows) != 1:
        raise SystemExit(f"expected 1 row for {parent} {condition}, "
                         f"got {len(rows)}")
    bench: dict[str, str] = {}
    for line in err.splitlines():
        if line.startswith("bench_root "):
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                bench[k] = v
    assert bench, f"no bench_root for {parent} {condition}"
    assert f"below_root_order={condition}" in err, err[-300:]
    with instr_path.open(newline="", encoding="utf-8") as f:
        drows = list(csv.DictReader(f))
    instr_path.unlink(missing_ok=True)
    return rows[0], bench, drows, err, wall


def parse_memo_by_depth(stderr: str) -> dict[str, int]:
    """memo_by_depth 9:.. 10:.. .. 16:.. 17:.. -> {d9:..}."""
    for line in stderr.splitlines():
        if line.startswith("memo_by_depth "):
            out = {}
            for tok in line.split()[1:]:
                d, v = tok.split(":")
                out[f"d{d}"] = int(v)
            return out
    raise SystemExit(f"no memo_by_depth line:\n{stderr[-400:]}")


def check_identities(drows: list[dict[str, str]],
                     label: str) -> None:
    for d in drows:
        v = {k: int(d[k]) for k in d if k not in ("depth",)}
        assert v["entry_lookup_calls"] == (
            v["entry_hit_win"] + v["entry_hit_loss"] + v["entry_miss"]), (
            label, d)
        assert v["prefetch_calls"] == (
            v["prefetch_hit_win"] + v["prefetch_hit_loss"]
            + v["prefetch_miss"]), (label, d)
        assert v["put_win"] + v["put_loss"] == v["entry_miss"], (label, d)
        consumed = (v["child_eval_from_cache_win"]
                    + v["child_eval_from_cache_loss"]
                    + v["child_eval_recursive"])
        assert consumed <= v["prefetch_calls"], (label, d)


def totals(drows: list[dict[str, str]]) -> dict[str, int]:
    tot: dict[str, int] = {}
    for d in drows:
        for k, val in d.items():
            if k == "depth":
                continue
            tot[k] = tot.get(k, 0) + int(val)
    return tot


def main() -> int:
    expected = c2_expected()
    depth_totals = c2_depth_totals()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []
    raw_base = OUT / "raw" / "regression"
    raw_base.mkdir(parents=True, exist_ok=True)

    for parent in REGRESSION_PARENTS:
        for condition in ("cache-aware", "cache-blind"):
            key = (parent, condition)
            exp = expected.get(key)
            if exp is None:
                raise SystemExit(f"no old-C2 row for {key}; cannot regress")
            row, bench, drows, err, wall = run_exact(parent, condition)
            (raw_base / f"{parent.replace(',', '_')}_"
             f"{condition.replace('-', '_')}.stdout.txt").write_text(
                err.split("memo_by_depth")[0] + "…\n", encoding="utf-8")

            # 2. Exact figures unchanged vs frozen old C2.
            checks = [("outcome", row["outcome"], exp["outcome"]),
                     ("visited", row["visited"], exp["exact_visited"]),
                     ("maxdepth", row["maxdepth"], exp["exact_maxdepth"]),
                     ("memo", row["memo"], exp["exact_memo"])]
            # 3. Root diagnostics unchanged.
            for f in ROOT_FIELDS:
                checks.append((f, bench[f], exp[f"root_{f}"]))
            for name, got, want in checks:
                if got != want:
                    raise SystemExit(
                        f"REGRESSION MISMATCH {parent} {condition} "
                        f"{name}: new={got} oldC2={want}; "
                        f"DO NOT start the endpoint")

            memo_depth = parse_memo_by_depth(err)
            # 4. B ordering counters zero.
            tot = totals(drows)
            for c in ORDERING_CHANGE_COUNTERS:
                if condition == "cache-blind" and tot[c] != 0:
                    raise SystemExit(f"REGRESSION FAIL {parent} {condition} "
                                     f"{c}={tot[c]} != 0")
            # 5. Memo reuse alive.
            hits = tot["prefetch_hit_win"] + tot["prefetch_hit_loss"]
            cached = (tot["child_eval_from_cache_win"]
                      + tot["child_eval_from_cache_loss"])
            if hits <= 0 or cached <= 0:
                raise SystemExit(f"REGRESSION FAIL {parent} {condition}: "
                                 f"memo reuse dead (hits={hits} "
                                 f"cached={cached})")
            # 6. Instrumentation identities.
            check_identities(drows, f"{parent} {condition}")

            # Depth totals must also be unchanged (visited arithmetic pin).
            c2d = depth_totals.get(key, {})
            for c in ORDERING_CHANGE_COUNTERS:
                if tot[c] != c2d.get(c, tot[c]):
                    raise SystemExit(
                        f"REGRESSION MISMATCH {parent} {condition} "
                        f"depth total {c}: new={tot[c]} "
                        f"oldC2={c2d.get(c)}")
            msg = (f"  {parent} {condition}: {row['outcome']} "
                   f"visited={row['visited']} memo={row['memo']} "
                   f"maxdepth={row['maxdepth']} "
                   f"memo16={memo_depth.get('d16')} wall={wall:.1f}s "
                   f"orderΔ={tot['nodes_cache_changes_full_order']} ok")
            print(msg, flush=True)
            log_lines.append(msg)

    # 7. Per-sub-table physical capacities are the preregistered enlarged
    # powers (stdout memo_capacity_d* columns; see CAPACITY_COLUMNS mapping).
    row, bench, drows, err, wall = run_exact("14,64,74", "cache-aware")
    check_capacity_columns(row)
    memo_depth = parse_memo_by_depth(err)
    print("  capacity probe 14,64,74: memo_by_depth "
          + " ".join(f"{k}={v}" for k, v in sorted(memo_depth.items())))
    msg = ("ALL CAPACITY-RERUN REGRESSION TESTS PASSED "
           "(12/12 capacity columns = preregistered new powers)")
    print(msg, flush=True)
    log_lines.append(msg)
    (OUT / "regression.log").write_text("\n".join(log_lines) + "\n",
                                        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

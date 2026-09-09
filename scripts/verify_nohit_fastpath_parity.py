#!/usr/bin/env python3
"""Fail-closed semantic parity verifier for cache-aware no-hit fast-path.

Run only after the frozen 24-run parity collection. Timing must not be
interpreted unless this verifier prints PASS.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-nohit-fastpath"
C1_OUT = ROOT / "results" / "10x10" / "cache-aware-vs-blind"
RAW = OUT / "raw_parity"
PLAN = OUT / "execution_plan.json"
COHORT = [
    "0,11,35", "11,38,44", "11,78,87", "12,24,68", "12,32,55",
    "13,52,57", "14,64,74", "23,44,45", "3,47,63", "3,53,84",
    "4,24,26", "4,42,54",
]
COUNTERS = [
    "entry_lookup_calls", "entry_hit_win", "entry_hit_loss", "entry_miss",
    "prefetch_calls", "prefetch_hit_win", "prefetch_hit_loss", "prefetch_miss",
    "put_win", "put_loss", "child_eval_from_cache_win",
    "child_eval_from_cache_loss", "child_eval_recursive",
    "visited_nonterminal_nodes", "nodes_with_any_prefetch_hit",
    "nodes_cache_changes_first_child", "nodes_cache_changes_full_order",
    "actual_first_cached_loss", "fallback_first_cached_loss",
    "solved_win_nodes", "win_return_from_cached_loss_child",
]
SUMMARY_EQ_FIELDS = ["outcome", "visited", "maxdepth", "memo"]
BENCH_EQ_FIELDS = ["unique", "entered", "first_lo", "first_hi", "witness"]


def fail(msg: str) -> None:
    print(f"NOHIT PARITY VERIFY FAIL: {msg}")
    raise SystemExit(1)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_stdout(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    if len(rows) != 1:
        fail(f"{path.relative_to(ROOT)}: expected exactly one stdout row")
    return rows[0]


def parse_bench(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("bench_root "):
            out: dict[str, str] = {}
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                out[k] = v
            return out
    fail(f"{path.relative_to(ROOT)}: no bench_root line")
    return {}


def load_run(parent: str, impl: str) -> dict[str, object]:
    d = RAW / f"{parent.replace(',', '_')}_{impl}"
    errp = d / "stderr.txt"
    row = parse_stdout(d / "stdout.txt")
    bench = parse_bench(errp)
    depth = read_csv(d / "depth_raw.csv")
    err = errp.read_text(encoding="utf-8")
    if "below_root_order=cache-aware" not in err:
        fail(f"{parent}/{impl}: not cache-aware")
    if f"cache_aware_impl={impl}" not in err:
        fail(f"{parent}/{impl}: implementation marker missing")
    return {"row": row, "bench": bench, "depth": depth}


def load_c1(parent: str) -> dict[str, object]:
    d = C1_OUT / "raw" / f"{parent.replace(',', '_')}_cache_aware"
    return {
        "row": parse_stdout(d / "stdout.txt"),
        "bench": parse_bench(d / "stderr.txt"),
        "depth": read_csv(d / "depth_raw.csv"),
    }


def compare(parent: str, label: str, got: dict[str, object], want: dict[str, object],
            compare_capacity: bool) -> None:
    gr = got["row"]
    wr = want["row"]
    gb = got["bench"]
    wb = want["bench"]
    for f in SUMMARY_EQ_FIELDS:
        if gr[f] != wr[f]:
            fail(f"{parent}/{label}: {f}: {gr[f]} != {wr[f]}")
    for f in BENCH_EQ_FIELDS:
        if gb[f] != wb[f]:
            fail(f"{parent}/{label}: root {f}: {gb[f]} != {wb[f]}")
    for i in range(20):
        f = f"depth_visited_{i}"
        if gr[f] != wr[f]:
            fail(f"{parent}/{label}: {f}: {gr[f]} != {wr[f]}")
    for d in range(9, 22):
        f = f"memo_used_d{d}"
        if gr[f] != wr[f]:
            fail(f"{parent}/{label}: {f}: {gr[f]} != {wr[f]}")
        if compare_capacity:
            f = f"memo_capacity_d{d}"
            if gr[f] != wr[f]:
                fail(f"{parent}/{label}: {f}: {gr[f]} != {wr[f]}")
    gd = {r["depth"]: r for r in got["depth"]}
    wd = {r["depth"]: r for r in want["depth"]}
    if set(gd) != set(wd):
        fail(f"{parent}/{label}: instrumentation depth sets differ")
    for depth in gd:
        for c in COUNTERS:
            if gd[depth][c] != wd[depth][c]:
                fail(f"{parent}/{label}: depth {depth} {c}: "
                     f"{gd[depth][c]} != {wd[depth][c]}")


def check_identities(parent: str, impl: str, run: dict[str, object]) -> None:
    row = run["row"]
    total = sum(int(row[f"depth_visited_{i}"]) for i in range(20))
    if total != int(row["visited"]):
        fail(f"{parent}/{impl}: depth_visited sum {total} != visited {row['visited']}")
    for r in run["depth"]:
        v = {k: int(r[k]) for k in COUNTERS}
        if v["entry_lookup_calls"] != v["entry_hit_win"] + v["entry_hit_loss"] + v["entry_miss"]:
            fail(f"{parent}/{impl}: entry lookup identity depth {r['depth']}")
        if v["prefetch_calls"] != v["prefetch_hit_win"] + v["prefetch_hit_loss"] + v["prefetch_miss"]:
            fail(f"{parent}/{impl}: prefetch identity depth {r['depth']}")
        if v["put_win"] + v["put_loss"] != v["entry_miss"]:
            fail(f"{parent}/{impl}: put/miss identity depth {r['depth']}")
        consumed = (v["child_eval_from_cache_win"] + v["child_eval_from_cache_loss"]
                    + v["child_eval_recursive"])
        if consumed > v["prefetch_calls"]:
            fail(f"{parent}/{impl}: child consumption exceeds prefetch depth {r['depth']}")


def main() -> int:
    if not PLAN.is_file():
        fail("missing frozen execution_plan.json")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if plan.get("parents_ranked") != COHORT:
        fail("cohort differs from frozen execution plan")
    if len(COHORT) != 12 or len(set(COHORT)) != 12:
        fail("cohort is not exactly 12 unique parents")

    # Exactly the expected 24 cache-aware run directories, no silent omission.
    expected_dirs = {f"{p.replace(',', '_')}_{impl}" for p in COHORT for impl in ("sort", "nohit")}
    if not RAW.is_dir():
        fail("raw_parity directory missing")
    actual_dirs = {p.name for p in RAW.iterdir() if p.is_dir() and not p.name.startswith("blindflag_")}
    if actual_dirs != expected_dirs:
        fail(f"raw parity directory set mismatch: missing={sorted(expected_dirs-actual_dirs)} extra={sorted(actual_dirs-expected_dirs)}")

    for p in COHORT:
        s = load_run(p, "sort")
        f = load_run(p, "nohit")
        c1 = load_c1(p)
        # Historical C1 may have older capacity columns; compare semantics/instrumentation,
        # but S/F must also agree exactly on current-binary capacity.
        compare(p, "sort-vs-C1", s, c1, compare_capacity=False)
        compare(p, "nohit-vs-C1", f, c1, compare_capacity=False)
        compare(p, "sort-vs-nohit", s, f, compare_capacity=True)
        check_identities(p, "sort", s)
        check_identities(p, "nohit", f)

    audit = subprocess.run(
        [sys.executable, "scripts/audit_cache_aware_nohit_fastpath_source_diff.py"],
        cwd=ROOT, text=True, capture_output=True,
    )
    if audit.returncode != 0 or "NOHIT SOURCE AUDIT PASS" not in audit.stdout:
        fail("source-diff audit does not PASS")

    print("NOHIT FASTPATH SEMANTIC PARITY VERIFIER: PASS")
    print("cohort=12/12 frozen C1")
    print("sort vs frozen C1=12/12 exact on semantic fields + instrumentation")
    print("nohit vs frozen C1=12/12 exact on semantic fields + instrumentation")
    print("sort == nohit=12/12 exact including memo capacities")
    print("counter identities + depth_visited sums=PASS")
    print("source-diff audit=PASS")
    print("timing_gate=OPEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())

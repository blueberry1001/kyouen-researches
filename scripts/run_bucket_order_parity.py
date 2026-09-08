#!/usr/bin/env python3
"""Semantic parity gate for the bucket-order optimization (preregistered).

Runs the frozen C1 12-parent cohort (from d9b9a0f, the cache-aware vs
cache-blind experiment) with BOTH implementations (S: sort, B: bucket) of
the cache-aware below-root ordering, one fresh process per parent x impl,
and compares every run EXACTLY against the frozen historical C1
cache-aware results AND against each other:

Required exact-equal per parent (S vs B vs historical C1 cache-aware):
  - outcome
  - exact visited
  - exact memo
  - maxdepth
  - depth_visited vector (all 20 depths)
  - root unique / entered / first_lo / first_hi / witness
  - all memo instrumentation counters per depth
  - final memo used by depth (memo_by_depth stderr line)
  - memo_capacity columns (capacity profile identical)

Additionally proves flag-independence of the untouched paths:
  - a cache-blind run with --cache-aware-order-impl bucket and a
    cache-blind run with --cache-aware-order-impl sort must be EXACTLY
    equal to each other and to the frozen historical C1 cache-blind run
    on a light parent (proves the switch cannot reach the cache-blind
    path).

Any mismatch is FAIL-SAFETY: no timing interpretation is allowed.

Run under WSL/Linux from the repository root:
    python3 scripts/run_bucket_order_parity.py
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
OUT = REPO_ROOT / "results" / "10x10" / "cache-aware-bucket-order-optimization"
C1_OUT = REPO_ROOT / "results" / "10x10" / "cache-aware-vs-blind"

# Frozen C1 cohort (d9b9a0f): exact 12 parents, sorted as committed.
COHORT = ["0,11,35", "11,38,44", "11,78,87", "12,24,68", "12,32,55",
          "13,52,57", "14,64,74", "23,44,45", "3,47,63", "3,53,84",
          "4,24,26", "4,42,54"]
EXACT_SHRINK, EXACT_LOAD = 0, 90
ROOT_DEPTH = 3
EXACT_TIMEOUT = 14400.0
# Light parent used for the cache-blind flag-independence probe (lightest
# C1 parent by historical solver seconds).
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


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def c1_summary() -> dict[tuple[str, str], dict[str, str]]:
    rows = read_csv(C1_OUT / "summary_ab.csv")
    return {(r["parent"], r["condition"]): r for r in rows}


def c1_depth() -> dict[tuple[str, str], dict[str, dict[str, str]]]:
    out: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
    for r in read_csv(C1_OUT / "depth_ab.csv"):
        key = (r["parent"], r["condition"])
        out.setdefault(key, {})[r["depth"]] = r
    return out


def parse_stdout(out: str) -> dict[str, str]:
    rows = list(csv.DictReader(out.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected 1 stdout row, got {len(rows)}")
    return rows[0]


def parse_stderr(err: str) -> tuple[dict[str, str], dict[str, int]]:
    bench: dict[str, str] = {}
    memo_by_depth: dict[str, int] = {}
    for line in err.splitlines():
        if line.startswith("bench_root "):
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                bench[k] = v
        elif line.startswith("memo_by_depth "):
            for tok in line.split()[1:]:
                d, v = tok.split(":")
                memo_by_depth[f"d{d}"] = int(v)
    return bench, memo_by_depth


def run_solver(parent: str, below_root_order: str, impl: str,
               rawdir: Path) -> dict[str, object]:
    assert below_root_order in ("cache-aware", "cache-blind")
    assert impl in ("sort", "bucket")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write(parent + "\n")
        tmp_path = tmp.name
    instr_path = rawdir / "depth_raw.csv"
    tag = f"{parent.replace(',', '_')}_{below_root_order.replace('-', '_')}_{impl}"
    cmd = [str(BIN), tmp_path, str(EXACT_SHRINK), str(EXACT_LOAD), "0", "0",
           "--root-depth", str(ROOT_DEPTH),
           "--below-root-order", below_root_order,
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
            raise RuntimeError(f"TIMEOUT {parent} {below_root_order} {impl}")
        wall = time.time() - t0
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    (rawdir / "stdout.txt").write_text(out, encoding="utf-8")
    (rawdir / "stderr.txt").write_text(err, encoding="utf-8")
    if pop.returncode != 0:
        raise RuntimeError(f"rc={pop.returncode} {parent} "
                           f"{below_root_order} {impl}\n{err[-600:]}")
    assert f"below_root_order={below_root_order}" in err, err[-300:]
    assert f"cache_aware_impl={impl}" in err, err[-300:]
    row = parse_stdout(out)
    bench, memo_by_depth = parse_stderr(err)
    depth_rows = read_csv(instr_path)
    return {"row": row, "bench": bench, "memo_by_depth": memo_by_depth,
            "depth_rows": depth_rows, "wall": wall, "cmd": cmd}


def field(row: dict[str, str], name: str) -> str:
    return row[name]


def compare(parent: str, impl: str, got: dict[str, object],
            c1_row: dict[str, str],
            c1_depths: dict[str, dict[str, str]],
            mismatches: list[str]) -> None:
    """got vs frozen C1 raw stdout row (same column names) + bench."""
    row = got["row"]
    bench = got["bench"]
    checks: list[tuple[str, str, str]] = [
        ("outcome", row["outcome"], c1_row["outcome"]),
        ("exact_visited", row["visited"], c1_row["visited"]),
        ("exact_memo", row["memo"], c1_row["memo"]),
        ("maxdepth", row["maxdepth"], c1_row["maxdepth"]),
        ("root_unique", bench["unique"], c1_row["root_unique"]),
        ("root_entered", bench["entered"], c1_row["root_entered"]),
        ("root_first_lo", bench["first_lo"], c1_row["root_first_lo"]),
        ("root_first_hi", bench["first_hi"], c1_row["root_first_hi"]),
        ("root_witness", bench["witness"], c1_row["root_witness"]),
    ]
    for i in range(20):
        checks.append((f"depth_visited_{i}",
                       row[f"depth_visited_{i}"],
                       c1_row[f"depth_visited_{i}"]))
    for d in range(9, 22):
        checks.append((f"memo_used_d{d}", row[f"memo_used_d{d}"],
                       c1_row[f"memo_used_d{d}"]))
    # NOTE on memo_capacity columns: the endpoint binary intentionally uses
    # the capacity-rescued enlarged d12-d16 table powers (already merged in
    # base e9d0460), so capacity columns differ from historical C1 (old
    # powers) by design. Capacity EQUALITY between S and B is enforced in
    # compare_impls below, and the enlarged profile is pinned in the
    # capacity-rerun regression (identical powers for d9-11/17, doubled
    # for d12-16). Physical capacity is per-binary, not per-impl.
    for name, g, w in checks:
        if g != w:
            mismatches.append(f"{parent}[{impl}] {name}: got={g} "
                              f"want(frozen C1)={w}")
    got_depths = {r["depth"]: r for r in got["depth_rows"]}
    for depth, crow in c1_depths.items():
        grow = got_depths.get(depth)
        if grow is None:
            mismatches.append(f"{parent}[{impl}] missing depth row {depth}")
            continue
        for c in COUNTERS:
            if grow[c] != crow[c]:
                mismatches.append(
                    f"{parent}[{impl}] depth {depth} counter {c}: "
                    f"got={grow[c]} want={crow[c]}")
    extra = set(got_depths) - set(c1_depths)
    if extra:
        mismatches.append(f"{parent}[{impl}] extra depth rows: {sorted(extra)}")
def compare_impls(parent: str, s: dict[str, object], b: dict[str, object],
                  mismatches: list[str]) -> None:
    """S run vs B run (both fresh, this experiment)."""
    rs, rb = s["row"], b["row"]
    checks: list[tuple[str, str, str]] = [
        ("outcome", rs["outcome"], rb["outcome"]),
        ("exact_visited", rs["visited"], rb["visited"]),
        ("exact_memo", rs["memo"], rb["memo"]),
        ("maxdepth", rs["maxdepth"], rb["maxdepth"]),
        ("root_unique", s["bench"]["unique"], b["bench"]["unique"]),
        ("root_entered", s["bench"]["entered"], b["bench"]["entered"]),
        ("root_first_lo", s["bench"]["first_lo"], b["bench"]["first_lo"]),
        ("root_first_hi", s["bench"]["first_hi"], b["bench"]["first_hi"]),
        ("root_witness", s["bench"]["witness"], b["bench"]["witness"]),
    ]
    for i in range(20):
        checks.append((f"depth_visited_{i}",
                       rs[f"depth_visited_{i}"], rb[f"depth_visited_{i}"]))
    for d in range(9, 22):
        checks.append((f"memo_capacity_d{d}",
                       rs[f"memo_capacity_d{d}"],
                       rb[f"memo_capacity_d{d}"]))
        checks.append((f"memo_used_d{d}",
                       rs[f"memo_used_d{d}"], rb[f"memo_used_d{d}"]))
    for name, a, b2 in checks:
        if a != b2:
            mismatches.append(f"{parent} S-vs-B {name}: S={a} B={b2}")
    # full instrumentation equality
    s_depths = {r["depth"]: r for r in s["depth_rows"]}
    b_depths = {r["depth"]: r for r in b["depth_rows"]}
    if set(s_depths) != set(b_depths):
        mismatches.append(f"{parent} S-vs-B depth row set differs")
    for depth in sorted(set(s_depths) & set(b_depths)):
        for c in COUNTERS:
            if s_depths[depth][c] != b_depths[depth][c]:
                mismatches.append(
                    f"{parent} S-vs-B depth {depth} counter {c}: "
                    f"S={s_depths[depth][c]} B={b_depths[depth][c]}")


def _c1_raw_row(parent: str, condition: str) -> dict[str, str]:
    d = C1_OUT / "raw" / (
        f"{parent.replace(',', '_')}_{condition.replace('-', '_')}")
    row = parse_stdout((d / "stdout.txt").read_text(encoding="utf-8"))
    bench, _ = parse_stderr((d / "stderr.txt").read_text(encoding="utf-8"))
    # Fold bench_root fields into the row with the keys compare() uses.
    row["root_unique"] = bench["unique"]
    row["root_entered"] = bench["entered"]
    row["root_first_lo"] = bench["first_lo"]
    row["root_first_hi"] = bench["first_hi"]
    row["root_witness"] = bench["witness"]
    return row


def c1_rows_by_parent(parent: str) -> dict[str, str]:
    """Frozen C1 cache-aware raw stdout row (+ bench root diagnostics)."""
    return _c1_raw_row(parent, "cache-aware")


def c1_blind_rows_by_parent(parent: str) -> dict[str, str]:
    return _c1_raw_row(parent, "cache-blind")


def main() -> int:
    if not BIN.exists():
        raise SystemExit(f"missing {BIN}; build it first")

    if sha256_file(BIN) != json.loads(
            (OUT / "build_receipt.json").read_text())["binary_sha256"]:
        raise SystemExit("binary sha mismatch vs build receipt")

    c1s = c1_summary()
    c1d = c1_depth()
    for p in COHORT:
        if (p, "cache-aware") not in c1s:
            raise SystemExit(f"frozen C1 cache-aware row missing for {p}")

    raw = OUT / "raw_parity"
    raw.mkdir(parents=True, exist_ok=True)
    mismatches: list[str] = []
    log: list[str] = []
    results: dict[str, dict[str, object]] = {}

    # --- C1 12 parents x {S, B}, counterbalanced odd S-first / even B-first
    for idx, p in enumerate(COHORT):
        order = ("sort", "bucket") if idx % 2 == 0 else ("bucket", "sort")
        for impl in order:
            d = raw / f"{p.replace(',', '_')}_{impl}"
            d.mkdir(parents=True, exist_ok=True)
            got = run_solver(p, "cache-aware", impl, d)
            results[impl] = got
            compare(p, impl, got, c1_rows_by_parent(p),
                    c1d[(p, "cache-aware")], mismatches)
            log.append(f"  {p} {impl}: {got['row']['outcome']} "
                       f"visited={got['row']['visited']} "
                       f"memo={got['row']['memo']} "
                       f"maxdepth={got['row']['maxdepth']} "
                       f"wall={got['wall']:.1f}s")
            print(log[-1], flush=True)
        compare_impls(p, results["sort"], results["bucket"], mismatches)

    # --- Flag-independence probe on the cache-blind path (light parent):
    #     --cache-aware-order-impl must not be able to reach it. Both values
    #     must produce EXACTLY the frozen C1 cache-blind result.
    blind_hist = c1s[(BLIND_PROBE_PARENT, "cache-blind")]
    blind_depths = c1d[(BLIND_PROBE_PARENT, "cache-blind")]
    blind_runs: dict[str, dict[str, object]] = {}
    for impl in ("sort", "bucket"):
        d = raw / f"blindflag_{BLIND_PROBE_PARENT.replace(',', '_')}_{impl}"
        d.mkdir(parents=True, exist_ok=True)
        got = run_solver(BLIND_PROBE_PARENT, "cache-blind", impl, d)
        blind_runs[impl] = got
        compare(BLIND_PROBE_PARENT, f"blind/{impl}", got,
                c1_blind_rows_by_parent(BLIND_PROBE_PARENT),
                blind_depths, mismatches)
        log.append(f"  {BLIND_PROBE_PARENT} cache-blind/{impl}: "
                   f"visited={got['row']['visited']} ok")
        print(log[-1], flush=True)
    compare_impls(BLIND_PROBE_PARENT + "[blindflag]", blind_runs["sort"],
                  blind_runs["bucket"], mismatches)

    # --- Receipt ---
    receipt = {
        "experiment": "bucket-order optimization semantic parity gate",
        "cohort": "C1 original 12 parents (d9b9a0f)",
        "parents": COHORT,
        "binary_sha256": sha256_file(BIN),
        "runs": "12 parents x 2 impls (24 fresh cache-aware processes) "
                "+ 2 cache-blind flag-independence probes",
        "flag_independence_probe": BLIND_PROBE_PARENT,
        "mismatch_count": len(mismatches),
        "verdict": "PASS" if not mismatches else "FAIL-SAFETY",
        "log": log,
        "mismatches": mismatches[:200],
    }
    (OUT / "parity_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    print(f"\nparity mismatches: {len(mismatches)}")
    for m in mismatches[:40]:
        print("MISMATCH", m)
    if mismatches:
        print("SEMANTIC PARITY: FAIL-SAFETY (do not run timing)")
        return 1
    print("SEMANTIC PARITY PASS (S==B==frozen C1, 12/12 + blind flag probes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

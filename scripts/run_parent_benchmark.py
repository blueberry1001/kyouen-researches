#!/usr/bin/env python3
"""Parent-level 10k benchmark runner (preregistered).

Phase 1 (probes, parallel): fresh probe Solver per root child with the FROZEN
probe binary (shrink=3, load=80, budget=10000). Builds per-parent root order
files sorted by (memo_used ascending, move id ascending). Reads NO exact
outcome labels in this phase.

Phase 2 (exacts, SERIAL across all parent/strategy runs): one fresh process +
fresh exact Solver per (parent, strategy) with the benchmark binary
(shrink=0, load=90, unbounded). A = native order; B = frozen probe order at
root depth only. Counterbalanced AB/BA per parent by SHA256(parent) parity.

Resume-safe: completed keys are (parent,state) for probes and
(parent,strategy) for exacts; the frozen manifest must match on every run.

Outputs under results/10x10/parent-benchmark/:
  probe_rows.csv, probe_runlog.jsonl, probe.protocol.json (written pre-run),
  root_orders/order_<parent>.txt, parent_benchmark_raw.csv, run_commands.log
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2 = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
BENCH = REPO_ROOT / "results" / "10x10" / "parent-benchmark"
ORDERS = BENCH / "root_orders"
TASK_CSV = V2 / "exact_task_list.csv"
PRIMARY_CSV = V2 / "holdout_v2_parents_primary.csv"

PROBE_BIN = REPO_ROOT / "tmp-kb" / "probe_holdout_native"
BENCH_BIN = REPO_ROOT / "tmp-kb" / "parent_bench_native"
MANIFEST = BENCH / "protocol.json"

EXPECTED_PARENTS = ["0,11,35", "11,38,44", "11,78,87", "12,24,68", "12,32,55",
                    "13,52,57", "14,64,74", "23,44,45", "3,47,63", "3,53,84",
                    "4,24,26", "4,42,54"]
PROBE_BUDGET = 10_000
PROBE_SHRINK, PROBE_LOAD = 3, 80
EXACT_SHRINK, EXACT_LOAD = 0, 90
ROOT_DEPTH = 3
EXACT_TIMEOUT = 10800.0

PROBE_FIELDS = ["parent", "batch", "batch_position", "state", "probe_outcome",
                "visited", "maxdepth", "memo", "seconds"]
RAW_FIELDS = ["parent", "strategy", "outcome", "exact_visited", "exact_maxdepth",
              "exact_memo", "exact_seconds", "wall_seconds", "pid",
              "root_unique", "root_entered", "root_first_lo", "root_first_hi",
              "root_witness", "root_children", "probe_visited_total",
              "probe_seconds_total", "solver_cmd"]


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
        h.update(len(rel).to_bytes(4, "big")); h.update(rel)
        h.update(len(d).to_bytes(8, "big")); h.update(d)
    return h.hexdigest()


def task_set_digest(tasks: list[dict[str, str]]) -> str:
    h = hashlib.sha256()
    for t in tasks:
        d = json.dumps([t["parent"], int(t["batch"]), int(t["batch_position"]),
                        t["state"]], separators=(",", ":")).encode()
        h.update(len(d).to_bytes(8, "big")); h.update(d)
    return h.hexdigest()

def load_tasks() -> list[dict[str, str]]:
    with TASK_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_parents(tasks: list[dict[str, str]]) -> list[str]:
    with PRIMARY_CSV.open(newline="", encoding="utf-8") as f:
        prim = [r["parent_canonical"].strip() for r in csv.DictReader(f)]
    assert set(prim) == set(EXPECTED_PARENTS), prim
    assert len(tasks) == 1136
    tparents = sorted({t["parent"].strip() for t in tasks})
    assert tparents == sorted(EXPECTED_PARENTS), tparents
    return sorted(EXPECTED_PARENTS)

def ab_order(parent: str) -> list[str]:
    parity = int(hashlib.sha256(parent.encode()).hexdigest(), 16) % 2
    return ["B", "A"] if parity else ["A", "B"]


def move_of(parent: str, child: str) -> int:
    p = {int(v) for v in parent.replace(",", "-").split("-")}
    c = {int(v) for v in child.replace(",", "-").split("-")}
    extra = c - p
    assert len(extra) == 1 and p < c, (parent, child)
    return next(iter(extra))

def frozen_manifest(tasks: list[dict[str, str]]) -> dict[str, object]:
    src = solver_sources_digest()
    probe_src = (REPO_ROOT / "tmp-kb" / "probe_holdout_native.sources.sha256").read_text(
        encoding="ascii").strip()
    return {
        "format": 1,
        "cohort": {"parents": sorted(EXPECTED_PARENTS), "total_tasks": 1136,
                   "task_set_sha256": task_set_digest(tasks)},
        "probe": {"binary": "tmp-kb/probe_holdout_native",
                  "binary_sha256": sha256_file(PROBE_BIN),
                  "sources_sha256": probe_src,
                  "sources_note": "frozen pre-patch lineage; byte-identical binary reused",
                  "budget": PROBE_BUDGET, "shrink": PROBE_SHRINK, "load": PROBE_LOAD,
                  "fresh_process_per_child": True},


        "parent_solve": {"binary": "tmp-kb/parent_bench_native",
                         "binary_sha256": sha256_file(BENCH_BIN),
                         "sources_sha256": src,
                         "build_cmd": ["g++", "-O2", "-std=c++20"],
                         "shrink": EXACT_SHRINK, "load": EXACT_LOAD,
                         "budget": 0, "root_depth": ROOT_DEPTH,
                         "fresh_process_per_parent_strategy": True},
        "treatment_order": {"key": "memo_used ascending, move id ascending",
                            "scope": "root depth only; native below root",
                            "staged_shortlists": "excluded"},
        "counterbalance": "SHA256(parent) parity decides AB vs BA; serial exacts",
        "resume": "probes by (parent,state); exacts by (parent,strategy); manifest must match",
        "failure": "nonzero exit/unparseable -> no row, stays pending",
        "exact_timeout_s": EXACT_TIMEOUT,
        "wall_time": "solver seconds primary for costs; process wall recorded per run",
    }


def require_manifest(tasks: list[dict[str, str]]) -> None:
    cur = frozen_manifest(tasks)
    import platform
    cur["platform"] = platform.platform()
    if MANIFEST.exists():
        rec = json.loads(MANIFEST.read_text(encoding="utf-8"))
        r2, c2 = dict(rec), dict(cur)
        # platform may legitimately differ across resume hosts; pin looser there
        r2.pop("platform", None); c2.pop("platform", None)
        if r2 != c2:
            raise RuntimeError("benchmark manifest mismatch; refusing to mix runs")
        return
    if (BENCH / "probe_rows.csv").exists() or (BENCH / "parent_benchmark_raw.csv").exists():
        raise RuntimeError("result files exist without a manifest; refusing to append")
    BENCH.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(cur, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def probe_one(task: dict[str, str]) -> dict[str, object]:
    state = task["state"]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     dir=PROBE_BIN.parent, encoding="utf-8") as tmp:
        tmp.write(state + "\n")
        tmp_path = Path(tmp.name)
    t0 = time.time()
    try:
        cmd = [str(PROBE_BIN), str(tmp_path), str(PROBE_SHRINK), str(PROBE_LOAD),
               str(PROBE_BUDGET), "0"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    finally:
        tmp_path.unlink(missing_ok=True)
    wall = time.time() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"probe failed {state}: rc={proc.returncode}\n{proc.stderr[-400:]}")
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected 1 row for {state}, got {len(rows)}")
    r = rows[0]
    return {"row": {"parent": task["parent"], "batch": task["batch"],
                    "batch_position": task["batch_position"], "state": state,
                    "probe_outcome": r["outcome"], "visited": r["visited"],
                    "maxdepth": r["maxdepth"], "memo": r["memo"],
                    "seconds": r["seconds"]},
            "wall": wall, "exit": proc.returncode}


def bench_from_stderr(stderr: str) -> dict[str, str]:
    for line in stderr.splitlines():
        if line.startswith("bench_root "):
            out = {}
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                out[k] = v
            return out
    raise AssertionError(f"no bench_root line:\n{stderr[-600:]}")


def solve_parent(parent: str, strategy: str, order_file: Path | None,
                 logf) -> dict[str, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     dir=BENCH_BIN.parent, encoding="utf-8") as tmp:
        tmp.write(parent + "\n")
        tmp_path = Path(tmp.name)
    try:
        cmd = [str(BENCH_BIN), str(tmp_path), str(EXACT_SHRINK), str(EXACT_LOAD),
               "0", "0", "--root-depth", str(ROOT_DEPTH)]
        if strategy == "B":
            assert order_file is not None and order_file.exists()
            cmd += ["--root-order-file", str(order_file)]
        logf.write(f"CMD {parent} {strategy}: {' '.join(cmd)}\n")
        logf.flush()
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True,
                              timeout=EXACT_TIMEOUT)
        wall = time.time() - t0
    finally:
        tmp_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"exact {parent} {strategy} rc={proc.returncode}\n{proc.stderr[-600:]}")
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected 1 row for {parent}, got {len(rows)}")
    r = rows[0]
    b = bench_from_stderr(proc.stderr)
    return {"parent": parent, "strategy": strategy,
            "outcome": r["outcome"], "exact_visited": r["visited"],
            "exact_maxdepth": r["maxdepth"], "exact_memo": r["memo"],
            "exact_seconds": r["seconds"], "wall_seconds": f"{wall:.3f}",
            "pid": str(proc.pid), "root_unique": b["unique"],
            "root_entered": b["entered"], "root_first_lo": b["first_lo"],
            "root_first_hi": b["first_hi"], "root_witness": b["witness"],
            "solver_cmd": " ".join(cmd)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--parents", nargs="*", default=None)
    ap.add_argument("--skip-probes", action="store_true")
    ap.add_argument("--skip-exacts", action="store_true")
    args = ap.parse_args()

    tasks = load_tasks()
    parents = load_parents(tasks)
    if args.parents:
        assert set(args.parents) <= set(parents)
        parents = [p for p in parents if p in args.parents]
    require_manifest(load_tasks())
    ORDERS.mkdir(parents=True, exist_ok=True)
    logf = (BENCH / "run_commands.log").open("a", encoding="utf-8")

    # ---- Phase 1: probes (parallel) ----
    probe_csv = BENCH / "probe_rows.csv"
    runlog = BENCH / "probe_runlog.jsonl"
    done: set[tuple[str, str]] = set()
    if probe_csv.exists():
        with probe_csv.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                done.add((r["parent"], r["state"]))
    wanted = [t for t in tasks if t["parent"].strip() in parents]
    pending = [t for t in wanted if (t["parent"], t["state"]) not in done]
    print(f"probes: wanted={len(wanted)} done={len(done)} pending={len(pending)}", flush=True)
    if pending and not args.skip_probes:
        outf = probe_csv.open("a" if done else "w", newline="", encoding="utf-8")
        w = csv.DictWriter(outf, fieldnames=PROBE_FIELDS)
        if not done:
            w.writeheader()
        logf2 = runlog.open("a", encoding="utf-8")
        t0 = time.time()
        n0 = len(done)
        with mp.Pool(processes=args.workers) as pool:
            for res in pool.imap_unordered(probe_one, pending, chunksize=16):
                w.writerow(res["row"])
                outf.flush()
                logf2.write(json.dumps({"parent": res["row"]["parent"],
                                        "state": res["row"]["state"],
                                        "solver_exit": res["exit"],
                                        "wall_seconds": round(res["wall"], 6)}) + "\n")
                logf2.flush()
                if (len(done) + 1) % 50 == 0:
                    print(f"  probes {len(done)+1}/{len(wanted)} "
                          f"elapsed={time.time()-t0:.0f}s", flush=True)
                done.add((res["row"]["parent"], res["row"]["state"]))
        outf.close()
        logf2.close()
    elif pending:
        print("  --skip-probes with pending tasks; exacts for incomplete parents refused below")

    # ---- Build root order files (probe data only; no exact labels) ----
    with probe_csv.open(newline="", encoding="utf-8") as f:
        probes = {(r["parent"], r["state"]): r for r in csv.DictReader(f)}
    for p in parents:
        kids = [t["state"] for t in wanted if t["parent"].strip() == p]
        assert all((p, s) in probes for s in kids), f"probes incomplete for {p}"
        mix = {probes[(p, s)]["probe_outcome"] for s in kids}
        print(f"  order {p}: n={len(kids)} probe_outcomes={sorted(mix)}", flush=True)
        ordered = sorted(kids, key=lambda s: (int(probes[(p, s)]["memo"]), move_of(p, s)))
        memos = [int(probes[(p, s)]["memo"]) for s in ordered]
        assert all(b >= a for a, b in zip(memos, memos[1:])), "memo ascending violated"
        op = ORDERS / f"order_{p.replace(',', '_')}.txt"
        op.write_text("\n".join(ordered) + "\n", encoding="utf-8")

    # ---- Phase 2: exacts (serial, counterbalanced) ----
    raw_csv = BENCH / "parent_benchmark_raw.csv"
    done_e: set[tuple[str, str]] = set()
    if raw_csv.exists():
        with raw_csv.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                done_e.add((r["parent"], r["strategy"]))
    if not args.skip_exacts:
        outf = raw_csv.open("a" if done_e else "w", newline="", encoding="utf-8")
        w = csv.DictWriter(outf, fieldnames=RAW_FIELDS)
        if not done_e:
            w.writeheader()
        # probe aggregates per parent (measured, includes early-terminated)
        with probe_csv.open(newline="", encoding="utf-8") as f:
            allp = list(csv.DictReader(f))
        for p in parents:
            kids = [t["state"] for t in wanted if t["parent"].strip() == p]
            pv = sum(int(probes[(p, s)]["visited"]) for s in kids)
            ps = sum(float(probes[(p, s)]["seconds"]) for s in kids)
            order_file = ORDERS / f"order_{p.replace(',', '_')}.txt"
            for strat in ab_order(p):
                if (p, strat) in done_e:
                    print(f"  skip {p} {strat} (done)", flush=True)
                    continue
                print(f"  solve {p} {strat} ...", flush=True)
                row = solve_parent(p, strat, order_file if strat == "B" else None, logf)
                row["root_children"] = str(len(kids))
                row["probe_visited_total"] = str(pv) if strat == "B" else ""
                row["probe_seconds_total"] = f"{ps:.3f}" if strat == "B" else ""
                w.writerow(row)
                outf.flush()
                print(f"  done {p} {strat}: {row['outcome']} "
                      f"visited={row['exact_visited']} wall={row['wall_seconds']}s", flush=True)
        outf.close()
    logf.close()
    print("benchmark runner finished")


if __name__ == "__main__":
    main()

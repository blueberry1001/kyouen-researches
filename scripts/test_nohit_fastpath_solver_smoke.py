#!/usr/bin/env python3
"""Small deterministic integration smoke for sort vs no-hit solver paths.

This is deliberately NOT an endpoint run. It uses a non-cohort 3-stone state,
a small memo profile, and a hard visited cap. Both implementations run in fresh
processes and must agree exactly on every deterministic output field and every
memo-instrumentation counter. Timing is ignored.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp-kb" / "nohit_fastpath_ab_native"
BUILD = ROOT / "results" / "10x10" / "cache-aware-nohit-fastpath" / "build_receipt.json"
STATE = "0,12,34"  # intentionally outside the frozen C1 endpoint cohort
SHRINK = 8
LOAD = 90
MAX_VISITED = 5000
ROOT_DEPTH = 3


def fail(msg: str) -> None:
    raise SystemExit(f"NOHIT SOLVER SMOKE FAIL: {msg}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv_text(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(text.splitlines()))


def parse_bench(stderr: str) -> dict[str, str]:
    for line in stderr.splitlines():
        if line.startswith("bench_root "):
            out: dict[str, str] = {}
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                out[k] = v
            return out
    fail("missing bench_root line")
    raise AssertionError


def run_one(impl: str) -> tuple[dict[str, str], dict[str, str], list[dict[str, str]], str]:
    with tempfile.TemporaryDirectory(prefix="nohit-smoke-") as td:
        td = Path(td)
        state = td / "state.txt"
        instr = td / "depth.csv"
        state.write_text(STATE + "\n", encoding="utf-8")
        cmd = [
            str(BIN), str(state), str(SHRINK), str(LOAD), str(MAX_VISITED), "0",
            "--root-depth", str(ROOT_DEPTH),
            "--below-root-order", "cache-aware",
            "--cache-aware-order-impl", impl,
            "--memo-instr-out", str(instr),
        ]
        p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=120)
        if p.returncode != 0:
            fail(f"{impl}: rc={p.returncode}\n{p.stderr[-1200:]}")
        if "below_root_order=cache-aware" not in p.stderr:
            fail(f"{impl}: cache-aware marker missing")
        if f"cache_aware_impl={impl}" not in p.stderr:
            fail(f"{impl}: implementation marker missing")
        rows = read_csv_text(p.stdout)
        if len(rows) != 1:
            fail(f"{impl}: expected one stdout row, got {len(rows)}")
        if rows[0].get("outcome") != "PROBE":
            fail(f"{impl}: expected capped PROBE, got {rows[0].get('outcome')}")
        if not instr.is_file():
            fail(f"{impl}: instrumentation file missing")
        depth = list(csv.DictReader(instr.read_text(encoding="utf-8").splitlines()))
        return rows[0], parse_bench(p.stderr), depth, p.stderr


def main() -> int:
    if not BIN.is_file() or not BUILD.is_file():
        fail("build binary/receipt missing; run build_nohit_fastpath_binary.py first")
    build = json.loads(BUILD.read_text(encoding="utf-8"))
    if sha256_file(BIN) != build.get("binary_sha256"):
        fail("binary SHA differs from build receipt")

    srow, sbench, sdepth, _ = run_one("sort")
    frow, fbench, fdepth, _ = run_one("nohit")

    # Solver-reported and wall-clock timing are intentionally excluded.
    fields = [k for k in srow if k != "seconds"]
    if fields != [k for k in frow if k != "seconds"]:
        fail("stdout schemas differ")
    for k in fields:
        if srow[k] != frow[k]:
            fail(f"stdout field {k}: sort={srow[k]} nohit={frow[k]}")
    if sbench != fbench:
        fail(f"bench_root differs: sort={sbench} nohit={fbench}")
    if sdepth != fdepth:
        fail("memo instrumentation differs")

    # Prove the optimized branch is actually reachable in this smoke: at least
    # one below-root visited nonterminal node must have zero prefetch hits.
    exercised = 0
    for r in fdepth:
        d = int(r["depth"])
        if d <= ROOT_DEPTH:
            continue
        visited = int(r["visited_nonterminal_nodes"])
        with_hit = int(r["nodes_with_any_prefetch_hit"])
        exercised += max(0, visited - with_hit)
    if exercised <= 0:
        fail("no below-root all-uncached node observed; fast path not exercised")

    print("NOHIT SOLVER INTEGRATION SMOKE: PASS")
    print(f"state={STATE}")
    print(f"shrink={SHRINK} load={LOAD} max_visited={MAX_VISITED}")
    print(f"below_root_all_uncached_nodes={exercised}")
    print("sort==nohit on deterministic stdout + bench_root + full instrumentation")
    print("timing_ignored=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

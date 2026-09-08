#!/usr/bin/env python3
"""Strategy-A-equivalent instrumented cohort runner (preregistered).

Re-solves the frozen 12 V2 parents with the native ordering and a fresh
solver per parent, collecting below-root memo-reuse counters. Strategy A
only: no root-order override, no probes, no new heuristic.

Outputs under results/10x10/memo-instrumentation/:
  summary.csv, depth.csv, raw/<parent tag>/{stdout.txt,stderr.txt},
  protocol.json

Must run under WSL/Linux (ELF solver binary). Serial exacts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "tmp-kb" / "memo_instr_native"
OUT = REPO_ROOT / "results" / "10x10" / "memo-instrumentation"

EXPECTED_PARENTS = ["0,11,35", "11,38,44", "11,78,87", "12,24,68",
                    "12,32,55", "13,52,57", "14,64,74", "23,44,45",
                    "3,47,63", "3,53,84", "4,24,26", "4,42,54"]
EXACT_SHRINK, EXACT_LOAD = 0, 90
ROOT_DEPTH = 3
EXACT_TIMEOUT = 10800.0

SUMMARY_FIELDS = ["parent", "outcome", "exact_visited", "exact_maxdepth",
                  "exact_memo", "root_unique", "root_entered",
                  "root_first_lo", "root_first_hi", "root_witness"]
DEPTH_FIELDS = ["parent", "depth", "entry_lookup_calls", "entry_hit_win",
                "entry_hit_loss", "entry_miss", "prefetch_calls",
                "prefetch_hit_win", "prefetch_hit_loss", "prefetch_miss",
                "put_win", "put_loss", "child_eval_from_cache_win",
                "child_eval_from_cache_loss", "child_eval_recursive",
                "visited_nonterminal_nodes", "nodes_with_any_prefetch_hit",
                "nodes_cache_changes_first_child",
                "nodes_cache_changes_full_order",
                "actual_first_cached_loss", "fallback_first_cached_loss",
                "solved_win_nodes", "win_return_from_cached_loss_child"]


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


def frozen_protocol() -> dict[str, object]:
    return {
        "cohort": {"parents": list(EXPECTED_PARENTS)},
        "instrumentation": "below-root memo reuse counters (preregistered)",
        "parent_solve": {"binary": "tmp-kb/memo_instr_native",
                         "binary_sha256": sha256_file(BIN),
                         "sources_sha256": solver_sources_digest(),
                         "build_cmd": ["g++", "-O2", "-std=c++20"],
                         "shrink": EXACT_SHRINK, "load": EXACT_LOAD,
                         "budget": 0, "root_depth": ROOT_DEPTH,
                         "root_order_override": None,
                         "fresh_process_per_parent": True},
    }


def require_protocol() -> None:
    cur = frozen_protocol()
    man_path = OUT / "protocol.json"
    if man_path.exists():
        rec = json.loads(man_path.read_text(encoding="utf-8"))
        if rec != cur:
            raise RuntimeError("memo-instrumentation protocol mismatch; "
                               "refusing to mix runs")
        return
    if (OUT / "summary.csv").exists() or (OUT / "depth.csv").exists():
        raise RuntimeError("result files exist without a protocol; "
                           "refusing to append")
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    man_path.write_text(json.dumps(cur, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")


def bench_from_stderr(stderr: str) -> dict[str, str]:
    for line in stderr.splitlines():
        if line.startswith("bench_root "):
            out = {}
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                out[k] = v
            return out
    raise AssertionError(f"no bench_root line:\n{stderr[-600:]}")


def solve_parent(parent: str) -> tuple[dict[str, str], list[dict[str, str]],
                                      str, str]:
    tag = parent.replace(",", "_")
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
            raise RuntimeError(f"exact {parent} TIMEOUT")
        wall = time.time() - t0
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    (rawdir / "stdout.txt").write_text(out, encoding="utf-8")
    (rawdir / "stderr.txt").write_text(err, encoding="utf-8")
    if pop.returncode != 0:
        raise RuntimeError(f"exact {parent} rc={pop.returncode}\n{err[-600:]}")
    rows = list(csv.DictReader(out.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected 1 row for {parent}, got {len(rows)}")
    r = rows[0]
    b = bench_from_stderr(err)
    summary = {"parent": parent, "outcome": r["outcome"],
               "exact_visited": r["visited"],
               "exact_maxdepth": r["maxdepth"], "exact_memo": r["memo"],
               "root_unique": b["unique"], "root_entered": b["entered"],
               "root_first_lo": b["first_lo"],
               "root_first_hi": b["first_hi"],
               "root_witness": b["witness"]}
    with instr_path.open(newline="", encoding="utf-8") as f:
        draw = list(csv.DictReader(f))
    depth_rows = [{"parent": parent, **{k: d[k] for k in DEPTH_FIELDS
                                        if k != "parent"}} for d in draw]
    print(f"  {parent} {r['outcome']} visited={r['visited']} "
          f"maxdepth={r['maxdepth']} memo={r['memo']} "
          f"depthrows={len(depth_rows)} wall={wall:.1f}s", flush=True)
    return summary, depth_rows, out, err


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parents", nargs="*", default=None)
    args = ap.parse_args()
    assert BIN.exists(), f"missing {BIN}"
    parents = args.parents or EXPECTED_PARENTS
    assert set(parents) <= set(EXPECTED_PARENTS), parents
    require_protocol()
    done: set[str] = set()
    if (OUT / "summary.csv").exists():
        with (OUT / "summary.csv").open(newline="", encoding="utf-8") as f:
            done = {r["parent"] for r in csv.DictReader(f)}
    summaries: list[dict[str, str]] = []
    depths: list[dict[str, str]] = []
    if done:
        with (OUT / "summary.csv").open(newline="", encoding="utf-8") as f:
            summaries = list(csv.DictReader(f))
        with (OUT / "depth.csv").open(newline="", encoding="utf-8") as f:
            depths = list(csv.DictReader(f))
    for p in EXPECTED_PARENTS:
        if p not in parents:
            continue
        if p in done:
            print(f"  {p} already done, skipping")
            continue
        s, d, _, _ = solve_parent(p)
        summaries.append(s)
        depths.extend(d)
        with (OUT / "summary.csv").open("w", newline="",
                                        encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
            w.writeheader()
            w.writerows([r for r in summaries
                         if r["parent"] in EXPECTED_PARENTS])
        with (OUT / "depth.csv").open("w", newline="",
                                      encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=DEPTH_FIELDS)
            w.writeheader()
            w.writerows([r for r in depths
                         if r["parent"] in EXPECTED_PARENTS])
    print("instrumented cohort runner finished")


if __name__ == "__main__":
    main()

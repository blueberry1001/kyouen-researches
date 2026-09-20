#!/usr/bin/env python3
"""AB staged-V3 root-order benchmark runner.

Phases (resume-safe):
  1. fresh 10k probes on all children
  2. freeze top-11 (V3 corrected key; no exact labels)
  3. fresh 1M probes on top-11
  4. freeze 1M ranking
  5. build root order files (shortlist head + native residual tail)
  6. serial exact A/B, SHA256(parent) parity counterbalance

Primary cost is probe-inclusive visited. Exact labels are never read to
construct order files.
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
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "results" / "10x10" / "ab-staged-v3-root"
ORDERS = OUT / "root_orders"
TASK_CSV = OUT / "exact_task_list.csv"
PARENTS_CSV = OUT / "ab_parents_primary.csv"

PROBE_BIN = REPO_ROOT / "tmp-kb" / "probe_holdout_native"
BENCH_BIN = REPO_ROOT / "tmp-kb" / "parent_bench_native"
PROBE_STAMP = REPO_ROOT / "tmp-kb" / "probe_holdout_native.sources.sha256"
BENCH_STAMP = REPO_ROOT / "tmp-kb" / "parent_bench_native.sources.sha256"

K = 11
PROBE_10K = 10_000
PROBE_1M = 1_000_000
PROBE_SHRINK, PROBE_LOAD = 3, 80
EXACT_SHRINK, EXACT_LOAD = 0, 90
ROOT_DEPTH = 3
EXACT_TIMEOUT = 10800.0

SEED = "kyouen-10x10-ab-staged-v3-root-seed-20260913"


def d4_point(p: int, k: int, n: int = 10) -> int:
    x, y = p % n, p // n
    xy = [
        (x, y), (n - 1 - x, y), (x, n - 1 - y), (n - 1 - x, n - 1 - y),
        (y, x), (n - 1 - y, x), (y, n - 1 - x), (n - 1 - y, n - 1 - x),
    ][k]
    return xy[1] * n + xy[0]


def det3(a, b, c, d, e, f, g, h, i):
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def forbidden(a, b, c, d, n=10):
    pts = [a, b, c, d]
    m = []
    for p in pts:
        x, y = p % n, p // n
        m.append([x * x + y * y, x, y, 1])
    z = 0
    for col in range(4):
        sub = []
        for r in range(1, 4):
            row = [m[r][j] for j in range(4) if j != col]
            sub.append(row)
        md = det3(sub[0][0], sub[0][1], sub[0][2], sub[1][0], sub[1][1], sub[1][2], sub[2][0], sub[2][1], sub[2][2])
        z += (-1 if col % 2 else 1) * m[0][col] * md
    return z == 0


def parse_state(s: str) -> tuple[int, int, int, int]:
    parts = tuple(sorted(int(x) for x in s.split(",")))
    if len(parts) != 4:
        raise ValueError(s)
    return parts


def canonical_key(points: tuple[int, ...]) -> tuple[int, int]:
    """Return (hi, lo) matching C++ Bits operator< (hi then lo)."""
    best = None
    for k in range(8):
        mask = 0
        for p in points:
            mask |= 1 << d4_point(p, k)
        cand = (mask >> 64, mask & ((1 << 64) - 1))
        if best is None or cand < best:
            best = cand
    assert best is not None
    return best


def legal_move_count(state4: tuple[int, int, int, int]) -> int:
    occ = set(state4)
    count = 0
    triples = [
        (state4[i], state4[j], state4[k])
        for i in range(4)
        for j in range(i + 1, 4)
        for k in range(j + 1, 4)
    ]
    for v in range(100):
        if v in occ:
            continue
        if any(forbidden(a, b, c, v) for a, b, c in triples):
            continue
        count += 1
    return count


def move_of(parent: str, child: str) -> int:
    p = {int(x) for x in parent.split(",")}
    c = {int(x) for x in child.split(",")}
    extra = c - p
    if len(extra) != 1:
        raise RuntimeError(f"not a child: {parent} -> {child}")
    return next(iter(extra))


def corrected_key(row: dict[str, str], parent: str) -> tuple:
    outcome = row["probe_outcome"].strip().upper()
    memo = int(row["memo"])
    move = move_of(parent, row["state"])
    if outcome == "LOSS":
        tier = 0
    elif outcome == "WIN":
        tier = 2
    else:
        tier = 1
    return (tier, memo, move)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_tasks() -> list[dict[str, str]]:
    with TASK_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_parents() -> list[str]:
    with PARENTS_CSV.open(newline="", encoding="utf-8") as f:
        return [r["parent_canonical"].strip() for r in csv.DictReader(f)]


def task_set_digest(tasks: list[dict[str, str]]) -> str:
    h = hashlib.sha256()
    for t in tasks:
        d = json.dumps(
            [t["parent"], int(t["batch"]), int(t["batch_position"]), t["state"]],
            separators=(",", ":"),
        ).encode()
        h.update(len(d).to_bytes(8, "big"))
        h.update(d)
    return h.hexdigest()


def ab_order(parent: str) -> list[str]:
    parity = int(hashlib.sha256(parent.encode()).hexdigest(), 16) % 2
    return ["B", "A"] if parity else ["A", "B"]


def frozen_manifest(tasks: list[dict[str, str]], parents: list[str]) -> dict[str, object]:
    return {
        "format": 1,
        "experiment": "ab-staged-v3-root-ordering",
        "seed": SEED,
        "cohort": {
            "parents": parents,
            "total_tasks": len(tasks),
            "task_set_sha256": task_set_digest(tasks),
            "sample_size": len(parents),
        },
        "probe": {
            "binary": "tmp-kb/probe_holdout_native",
            "binary_sha256": sha256_file(PROBE_BIN),
            "sources_sha256": PROBE_STAMP.read_text(encoding="ascii").strip(),
            "budget_10k": PROBE_10K,
            "budget_1m": PROBE_1M,
            "k": K,
            "shrink": PROBE_SHRINK,
            "load": PROBE_LOAD,
            "fresh_process_per_child": True,
            "ranking_key": "probe LOSS first; unresolved memo_used asc; probe WIN last; move asc",
        },
        "parent_solve": {
            "binary": "tmp-kb/parent_bench_native",
            "binary_sha256": sha256_file(BENCH_BIN),
            "sources_sha256": BENCH_STAMP.read_text(encoding="ascii").strip(),
            "build_cmd": ["g++", "-O2", "-std=c++20"],
            "shrink": EXACT_SHRINK,
            "load": EXACT_LOAD,
            "budget": 0,
            "root_depth": ROOT_DEPTH,
            "fresh_process_per_parent_strategy": True,
            "exact_repeats": 1,
        },
        "treatment_order": {
            "head": "1M-reordered top-11 unique canonical children",
            "tail": "remaining unique children in native residual order (legal_move_count asc, Bits key asc)",
            "exact_labels_used": False,
        },
        "counterbalance": "SHA256(parent) parity decides AB vs BA; serial exacts",
        "exact_timeout_s": EXACT_TIMEOUT,
        "primary_endpoint": "probe-inclusive visited: 10k+1M+exact_B vs exact_A",
        "success_gates": {
            "correctness_outcome_agreement": "16/16",
            "aggregate_ratio_lt_1": True,
            "median_ratio_lt_1": True,
            "improved_parents_min": 13,
            "worst_ratio_le": 2.0,
        },
    }


def require_manifest(tasks: list[dict[str, str]], parents: list[str]) -> None:
    cur = frozen_manifest(tasks, parents)
    import platform

    cur["platform"] = platform.platform()
    if (OUT / "protocol.json").exists():
        rec = json.loads((OUT / "protocol.json").read_text(encoding="utf-8"))
        r2, c2 = dict(rec), dict(cur)
        r2.pop("platform", None)
        c2.pop("platform", None)
        if r2 != c2:
            raise RuntimeError("benchmark manifest mismatch; refusing to mix runs")
        return
    if (OUT / "probe_10000.csv").exists() or (OUT / "ab_exact_raw.csv").exists():
        raise RuntimeError("result files exist without a manifest; refusing to append")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "protocol.json").write_text(json.dumps(cur, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def probe_one(args: tuple[str, str, int]) -> dict[str, object]:
    parent, state, budget = args
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, dir=PROBE_BIN.parent, encoding="utf-8"
    ) as tmp:
        tmp.write(state + "\n")
        tmp_path = Path(tmp.name)
    t0 = time.time()
    try:
        cmd = [str(PROBE_BIN), str(tmp_path), str(PROBE_SHRINK), str(PROBE_LOAD), str(budget), "0"]
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
    return {
        "row": {
            "parent": parent,
            "state": state,
            "budget": budget,
            "probe_outcome": r["outcome"],
            "visited": r["visited"],
            "maxdepth": r["maxdepth"],
            "memo": r["memo"],
            "seconds": r["seconds"],
        },
        "wall": wall,
    }


def run_probes(csv_path: Path, pairs: list[tuple[str, str, int]], workers: int) -> None:
    done: set[tuple[str, str, int]] = set()
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                done.add((r["parent"], r["state"], int(r["budget"])))
    pending = [p for p in pairs if p not in done]
    fields = ["parent", "state", "budget", "probe_outcome", "visited", "maxdepth", "memo", "seconds"]
    print(f"probes {csv_path.name}: total={len(pairs)} done={len(done)} pending={len(pending)}", flush=True)
    if not pending:
        return
    outf = csv_path.open("a" if done else "w", newline="", encoding="utf-8")
    w = csv.DictWriter(outf, fieldnames=fields)
    if not done:
        w.writeheader()
    t0 = time.time()
    with mp.Pool(processes=workers) as pool:
        for i, res in enumerate(pool.imap_unordered(probe_one, pending, chunksize=16), start=1):
            w.writerow(res["row"])
            outf.flush()
            if i % 50 == 0 or i == len(pending):
                print(f"  {csv_path.name} {len(done)+i}/{len(pairs)} elapsed={time.time()-t0:.0f}s", flush=True)
    outf.close()


def select_top11() -> Path:
    tasks = load_tasks()
    probes = list(csv.DictReader((OUT / "probe_10000.csv").open(newline="", encoding="utf-8")))
    probe_map = {(r["parent"], r["state"]): r for r in probes}
    task_keys = {(t["parent"], t["state"]) for t in tasks}
    if set(probe_map) != task_keys:
        raise RuntimeError("10k probe set != tasks")
    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in probes:
        by_parent[r["parent"]].append(r)
    rows_out = []
    for parent in sorted(by_parent):
        ranked = sorted(by_parent[parent], key=lambda r: corrected_key(r, parent))
        for rank, r in enumerate(ranked[:K], start=1):
            rows_out.append(
                {
                    "parent": parent,
                    "rank": rank,
                    "state": r["state"],
                    "probe_outcome": r["probe_outcome"],
                    "visited": r["visited"],
                    "maxdepth": r["maxdepth"],
                    "memo": r["memo"],
                    "seconds": r["seconds"],
                    "move": move_of(parent, r["state"]),
                }
            )
    out_csv = OUT / "top11_shortlist.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    digest = hashlib.sha256()
    for r in rows_out:
        payload = f"{r['parent']}|{r['rank']}|{r['state']}".encode()
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    manifest = {
        "k": K,
        "source_probe_sha256": sha256_file(OUT / "probe_10000.csv"),
        "ranking_key": "probe LOSS first; unresolved memo_used ascending; probe WIN last; move ascending",
        "rows": len(rows_out),
        "shortlist_sha256": digest.hexdigest(),
        "labels_used": "10k probe outcomes only; exact labels not consulted",
    }
    (OUT / "top11_shortlist.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"top11 freeze sha256={digest.hexdigest()} rows={len(rows_out)}")
    return out_csv


def rank_1m() -> Path:
    shortlist = list(csv.DictReader((OUT / "top11_shortlist.csv").open(newline="", encoding="utf-8")))
    probes = list(csv.DictReader((OUT / "probe_1000000_top11.csv").open(newline="", encoding="utf-8")))
    probe_map = {(r["parent"], r["state"]): r for r in probes}
    if len(probe_map) != len(shortlist):
        raise RuntimeError(f"1M rows {len(probe_map)} != shortlist {len(shortlist)}")
    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for s in shortlist:
        key = (s["parent"], s["state"])
        if key not in probe_map:
            raise RuntimeError(f"missing 1M row for {key}")
        row = dict(probe_map[key])
        row["rank_10k"] = s["rank"]
        row["memo_10k"] = s["memo"]
        by_parent[s["parent"]].append(row)
    out_rows = []
    for parent in sorted(by_parent):
        ranked = sorted(by_parent[parent], key=lambda r: corrected_key(r, parent))
        for rank, r in enumerate(ranked, start=1):
            out_rows.append(
                {
                    "parent": parent,
                    "rank_1m": rank,
                    "rank_10k": r["rank_10k"],
                    "state": r["state"],
                    "probe_outcome_1m": r["probe_outcome"],
                    "visited_1m": r["visited"],
                    "maxdepth_1m": r["maxdepth"],
                    "memo_1m": r["memo"],
                    "seconds_1m": r["seconds"],
                    "memo_10k": r["memo_10k"],
                    "move": move_of(parent, r["state"]),
                }
            )
    out_csv = OUT / "top11_rank_1m.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    digest = hashlib.sha256()
    for r in out_rows:
        payload = f"{r['parent']}|{r['rank_1m']}|{r['state']}".encode()
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    manifest = {
        "source_shortlist_sha256": sha256_file(OUT / "top11_shortlist.csv"),
        "source_1m_probe_sha256": sha256_file(OUT / "probe_1000000_top11.csv"),
        "ranking_key": "probe LOSS first; unresolved memo_used ascending; probe WIN last; move ascending",
        "rows": len(out_rows),
        "ranking_sha256": digest.hexdigest(),
        "labels_used": "1M probe outcomes only; exact labels not consulted",
    }
    (OUT / "top11_rank_1m.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"1M rank freeze sha256={digest.hexdigest()}")
    return out_csv


def build_root_orders() -> None:
    ORDERS.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks()
    rank_rows = list(csv.DictReader((OUT / "top11_rank_1m.csv").open(newline="", encoding="utf-8")))
    by_parent_rank: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rank_rows:
        by_parent_rank[r["parent"]].append(r)
    by_parent_tasks: dict[str, list[str]] = defaultdict(list)
    for t in tasks:
        by_parent_tasks[t["parent"]].append(t["state"])

    for parent in sorted(by_parent_tasks):
        kids = by_parent_tasks[parent]
        # unique by canonical key, first spelling
        unique: dict[tuple[int, int], str] = {}
        state_key: dict[str, tuple[int, int]] = {}
        state_count: dict[str, int] = {}
        for s in kids:
            pts = parse_state(s)
            key = canonical_key(pts)
            state_key[s] = key
            state_count[s] = legal_move_count(pts)
            if key not in unique:
                unique[key] = s

        head: list[str] = []
        seen: set[tuple[int, int]] = set()
        for r in sorted(by_parent_rank[parent], key=lambda x: int(x["rank_1m"])):
            s = r["state"]
            key = state_key[s]
            if key in seen:
                continue
            head.append(s)
            seen.add(key)

        tail_states = [s for s in unique.values() if state_key[s] not in seen]
        tail_states.sort(key=lambda s: (state_count[s], state_key[s]))
        ordered = head + tail_states

        # coverage: every unique key exactly once
        keys = [state_key[s] for s in ordered]
        if len(keys) != len(set(keys)):
            raise RuntimeError(f"duplicate keys in order for {parent}")
        if set(keys) != set(unique):
            raise RuntimeError(f"incomplete order for {parent}: {len(keys)} vs {len(unique)}")

        op = ORDERS / f"order_{parent.replace(',', '_')}.txt"
        op.write_text("\n".join(ordered) + "\n", encoding="utf-8")
        print(f"  order {parent}: unique={len(ordered)} head={len(head)} tail={len(tail_states)}", flush=True)

    digest = hashlib.sha256()
    for p in sorted(ORDERS.glob("order_*.txt")):
        digest.update(p.name.encode())
        digest.update(p.read_bytes())
    (ORDERS / "orders.manifest.json").write_text(
        json.dumps(
            {
                "files": sorted(p.name for p in ORDERS.glob("order_*.txt")),
                "combined_sha256": digest.hexdigest(),
                "head_rule": "1M-reordered top-11 unique",
                "tail_rule": "native residual legal_move_count asc, Bits key asc",
                "labels_used": "probe ranks only",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"orders sha256={digest.hexdigest()}")


def bench_from_stderr(stderr: str) -> dict[str, str]:
    for line in stderr.splitlines():
        if line.startswith("bench_root "):
            out = {}
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                out[k] = v
            return out
    raise AssertionError(f"no bench_root line:\n{stderr[-600:]}")


def solve_parent(parent: str, strategy: str, order_file: Path | None, logf) -> dict[str, str]:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, dir=BENCH_BIN.parent, encoding="utf-8"
    ) as tmp:
        tmp.write(parent + "\n")
        tmp_path = Path(tmp.name)
    try:
        cmd = [str(BENCH_BIN), str(tmp_path), str(EXACT_SHRINK), str(EXACT_LOAD), "0", "0",
               "--root-depth", str(ROOT_DEPTH)]
        if strategy == "B":
            assert order_file is not None and order_file.exists()
            cmd += ["--root-order-file", str(order_file)]
        logf.write(f"CMD {parent} {strategy}: {' '.join(cmd)}\n")
        logf.flush()
        t0 = time.time()
        pop = subprocess.Popen(
            cmd, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        pid = pop.pid
        try:
            out, err = pop.communicate(timeout=EXACT_TIMEOUT)
        except subprocess.TimeoutExpired:
            pop.kill()
            out, err = pop.communicate()
            raise RuntimeError(f"exact {parent} {strategy} TIMEOUT after {EXACT_TIMEOUT}s")
        wall = time.time() - t0
        rc = pop.returncode
    finally:
        tmp_path.unlink(missing_ok=True)
    if rc != 0:
        raise RuntimeError(f"exact {parent} {strategy} rc={rc}\n{err[-600:]}")
    rows = list(csv.DictReader(out.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected 1 row for {parent}, got {len(rows)}")
    r = rows[0]
    b = bench_from_stderr(err)
    return {
        "parent": parent,
        "strategy": strategy,
        "outcome": r["outcome"],
        "exact_visited": r["visited"],
        "exact_maxdepth": r["maxdepth"],
        "exact_memo": r["memo"],
        "exact_seconds": r["seconds"],
        "wall_seconds": f"{wall:.3f}",
        "pid": str(pid),
        "root_unique": b["unique"],
        "root_entered": b["entered"],
        "root_first_lo": b["first_lo"],
        "root_first_hi": b["first_hi"],
        "root_witness": b["witness"],
        "solver_cmd": " ".join(cmd),
    }


def probe_aggregates() -> dict[str, dict[str, float]]:
    p10 = list(csv.DictReader((OUT / "probe_10000.csv").open(newline="", encoding="utf-8")))
    p1m = list(csv.DictReader((OUT / "probe_1000000_top11.csv").open(newline="", encoding="utf-8")))
    agg: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in p10:
        agg[r["parent"]]["probe10k_visited"] += int(r["visited"])
        agg[r["parent"]]["probe10k_seconds"] += float(r["seconds"])
        agg[r["parent"]]["probe10k_n"] += 1
    for r in p1m:
        agg[r["parent"]]["probe1m_visited"] += int(r["visited"])
        agg[r["parent"]]["probe1m_seconds"] += float(r["seconds"])
        agg[r["parent"]]["probe1m_n"] += 1
    return agg


def run_exacts() -> None:
    parents = load_parents()
    tasks = load_tasks()
    agg = probe_aggregates()
    raw_csv = OUT / "ab_exact_raw.csv"
    fields = [
        "parent", "strategy", "outcome", "exact_visited", "exact_maxdepth", "exact_memo",
        "exact_seconds", "wall_seconds", "pid", "root_unique", "root_entered",
        "root_first_lo", "root_first_hi", "root_witness", "root_children",
        "probe10k_visited", "probe10k_seconds", "probe10k_n",
        "probe1m_visited", "probe1m_seconds", "probe1m_n",
        "probe_visited_total", "probe_seconds_total", "b_total_visited",
        "solver_cmd",
    ]
    done: set[tuple[str, str]] = set()
    if raw_csv.exists():
        with raw_csv.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                done.add((r["parent"], r["strategy"]))
    outf = raw_csv.open("a" if done else "w", newline="", encoding="utf-8")
    w = csv.DictWriter(outf, fieldnames=fields)
    if not done:
        w.writeheader()
    logf = (OUT / "run_commands.log").open("a", encoding="utf-8")
    kids_by_parent: dict[str, int] = defaultdict(int)
    for t in tasks:
        kids_by_parent[t["parent"]] += 1

    for parent in parents:
        order_file = ORDERS / f"order_{parent.replace(',', '_')}.txt"
        for strat in ab_order(parent):
            if (parent, strat) in done:
                print(f"  skip {parent} {strat} (done)", flush=True)
                continue
            print(f"  solve {parent} {strat} ...", flush=True)
            row = solve_parent(parent, strat, order_file if strat == "B" else None, logf)
            row["root_children"] = str(kids_by_parent[parent])
            a = agg[parent]
            if strat == "B":
                row["probe10k_visited"] = str(int(a["probe10k_visited"]))
                row["probe10k_seconds"] = f"{a['probe10k_seconds']:.3f}"
                row["probe10k_n"] = str(int(a["probe10k_n"]))
                row["probe1m_visited"] = str(int(a["probe1m_visited"]))
                row["probe1m_seconds"] = f"{a['probe1m_seconds']:.3f}"
                row["probe1m_n"] = str(int(a["probe1m_n"]))
                pv = int(a["probe10k_visited"] + a["probe1m_visited"])
                ps = a["probe10k_seconds"] + a["probe1m_seconds"]
                row["probe_visited_total"] = str(pv)
                row["probe_seconds_total"] = f"{ps:.3f}"
                row["b_total_visited"] = str(pv + int(row["exact_visited"]))
            else:
                row["probe10k_visited"] = ""
                row["probe10k_seconds"] = ""
                row["probe10k_n"] = ""
                row["probe1m_visited"] = ""
                row["probe1m_seconds"] = ""
                row["probe1m_n"] = ""
                row["probe_visited_total"] = ""
                row["probe_seconds_total"] = ""
                row["b_total_visited"] = ""
            w.writerow(row)
            outf.flush()
            done.add((parent, strat))
            print(
                f"  done {parent} {strat}: {row['outcome']} visited={row['exact_visited']} "
                f"entered={row['root_entered']} wall={row['wall_seconds']}s",
                flush=True,
            )
    outf.close()
    logf.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--phase",
        choices=["all", "probe10k", "shortlist", "probe1m", "rank1m", "orders", "exacts"],
        default="all",
    )
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--skip-probes", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks()
    parents = load_parents()
    assert len(parents) == 16, parents
    require_manifest(tasks, parents)

    if args.phase in ("all", "probe10k") and not args.skip_probes:
        run_probes(OUT / "probe_10000.csv", [(t["parent"], t["state"], PROBE_10K) for t in tasks], args.workers)
    if args.phase in ("all", "shortlist"):
        select_top11()
    if args.phase in ("all", "probe1m") and not args.skip_probes:
        shortlist = list(csv.DictReader((OUT / "top11_shortlist.csv").open(newline="", encoding="utf-8")))
        run_probes(
            OUT / "probe_1000000_top11.csv",
            [(r["parent"], r["state"], PROBE_1M) for r in shortlist],
            args.workers,
        )
    if args.phase in ("all", "rank1m"):
        rank_1m()
    if args.phase in ("all", "orders"):
        build_root_orders()
    if args.phase in ("all", "exacts"):
        run_exacts()
    print("runner finished", flush=True)


if __name__ == "__main__":
    main()

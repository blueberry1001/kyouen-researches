#!/usr/bin/env python3
"""Sharded exact solve runner for 9x9 factorial comparisons.

Splits each comparison input into shards, runs kyouen-solver-9-compare in
parallel, validates complete shards, and retries memo-over shards at smaller
sizes. Outcome meaning and exploration order are unchanged.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path

COMPARISONS = ["O_at_E0", "O_at_E1", "E_at_O0", "E_at_O1"]
EXPECTED_HEADER = [
    "canonical_parent",
    "pair_top",
    "added_top",
    "pair_child_outcome",
    "other_child_outcome",
    "pair_visited",
    "other_visited",
    "pair_seconds",
    "other_seconds",
    "memo_used",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class ShardJob:
    comparison: str
    shard_id: str
    input_path: str
    stdout_path: str
    stderr_path: str
    memo_power: int
    expected_rows: int
    parents: list[str]
    attempt: int = 1


def read_input_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"empty input: {path}")
    required = {"canonical_parent", "pair_top", "added_top"}
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(f"{path} missing columns: {sorted(missing)}")
    return rows


def write_shard(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["canonical_parent", "pair_top", "added_top"])
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "canonical_parent": r["canonical_parent"],
                    "pair_top": r["pair_top"],
                    "added_top": r["added_top"],
                }
            )


def validate_result(shard: ShardJob) -> tuple[bool, str]:
    out = Path(shard.stdout_path)
    if not out.exists():
        return False, "missing stdout"
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return False, "empty stdout"
    if rows[0] != EXPECTED_HEADER:
        return False, f"bad header: {rows[0]}"
    data = rows[1:]
    if len(data) != shard.expected_rows:
        return False, f"row count {len(data)} != {shard.expected_rows}"
    parents = [r[0] for r in data]
    if parents != shard.parents:
        return False, "parent order/set mismatch"
    for r in data:
        if len(r) < 5 or r[3].upper() not in {"WIN", "LOSS"} or r[4].upper() not in {"WIN", "LOSS"}:
            return False, f"bad outcome row: {r[:5]}"
    return True, "ok"


def run_shard(solver: str, shard: ShardJob) -> dict:
    out_path = Path(shard.stdout_path)
    err_path = Path(shard.stderr_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    err_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [solver, shard.input_path, str(shard.memo_power)]
    t0 = time.time()
    with open(out_path, "w", encoding="utf-8", newline="") as out_f, open(
        err_path, "w", encoding="utf-8", newline=""
    ) as err_f:
        proc = subprocess.run(cmd, stdout=out_f, stderr=err_f, text=True)
    elapsed = time.time() - t0
    ok, reason = validate_result(shard)
    stderr_text = err_path.read_text(encoding="utf-8", errors="replace")
    memo_over = "memo table over 80%" in stderr_text
    forbidden = "forbidden quadruple" in stderr_text
    return {
        "comparison": shard.comparison,
        "shard_id": shard.shard_id,
        "input": shard.input_path,
        "stdout": shard.stdout_path,
        "stderr": shard.stderr_path,
        "memo_power": shard.memo_power,
        "expected_rows": shard.expected_rows,
        "exit_code": proc.returncode,
        "valid": ok,
        "reason": reason,
        "memo_over": memo_over,
        "forbidden": forbidden,
        "elapsed_sec": round(elapsed, 3),
        "attempt": shard.attempt,
        "parents": shard.parents,
    }


def plan_shards(
    comparison: str,
    rows: list[dict],
    shard_dir: Path,
    shard_size: int,
    memo_power: int,
    attempt: int = 1,
    parent_prefix: str = "",
) -> list[ShardJob]:
    jobs = []
    for i in range(0, len(rows), shard_size):
        chunk = rows[i : i + shard_size]
        sid = f"{parent_prefix}{i // shard_size:04d}"
        in_path = shard_dir / comparison / f"attempt{attempt}" / f"{sid}.csv"
        write_shard(in_path, chunk)
        jobs.append(
            ShardJob(
                comparison=comparison,
                shard_id=sid,
                input_path=str(in_path),
                stdout_path=str(
                    shard_dir / comparison / f"attempt{attempt}" / f"{sid}.out.csv"
                ),
                stderr_path=str(
                    shard_dir / comparison / f"attempt{attempt}" / f"{sid}.err.log"
                ),
                memo_power=memo_power,
                expected_rows=len(chunk),
                parents=[r["canonical_parent"] for r in chunk],
                attempt=attempt,
            )
        )
    return jobs


def _iter_valid_result_files(shard_root: Path):
    for out in sorted(shard_root.rglob("*.out.csv")):
        input_path = Path(str(out).replace(".out.csv", ".csv"))
        if not input_path.exists():
            continue
        try:
            expected = len(read_input_rows(input_path))
        except Exception:
            continue
        try:
            with open(out, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames != EXPECTED_HEADER:
                    continue
                rows = list(reader)
        except Exception:
            continue
        if len(rows) != expected:
            continue
        ok = True
        for r in rows:
            if r["pair_child_outcome"].strip().upper() not in {"WIN", "LOSS"}:
                ok = False
                break
            if r["other_child_outcome"].strip().upper() not in {"WIN", "LOSS"}:
                ok = False
                break
        if not ok:
            continue
        yield rows


def aggregate_completed(comparison: str, shard_dir: Path, all_parents: set[str]) -> dict:
    parent_rows = {}
    meta = {
        "comparison": comparison,
        "solved_parents": 0,
        "remaining": 0,
        "both_loss": 0,
        "both_win": 0,
        "baseline_only": 0,
        "added_only": 0,
        "discordant": 0,
    }
    for rows in _iter_valid_result_files(shard_dir / comparison):
        for r in rows:
            parent_rows[r["canonical_parent"]] = r
    for parent in all_parents:
        r = parent_rows.get(parent)
        if r is None:
            continue
        lo = r["pair_child_outcome"].strip().upper()
        ro = r["other_child_outcome"].strip().upper()
        if lo == "LOSS" and ro == "LOSS":
            meta["both_loss"] += 1
        elif lo == "WIN" and ro == "WIN":
            meta["both_win"] += 1
        elif lo == "LOSS" and ro == "WIN":
            meta["baseline_only"] += 1
        elif lo == "WIN" and ro == "LOSS":
            meta["added_only"] += 1
    meta["discordant"] = meta["baseline_only"] + meta["added_only"]
    meta["solved_parents"] = (
        meta["both_loss"]
        + meta["both_win"]
        + meta["baseline_only"]
        + meta["added_only"]
    )
    meta["remaining"] = len(all_parents) - meta["solved_parents"]
    return meta


def write_merged(comparison: str, shard_dir: Path, expected_parents: list[str], out_path: Path):
    parent_rows = {}
    for rows in _iter_valid_result_files(shard_dir / comparison):
        for r in rows:
            parent_rows[r["canonical_parent"]] = r
    missing = [p for p in expected_parents if p not in parent_rows]
    extra = sorted(set(parent_rows) - set(expected_parents))
    if missing or extra:
        raise SystemExit(
            f"{comparison} merge mismatch missing={len(missing)} extra={len(extra)}"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EXPECTED_HEADER)
        w.writeheader()
        for p in expected_parents:
            w.writerow(parent_rows[p])
    return sha256_file(out_path), len(expected_parents)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solver", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--shard-size", type=int, default=12)
    ap.add_argument("--max-jobs", type=int, default=7)
    ap.add_argument("--memo-power", type=int, default=28)
    ap.add_argument("--progress-json", required=True)
    ap.add_argument("--only", action="append", default=[], help="restrict comparisons")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    shard_dir = out_dir / "shards"
    merged_dir = out_dir / "merged"
    progress_path = Path(args.progress_json)
    progress_path.parent.mkdir(parents=True, exist_ok=True)

    comparisons = [c for c in COMPARISONS if (not args.only) or c in args.only]
    inputs = {}
    for c in comparisons:
        path = input_dir / f"{c}.csv"
        rows = read_input_rows(path)
        inputs[c] = rows
        print(f"loaded {c}: n={len(rows)}", flush=True)

    # Run O comparisons first as a wave, then E, but keep max-jobs saturated.
    ordered_jobs: list[ShardJob] = []
    for c in comparisons:
        ordered_jobs.extend(
            plan_shards(c, inputs[c], shard_dir, args.shard_size, args.memo_power)
        )

    print(
        f"planned_shards={len(ordered_jobs)} shard_size={args.shard_size} "
        f"max_jobs={args.max_jobs} memo_power={args.memo_power}",
        flush=True,
    )

    results: list[dict] = []
    failed_rows_for_escalation: list[tuple[str, dict]] = []
    retries = []
    t_start = time.time()
    start_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def handle_result(res: dict):
        results.append({k: v for k, v in res.items() if k != "parents"})
        status = "ok" if res["valid"] and res["exit_code"] == 0 else "fail"
        if res["memo_over"]:
            status = "memo_over"
        print(
            f"[{status}] {res['comparison']} {res['shard_id']} "
            f"rows={res['expected_rows']} exit={res['exit_code']} "
            f"t={res['elapsed_sec']}s {res['reason']}",
            flush=True,
        )

    # First pass
    with ThreadPoolExecutor(max_workers=args.max_jobs) as ex:
        futs = [ex.submit(run_shard, args.solver, job) for job in ordered_jobs]
        for fut in as_completed(futs):
            handle_result(fut.result())
            # periodic progress
            prog = {
                "updated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "elapsed_sec": round(time.time() - t_start, 1),
                "comparisons": {},
            }
            for c in comparisons:
                parents = {r["canonical_parent"] for r in inputs[c]}
                prog["comparisons"][c] = aggregate_completed(c, shard_dir, parents)
            progress_path.write_text(json.dumps(prog, indent=2) + "\n", encoding="utf-8")

    # Retry memo-over shards at half size, then individual rows at memo_power+1
    pending_retries = [r for r in results if r["memo_over"] or not r["valid"]]
    attempt = 2
    while pending_retries:
        next_retries = []
        retry_jobs = []
        for r in pending_retries:
            if r["forbidden"]:
                print(f"[fatal-forbidden] {r['comparison']} {r['shard_id']}", flush=True)
                continue
            src = read_input_rows(Path(r["input"]))
            if r["memo_over"] and len(src) > 1:
                half = max(1, len(src) // 2)
                for j, start in enumerate(range(0, len(src), half)):
                    chunk = src[start : start + half]
                    sid = f"{r['shard_id']}-h{j}"
                    in_path = shard_dir / r["comparison"] / f"attempt{attempt}" / f"{sid}.csv"
                    write_shard(in_path, chunk)
                    retry_jobs.append(
                        ShardJob(
                            comparison=r["comparison"],
                            shard_id=sid,
                            input_path=str(in_path),
                            stdout_path=str(
                                shard_dir
                                / r["comparison"]
                                / f"attempt{attempt}"
                                / f"{sid}.out.csv"
                            ),
                            stderr_path=str(
                                shard_dir
                                / r["comparison"]
                                / f"attempt{attempt}"
                                / f"{sid}.err.log"
                            ),
                            memo_power=args.memo_power,
                            expected_rows=len(chunk),
                            parents=[row["canonical_parent"] for row in chunk],
                            attempt=attempt,
                        )
                    )
            elif r["memo_over"] and len(src) == 1:
                # escalate single row memo power
                sid = f"{r['shard_id']}-mp29"
                in_path = shard_dir / r["comparison"] / f"attempt{attempt}" / f"{sid}.csv"
                write_shard(in_path, src)
                retry_jobs.append(
                    ShardJob(
                        comparison=r["comparison"],
                        shard_id=sid,
                        input_path=str(in_path),
                        stdout_path=str(
                            shard_dir
                            / r["comparison"]
                            / f"attempt{attempt}"
                            / f"{sid}.out.csv"
                        ),
                        stderr_path=str(
                            shard_dir
                            / r["comparison"]
                            / f"attempt{attempt}"
                            / f"{sid}.err.log"
                        ),
                        memo_power=29,
                        expected_rows=len(src),
                        parents=[row["canonical_parent"] for row in src],
                        attempt=attempt,
                    )
                )
            else:
                # invalid without memo_over: retry once at same power
                sid = f"{r['shard_id']}-r"
                in_path = shard_dir / r["comparison"] / f"attempt{attempt}" / f"{sid}.csv"
                write_shard(in_path, src)
                retry_jobs.append(
                    ShardJob(
                        comparison=r["comparison"],
                        shard_id=sid,
                        input_path=str(in_path),
                        stdout_path=str(
                            shard_dir
                            / r["comparison"]
                            / f"attempt{attempt}"
                            / f"{sid}.out.csv"
                        ),
                        stderr_path=str(
                            shard_dir
                            / r["comparison"]
                            / f"attempt{attempt}"
                            / f"{sid}.err.log"
                        ),
                        memo_power=args.memo_power,
                        expected_rows=len(src),
                        parents=[row["canonical_parent"] for row in src],
                        attempt=attempt,
                    )
                )
        if not retry_jobs:
            break
        print(f"retry_wave attempt={attempt} jobs={len(retry_jobs)}", flush=True)
        wave_results = []
        with ThreadPoolExecutor(max_workers=args.max_jobs) as ex:
            futs = [ex.submit(run_shard, args.solver, job) for job in retry_jobs]
            for fut in as_completed(futs):
                res = fut.result()
                handle_result(res)
                wave_results.append(res)
                prog = {
                    "updated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "elapsed_sec": round(time.time() - t_start, 1),
                    "comparisons": {},
                }
                for c in comparisons:
                    parents = {r["canonical_parent"] for r in inputs[c]}
                    prog["comparisons"][c] = aggregate_completed(c, shard_dir, parents)
                progress_path.write_text(
                    json.dumps(prog, indent=2) + "\n", encoding="utf-8"
                )
        retries.extend(wave_results)
        pending_retries = [
            r for r in wave_results if (r["memo_over"] or not r["valid"]) and not r["forbidden"]
        ]
        attempt += 1
        if attempt > 6:
            print("retry attempt limit reached", flush=True)
            break

    # Merge and final progress
    merged_info = {}
    for c in comparisons:
        expected = [r["canonical_parent"] for r in inputs[c]]
        mpath = merged_dir / f"{c}.csv"
        digest, n = write_merged(c, shard_dir, expected, mpath)
        merged_info[c] = {
            "path": str(mpath).replace("\\", "/"),
            "sha256": digest,
            "rows": n,
        }
        print(f"merged {c}: rows={n} sha256={digest}", flush=True)

    final_prog = {
        "started_at_utc": start_iso,
        "finished_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_sec": round(time.time() - t_start, 1),
        "shard_size": args.shard_size,
        "max_jobs": args.max_jobs,
        "memo_power": args.memo_power,
        "comparisons": {},
        "merged": merged_info,
        "n_shards": len(results) + len(retries),
        "failed_shards": [r for r in results + retries if not r["valid"]],
        "memo_over_shards": [r for r in results + retries if r["memo_over"]],
        "mp29_shards": [r for r in results + retries if r["memo_power"] == 29],
    }
    for c in comparisons:
        parents = {r["canonical_parent"] for r in inputs[c]}
        final_prog["comparisons"][c] = aggregate_completed(c, shard_dir, parents)
    progress_path.write_text(json.dumps(final_prog, indent=2) + "\n", encoding="utf-8")

    for c, info in merged_info.items():
        print(
            f"{c}: solved={final_prog['comparisons'][c]['solved_parents']}/"
            f"{final_prog['comparisons'][c]['solved_parents']+final_prog['comparisons'][c]['remaining']} "
            f"merged_sha256={info['sha256']}"
        )
    if any(not r["valid"] for r in final_prog["failed_shards"] if r["exit_code"] != 0 or not r["valid"]):
        # If merge succeeded, failures were superseded by retries.
        still_bad = []
        for c in comparisons:
            parents = {r["canonical_parent"] for r in inputs[c]}
            meta = final_prog["comparisons"][c]
            if meta["remaining"] != 0:
                still_bad.append(c)
        if still_bad:
            print(f"INCOMPLETE: {still_bad}", flush=True)
            sys.exit(1)
    print("ALL_COMPLETE", flush=True)


if __name__ == "__main__":
    main()

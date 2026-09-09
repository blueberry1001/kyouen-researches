#!/usr/bin/env python3
"""Seal and collect the preregistered 72-run no-hit timing endpoint.

Two-step use is intentional:

  python3 scripts/run_nohit_fastpath_timing.py --seal
  git add results/10x10/cache-aware-nohit-fastpath/timing_execution_manifest.json
  git commit -m "Freeze no-hit timing execution manifest"
  python3 scripts/run_nohit_fastpath_timing.py --run

--seal performs NO timing runs.  It requires semantic-parity PASS and records
the exact 72-run order plus binary/plan/collector/verifier/analyzer hashes.
--run refuses to start unless that manifest is byte-identical to the version
committed at HEAD.  Raw timing is collected only; analysis is a separate step.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-nohit-fastpath"
PLAN_PATH = OUT / "execution_plan.json"
BUILD_RECEIPT = OUT / "build_receipt.json"
PARITY_RECEIPT = OUT / "parity_collection_receipt.json"
MANIFEST = OUT / "timing_execution_manifest.json"
TIMING = OUT / "timing"
COLLECTION_RECEIPT = OUT / "timing_collection_receipt.json"
VERIFIER = ROOT / "scripts" / "verify_nohit_fastpath_parity.py"
ANALYZER = ROOT / "scripts" / "analyze_nohit_fastpath_timing.py"
SELF = Path(__file__).resolve()

EXACT_SHRINK = 0
EXACT_LOAD = 90
ROOT_DEPTH = 3
DEFAULT_TIMEOUT = 14400.0
PARENTS = [
    "0,11,35", "11,38,44", "11,78,87", "12,24,68", "12,32,55",
    "13,52,57", "14,64,74", "23,44,45", "3,47,63", "3,53,84",
    "4,24,26", "4,42,54",
]
IMPL_MAP = {"S": "sort", "F": "nohit"}


def fail(msg: str) -> None:
    raise SystemExit(f"NOHIT TIMING COLLECT FAIL: {msg}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict:
    if not path.is_file():
        fail(f"missing {rel(path)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"cannot parse {rel(path)}: {e}")
    raise AssertionError


def check_parity_pass() -> None:
    pr = load_json(PARITY_RECEIPT)
    if pr.get("runs_completed") != 24:
        fail("parity collection is not 24/24")
    p = subprocess.run(
        [sys.executable, rel(VERIFIER)], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if p.returncode != 0 or "NOHIT FASTPATH SEMANTIC PARITY VERIFIER: PASS" not in p.stdout:
        print(p.stdout, end="")
        print(p.stderr, end="", file=sys.stderr)
        fail("semantic parity verifier does not PASS")


def load_binary() -> tuple[Path, dict]:
    receipt = load_json(BUILD_RECEIPT)
    b = receipt.get("binary")
    hs = receipt.get("binary_sha256")
    if not isinstance(b, str) or not isinstance(hs, str):
        fail("build receipt lacks sealed binary")
    binary = ROOT / b
    if not binary.is_file() or sha256_file(binary) != hs:
        fail("endpoint binary missing or SHA differs from build receipt")
    if receipt.get("same_binary_required_for") != ["sort", "nohit"]:
        fail("build receipt does not seal same binary for sort/nohit")
    return binary, receipt


def exact_run_order(plan: dict) -> list[dict[str, object]]:
    if plan.get("parents_ranked") != PARENTS:
        fail("cohort differs from frozen execution plan")
    tp = plan.get("timing", {})
    if tp.get("runs") != 72 or tp.get("repetitions") != 3:
        fail("timing plan is not 72 runs / 3 reps")
    if tp.get("fresh_process_each_run") is not True or tp.get("serial") is not True:
        fail("timing plan is not fresh-process serial")
    rules = tp.get("order_by_rank_parity", {})
    odd = [["S", "F"], ["F", "S"], ["S", "F"]]
    even = [["F", "S"], ["S", "F"], ["F", "S"]]
    if rules.get("odd_rank") != odd or rules.get("even_rank") != even:
        fail("timing counterbalance differs from frozen plan")

    runs: list[dict[str, object]] = []
    oi = 0
    # Global order is frozen here, pre-endpoint: ascending parent rank, then
    # repetition 1..3, then the two implementations in the frozen pair.
    for rank, parent in enumerate(PARENTS, 1):
        rep_pairs = odd if rank % 2 else even
        for rep, labels in enumerate(rep_pairs, 1):
            for label in labels:
                oi += 1
                runs.append({
                    "order_index": oi,
                    "rank": rank,
                    "parent": parent,
                    "repetition": rep,
                    "implementation": IMPL_MAP[label],
                })
    if len(runs) != 72:
        fail(f"constructed timing order has {len(runs)} runs")
    return runs


def git_show_head(path: Path) -> bytes:
    rp = rel(path)
    p = subprocess.run(
        ["git", "show", f"HEAD:{rp}"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if p.returncode == 0:
        return p.stdout

    # WSL fallback for a Windows-created worktree whose .git pointer is not
    # directly traversable by WSL git.
    dotgit = ROOT / ".git"
    if dotgit.is_file():
        pointer = dotgit.read_text(encoding="utf-8", errors="replace").strip()
        if pointer.startswith("gitdir:"):
            pointer = pointer[len("gitdir:"):].strip()
        m = re.match(r"(.*)[/\\]\.git[/\\]worktrees[/\\](.+)$", pointer)
        if m:
            repo = m.group(1)
            mm = re.match(r"^([A-Za-z]):[/\\](.*)$", repo)
            if mm and Path("/mnt").exists() and not Path("C:/").exists():
                repo = "/mnt/" + mm.group(1).lower() + "/" + mm.group(2).replace("\\", "/")
            gitdir = Path(repo) / ".git"
            q = subprocess.run(
                ["git", "--git-dir", str(gitdir), "show", f"HEAD:{rp}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            if q.returncode == 0:
                return q.stdout
    fail(f"cannot read committed HEAD:{rp}")
    raise AssertionError


def seal() -> int:
    check_parity_pass()
    binary, build = load_binary()
    plan = load_json(PLAN_PATH)
    runs = exact_run_order(plan)
    if MANIFEST.exists():
        fail(f"manifest already exists: {rel(MANIFEST)}")
    if TIMING.exists() and any(TIMING.iterdir()):
        fail("timing raw already exists before seal")
    if COLLECTION_RECEIPT.exists():
        fail("timing collection receipt already exists before seal")
    for tool in (SELF, VERIFIER, ANALYZER):
        if not tool.is_file():
            fail(f"missing frozen tool {rel(tool)}")

    manifest = {
        "experiment": "10x10-cache-aware-nohit-fastpath",
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "SEALED BEFORE FIRST TIMING RUN",
        "binary": rel(binary),
        "binary_sha256": build["binary_sha256"],
        "build_receipt_sha256": sha256_file(BUILD_RECEIPT),
        "parity_collection_receipt_sha256": sha256_file(PARITY_RECEIPT),
        "execution_plan_sha256": sha256_file(PLAN_PATH),
        "collector_sha256": sha256_file(SELF),
        "parity_verifier_sha256": sha256_file(VERIFIER),
        "analyzer_sha256": sha256_file(ANALYZER),
        "compiler": build.get("compiler"),
        "flags": build.get("flags"),
        "shrink": EXACT_SHRINK,
        "load": EXACT_LOAD,
        "root_depth": ROOT_DEPTH,
        "below_root_order": "cache-aware",
        "fresh_process_each_run": True,
        "serial": True,
        "historical_timing_reuse": False,
        "run_order_definition": "rank ascending; rep 1..3; frozen impl pair within rep",
        "runs": runs,
        "primary": {
            "per_parent": "median(seconds_sort)/median(seconds_nohit)",
            "pass_all": ["median_parent_ratio > 1", "F_faster_count >= 7_of_12"],
            "effect_size_threshold": None,
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("NOHIT TIMING MANIFEST SEALED; NO ENDPOINT RUNS EXECUTED")
    print(f"manifest={rel(MANIFEST)}")
    print("REQUIRED: commit the manifest before --run")
    return 0


def read_one_stdout(text: str, label: str) -> dict[str, str]:
    rows = list(csv.DictReader(text.splitlines()))
    if len(rows) != 1:
        fail(f"{label}: expected one stdout row, got {len(rows)}")
    if rows[0].get("outcome") not in ("WIN", "LOSS"):
        fail(f"{label}: invalid outcome {rows[0].get('outcome')!r}")
    return rows[0]


def parity_semantic_reference(parent: str) -> tuple[str, str, str, str]:
    d = OUT / "raw_parity" / f"{parent.replace(',', '_')}_sort" / "stdout.txt"
    if not d.is_file():
        fail(f"missing parity semantic reference for {parent}")
    row = read_one_stdout(d.read_text(encoding="utf-8"), f"parity {parent}")
    return row["outcome"], row["visited"], row["memo"], row["maxdepth"]


def run_one(binary: Path, spec: dict[str, object], timeout: float) -> dict[str, object]:
    oi = int(spec["order_index"])
    rank = int(spec["rank"])
    parent = str(spec["parent"])
    rep = int(spec["repetition"])
    impl = str(spec["implementation"])
    tag = f"run_{oi:03d}_rank{rank:02d}_{parent.replace(',', '_')}_rep{rep}_{impl}"
    d = TIMING / tag
    if d.exists():
        fail(f"timing directory already exists: {rel(d)}")
    d.mkdir(parents=True)

    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8", dir=str(ROOT)
    ) as tmp:
        tmp.write(parent + "\n")
        state = Path(tmp.name)

    stdout_path = d / "stdout.txt"
    stderr_path = d / "stderr.txt"
    meta_path = d / "run_meta.json"
    cmd = [
        str(binary), str(state), str(EXACT_SHRINK), str(EXACT_LOAD), "0", "0",
        "--root-depth", str(ROOT_DEPTH),
        "--below-root-order", "cache-aware",
        "--cache-aware-order-impl", impl,
    ]
    started = datetime.now(timezone.utc)
    t0 = time.monotonic()
    out = err = ""
    timed_out = False
    rc: int | None = None
    try:
        pop = subprocess.Popen(cmd, cwd=ROOT, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            out, err = pop.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            pop.kill()
            out, err = pop.communicate()
        rc = pop.returncode
    finally:
        state.unlink(missing_ok=True)
    wall = time.monotonic() - t0
    stdout_path.write_text(out, encoding="utf-8")
    stderr_path.write_text(err, encoding="utf-8")
    meta = {
        **spec,
        "started_at_utc": started.isoformat(),
        "wall_seconds": wall,
        "returncode": rc,
        "timed_out": timed_out,
    }
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if timed_out:
        fail(f"run {oi}/72 {parent} rep{rep} {impl}: timeout; raw preserved")
    if rc != 0:
        fail(f"run {oi}/72 {parent} rep{rep} {impl}: rc={rc}; raw preserved")
    if "below_root_order=cache-aware" not in err or f"cache_aware_impl={impl}" not in err:
        fail(f"run {oi}/72 {parent} rep{rep} {impl}: implementation markers missing")
    row = read_one_stdout(out, f"run {oi}/72")
    sem = (row["outcome"], row["visited"], row["memo"], row["maxdepth"])
    if sem != parity_semantic_reference(parent):
        fail(f"run {oi}/72 {parent}/{impl}: semantic fields differ from parity reference")

    return {
        **spec,
        "run_dir": rel(d),
        "wall_seconds": wall,
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
        "meta_sha256": sha256_file(meta_path),
    }


def run_endpoint(timeout: float) -> int:
    if not MANIFEST.is_file():
        fail("timing manifest missing; run --seal and commit it first")
    # Strong commit gate: the exact manifest consumed must already be in HEAD.
    committed = git_show_head(MANIFEST)
    current = MANIFEST.read_bytes()
    if committed != current:
        fail("timing manifest is not byte-identical to committed HEAD; commit before --run")

    check_parity_pass()
    binary, build = load_binary()
    manifest = load_json(MANIFEST)
    plan = load_json(PLAN_PATH)
    expected_runs = exact_run_order(plan)
    if manifest.get("runs") != expected_runs:
        fail("committed timing manifest run order differs from frozen execution plan")
    checks = {
        "binary_sha256": build["binary_sha256"],
        "build_receipt_sha256": sha256_file(BUILD_RECEIPT),
        "parity_collection_receipt_sha256": sha256_file(PARITY_RECEIPT),
        "execution_plan_sha256": sha256_file(PLAN_PATH),
        "collector_sha256": sha256_file(SELF),
        "parity_verifier_sha256": sha256_file(VERIFIER),
        "analyzer_sha256": sha256_file(ANALYZER),
    }
    for k, want in checks.items():
        if manifest.get(k) != want:
            fail(f"manifest provenance mismatch {k}: {manifest.get(k)} != {want}")
    if COLLECTION_RECEIPT.exists():
        fail("timing collection receipt already exists; refusing duplicate endpoint")
    if TIMING.exists() and any(TIMING.iterdir()):
        fail("timing directory nonempty; refusing overwrite/restart")
    TIMING.mkdir(parents=True, exist_ok=True)

    print("NOHIT TIMING ENDPOINT START: 72 fresh serial runs")
    print(f"binary_sha256={build['binary_sha256']}")
    completed: list[dict[str, object]] = []
    for spec in expected_runs:
        print(
            f"[{spec['order_index']:02d}/72] rank={spec['rank']} parent={spec['parent']} "
            f"rep={spec['repetition']} impl={spec['implementation']}",
            flush=True,
        )
        completed.append(run_one(binary, spec, timeout))

    receipt = {
        "experiment": "10x10-cache-aware-nohit-fastpath",
        "status": "72/72 operationally complete; UNANALYZED",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_completed": 72,
        "fresh_process_each_run": True,
        "serial": True,
        "analysis_performed": False,
        "binary_sha256": build["binary_sha256"],
        "manifest_sha256": sha256_file(MANIFEST),
        "runs": completed,
        "next_required_command": "python3 scripts/analyze_nohit_fastpath_timing.py",
    }
    tmp = COLLECTION_RECEIPT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(COLLECTION_RECEIPT)
    print("NOHIT TIMING COLLECTION COMPLETE: 72/72")
    print("analysis_status=UNANALYZED")
    print(f"receipt={rel(COLLECTION_RECEIPT)}")
    print("next=python3 scripts/analyze_nohit_fastpath_timing.py")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--seal", action="store_true", help="write pre-run manifest only")
    mode.add_argument("--run", action="store_true", help="run only from committed manifest")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                    help="operational per-run timeout seconds; default 14400")
    args = ap.parse_args()
    if args.timeout <= 0:
        fail("timeout must be positive")
    if args.seal:
        return seal()
    return run_endpoint(args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())

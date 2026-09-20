#!/usr/bin/env python3
"""Validate and run the preregistered 10x10 below-root instrumentation.

The normal solver source is retained as the semantic baseline.  This runner
builds baseline and instrumented binaries from the same checkout, forces one
state per process, compares outcome/visited/maxdepth/memo/root diagnostics, and
only then accepts the observational counter rows.

Default mode is a tiny deterministic regression derived from the repository's
KYOENC4 10x10 smoke generator.  --run-four additionally runs the frozen four
mechanism parents with exact shrink=0/load=90 and writes immutable raw rows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import struct
import subprocess
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP = REPO_ROOT / "tmp-kb" / "below-root-instrumentation"
RESULTS = REPO_ROOT / "results" / "10x10" / "below-root-instrumentation"

BASE_SRC = REPO_ROOT / "scripts" / "probe_cert_solver.cpp"
INST_SRC = REPO_ROOT / "scripts" / "probe_cert_solver_below_root.cpp"
SMOKE_SRC = REPO_ROOT / "cpp" / "certificate" / "kyouen_certgen_v4_smoke.cpp"
BASE_BIN = TMP / "solver_base"
INST_BIN = TMP / "solver_instrumented"
SMOKE_BIN = TMP / "kyoenc4_smoke"

FROZEN_FOUR = ["12,32,55", "14,64,74", "0,11,35", "13,52,57"]
ROOT_DIAG_RE = re.compile(
    r"^bench_root unique=(\d+) entered=(\d+) first_lo=(\d+) first_hi=(\d+) "
    r"witness=(-?\d+) outcome=(WIN|LOSS|PROBE)$"
)

COUNTER_FIELDS = [
    "root_lo", "root_hi", "root_depth", "outcome", "depth", "visited",
    "maxdepth", "memo", "expanded", "terminal", "entry_get",
    "entry_hit_loss", "entry_hit_win", "child_get", "child_hit_loss",
    "child_hit_win", "put_loss", "put_win", "children_generated",
    "children_duplicate", "unique_children", "cached_loss_children",
    "cached_win_children", "unknown_children", "children_entered",
    "win_nodes", "loss_nodes", "cutoff_index_sum", "work_into_win_child",
    "work_into_loss_child", "calls_into_win_child", "calls_into_loss_child",
    "late_entry_hit_win", "late_entry_hit_loss",
]


def run(cmd: list[str], *, env: dict[str, str] | None = None,
        timeout: float = 600.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=REPO_ROOT, env=env, text=True, capture_output=True,
        timeout=timeout, check=False,
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def source_digest(instrumented: bool) -> str:
    top = INST_SRC if instrumented else BASE_SRC
    paths = [top]
    names = [
        "kyouen_solver_10_kyoenc4_witness_log.inc",
        "kyouen_solver_10_kyoenc4_resume_0.inc",
        "kyouen_solver_10_kyoenc4_resume_1.inc",
        "kyouen_solver_10_kyoenc4_resume_2.inc",
    ]
    if instrumented:
        names += [
            "kyouen_solver_10_below_root_instrumentation.inc",
            "kyouen_solver_10_kyoenc4_resume_3_below_root.inc",
        ]
    else:
        names += ["kyouen_solver_10_kyoenc4_resume_3.inc"]
    names += ["kyouen_solver_10_kyoenc4_resume_4.inc"]
    paths += [REPO_ROOT / "scripts" / "probe_parts" / name for name in names]
    h = hashlib.sha256()
    for path in paths:
        rel = path.relative_to(REPO_ROOT).as_posix().encode()
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big")); h.update(rel)
        h.update(len(data).to_bytes(8, "big")); h.update(data)
    return h.hexdigest()


def build() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    commands = [
        ["g++", "-O2", "-std=c++20", str(BASE_SRC), "-o", str(BASE_BIN)],
        ["g++", "-O2", "-std=c++20", str(INST_SRC), "-o", str(INST_BIN)],
        ["g++", "-O2", "-std=c++20", str(SMOKE_SRC), "-o", str(SMOKE_BIN)],
    ]
    for cmd in commands:
        cp = run(cmd, timeout=900.0)
        if cp.returncode:
            raise RuntimeError(
                "build failed:\n" + " ".join(cmd) + "\nstdout:\n" + cp.stdout +
                "\nstderr:\n" + cp.stderr
            )


def state_from_smoke_certificate() -> str:
    cert = TMP / "smoke.cert"
    cp = run([str(SMOKE_BIN), str(cert)], timeout=120.0)
    if cp.returncode:
        raise RuntimeError("smoke generator failed:\n" + cp.stderr)
    data = cert.read_bytes()
    if len(data) < 48:
        raise RuntimeError("smoke certificate header truncated")
    magic, version, board, nodes, root_lo, root_hi, forbidden = struct.unpack(
        "<8sIIQQQQ", data[:48]
    )
    if not magic.startswith(b"KYOENC4") or version != 4 or board != 10 or nodes != 2:
        raise RuntimeError("unexpected smoke certificate header")
    bits = root_lo | (root_hi << 64)
    pts = [str(i) for i in range(100) if (bits >> i) & 1]
    if not pts or not root_hi:
        raise RuntimeError("smoke root did not exercise the high 64-bit word")
    return ",".join(pts)


def parse_primary(stdout: str) -> dict[str, str]:
    lines = [line for line in stdout.splitlines() if line.strip()]
    if len(lines) != 2:
        raise RuntimeError(f"expected one solver CSV row, got {len(lines)} lines: {lines[:4]}")
    rows = list(csv.DictReader(lines))
    if len(rows) != 1:
        raise RuntimeError("could not parse solver CSV row")
    return rows[0]


def parse_root_diag(stderr: str) -> tuple[str, ...]:
    hits = []
    for line in stderr.splitlines():
        m = ROOT_DIAG_RE.match(line.strip())
        if m:
            hits.append(m.groups())
    if len(hits) != 1:
        raise RuntimeError(f"expected one bench_root line, got {len(hits)}")
    return hits[0]


def parse_counter_rows(stderr: str) -> list[dict[str, str]]:
    header_seen = False
    rows: list[dict[str, str]] = []
    total_seen = 0
    for line in stderr.splitlines():
        if line.startswith("below_root_csv_header,"):
            got = line.split(",")[1:]
            if got != COUNTER_FIELDS:
                raise RuntimeError(f"instrumentation header mismatch: {got}")
            header_seen = True
        elif line.startswith("below_root_csv,"):
            values = line.split(",")[1:]
            if len(values) != len(COUNTER_FIELDS):
                raise RuntimeError("instrumentation depth row has wrong column count")
            rows.append(dict(zip(COUNTER_FIELDS, values)))
        elif line.startswith("below_root_total,"):
            values = line.split(",")[1:]
            if len(values) != len(COUNTER_FIELDS):
                raise RuntimeError("instrumentation TOTAL row has wrong column count")
            rows.append(dict(zip(COUNTER_FIELDS, values)))
            total_seen += 1
    if not header_seen or total_seen != 1:
        raise RuntimeError("missing instrumentation header or unique TOTAL row")
    depth_rows = [r for r in rows if r["depth"] != "TOTAL"]
    if [int(r["depth"]) for r in depth_rows] != list(range(20)):
        raise RuntimeError("instrumentation must emit exactly depths 0..19")
    return rows


def validate_rows(rows: list[dict[str, str]], primary: dict[str, str]) -> None:
    depth_rows = [r for r in rows if r["depth"] != "TOTAL"]
    total = next(r for r in rows if r["depth"] == "TOTAL")
    numeric = [f for f in COUNTER_FIELDS if f not in {
        "outcome", "depth", "work_into_win_child", "work_into_loss_child"
    }]
    for r in depth_rows:
        d = int(r["depth"])
        v = {k: int(r[k]) for k in numeric}
        if v["entry_get"] != v["expanded"] + v["entry_hit_loss"] + v["entry_hit_win"]:
            raise RuntimeError(f"depth {d}: entry accounting failed")
        if v["child_get"] != v["unique_children"]:
            raise RuntimeError(f"depth {d}: child_get != unique_children")
        if v["unique_children"] + v["children_duplicate"] != v["children_generated"]:
            raise RuntimeError(f"depth {d}: D4 dedup accounting failed")
        if v["unique_children"] != v["cached_loss_children"] + v["cached_win_children"] + v["unknown_children"]:
            raise RuntimeError(f"depth {d}: child cache split failed")
        if v["put_loss"] + v["put_win"] != v["expanded"]:
            raise RuntimeError(f"depth {d}: put accounting failed")
        if v["win_nodes"] + v["loss_nodes"] != v["expanded"]:
            raise RuntimeError(f"depth {d}: node outcome accounting failed")
        if int(r["late_entry_hit_win"]) > int(r["calls_into_win_child"]):
            raise RuntimeError(f"depth {d}: late WIN hits exceed calls")
        if int(r["late_entry_hit_loss"]) > int(r["calls_into_loss_child"]):
            raise RuntimeError(f"depth {d}: late LOSS hits exceed calls")
    if sum(int(r["expanded"]) for r in depth_rows) != int(primary["visited"]):
        raise RuntimeError("sum(expanded) != solver visited")
    for key in ("visited", "maxdepth", "memo"):
        if total[key] != primary[key]:
            raise RuntimeError(f"TOTAL {key} disagrees with solver row")
    if total["work_into_win_child"] != "NA" or total["work_into_loss_child"] != "NA":
        raise RuntimeError("cross-depth subtree work must remain NA")


def solve_once(binary: Path, state: str, *, shrink: int, load: int,
               timeout: float, instrumented: bool) -> tuple[dict[str, str], tuple[str, ...], list[dict[str, str]]]:
    depth = len(state.split(","))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write(state + "\n")
        task = Path(f.name)
    try:
        cmd = [str(binary), str(task), str(shrink), str(load), "0", "0",
               "--root-depth", str(depth)]
        env = os.environ.copy()
        if instrumented:
            env["KYOEN_BELOW_ROOT_INSTRUMENT"] = "1"
        cp = run(cmd, env=env, timeout=timeout)
    finally:
        task.unlink(missing_ok=True)
    if cp.returncode:
        raise RuntimeError(
            f"solver failed rc={cp.returncode}: {' '.join(cmd)}\nstdout:\n{cp.stdout}\nstderr:\n{cp.stderr}"
        )
    primary = parse_primary(cp.stdout)
    diag = parse_root_diag(cp.stderr)
    counters = parse_counter_rows(cp.stderr) if instrumented else []
    if instrumented:
        validate_rows(counters, primary)
    return primary, diag, counters


def paired_check(state: str, *, shrink: int, load: int,
                 timeout: float) -> tuple[dict[str, str], list[dict[str, str]]]:
    base, base_diag, _ = solve_once(
        BASE_BIN, state, shrink=shrink, load=load, timeout=timeout, instrumented=False
    )
    inst, inst_diag, rows = solve_once(
        INST_BIN, state, shrink=shrink, load=load, timeout=timeout, instrumented=True
    )
    for key in ("outcome", "visited", "maxdepth", "memo"):
        if base[key] != inst[key]:
            raise RuntimeError(f"semantic regression for {state}: {key} {base[key]} != {inst[key]}")
    if base_diag != inst_diag:
        raise RuntimeError(f"root diagnostic regression for {state}: {base_diag} != {inst_diag}")
    return inst, rows


def git_head() -> str:
    cp = run(["git", "rev-parse", "HEAD"], timeout=30.0)
    return cp.stdout.strip() if cp.returncode == 0 else "UNKNOWN"


def validate_smoke(timeout: float) -> dict[str, object]:
    state = state_from_smoke_certificate()
    primary, rows = paired_check(state, shrink=3, load=80, timeout=timeout)
    depth_rows = [r for r in rows if r["depth"] != "TOTAL"]
    active = [r for r in depth_rows if int(r["expanded"]) > 0]
    if not active:
        raise RuntimeError("smoke instrumentation produced no expanded depth")
    return {
        "state": state,
        "stones": len(state.split(",")),
        "outcome": primary["outcome"],
        "visited": int(primary["visited"]),
        "maxdepth": int(primary["maxdepth"]),
        "memo": int(primary["memo"]),
        "active_depths": [int(r["depth"]) for r in active],
    }


def run_four(timeout: float) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "four_parent_raw.csv"
    if out.exists():
        raise RuntimeError(f"refusing to overwrite immutable raw output: {out}")
    all_rows: list[dict[str, str]] = []
    comparisons: list[dict[str, object]] = []
    for state in FROZEN_FOUR:
        t0 = time.monotonic()
        primary, rows = paired_check(state, shrink=0, load=90, timeout=timeout)
        comparisons.append({
            "state": state, "outcome": primary["outcome"],
            "visited": int(primary["visited"]), "maxdepth": int(primary["maxdepth"]),
            "memo": int(primary["memo"]), "wall_seconds_pair": time.monotonic() - t0,
        })
        for row in rows:
            all_rows.append({"state": state, **row})
    fields = ["state", *COUNTER_FIELDS]
    with out.open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(all_rows)
    protocol = {
        "format": 1,
        "git_head": git_head(),
        "frozen_parents": FROZEN_FOUR,
        "fresh_process_per_parent_and_binary": True,
        "baseline_source_sha256": source_digest(False),
        "instrumented_source_sha256": source_digest(True),
        "baseline_binary_sha256": sha256_file(BASE_BIN),
        "instrumented_binary_sha256": sha256_file(INST_BIN),
        "compile": ["g++", "-O2", "-std=c++20"],
        "exact": {"shrink": 0, "load": 90, "max_visited": 0, "max_seconds": 0},
        "semantic_equality_fields": ["outcome", "visited", "maxdepth", "memo", "root_diag"],
        "comparisons": comparisons,
        "raw_csv": str(out.relative_to(REPO_ROOT)),
    }
    (RESULTS / "four_parent_protocol.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-four", action="store_true",
                    help="after smoke validation, run the frozen four exact parents")
    ap.add_argument("--timeout", type=float, default=600.0,
                    help="per-solver timeout for smoke validation")
    ap.add_argument("--exact-timeout", type=float, default=10800.0,
                    help="per-solver timeout for --run-four")
    args = ap.parse_args()

    build()
    smoke = validate_smoke(args.timeout)
    report = {
        "status": "PASS",
        "git_head": git_head(),
        "fresh_process": True,
        "baseline_source_sha256": source_digest(False),
        "instrumented_source_sha256": source_digest(True),
        "smoke": smoke,
    }
    print(json.dumps(report, sort_keys=True))
    if args.run_four:
        print(f"raw={run_four(args.exact_timeout).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

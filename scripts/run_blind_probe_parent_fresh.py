#!/usr/bin/env python3
"""Corrected blind-probe runner for the frozen seven-parent primary rerun.

Primary mode is intentionally narrow:
  * exactly the seven previously evaluated 3-stone LOSS parents;
  * exactly batch0 (20 children), matching the historical primary evaluation;
  * one fresh native solver process per child;
  * 1,000,000 visited-node probe budget;
  * no exact-outcome input is read by this program.

Use --exploratory only after the corrected primary rerun is committed.  It may
run a non-primary parent and/or all batches, but writes a visibly different
`probe_fresh_exploratory_*` filename so it cannot be mistaken for primary data.
"""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / "scripts" / "probe_cert_solver"
DIR = ROOT / "results" / "10x10" / "blind_probe_children"
BUDGET = 1_000_000
SHRINK, LOAD = 3, 80

FROZEN_PRIMARY_PARENTS = {
    "2,9,33",
    "4,9,33",
    "9,12,33",
    "9,19,33",
    "9,23,33",
    "0,31,36",
    "0,36,44",
}


def wsl_path(p: Path) -> str:
    p = p.resolve()
    parts = p.parts
    drive = parts[0].rstrip(":\\").lower()
    return f"/mnt/{drive}/" + "/".join(parts[1:]).replace("\\", "/")


def run_one(state: str) -> dict[str, str]:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, dir=DIR, encoding="utf-8"
    ) as f:
        f.write(state + "\n")
        tmp = Path(f.name)
    try:
        cmd = [
            "wsl", "bash", "-c",
            f"cd {wsl_path(ROOT)} && {wsl_path(SOLVER)} "
            f"{wsl_path(tmp)} {SHRINK} {LOAD} {BUDGET} 0",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        tmp.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"solver rc={proc.returncode} state={state}: "
            f"{proc.stderr[-500:].decode(errors='replace')}"
        )
    rows = list(csv.DictReader(proc.stdout.decode().splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected one row for {state}, got {len(rows)}")
    row = rows[0]
    if row.get("state", "").replace(",", "-") != state.replace(",", "-"):
        raise RuntimeError(f"solver state mismatch: requested={state} got={row.get('state')}")

    outcome = row["outcome"].upper()
    visited = int(row["visited"])
    memo = int(row["memo"])
    if outcome not in {"PROBE", "WIN", "LOSS"}:
        raise RuntimeError(f"unknown probe outcome for {state}: {row['outcome']}")
    if visited <= 0 or visited > BUDGET:
        raise RuntimeError(f"invalid probe visited for {state}: visited={visited}")

    # Exact fresh-Solver invariant. Solver::win() increments visited only after
    # a memo miss, and such a newly visited state can contribute at most one new
    # memo entry. Therefore a genuinely fresh child process must satisfy
    # memo_used <= visited. This catches the historical cross-child accumulation
    # immediately instead of waiting for the post-run verifier.
    if memo < 0 or memo > visited:
        raise RuntimeError(
            f"freshness invariant failed for {state}: memo={memo} visited={visited}"
        )

    # With a visited-only budget, PROBE is emitted by ProbeExhausted exactly at
    # the requested budget. Early exact WIN/LOSS is allowed below the budget.
    if outcome == "PROBE" and visited != BUDGET:
        raise RuntimeError(
            f"PROBE did not hit exact visited budget for {state}: "
            f"visited={visited} budget={BUDGET}"
        )
    return row


def main() -> None:
    args = sys.argv[1:]
    exploratory = "--exploratory" in args
    all_batches = "--all-batches" in args
    args = [a for a in args if a not in {"--exploratory", "--all-batches"}]
    if len(args) != 1:
        raise SystemExit(
            "usage: run_blind_probe_parent_fresh.py <parent> "
            "[--exploratory] [--all-batches]"
        )
    parent = args[0]
    if not exploratory:
        if parent not in FROZEN_PRIMARY_PARENTS:
            raise SystemExit(
                f"primary rerun is frozen to seven parents; refusing {parent}. "
                "Use --exploratory only after primary results are committed."
            )
        if all_batches:
            raise SystemExit("primary rerun is frozen to batch0 only")

    safe = parent.replace(",", "_")
    if all_batches:
        batch_files = sorted(DIR.glob(f"children_{safe}_batch*.txt"))
    else:
        batch0 = DIR / f"children_{safe}_batch0.txt"
        batch_files = [batch0] if batch0.exists() else []
    if not batch_files:
        raise SystemExit(f"no requested batch files for {parent}")

    for bp in batch_files:
        bi = int(bp.stem.split("batch")[-1])
        prefix = "probe_fresh_exploratory" if exploratory else "probe_fresh"
        out = DIR / f"{prefix}_{safe}_batch{bi}_{BUDGET}.csv"
        if out.exists():
            raise SystemExit(f"refusing to overwrite existing raw probe file: {out}")
        states = [
            x.strip() for x in bp.read_text(encoding="utf-8").splitlines()
            if x.strip()
        ]
        if not exploratory and len(states) != 20:
            raise RuntimeError(
                f"frozen batch0 must contain exactly 20 children for {parent}, got {len(states)}"
            )

        rows = [run_one(s) for s in states]
        fields = list(rows[0].keys())
        with out.open("x", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"{parent} batch {bi}: wrote {len(rows)} fresh probes -> {out.name}")


if __name__ == "__main__":
    main()

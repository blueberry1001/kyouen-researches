#!/usr/bin/env python3
"""Solve every unique 5-stone response state in a sealed killer-response manifest.

The input must be completely blind: exact_outcome must be blank on every row.
All unique response states are solved with the same certified settings used by
run_blind_exact_targeted.py (shrink=0, load=90, budget=0).  The input is never
modified.  The completed manifest is written only if every solve succeeds.

Usage:
  python scripts/run_killer_response_exact.py sealed.csv completed.csv [timeout_seconds]
"""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / "scripts" / "probe_cert_solver"
SHRINK = 0
LOAD = 90


def wsl_path(p: Path) -> str:
    p = p.resolve()
    parts = p.parts
    drive = parts[0].rstrip(":\\").lower()
    return f"/mnt/{drive}/" + "/".join(parts[1:]).replace("\\", "/")


def canonical_text(state: str) -> str:
    ids = [int(x) for x in state.replace("-", ",").split(",") if x.strip()]
    if len(ids) != 5 or len(set(ids)) != 5:
        raise ValueError(f"expected five distinct ids: {state!r}")
    return ",".join(map(str, sorted(ids)))


def solve(state: str, timeout: float) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(state + "\n")
        tmp = Path(f.name)
    try:
        cmd = [
            "wsl", "bash", "-c",
            f"cd {wsl_path(ROOT)} && {wsl_path(SOLVER)} {wsl_path(tmp)} {SHRINK} {LOAD} 0 0",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"solver rc={proc.returncode} for {state}: {proc.stderr.decode(errors='replace')[:500]}")
        rows = list(csv.DictReader(io.StringIO(proc.stdout.decode("utf-8", errors="replace"))))
        if len(rows) != 1:
            raise RuntimeError(f"expected exactly one solver row for {state}, got {len(rows)}")
        got = canonical_text(rows[0].get("state", ""))
        if got != state:
            raise RuntimeError(f"solver state mismatch: requested={state} returned={got}")
        outcome = rows[0].get("outcome", "").strip().upper()
        if outcome not in {"WIN", "LOSS"}:
            raise RuntimeError(f"invalid outcome for {state}: {outcome!r}")
        return outcome
    finally:
        tmp.unlink(missing_ok=True)


def main() -> None:
    if len(sys.argv) not in {3, 4}:
        raise SystemExit("Usage: run_killer_response_exact.py sealed.csv completed.csv [timeout_seconds]")
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    timeout = float(sys.argv[3]) if len(sys.argv) == 4 else 600.0
    if src.resolve() == dst.resolve():
        raise SystemExit("refusing to overwrite sealed input")
    if dst.exists():
        raise SystemExit(f"refusing to overwrite existing output: {dst}")

    with src.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    required = {"response_state", "exact_outcome"}
    if not required <= set(fields):
        raise SystemExit(f"missing columns: {sorted(required - set(fields))}")
    if not rows:
        raise SystemExit("empty manifest")
    dirty = [i + 2 for i, r in enumerate(rows) if r["exact_outcome"].strip()]
    if dirty:
        raise SystemExit(f"input is not sealed; exact_outcome already filled on CSV lines {dirty[:10]}")

    normalized = []
    for r in rows:
        try:
            normalized.append(canonical_text(r["response_state"]))
        except ValueError as e:
            raise SystemExit(str(e)) from e
    unique = sorted(set(normalized), key=lambda s: tuple(map(int, s.split(","))))
    print(f"rows={len(rows)} unique_states={len(unique)}")

    outcomes: dict[str, str] = {}
    for i, state in enumerate(unique, 1):
        try:
            outcomes[state] = solve(state, timeout)
        except subprocess.TimeoutExpired as e:
            raise SystemExit(f"timeout after {timeout}s for {state}; no completed manifest written") from e
        except Exception as e:
            raise SystemExit(f"{e}; no completed manifest written") from e
        print(f"[{i}/{len(unique)}] solved")

    completed = []
    for r, state in zip(rows, normalized):
        q = dict(r)
        q["exact_outcome"] = outcomes[state]
        completed.append(q)

    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=dst.name + ".", suffix=".tmp", dir=dst.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with tmp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(completed)
        os.replace(tmp, dst)
    finally:
        tmp.unlink(missing_ok=True)
    print(f"wrote completed manifest atomically to {dst}")


if __name__ == "__main__":
    main()

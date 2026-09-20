#!/usr/bin/env python3
"""Generic one-move split prover for 10x10 kyouen.

Reuses game rules, legal move generation, D4 canonicalization,
search order and win/loss recursion from the existing solver
(kyouen-local-handoff/solver.cpp) and proves an arbitrary parent
state by splitting it into its normalized children.

Usage examples (see task spec):
  python scripts/split_prove.py --parent "9,10,30" --solver kyouen-local-handoff/solver.cpp --results results.csv --workers 8 --shrink 2 --load 80 --timeout 900
  python scripts/split_prove.py --parent "9,29,30" --solver kyouen-local-handoff/solver.cpp --results results.csv --workers 8 --shrink 1 --load 85 --timeout 1800
  python scripts/split_prove.py --parent "3,19,90" --solver kyouen-local-handoff/solver.cpp --results results.csv --workers 4 --shrink 0 --load 90 --timeout 3600

Proof rule:
  - If any normalized child is LOSS, parent is WIN (LOSS witness saved).
  - If every normalized child is WIN, parent is LOSS.
  - TABLE_FULL / TIMEOUT are unresolved and not used as wins/losses.

Each child is solved with an independent memo and saved atomically.
Resume: re-running the same command skips already-decided children.
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

FIELDS = [
    "parent_state",
    "parent_outcome",
    "child_state",
    "child_outcome",
    "proof_method",
    "shrink",
    "load",
    "visited",
    "maxdepth",
    "memo",
    "seconds",
    "wall_seconds",
    "source",
]

STATES_WITHOUT_VERIFIED_WITNESS = set()

WIN_LOSS = {"WIN", "LOSS"}
UNRESOLVED = {"TABLE_FULL", "TIMEOUT", "ERROR"}


def compile_solver(solver_cpp: Path, solver_bin: Path, force: bool = False) -> Path:
    if not force and solver_bin.exists() and solver_bin.stat().st_mtime >= solver_cpp.stat().st_mtime:
        return solver_bin
    solver_bin.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["g++", "-std=c++20", "-O3", "-DNDEBUG", "-march=native", str(solver_cpp), "-o", str(solver_bin)]
    print(f"Compiling: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)
    return solver_bin


def solver_children(solver_bin: Path, parent: str) -> List[Tuple[int, str, int]]:
    cp = subprocess.run(
        [str(solver_bin), "--children", parent],
        text=True,
        capture_output=True,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"--children failed for {parent}: {cp.stderr[:2000]}")
    reader = csv.DictReader(cp.stdout.splitlines())
    out: List[Tuple[int, str, int]] = []
    for row in reader:
        out.append((int(row["index"]), row["state"], int(row["legal_count"])))
    return out


def parse_solver_output(stdout: str) -> Dict[str, str]:
    rows = list(csv.reader(stdout.splitlines()))
    if len(rows) < 2:
        return {"outcome": "ERROR", "visited": "", "maxdepth": "", "memo": "", "seconds": ""}
    row = rows[-1]
    if not row:
        return {"outcome": "ERROR", "visited": "", "maxdepth": "", "memo": "", "seconds": ""}
    # header: state,outcome,visited,maxdepth,memo,seconds
    # The state field itself contains commas, so the last 5 fields are stable.
    return {
        "outcome": row[-5] if len(row) >= 5 else "ERROR",
        "visited": row[-4] if len(row) >= 4 else "",
        "maxdepth": row[-3] if len(row) >= 3 else "",
        "memo": row[-2] if len(row) >= 2 else "",
        "seconds": row[-1] if len(row) >= 1 else "",
    }


def solve_one(solver_bin: Path, state: str, shrink: int, load: int, timeout_s: int) -> Dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="kyouen-split-") as td:
        state_file = Path(td) / "state.txt"
        state_file.write_text(state + "\n", encoding="utf-8")
        started = time.perf_counter()
        try:
            cp = subprocess.run(
                [str(solver_bin), str(state_file), str(shrink), str(load)],
                text=True,
                capture_output=True,
                timeout=timeout_s,
                check=False,
            )
            parsed = parse_solver_output(cp.stdout)
            if parsed["outcome"] not in {"WIN", "LOSS", "TABLE_FULL"}:
                parsed["outcome"] = "ERROR"
                parsed["error_stderr"] = cp.stderr[:4000]
                parsed["error_stdout"] = cp.stdout[:4000]
                parsed["exit_code"] = str(cp.returncode)
            else:
                parsed["exit_code"] = str(cp.returncode)
        except subprocess.TimeoutExpired:
            parsed = {
                "outcome": "TIMEOUT",
                "visited": "",
                "maxdepth": "",
                "memo": "",
                "seconds": "",
                "exit_code": "124",
            }
        parsed["wall_seconds"] = f"{time.perf_counter() - started:.3f}"
        return parsed


def verify_fixed_position(solver_bin: Path) -> None:
    r = solve_one(solver_bin, "2,73,66", 3, 80, 300)
    expected = {"outcome": "WIN", "visited": "10067830", "maxdepth": "18", "memo": "10023329"}
    got = {k: r.get(k, "") for k in expected}
    if got != expected:
        raise RuntimeError(f"solver verification failed: expected {expected}, got {got} (full={r})")
    print(f"Verification OK: 2,73,66 => {got}", flush=True)


def load_results(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return {}
        out: Dict[str, Dict[str, str]] = {}
        for row in reader:
            key = row.get("child_state", "")
            if key:
                out[key] = row
        return out


def save_atomic(path: Path, rows: Dict[str, Dict[str, str]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for k in sorted(rows.keys(), key=lambda s: tuple(int(x) for x in s.split(",")) if s else ()):
            w.writerow({field: rows[k].get(field, "") for field in FIELDS})
    os.replace(tmp, path)


def deduce_parent(
    child_results: Dict[str, Dict[str, str]],
    child_states: List[str],
) -> Tuple[str, str]:
    """Return (parent_outcome, witness_child_state).

    parent_outcome is WIN / LOSS / UNDECIDED.
    """
    unresolved: List[str] = []
    loss_witness = ""
    for s in child_states:
        r = child_results.get(s)
        if r is None:
            unresolved.append(s)
            continue
        o = r.get("child_outcome", "")
        if o == "LOSS" and not loss_witness:
            loss_witness = s
        if o in UNRESOLVED or o not in WIN_LOSS:
            unresolved.append(s)
    if loss_witness:
        return "WIN", loss_witness
    if unresolved:
        return "UNDECIDED", ""
    # All children resolved and none is LOSS -> LOSS
    # Need to confirm every child is WIN
    for s in child_states:
        o = child_results.get(s, {}).get("child_outcome", "")
        if o != "WIN":
            return "UNDECIDED", ""
    return "LOSS", ""


def main() -> None:
    ap = argparse.ArgumentParser(description="Generic one-move split prover")
    ap.add_argument("--parent", required=True, help='Parent state, e.g. "9,10,30"')
    ap.add_argument("--solver", required=True, help="Path to solver.cpp")
    ap.add_argument("--solver-bin", default="", help="Path to solver binary (default: <solver>.bin next to solver.cpp)")
    ap.add_argument("--results", required=True, help="Output CSV path (proof CSV)")
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--shrink", type=int, required=True, choices=(0, 1, 2, 3))
    ap.add_argument("--load", type=int, default=80)
    ap.add_argument("--timeout", type=int, default=900, help="Seconds per child")
    ap.add_argument("--force-compile", action="store_true")
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument("--proof-method", default="", help="proof_method value for CSV")
    args = ap.parse_args()

    solver_cpp = Path(args.solver)
    if not solver_cpp.exists():
        print(f"solver.cpp not found: {solver_cpp}", file=sys.stderr)
        sys.exit(2)
    if args.solver_bin:
        solver_bin = Path(args.solver_bin)
    else:
        solver_bin = solver_cpp.with_suffix(".split_prove_bin")
        if os.name == "nt":
            solver_bin = Path(str(solver_bin) + ".exe")

    compile_solver(solver_cpp, solver_bin, args.force_compile)
    if not args.skip_verify:
        verify_fixed_position(solver_bin)

    parent = args.parent.strip()
    proof_method = args.proof_method or f"split-exact-search shrink={args.shrink} load={args.load}"

    children = solver_children(solver_bin, parent)
    child_states_ordered = [state for _, state, _ in children]
    # Deduplicate by normalized child_state (solver already deduplicates, but verify)
    seen: Dict[str, int] = {}
    deduped: List[str] = []
    for _, state, _ in children:
        if state not in seen:
            seen[state] = 1
            deduped.append(state)
        else:
            print(f"WARNING: duplicate normalized child {state} (should not happen)", file=sys.stderr)
    if len(deduped) != len(child_states_ordered):
        print(f"Note: {len(child_states_ordered)} raw, {len(deduped)} deduped", flush=True)
        child_states_ordered = deduped

    print(f"Parent {parent}: {len(child_states_ordered)} normalized children", flush=True)
    for _, state, lc in children:
        pass

    results_path = Path(args.results)
    rows = load_results(results_path)

    # If parent already decided, still report
    # Filter rows that belong to current parent (in case file reused for multiple parents,
    # key by child_state which is unique per parent set - for safety we keep all).
    # But for deduction we only consider children of this parent.

    pending = [s for s in child_states_ordered if rows.get(s, {}).get("child_outcome") not in WIN_LOSS]
    decided = len(child_states_ordered) - len(pending)
    print(f"Resume: decided={decided}/{len(child_states_ordered)}, pending={len(pending)}, workers={args.workers}, shrink={args.shrink} load={args.load} timeout={args.timeout}", flush=True)

    # Quick parent deduction before solving
    outcome, witness = deduce_parent(rows, child_states_ordered)
    if outcome == "WIN":
        print(f"Already decided: parent {parent} = WIN via child {witness} = LOSS (skip solving)", flush=True)
        return
    if outcome == "LOSS":
        print(f"Already decided: parent {parent} = LOSS (all {len(child_states_ordered)} children WIN)", flush=True)
        return

    def task(child_state: str) -> Dict[str, str]:
        r = solve_one(solver_bin, child_state, args.shrink, args.load, args.timeout)
        return r

    # Submit pending children
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(task, s): s for s in pending}
        for fut in as_completed(futs):
            child_state = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"outcome": "ERROR", "visited": "", "maxdepth": "", "memo": "", "seconds": "", "wall_seconds": "", "error": str(e)}

            outcome_child = r.get("outcome", "ERROR")
            wall = r.get("wall_seconds", "")
            row: Dict[str, str] = {
                "parent_state": parent,
                "parent_outcome": "",
                "child_state": child_state,
                "child_outcome": outcome_child,
                "proof_method": proof_method,
                "shrink": str(args.shrink),
                "load": str(args.load),
                "visited": r.get("visited", ""),
                "maxdepth": r.get("maxdepth", ""),
                "memo": r.get("memo", ""),
                "seconds": r.get("seconds", ""),
                "wall_seconds": wall,
                "source": "split-exact-search",
            }
            rows[child_state] = row
            # Deduce parent outcome so far and fill parent_outcome column
            deduced, wit = deduce_parent(rows, child_states_ordered)
            if deduced == "WIN":
                for k in rows:
                    rows[k]["parent_outcome"] = "WIN"
            elif deduced == "LOSS":
                for k in rows:
                    rows[k]["parent_outcome"] = "LOSS"
            else:
                for k in rows:
                    rows[k]["parent_outcome"] = "UNDECIDED"

            save_atomic(results_path, rows)
            exact = sum(1 for s in child_states_ordered if rows.get(s, {}).get("child_outcome") in WIN_LOSS)
            print(f"[{child_state}] => {outcome_child} wall={wall}s exact={exact}/{len(child_states_ordered)} parent={deduced or 'UNDECIDED'}", flush=True)

            if outcome_child == "LOSS":
                # Witness found: parent is WIN. Cancel remaining.
                print(f"PARENT RESULT: {parent} = WIN via child {child_state} = LOSS", flush=True)
                for other in list(futs.keys()):
                    other.cancel()
                # Do one more atomic save with parent_outcome=WIN already done
                return

    deduced_final, wit_final = deduce_parent(rows, child_states_ordered)
    wins = sum(1 for s in child_states_ordered if rows.get(s, {}).get("child_outcome") == "WIN")
    losses = sum(1 for s in child_states_ordered if rows.get(s, {}).get("child_outcome") == "LOSS")
    unresolved = len(child_states_ordered) - wins - losses
    if deduced_final == "WIN":
        print(f"Stage finished: parent {parent} = WIN (witness {wit_final}), WIN={wins} LOSS={losses} unresolved={unresolved}", flush=True)
    elif deduced_final == "LOSS":
        print(f"Stage finished: parent {parent} = LOSS (all {len(child_states_ordered)} children WIN)", flush=True)
    else:
        print(f"Stage finished: parent {parent} = UNDECIDED, WIN={wins} LOSS={losses} unresolved={unresolved}", flush=True)
        print("Unresolved children remain. Re-run with a larger profile or split recursively.", flush=True)


if __name__ == "__main__":
    main()

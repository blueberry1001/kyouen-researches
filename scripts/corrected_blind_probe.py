#!/usr/bin/env python3
"""Corrected blind-probe experiment: independent per-candidate memo + order swap.

Background (see scripts/audit_blind_probe.py): the b5172a4 blind-validation
probe ran all candidates of a batch through ONE solver process whose memo
table is shared and never cleared, so the recorded `memo` column is the
cumulative table size and memo-desc ranking == reverse input-file order.

This script produces two corrected comparisons WITHOUT touching old results:

  A. INDEPENDENT probe: one solver process per candidate (fresh memo, same
     shrink/load/budget as the original: 3-stone -> 1M visited, shrink 3,
     load 80). Compares independent-memo-desc ranking vs exact outcomes.
  B. ORDER SWAP: same shared-memo binary, but candidates fed in ascending vs
     descending file order; measures rank correlation to prove order bias.

Scope control: batch0 (20 children) of the 7 LOSS parents from the blind
evaluation (0,36,43 excluded: no LOSS in batch0). Each candidate costs ~4-8s
at 1M budget => ~140 probes, fits in the session budget with checkpoints.

Outputs (new files only, resumable via per-row CSV append):
    results/10x10/blind-probe-corrected/independent_probe_<safe>.csv
    results/10x10/blind-probe-corrected/order_desc_<safe>.csv  (shared-memo, reversed input)
    results/10x10/blind-probe-corrected/corrected-analysis.json
    results/10x10/blind-probe-corrected/corrected-parents.csv

Usage:
    python scripts/corrected_blind_probe.py --build          # build solver (needs g++/bash)
    python scripts/corrected_blind_probe.py --independent    # run part A (resumable)
    python scripts/corrected_blind_probe.py --orderswap      # run part B (resumable)
    python scripts/corrected_blind_probe.py --analyze        # write analysis (needs exact CSVs)
"""

import argparse
import csv
import json
import math
import random
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHILDREN_DIR = REPO_ROOT / "results" / "10x10" / "blind_probe_children"
OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-corrected"
SOLVER_SRC = REPO_ROOT / "scripts" / "probe_cert_solver.cpp"
SOLVER_BIN = REPO_ROOT / "tmp-kb" / "probe_native"

PARENTS = ["2,9,33", "4,9,33", "9,12,33", "9,19,33", "9,23,33", "0,31,36", "0,36,44"]
BUDGET = 1_000_000
SHRINK = 3
LOAD = 80

FIELDNAMES = ["parent", "batch", "state", "order", "outcome_probe", "visited",
              "maxdepth", "memo", "seconds"]


def safe_parent(p):
    return p.replace(",", "_")


def run_solver(states_path, extra_args=()):
    cmd = ["bash", "-c",
           f"./tmp-kb/probe_native {states_path} {SHRINK} {LOAD} {BUDGET} 0"]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    dt = time.time() - t0
    return proc, dt


def build():
    cmd = ["bash", "-c", "mkdir -p ./tmp-kb && g++ -O2 -std=c++20 "
                          "-o ./tmp-kb/probe_native ./scripts/probe_cert_solver.cpp && ls -la ./tmp-kb/"]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    print(proc.stdout[-2000:])
    print(proc.stderr[-2000:], file=sys.stderr)
    if proc.returncode != 0:
        sys.exit(proc.returncode)
    print("build OK")


def load_children(parent, batch=0):
    path = CHILDREN_DIR / f"children_{safe_parent(parent)}_batch{batch}.txt"
    return [l.strip() for l in path.read_text().splitlines() if l.strip()]


def load_outcomes(parent, batch=0):
    """Exact outcomes from existing exact_<parent>_batch0.csv (child_state with dashes)."""
    path = CHILDREN_DIR / f"exact_{safe_parent(parent)}_batch{batch}.csv"
    out = {}
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            out[r["state"]] = r["outcome"]
    return out


def existing_states(path):
    if not path.exists():
        return set()
    with path.open(newline="") as f:
        return {r["state"] for r in csv.DictReader(f)}


def cmd_independent():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not SOLVER_BIN.exists():
        print("solver binary missing; run --build first")
        sys.exit(2)
    total_new = 0
    for parent in PARENTS:
        out_path = OUT_DIR / f"independent_probe_{safe_parent(parent)}.csv"
        done = existing_states(out_path)
        children = load_children(parent)
        need = [c for c in children if c.replace(",", "-") not in done and c not in done]
        print(f"{parent}: {len(children)} children, {len(done)} done, {len(need)} to run")
        write_header = not out_path.exists() or out_path.stat().st_size == 0
        with out_path.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if write_header:
                w.writeheader()
            for i, child in enumerate(need):
                tmp = REPO_ROOT / "tmp-kb" / "_single.txt"
                tmp.write_text(child + "\n")
                proc, dt = run_solver("tmp-kb/_single.txt")
                if proc.returncode != 0:
                    print(f"  FAIL {child} rc={proc.returncode}: {proc.stderr[-300:]}")
                    continue
                rows = list(csv.DictReader(proc.stdout.splitlines()))
                assert len(rows) == 1, f"expected 1 row, got {len(rows)}"
                r = rows[0]
                w.writerow({"parent": parent, "batch": 0, "state": r["state"],
                            "order": "independent", "outcome_probe": r["outcome"],
                            "visited": r["visited"], "maxdepth": r["maxdepth"],
                            "memo": r["memo"], "seconds": r["seconds"]})
                f.flush()
                total_new += 1
                print(f"  [{i + 1}/{len(need)}] {child} memo={r['memo']} "
                      f"maxdepth={r['maxdepth']} wall={dt:.1f}s")
    print(f"independent pass done, new rows: {total_new}")


def cmd_orderswap():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not SOLVER_BIN.exists():
        print("solver binary missing; run --build first")
        sys.exit(2)
    for parent in PARENTS:
        children = load_children(parent)
        rev = list(reversed(children))
        out_path = OUT_DIR / f"order_desc_{safe_parent(parent)}.csv"
        if out_path.exists() and out_path.stat().st_size > 0:
            print(f"{parent}: order_desc exists, skipping (delete to re-run)")
            continue
        tmp = REPO_ROOT / "tmp-kb" / f"_rev_{safe_parent(parent)}.txt"
        tmp.write_text("\n".join(rev) + "\n")
        proc, dt = run_solver(f"tmp-kb/_rev_{safe_parent(parent)}.txt")
        if proc.returncode != 0:
            print(f"  FAIL {parent} rc={proc.returncode}: {proc.stderr[-300:]}")
            continue
        rows = list(csv.DictReader(proc.stdout.splitlines()))
        with out_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDNAMES)
            w.writeheader()
            for pos, r in enumerate(rows):
                w.writerow({"parent": parent, "batch": 0, "state": r["state"],
                            "order": f"shared_rev_pos{pos}", "outcome_probe": r["outcome"],
                            "visited": r["visited"], "maxdepth": r["maxdepth"],
                            "memo": r["memo"], "seconds": r["seconds"]})
        print(f"{parent}: reversed shared-memo run done in {dt:.1f}s, rows={len(rows)}")


def spearman(xs, ys):
    n = len(xs)
    assert n == len(ys) and n >= 2
    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def q_first_loss_leq(r, m, loss):
    if loss == 0:
        return 0.0 if r <= m else 1.0
    if r > m:
        return 1.0
    if loss > m - r:
        return 1.0
    return 1.0 - math.comb(m - r, loss) / math.comb(m, loss)


def first_loss(order, outcomes):
    for i, s in enumerate(order, start=1):
        if outcomes.get(s) == "LOSS":
            return i
    return len(order) + 1


def cmd_analyze():
    rng = random.Random(42)
    summary = []
    for parent in PARENTS:
        children = load_children(parent)
        outcomes = load_outcomes(parent)  # dash-state -> WIN/LOSS
        m = len(children)
        dash = [c.replace(",", "-") for c in children]
        loss = sum(1 for s in dash if outcomes.get(s) == "LOSS")

        # A. independent memo ranking (desc), tie-break: file order for determinism.
        ipath = OUT_DIR / f"independent_probe_{safe_parent(parent)}.csv"
        if not ipath.exists():
            print(f"{parent}: independent file missing, skipping in analysis")
            continue
        with ipath.open(newline="") as f:
            irows = list(csv.DictReader(f))
        imemo = {r["state"]: int(r["memo"]) for r in irows}
        assert len(imemo) == m, f"{parent}: independent rows {len(imemo)} != {m}"
        asc_file = sorted(dash, key=lambda s: children.index(s.replace("-", ",")))
        indep_order = sorted(dash, key=lambda s: (-imemo[s], asc_file.index(s)))
        r_indep = first_loss(indep_order, outcomes)

        # Original (buggy) fixed position from stored results CSV.
        with (REPO_ROOT / "results" / "10x10" / "blind-probe-results.csv").open(newline="") as f:
            for r in csv.DictReader(f):
                if r["parent"] == parent:
                    r_orig = int(r["fixed_first_loss_position"])
                    r_solver = int(r["solver_default_first_loss_position"])
                    break

        # B. order-swap: ascending-input shared memo ranking vs descending-input.
        # Ascending input + desc sort == reverse file order (original). Descending
        # input + desc sort == file order. So the swap check is analytic, but we
        # verify with the actual re-run file that memo-desc order == input reverse.
        opath = OUT_DIR / f"order_desc_{safe_parent(parent)}.csv"
        swap_ok = None
        if opath.exists():
            with opath.open(newline="") as f:
                orows = list(csv.DictReader(f))
            # rows are in reversed-input processing order; memo asc in file =>
            # memo-desc ranking == original file order.
            om = [int(r["memo"]) for r in orows]
            swap_ok = all(b > a for a, b in zip(om, om[1:]))
        rev_states = [r["state"] for r in reversed(irows)]  # not used; placeholder

        # Random baseline: exact distribution by enumeration-free simulation (seeded).
        sims = []
        base = dash[:]
        for _ in range(1000):
            s = base[:]
            rng.shuffle(s)
            sims.append(first_loss(s, outcomes))
        sims_sorted = sorted(sims)
        med = sims_sorted[500]
        entry = {
            "parent": parent, "m": m, "l": loss,
            "orig_fixed_rank": r_orig,
            "corrected_indep_rank": r_indep,
            "solver_rank": r_solver,
            "q_orig": round(q_first_loss_leq(r_orig, m, loss), 4),
            "q_indep": round(q_first_loss_leq(r_indep, m, loss), 4),
            "q_solver": round(q_first_loss_leq(r_solver, m, loss), 4),
            "E_R": round((m + 1) / (loss + 1), 4),
            "random_median_sim": med,
            "indep_memo_min": min(imemo.values()),
            "indep_memo_max": max(imemo.values()),
            "indep_memo_spread": max(imemo.values()) - min(imemo.values()),
            "order_swap_reversed_run_monotone": swap_ok,
        }
        summary.append(entry)
        print(f"{parent}: m={m} l={loss} orig={r_orig} indep={r_indep} "
              f"solver={r_solver} E={entry['E_R']} swap_mono={swap_ok}")

    wins = sum(1 for e in summary if e["corrected_indep_rank"] < e["random_median_sim"])
    loss_ = sum(1 for e in summary if e["corrected_indep_rank"] > e["random_median_sim"])
    ties = len(summary) - wins - loss_
    # Sign test on discordant (indep vs median) pairs, two-sided exact binomial.
    n_disc = wins + loss_
    k = min(wins, loss_)
    p_sign = (sum(math.comb(n_disc, i) for i in range(k + 1)) * 2 / 2 ** n_disc
              if n_disc else None)
    if p_sign is not None and p_sign > 1.0:
        p_sign = 1.0
    analysis = {
        "description": "Corrected blind-probe: independent per-candidate memo + order swap",
        "board": "10x10", "budget": BUDGET, "shrink": SHRINK, "load": LOAD,
        "parents": summary,
        "aggregate": {"n": len(summary), "indep_better_than_random_median": wins,
                      "worse": loss_, "tie": ties, "sign_test_two_sided_p": p_sign},
    }
    with (OUT_DIR / "corrected-analysis.json").open("w") as f:
        json.dump(analysis, f, indent=2)
    with (OUT_DIR / "corrected-parents.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["parent", "m", "l", "orig_fixed_rank",
                                          "corrected_indep_rank", "solver_rank", "q_orig",
                                          "q_indep", "q_solver", "E_R", "random_median_sim",
                                          "order_swap_reversed_run_monotone",
                                          "indep_memo_min", "indep_memo_max",
                                          "indep_memo_spread"])
        w.writeheader()
        w.writerows(summary)
    print(f"sign test: better={wins} worse={loss_} tie={ties} p={p_sign}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--independent", action="store_true")
    ap.add_argument("--orderswap", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args()
    if args.build:
        build()
    if args.independent:
        cmd_independent()
    if args.orderswap:
        cmd_orderswap()
    if args.analyze:
        cmd_analyze()
    if not (args.build or args.independent or args.orderswap or args.analyze):
        ap.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()

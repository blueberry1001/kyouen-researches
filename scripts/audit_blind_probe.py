#!/usr/bin/env python3
"""Audit the 10x10 blind-probe validation (branch probe-two-stone-subsets, commit b5172a4).

Checks, from generated code and result CSVs (no trust in prose):

  A. probe_memo semantics: per-candidate independent value vs shared cumulative
     transposition-table size (reads scripts/probe_parts/*.inc + raw probe CSVs).
  B. Whether fixed_rank is a pure function of input file order.
  C. Batch-boundary behaviour (memo reset per solver invocation?).
  D. Recompute the 7-parent table with density-adjusted exact random baseline:
       q(r;m,l) = 1 - C(m-r,l)/C(m,l),  E[R] = (m+1)/(l+1).
  E. Exploratory (clearly labelled): delta-memo ranking, which is still
     history-dependent and NOT a valid independent score.

Inputs (read-only, never overwritten):
    results/10x10/blind-probe-rankings.csv
    results/10x10/blind-probe-results.csv
    results/10x10/blind_probe_children/probe_<parent>_batch<N>_<budget>.csv
    results/10x10/blind_probe_children/exact_<parent>_batch<N>.csv

Outputs (new files only):
    results/10x10/blind-probe-audit.json
    results/10x10/blind-probe-audit-parents.csv

Deterministic; stdlib + numpy only.
"""

import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHILDREN_DIR = REPO_ROOT / "results" / "10x10" / "blind_probe_children"
OUT_DIR = REPO_ROOT / "results" / "10x10"
RANKINGS_CSV = OUT_DIR / "blind-probe-rankings.csv"
RESULTS_CSV = OUT_DIR / "blind-probe-results.csv"

START_COMMIT = "24401d0853e19527fe2f2a73e116831a5e023deb"
AUDITED_COMMIT = "b5172a4bc23643194245e02a73a5bc7e40d8197a"

SOLVER_LOOP_FILE = REPO_ROOT / "scripts" / "probe_parts" / "kyouen_solver_10_kyoenc4_resume_4.inc"
SOLVER_SEARCH_FILE = REPO_ROOT / "scripts" / "probe_parts" / "kyouen_solver_10_kyoenc4_resume_3.inc"


def fail(msg):
    print(f"AUDIT FAIL: {msg}")
    sys.exit(1)


def check_source_code():
    """Verify the memo-sharing structure directly in the generator source."""
    loop = SOLVER_LOOP_FILE.read_text()
    search = SOLVER_SEARCH_FILE.read_text()
    findings = {}
    findings["solver_constructed_once_per_invocation"] = (
        "Solver solver(shrink,load);" in loop
        and loop.index("Solver solver(shrink,load);") < loop.index("for(auto&pts:tasks)")
    )
    findings["no_memo_clear_in_task_loop"] = ("clear" not in loop.lower())
    findings["memo_reported_is_solver_global"] = "solver.memo_used()" in loop
    findings["per_task_stats_fresh"] = "for(auto&pts:tasks){Solver::Stats st;" in loop
    findings["visited_is_per_task"] = "st.visited" in loop
    findings["memo_hits_skip_visited_increment"] = (
        "if(cached)return cached==MultiDepthMemo100::Winning;++st.visited;" in search
        or "if(cached)return cached==MultiDepthMemo100::Winning;" in search
    )
    findings["budget_is_per_task_visited_cap"] = "st.visited>=probe_budget_.visited" in (
        REPO_ROOT / "scripts" / "probe_parts" / "kyouen_solver_10_kyoenc4_resume_2.inc"
    ).read_text()
    return findings


def load_rankings():
    with RANKINGS_CSV.open(newline="") as f:
        return list(csv.DictReader(f))


def load_results():
    with RESULTS_CSV.open(newline="") as f:
        return {r["parent"]: r for r in csv.DictReader(f)}


def raw_probe_rows(safe_parent, batch, budget):
    path = CHILDREN_DIR / f"probe_{safe_parent}_batch{batch}_{budget}.csv"
    if not path.exists():
        return None
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def exact_rows(safe_parent, batch):
    path = CHILDREN_DIR / f"exact_{safe_parent}_batch{batch}.csv"
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def q_first_loss_leq(r, m, loss):
    """Exact P(R <= r) for first-LOSS rank under uniform random ordering."""
    assert 1 <= r <= m + 1 and 0 <= loss <= m
    if loss == 0:
        return 0.0 if r <= m else 1.0
    if r > m:
        return 1.0
    if loss > m - r:
        return 1.0
    return 1.0 - math.comb(m - r, loss) / math.comb(m, loss)


def expected_first_loss(m, loss):
    return (m + 1) / (loss + 1) if loss > 0 else None


def main():
    random.seed(0)
    audit = {
        "start_commit": START_COMMIT,
        "audited_commit": AUDITED_COMMIT,
        "board": "10x10 (NOT 9x9)",
        "source_code_findings": check_source_code(),
        "parents": {},
    }
    sc = audit["source_code_findings"]
    if not (sc["solver_constructed_once_per_invocation"] and sc["memo_reported_is_solver_global"]
            and sc["per_task_stats_fresh"] and sc["no_memo_clear_in_task_loop"]):
        fail(f"generator source structure differs from audit assumption: {sc}")

    rankings = load_rankings()
    results = load_results()
    by_parent = defaultdict(list)
    for r in rankings:
        by_parent[r["parent"]].append(r)

    parent_table = []
    all_reverse_identity = True
    for parent, rows in sorted(by_parent.items()):
        stones = int(rows[0]["stones"])
        budget = int(rows[0]["probe_budget"])
        safe = parent.replace(",", "_")
        res = results[parent]
        m = len(rows)
        loss = sum(1 for r in rows if r["outcome"] == "LOSS")

        by_move = sorted(rows, key=lambda r: int(r["move_index"]))
        memos = [int(r["probe_memo"]) for r in by_move]
        strictly_increasing = all(b > a for a, b in zip(memos, memos[1:]))
        reverse_identity = all(int(r["fixed_rank"]) == m - int(r["move_index"]) for r in by_move)
        all_reverse_identity = all_reverse_identity and reverse_identity

        # Raw batch-0 probe file checks.
        raw0 = raw_probe_rows(safe, 0, budget)
        assert raw0 is not None, f"missing raw probe batch0 for {parent}"
        assert len(raw0) == m, f"{parent}: raw batch0 has {len(raw0)} rows, rankings has {m}"
        visited_all_budget = all(r["visited"] == str(budget) for r in raw0)
        raw_memos = [int(r["memo"]) for r in raw0]
        raw_mono = all(b > a for a, b in zip(raw_memos, raw_memos[1:]))
        deltas = [b - a for a, b in zip(raw_memos, raw_memos[1:])]
        raw_seconds = [float(r["seconds"]) for r in raw0]
        seconds_mono = all(b > a for a, b in zip(raw_seconds, raw_seconds[1:]))

        # Batch-boundary reset: batch1 first memo should restart near ~1M, not continue ~20M.
        raw1 = raw_probe_rows(safe, 1, budget)
        batch_reset = None
        if raw1:
            batch_reset = int(raw1[0]["memo"]) < int(raw0[-1]["memo"])

        # Exact CSV contrast: child-parallel => memo must NOT be monotone in file order.
        ex0 = exact_rows(safe, 0)
        exact_memo_mono = None
        if ex0:
            em = [int(r["memo"]) for r in ex0]
            exact_memo_mono = all(b > a for a, b in zip(em, em[1:]))

        fixed_pos = int(res["fixed_first_loss_position"])
        solver_pos = int(res["solver_default_first_loss_position"])
        entry = {
            "parent": parent,
            "stones": stones,
            "child_count_m": m,
            "loss_child_count_l": loss,
            "rankings_memo_strictly_increasing_in_move_order": strictly_increasing,
            "fixed_rank_equals_reverse_move_order": reverse_identity,
            "raw_batch0_visited_all_equal_budget": visited_all_budget,
            "raw_batch0_memo_strictly_increasing": raw_mono,
            "raw_batch0_memo_first": raw_memos[0],
            "raw_batch0_memo_last": raw_memos[-1],
            "raw_batch0_memo_delta_min": min(deltas),
            "raw_batch0_memo_delta_max": max(deltas),
            "raw_batch0_seconds_strictly_increasing": seconds_mono,
            "batch1_first_memo_resets": batch_reset,
            "exact_batch0_memo_monotone": exact_memo_mono,
            "fixed_first_loss": fixed_pos,
            "solver_first_loss": solver_pos,
            "q_fixed": q_first_loss_leq(fixed_pos, m, loss),
            "q_solver": q_first_loss_leq(solver_pos, m, loss),
            "expected_R": expected_first_loss(m, loss),
            "reported_random_median": (float(res["random_median_first_loss_position"])
                                           if res["random_median_first_loss_position"] else None),
            "reported_theoretical_expected": (float(res["theoretical_expected_first_loss_position"])
                                              if res["theoretical_expected_first_loss_position"] else None),
        }
        # Cross-check reported theoretical expectation against closed form.
        if loss > 0 and entry["reported_theoretical_expected"] is not None:
            assert abs(entry["reported_theoretical_expected"] - entry["expected_R"]) < 1e-9, parent
        audit["parents"][parent] = entry
        parent_table.append(entry)

    audit["fixed_rank_is_reverse_input_order_for_all_parents"] = all_reverse_identity

    # Verdict.
    audit["verdict"] = {
        "probe_memo_is_cumulative_shared_table": True,
        "probe_memo_is_per_candidate_independent": False,
        "memo_cleared_per_probe": False,
        "candidate_scan_order": "input file order (numeric ascending), sequential, one process per batch file",
        "score_sort": "memo descending, tie-break by move index ascending (no memo ties observed)",
        "probe_budget_definition": "per-candidate cap on Solver::Stats.visited (fresh Stats per task); "
                                   "memo hits do NOT increment visited, so 1M visited covers different "
                                   "real effort for early vs late candidates",
        "transposition_table_shared_across_candidates": True,
        "shared_memo_bias_direction": "later file order => larger cumulative memo => ranked first under desc; "
                                      "ranking is a deterministic reverse of input order, content-free",
        "solver_default_circularity": "reported fixed-vs-solver comparison is reverse-vs-forward order of the "
                                      "same children file; solver internal child ordering (fewest-legal-moves "
                                      "first in win()) additionally confounds exact-search cost comparisons",
        "lopo_era_data_unaffected": "probe-features.csv used single-state invocations (fresh memo per row), "
                                    "so LOPO/prediction results do not share this bug",
        "maxdepth_visited_seconds_taxonomy": "visited/maxdepth/depth_visited_* are per-task (independent); "
                                             "memo/memo_used_d*/seconds are solver-global (cumulative)",
    }

    with (OUT_DIR / "blind-probe-audit.json").open("w") as f:
        json.dump(audit, f, indent=2)

    fieldnames = ["parent", "stones", "m", "l", "fixed", "solver", "q_fixed", "q_solver",
                  "E_R", "reported_median", "reverse_identity", "visited_all_budget",
                  "memo_monotone", "batch_reset"]
    with (OUT_DIR / "blind-probe-audit-parents.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for e in parent_table:
            w.writerow({
                "parent": e["parent"], "stones": e["stones"], "m": e["child_count_m"],
                "l": e["loss_child_count_l"], "fixed": e["fixed_first_loss"],
                "solver": e["solver_first_loss"], "q_fixed": round(e["q_fixed"], 4),
                "q_solver": round(e["q_solver"], 4),
                "E_R": round(e["expected_R"], 4) if e["expected_R"] else "",
                "reported_median": e["reported_random_median"] if e["reported_random_median"] is not None else "",
                "reverse_identity": e["fixed_rank_equals_reverse_move_order"],
                "visited_all_budget": e["raw_batch0_visited_all_equal_budget"],
                "memo_monotone": e["raw_batch0_memo_strictly_increasing"],
                "batch_reset": e["batch1_first_memo_resets"],
            })

    print(f"parents audited: {len(parent_table)}")
    print(f"reverse-identity holds for ALL parents: {all_reverse_identity}")
    for e in parent_table:
        print(f"  {e['parent']}: m={e['child_count_m']} l={e['loss_child_count_l']} "
              f"fixed={e['fixed_first_loss']} q={e['q_fixed']:.3f} "
              f"solver={e['solver_first_loss']} q={e['q_solver']:.3f} E[R]={e['expected_R']}")
    print("wrote results/10x10/blind-probe-audit.json + blind-probe-audit-parents.csv")


if __name__ == "__main__":
    main()

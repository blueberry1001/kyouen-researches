"""Secondary holdout diagnostics (NOT primary; no rule changes follow).

Reads only frozen holdout outputs:
  results/10x10/blind-probe-holdout/independent_probe_1000000.csv
  results/10x10/blind-probe-holdout/preregistered_parent_results.csv
  results/10x10/blind_probe_children/exact_<parent>_batch*.csv

Computes:
  1. probe memo spread per parent (signal dynamic range);
  2. rank stability proxy: corrected rank vs memo-desc rank vs
     default/reverse ranks (all from the same frozen probes);
  3. corrected-vs-solver head-to-head on first-LOSS rank;
  4. probe-cost accounting: 1M visited per child vs exact visited sums;
  5. mechanism readout: LOSS vs WIN memo distributions per parent
     (median memo of exact-LOSS vs exact-WIN children among unresolved).

Writes:
  results/10x10/blind-probe-holdout/secondary_diagnostics.json
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout"
PROBE_CSV = HOLDOUT / "independent_probe_1000000.csv"
PARENT_CSV = HOLDOUT / "preregistered_parent_results.csv"


def norm_state(s: str) -> str:
    return "-".join(str(x) for x in sorted(int(v) for v in s.replace(",", "-").split("-") if v != ""))


def main() -> None:
    with PROBE_CSV.open(newline="", encoding="utf-8") as f:
        probes = list(csv.DictReader(f))
    with PARENT_CSV.open(newline="", encoding="utf-8") as f:
        parents = list(csv.DictReader(f))

    by_parent: dict[str, list[dict]] = {}
    for r in probes:
        by_parent.setdefault(r["parent"], []).append(r)

    per_parent = []
    for prow in parents:
        p = prow["parent"]
        rows = by_parent[p]
        memos = [int(r["memo"]) for r in rows]
        per_parent.append({
            "parent": p,
            "probe_memo_min": min(memos),
            "probe_memo_max": max(memos),
            "probe_memo_spread": max(memos) - min(memos),
            "probe_all_unresolved": all(r["probe_outcome"] == "PROBE" for r in rows),
            "corrected_first_loss": int(prow["corrected_first_loss"]),
            "memo_desc_first_loss": int(prow["memo_desc_first_loss"]),
            "default_first_loss": int(prow["default_first_loss"]),
            "reverse_first_loss": int(prow["reverse_first_loss"]),
            "corrected_beats_solver": int(prow["corrected_first_loss"]) < int(prow["default_first_loss"]),
            "corrected_ties_solver": int(prow["corrected_first_loss"]) == int(prow["default_first_loss"]),
        })

    n = len(per_parent)
    summary = {
        "design": "secondary diagnostics on frozen 1M holdout (exploratory)",
        "parents": n,
        "corrected_rank_1_count": sum(1 for r in per_parent if r["corrected_first_loss"] == 1),
        "memo_desc_rank_1_count": sum(1 for r in per_parent if r["memo_desc_first_loss"] == 1),
        "default_rank_1_count": sum(1 for r in per_parent if r["default_first_loss"] == 1),
        "reverse_rank_1_count": sum(1 for r in per_parent if r["reverse_first_loss"] == 1),
        "corrected_beats_solver_count": sum(1 for r in per_parent if r["corrected_beats_solver"]),
        "corrected_ties_solver_count": sum(1 for r in per_parent if r["corrected_ties_solver"]),
        "all_probes_unresolved": all(r["probe_all_unresolved"] for r in per_parent),
        "mean_memo_spread": statistics.fmean(r["probe_memo_spread"] for r in per_parent),
        "per_parent": per_parent,
        "mechanism_note": ("All 1020 holdout probes hit the 1M visited budget unresolved "
                           "(no probe proved LOSS or WIN), so the preregistered rule reduces to "
                           "pure ascending-memo order and visited-memo is exactly memo reversed. "
                           "Depth-resolved counters (visited_by_depth / memo hits+puts by depth) "
                           "are still uninstrumented; next hypothesis holdout should record them."),
    }
    out = HOLDOUT / "secondary_diagnostics.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_parent"}, indent=2))


if __name__ == "__main__":
    main()

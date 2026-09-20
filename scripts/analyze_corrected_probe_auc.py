#!/usr/bin/env python3
"""Exploratory candidate-level discrimination for corrected 10x10 probes.

For each of the seven hypothesis-generating LOSS parents, join the stored
independent fixed-budget probe to exact child outcomes and measure whether
larger ``visited - memo`` (equivalently smaller memo for unresolved 1M probes)
ranks LOSS children above WIN children.

This is exploratory: the score direction was selected after inspecting these
parents.  Results must not be presented as confirmatory evidence.  The main
purpose is to freeze a better candidate-level endpoint before testing on a new
blind set.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORR = ROOT / "results" / "10x10" / "blind-probe-corrected"
CHILD = ROOT / "results" / "10x10" / "blind_probe_children"
PARENTS = [
    "2,9,33", "4,9,33", "9,12,33", "9,19,33",
    "9,23,33", "0,31,36", "0,36,44",
]


def safe(parent: str) -> str:
    return parent.replace(",", "_")


def read_csv(path: Path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def auc_loss_high(score, exact):
    """Mann-Whitney AUC: P(score(LOSS)>score(WIN)) + 1/2 ties."""
    losses = [s for s in score if exact[s] == "LOSS"]
    wins = [s for s in score if exact[s] == "WIN"]
    if not losses or not wins:
        return None, 0, 0, 0.0
    concordant = 0.0
    for l in losses:
        for w in wins:
            if score[l] > score[w]:
                concordant += 1.0
            elif score[l] == score[w]:
                concordant += 0.5
    pairs = len(losses) * len(wins)
    return concordant / pairs, len(losses), len(wins), concordant


def main():
    output = []
    total_pairs = 0
    total_concordant = 0.0

    for parent in PARENTS:
        probe = read_csv(CORR / f"independent_probe_{safe(parent)}.csv")
        exact_rows = read_csv(CHILD / f"exact_{safe(parent)}_batch0.csv")
        exact = {r["state"]: r["outcome"] for r in exact_rows}
        assert set(r["state"] for r in probe) == set(exact)

        # A solved bounded probe is already direct outcome information and should
        # not be folded into the unresolved-search structural score.  Report the
        # unresolved-only AUC separately; this also avoids treating an early WIN
        # with a tiny memo as strongly LOSS-like.
        unresolved = [r for r in probe if r["outcome_probe"] == "PROBE"]
        score = {
            r["state"]: int(r["visited"]) - int(r["memo"])
            for r in unresolved
        }
        exact_unresolved = {s: exact[s] for s in score}
        auc, n_loss, n_win, concordant = auc_loss_high(score, exact_unresolved)
        pairs = n_loss * n_win
        total_pairs += pairs
        total_concordant += concordant

        loss_scores = [score[s] for s in score if exact[s] == "LOSS"]
        win_scores = [score[s] for s in score if exact[s] == "WIN"]
        output.append({
            "parent": parent,
            "unresolved": len(score),
            "loss": n_loss,
            "win": n_win,
            "auc": "" if auc is None else f"{auc:.9f}",
            "loss_mean_redundancy": "" if not loss_scores else f"{sum(loss_scores)/len(loss_scores):.3f}",
            "win_mean_redundancy": "" if not win_scores else f"{sum(win_scores)/len(win_scores):.3f}",
            "probe_solved_loss": sum(r["outcome_probe"] == "LOSS" for r in probe),
            "probe_solved_win": sum(r["outcome_probe"] == "WIN" for r in probe),
            "pairwise_concordant": concordant,
            "pairwise_total": pairs,
        })

    out = CORR / "probe-candidate-auc.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)

    print("parent-level unresolved-only AUC (higher visited-memo => LOSS):")
    for row in output:
        print(row)
    pooled = total_concordant / total_pairs if total_pairs else float("nan")
    print(f"pair-weighted stratified concordance={pooled:.9f} ({total_concordant}/{total_pairs})")
    print("NOTE: exploratory/post-hoc; use only to define a future blind endpoint.")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

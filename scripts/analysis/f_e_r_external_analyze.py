#!/usr/bin/env python3
"""Preregistered analysis for the F-E R-external 4-stone holdout.

Applies the frozen decision rules in docs/10X10_F_E_R_EXTERNAL_HOLDOUT_PREREG.md.
Does not re-tune sampling. Compares direction only against the R-internal F-E
reference numbers from analysis/f-e-exact-label-test.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "10x10" / "f-e-r-external-holdout"
OUT_CSV = OUT_DIR / "exact_outcomes.csv"
SUMMARY = OUT_DIR / "holdout_summary.json"

# Frozen R-internal F-E reference (do not refit on holdout).
R_INTERNAL = {
    "loss_n": 12,
    "win_n": 58,
    "loss_mean_sigma": 8732.833333333334,
    "win_mean_sigma": 8285.275862068966,
    "auc": 0.7593389830508475,
    "rank_biserial": 0.5186779661016949,
    "hedges_g": 0.957284,
    "direction": "LOSS has higher sigma_d",
}


def percentile_rank_auc(loss: list[float], win: list[float]) -> tuple[float, float]:
    if not loss or not win:
        return float("nan"), float("nan")
    gt = eq = 0
    for a in loss:
        for b in win:
            if a > b:
                gt += 1
            elif a == b:
                eq += 1
    auc = (gt + 0.5 * eq) / (len(loss) * len(win))
    return auc, 2.0 * auc - 1.0


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def median(xs: list[float]) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return float(s[mid]) if n % 2 else 0.5 * (s[mid - 1] + s[mid])


def exact_upper_tail(scores: list[int], selected_n: int, observed_sum: int) -> dict:
    """Exact random-label upper tail on fixed LOSS count (descriptive only)."""
    if selected_n <= 0 or selected_n > len(scores):
        return {"p": None, "tail": None, "denom": None}
    dp = [defaultdict(int) for _ in range(selected_n + 1)]
    dp[0][0] = 1
    for score in scores:
        for k in range(selected_n - 1, -1, -1):
            for total, ways in list(dp[k].items()):
                dp[k + 1][total + score] += ways
    tail = sum(ways for total, ways in dp[selected_n].items() if total >= observed_sum)
    denom = math.comb(len(scores), selected_n)
    return {"p": tail / denom if denom else None, "tail": tail, "denom": denom}


def main() -> None:
    rows = list(csv.DictReader(OUT_CSV.open(newline="", encoding="utf-8")))
    if len(rows) != 36:
        raise SystemExit(f"expected 36 outcome rows, got {len(rows)}")

    exact = [r for r in rows if r["outcome"] in ("WIN", "LOSS")]
    nonexact = [r for r in rows if r["outcome"] not in ("WIN", "LOSS")]
    loss = [r for r in exact if r["outcome"] == "LOSS"]
    win = [r for r in exact if r["outcome"] == "WIN"]

    loss_s = [float(r["sigma_d"]) for r in loss]
    win_s = [float(r["sigma_d"]) for r in win]
    all_s = [float(r["sigma_d"]) for r in exact]
    labels = [1 if r["outcome"] == "LOSS" else 0 for r in exact]

    auc, rb = percentile_rank_auc(loss_s, win_s)

    by_stratum = {"low": [0, 0], "middle": [0, 0], "high": [0, 0]}  # [loss, total]
    for r in exact:
        st = r["stratum"]
        if st not in by_stratum:
            continue
        by_stratum[st][1] += 1
        if r["outcome"] == "LOSS":
            by_stratum[st][0] += 1

    def p_loss(st: str) -> float | None:
        l, n = by_stratum[st]
        return (l / n) if n else None

    p_high = p_loss("high")
    p_low = p_loss("low")

    if loss:
        observed_sum = int(sum(loss_s))
        perm = exact_upper_tail([int(x) for x in all_s], len(loss), observed_sum)
    else:
        perm = {"p": None, "tail": None, "denom": None}

    L = len(loss)
    nonexact_rate = len(nonexact) / 36.0

    mean_loss = mean(loss_s)
    mean_win = mean(win_s)
    mean_diff = mean_loss - mean_win if loss and win else float("nan")

    # Decision rules (frozen).
    sparse_extreme = (
        p_high == 0
        and p_low == 0
        and all(r["stratum"] == "middle" for r in loss)
        and L > 0
    )

    if L < 3 or nonexact_rate > 0.20 or sparse_extreme:
        decision = "inconclusive"
        reasons = []
        if L < 3:
            reasons.append(f"LOSS count L={L} < 3")
        if nonexact_rate > 0.20:
            reasons.append(f"non-exact rate {nonexact_rate:.2%} > 20%")
        if sparse_extreme:
            reasons.append("all LOSS confined to middle with 0 LOSS in both extremes")
    else:
        support_all = (
            auc > 0.5
            and (p_high is not None and p_low is not None and p_high >= p_low)
            and (not (loss and win) or mean_loss > mean_win)
        )
        if support_all:
            decision = "reversal_supported_outside_R"
            reasons = ["AUC>0.5 and P(LOSS|high)>=P(LOSS|low) and mean(LOSS)>mean(WIN)"]
        else:
            decision = "reversal_not_supported_outside_R"
            reasons = []
            if not (auc > 0.5):
                reasons.append(f"AUC={auc:.6f} <= 0.5")
            if p_high is not None and p_low is not None and p_high < p_low:
                reasons.append(f"P(LOSS|high)={p_high:.4f} < P(LOSS|low)={p_low:.4f}")
            if loss and win and not (mean_loss > mean_win):
                reasons.append(f"mean(LOSS)={mean_loss:.3f} <= mean(WIN)={mean_win:.3f}")

    direction_note = "same_as_R_internal" if (auc == auc and auc > 0.5) else "opposite_or_null"

    summary = {
        "prereg": "docs/10X10_F_E_R_EXTERNAL_HOLDOUT_PREREG.md",
        "decision": decision,
        "decision_reasons": reasons,
        "n_total": 36,
        "n_exact": len(exact),
        "n_loss": L,
        "n_win": len(win),
        "n_nonexact": len(nonexact),
        "nonexact_outcomes": {r["state"] if "state" in r else r["raw_state"]: r["outcome"] for r in nonexact},
        "sigma_d": {
            "loss_mean": mean_loss,
            "loss_median": median(loss_s),
            "loss_min": min(loss_s) if loss_s else None,
            "loss_max": max(loss_s) if loss_s else None,
            "win_mean": mean_win,
            "win_median": median(win_s),
            "win_min": min(win_s) if win_s else None,
            "win_max": max(win_s) if win_s else None,
            "mean_diff_loss_minus_win": mean_diff,
        },
        "auc": auc,
        "rank_biserial": rb,
        "p_loss_by_stratum": {
            "low": {"p": p_loss("low"), "loss": by_stratum["low"][0], "n": by_stratum["low"][1]},
            "middle": {"p": p_loss("middle"), "loss": by_stratum["middle"][0], "n": by_stratum["middle"][1]},
            "high": {"p": p_loss("high"), "loss": by_stratum["high"][0], "n": by_stratum["high"][1]},
        },
        "p_loss_high_minus_low": (
            (p_high - p_low) if (p_high is not None and p_low is not None) else None
        ),
        "exact_random_label_upper_tail_on_loss_sum": perm,
        "r_internal_reference": R_INTERNAL,
        "direction_vs_r_internal": direction_note,
        "notes": [
            "Holdout is stratified by sigma_d; permutation p is descriptive only.",
            "No sampling rule changes after outcomes were observed.",
        ],
    }

    # Fix nonexact key naming
    summary["nonexact_states"] = [
        {"raw_state": r["raw_state"], "outcome": r["outcome"]} for r in nonexact
    ]
    summary.pop("nonexact_outcomes", None)

    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("=== F-E R-external holdout ===")
    print(f"decision: {decision}")
    for reason in reasons:
        print(f"  - {reason}")
    print(f"exact n={len(exact)}  LOSS={L}  WIN={len(win)}  nonexact={len(nonexact)}")
    print(
        f"mean Σd  LOSS={mean_loss:.3f}  WIN={mean_win:.3f}  diff={mean_diff:.3f}"
    )
    print(f"median Σd LOSS={median(loss_s):.3f}  WIN={median(win_s):.3f}")
    print(f"AUC={auc:.6f}  rank-biserial={rb:.6f}")
    print(
        "P(LOSS|stratum): "
        f"low={p_loss('low')} ({by_stratum['low']})  "
        f"middle={p_loss('middle')} ({by_stratum['middle']})  "
        f"high={p_loss('high')} ({by_stratum['high']})"
    )
    print(f"P(LOSS|high)-P(LOSS|low) = {summary['p_loss_high_minus_low']}")
    print(f"exact random-label p (LOSS sum upper) = {perm}")
    print(f"R-internal AUC={R_INTERNAL['auc']}  direction={direction_note}")
    print(f"wrote {SUMMARY}")


if __name__ == "__main__":
    main()

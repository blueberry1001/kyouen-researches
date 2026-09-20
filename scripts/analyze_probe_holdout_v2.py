#!/usr/bin/env python3
"""Analyze clean holdout V2 with the ranking and endpoints frozen before outcomes."""

from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from holdout_v2_common import cells, legal_children, load_parents, load_tasks, task_set_digest  # noqa: E402

OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout-v2"
PARENT_CSV = OUT_DIR / "preregistered_v2_parent_results.csv"
SUMMARY_JSON = OUT_DIR / "preregistered_v2_summary.json"


def move_of(parent: str, child: str) -> int:
    p = set(cells(parent)); c = set(cells(child)); extra = c - p
    if len(extra) != 1 or not p < c:
        raise RuntimeError(f"not a one-move child: {parent} -> {child}")
    return next(iter(extra))


def load_unique_rows(pattern: str, outcome_field: str) -> dict[tuple[str, str], dict[str, str]]:
    paths = sorted(OUT_DIR.glob(pattern))
    if not paths:
        raise RuntimeError(f"no files matched {OUT_DIR / pattern}")
    rows: dict[tuple[str, str], dict[str, str]] = {}
    seen_global: set[int] = set()
    for path in paths:
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (row["parent"].strip(), row["state"].replace("-", ","))
                gi = int(row["global_index"])
                if key in rows or gi in seen_global:
                    raise RuntimeError(f"duplicate row/global index in {path}: {key} i={gi}")
                rows[key] = row; seen_global.add(gi)
                value = row[outcome_field].strip().upper()
                allowed = {"LOSS", "WIN"} if outcome_field == "outcome" else {"LOSS", "PROBE", "WIN"}
                if value not in allowed:
                    raise RuntimeError(f"bad {outcome_field}={value} in {path}")
    return rows


def verify_coverage(probes: dict[tuple[str, str], dict[str, str]], exact: dict[tuple[str, str], dict[str, str]]) -> None:
    tasks = load_tasks()
    expected = {(p, s): i for i, (p, _b, _pos, s) in enumerate(tasks)}
    if set(probes) != set(expected):
        raise RuntimeError(f"probe coverage mismatch: missing={len(set(expected)-set(probes))} extra={len(set(probes)-set(expected))}")
    if set(exact) != set(expected):
        raise RuntimeError(f"exact coverage mismatch: missing={len(set(expected)-set(exact))} extra={len(set(exact)-set(expected))}")
    for key, i in expected.items():
        if int(probes[key]["global_index"]) != i or int(exact[key]["global_index"]) != i:
            raise RuntimeError(f"global index mismatch for {key}")
    failures = sorted(OUT_DIR.glob("exact_failures_*.csv"))
    nonempty: list[Path] = []
    for p in failures:
        with p.open(newline="", encoding="utf-8") as f:
            if any(True for _ in csv.DictReader(f)):
                nonempty.append(p)
    if nonempty:
        raise RuntimeError(f"exact failures are present: {nonempty}")


def corrected_key(parent: str, state: str, probe: dict[str, str]) -> tuple[int, int, int]:
    outcome = probe["probe_outcome"].strip().upper()
    move = move_of(parent, state)
    if outcome == "LOSS": return (0, 0, move)
    if outcome == "PROBE": return (1, int(probe["memo"]), move)
    if outcome == "WIN": return (2, 0, move)
    raise AssertionError(outcome)


def memo_desc_key(parent: str, state: str, probe: dict[str, str]) -> tuple[int, int]:
    return (-int(probe["memo"]), move_of(parent, state))


def first_loss_rank(order: list[str], exact: dict[str, str]) -> int:
    for i, state in enumerate(order, 1):
        if exact[state] == "LOSS": return i
    return len(order) + 1


def random_cdf(r: int, m: int, loss: int) -> float:
    if loss <= 0 or r <= 0: return 0.0
    if r >= m - loss + 1: return 1.0
    return 1.0 - math.comb(m - r, loss) / math.comb(m, loss)


def random_median(m: int, loss: int) -> int:
    for r in range(1, m + 1):
        if random_cdf(r, m, loss) >= 0.5: return r
    raise AssertionError("median not found")


def auc_from_order(order: list[str], exact: dict[str, str]) -> float | None:
    losses = [s for s in order if exact[s] == "LOSS"]
    wins = [s for s in order if exact[s] == "WIN"]
    if not losses or not wins: return None
    rank = {s: i for i, s in enumerate(order)}
    good = sum(rank[l] < rank[w] for l in losses for w in wins)
    return good / (len(losses) * len(wins))


def one_sided_sign_p(better: int, worse: int) -> float | None:
    n = better + worse
    if not n: return None
    return sum(math.comb(n, k) for k in range(better, n + 1)) / (2 ** n)


def first_loss_pmf(m: int, loss: int) -> list[float]:
    if loss <= 0: raise ValueError("loss must be positive")
    den = math.comb(m, loss)
    # index is rank; index 0 stays zero
    pmf = [0.0] * (m - loss + 2)
    for r in range(1, m - loss + 2):
        pmf[r] = math.comb(m - r, loss - 1) / den
    if abs(sum(pmf) - 1.0) > 1e-12:
        raise RuntimeError("random-rank PMF does not sum to 1")
    return pmf


def convolution_lower_tail(specs: list[tuple[int, int]], observed_sum: int) -> float:
    dist = [1.0]
    for m, loss in specs:
        pmf = first_loss_pmf(m, loss)
        new = [0.0] * (len(dist) + len(pmf) - 1)
        for i, a in enumerate(dist):
            if a == 0.0: continue
            for j, b in enumerate(pmf):
                if b: new[i + j] += a * b
        dist = new
    return sum(dist[: observed_sum + 1])


def main() -> None:
    probes = load_unique_rows("independent_probe_1000000_w*-of-*.csv", "probe_outcome")
    exact_rows = load_unique_rows("exact_outcomes_w*-of-*.csv", "outcome")
    verify_coverage(probes, exact_rows)

    parent_rows: list[dict[str, object]] = []
    aucs: list[float] = []
    null_specs: list[tuple[int, int]] = []
    for parent in load_parents():
        children = legal_children(parent)
        pmap = {s: probes[(parent, s)] for s in children}
        exact = {s: exact_rows[(parent, s)]["outcome"].strip().upper() for s in children}
        m = len(children); loss = sum(v == "LOSS" for v in exact.values())
        if loss == 0:
            raise RuntimeError(f"selected parent has zero exact LOSS children: {parent}")
        corrected = sorted(children, key=lambda s: corrected_key(parent, s, pmap[s]))
        memo_desc = sorted(children, key=lambda s: memo_desc_key(parent, s, pmap[s]))
        default = list(children); reverse = list(reversed(children))
        r = first_loss_rank(corrected, exact); med = random_median(m, loss)
        auc = auc_from_order(corrected, exact)
        if auc is not None: aucs.append(auc)
        proved_loss = sum(pmap[s]["probe_outcome"].upper() == "LOSS" for s in children)
        proved_win = sum(pmap[s]["probe_outcome"].upper() == "WIN" for s in children)
        parent_rows.append({
            "parent": parent, "m": m, "loss_children": loss,
            "probe_proved_loss": proved_loss,
            "probe_unresolved": m - proved_loss - proved_win,
            "probe_proved_win": proved_win,
            "corrected_first_loss": r,
            "memo_desc_first_loss": first_loss_rank(memo_desc, exact),
            "default_first_loss": first_loss_rank(default, exact),
            "reverse_first_loss": first_loss_rank(reverse, exact),
            "random_expected_first_loss": (m + 1) / (loss + 1),
            "random_exact_median": med,
            "corrected_vs_random_median": "better" if r < med else "worse" if r > med else "tie",
            "random_cdf_at_corrected_rank": random_cdf(r, m, loss),
            "corrected_auc": auc,
        })
        null_specs.append((m, loss))

    better = sum(r["corrected_vs_random_median"] == "better" for r in parent_rows)
    tie = sum(r["corrected_vs_random_median"] == "tie" for r in parent_rows)
    worse = sum(r["corrected_vs_random_median"] == "worse" for r in parent_rows)
    observed_sum = sum(int(r["corrected_first_loss"]) for r in parent_rows)
    expected_sum = sum(float(r["random_expected_first_loss"]) for r in parent_rows)
    summary = {
        "design": "preregistered clean holdout V2 fresh-memo 1M",
        "task_set_sha256": task_set_digest(),
        "parents": len(parent_rows), "tasks": len(load_tasks()),
        "better_vs_exact_random_median": better,
        "ties_vs_exact_random_median": tie,
        "worse_vs_exact_random_median": worse,
        "one_sided_exact_sign_p_ties_excluded": one_sided_sign_p(better, worse),
        "corrected_first_loss_sum": observed_sum,
        "random_expected_first_loss_sum": expected_sum,
        "exact_combinatorial_convolution_lower_tail_p": convolution_lower_tail(null_specs, observed_sum),
        "mean_corrected_first_loss": statistics.fmean(float(r["corrected_first_loss"]) for r in parent_rows),
        "median_corrected_first_loss": statistics.median(float(r["corrected_first_loss"]) for r in parent_rows),
        "mean_random_expected_first_loss": statistics.fmean(float(r["random_expected_first_loss"]) for r in parent_rows),
        "auc_parent_count": len(aucs),
        "mean_parent_auc": statistics.fmean(aucs) if aucs else None,
        "median_parent_auc": statistics.median(aucs) if aucs else None,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with PARENT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(parent_rows[0])); w.writeheader(); w.writerows(parent_rows)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

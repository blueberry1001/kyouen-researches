#!/usr/bin/env python3
"""Analyze the 10x10 fresh-memo holdout exactly as preregistered.

IMPORTANT: this implementation is committed before the holdout probe outcomes
are collected/analyzed.  Do not change ranking direction, primary budget,
parent subset, or primary test after seeing holdout outcomes.

Inputs:
  results/10x10/holdout-parent-selection-preregistered.csv
  results/10x10/blind_probe_children/children_<parent>_batch*.txt
  results/10x10/blind_probe_children/exact_<parent>_batch*.csv
  results/10x10/blind-probe-holdout/independent_probe_1000000.csv

Outputs:
  results/10x10/blind-probe-holdout/preregistered_parent_results.csv
  results/10x10/blind-probe-holdout/preregistered_summary.json
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SELECTION = REPO_ROOT / "results" / "10x10" / "holdout-parent-selection-preregistered.csv"
CHILDREN_DIR = REPO_ROOT / "results" / "10x10" / "blind_probe_children"
OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout"
PROBE_CSV = OUT_DIR / "independent_probe_1000000.csv"
PARENT_CSV = OUT_DIR / "preregistered_parent_results.csv"
SUMMARY_JSON = OUT_DIR / "preregistered_summary.json"


def safe_parent(parent: str) -> str:
    return parent.replace(",", "_")


def norm_state(state: str) -> str:
    return "-".join(str(x) for x in sorted(int(v) for v in state.replace(",", "-").split("-") if v != ""))


def cells(state: str) -> tuple[int, ...]:
    return tuple(int(v) for v in norm_state(state).split("-"))


def move_of(parent: str, child: str) -> int:
    p = set(cells(parent))
    c = set(cells(child))
    extra = c - p
    if len(extra) != 1 or not p < c:
        raise RuntimeError(f"not a one-move child: parent={parent}, child={child}")
    return next(iter(extra))


def load_parents() -> list[str]:
    with SELECTION.open(newline="", encoding="utf-8") as f:
        parents = [r["parent"].strip() for r in csv.DictReader(f)]
    if not parents or len(parents) != len(set(parents)):
        raise RuntimeError("invalid frozen parent selection")
    return parents


def batch_no(path: Path) -> int:
    return int(path.stem.rsplit("batch", 1)[1])


def load_children(parent: str) -> list[str]:
    paths = sorted(CHILDREN_DIR.glob(f"children_{safe_parent(parent)}_batch*.txt"), key=batch_no)
    if not paths:
        raise RuntimeError(f"no children for {parent}")
    out: list[str] = []
    for path in paths:
        out.extend(norm_state(x.strip()) for x in path.read_text(encoding="utf-8").splitlines() if x.strip())
    if len(out) != len(set(out)):
        raise RuntimeError(f"duplicate children for {parent}")
    # Confirm deterministic file order has deterministic move order within the
    # complete concatenated child set; it remains a comparator, not primary.
    return out


def load_exact(parent: str) -> dict[str, str]:
    paths = sorted(CHILDREN_DIR.glob(f"exact_{safe_parent(parent)}_batch*.csv"), key=batch_no)
    if not paths:
        raise RuntimeError(f"no exact files for {parent}")
    out: dict[str, str] = {}
    for path in paths:
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                s = norm_state(row["state"])
                outcome = row["outcome"].strip().upper()
                if outcome not in {"WIN", "LOSS"}:
                    raise RuntimeError(f"non-exact outcome in {path}: {outcome}")
                if s in out and out[s] != outcome:
                    raise RuntimeError(f"conflicting exact outcome for {s}")
                out[s] = outcome
    return out


def load_probe() -> dict[tuple[str, str], dict[str, str]]:
    with PROBE_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["parent"].strip(), norm_state(row["state"]))
        if key in out:
            raise RuntimeError(f"duplicate probe row: {key}")
        out[key] = row
    return out


def corrected_key(parent: str, state: str, probe: dict[str, str]) -> tuple[int, int, int]:
    outcome = probe["probe_outcome"].strip().upper()
    # Preregistered strata: proved LOSS first, unresolved second, proved WIN last.
    if outcome == "LOSS":
        stratum = 0
    elif outcome == "WIN":
        stratum = 2
    else:
        stratum = 1
    return (stratum, int(probe["memo"]), move_of(parent, state))


def memo_desc_key(parent: str, state: str, probe: dict[str, str]) -> tuple[int, int]:
    return (-int(probe["memo"]), move_of(parent, state))


def first_loss_rank(order: list[str], exact: dict[str, str]) -> int:
    for rank, state in enumerate(order, 1):
        if exact[state] == "LOSS":
            return rank
    return len(order) + 1


def random_cdf(r: int, m: int, loss: int) -> float:
    """P(first LOSS rank <= r) under a uniformly random permutation."""
    if loss <= 0:
        return 0.0
    if r <= 0:
        return 0.0
    if r >= m - loss + 1:
        return 1.0
    return 1.0 - math.comb(m - r, loss) / math.comb(m, loss)


def random_median(m: int, loss: int) -> int:
    if loss <= 0:
        return m + 1
    for r in range(1, m + 1):
        if random_cdf(r, m, loss) >= 0.5:
            return r
    raise AssertionError("median not found")


def auc_from_order(order: list[str], exact: dict[str, str]) -> float | None:
    losses = [s for s in order if exact[s] == "LOSS"]
    wins = [s for s in order if exact[s] == "WIN"]
    if not losses or not wins:
        return None
    rank = {s: i for i, s in enumerate(order)}
    good = sum(1 for l in losses for w in wins if rank[l] < rank[w])
    return good / (len(losses) * len(wins))


def one_sided_sign_p(better: int, worse: int) -> float | None:
    """P[X >= better], X~Binomial(n, 0.5), ties excluded."""
    n = better + worse
    if n == 0:
        return None
    return sum(math.comb(n, k) for k in range(better, n + 1)) / (2 ** n)


def main() -> None:
    parents = load_parents()
    probes = load_probe()
    expected_probe_keys: set[tuple[str, str]] = set()
    parent_rows: list[dict[str, object]] = []
    aucs: list[float] = []

    for parent in parents:
        children = load_children(parent)
        exact = load_exact(parent)
        child_set = set(children)
        if set(exact) != child_set:
            missing = child_set - set(exact)
            extra = set(exact) - child_set
            raise RuntimeError(f"exact child-set mismatch for {parent}: missing={len(missing)} extra={len(extra)}")

        pmap: dict[str, dict[str, str]] = {}
        for state in children:
            key = (parent, state)
            expected_probe_keys.add(key)
            if key not in probes:
                raise RuntimeError(f"missing probe row for {parent} {state}")
            pmap[state] = probes[key]

        m = len(children)
        loss = sum(exact[s] == "LOSS" for s in children)
        if loss == 0:
            # The frozen set was selected as LOSS parents; silently dropping one
            # would change the confirmatory sample, so fail loudly instead.
            raise RuntimeError(f"frozen parent has zero LOSS children: {parent}")

        corrected = sorted(children, key=lambda s: corrected_key(parent, s, pmap[s]))
        memo_desc = sorted(children, key=lambda s: memo_desc_key(parent, s, pmap[s]))
        default = list(children)
        reverse = list(reversed(children))

        r_corrected = first_loss_rank(corrected, exact)
        r_desc = first_loss_rank(memo_desc, exact)
        r_default = first_loss_rank(default, exact)
        r_reverse = first_loss_rank(reverse, exact)
        med = random_median(m, loss)
        expected_r = (m + 1) / (loss + 1)
        q = random_cdf(r_corrected, m, loss)
        relation = "better" if r_corrected < med else "worse" if r_corrected > med else "tie"
        auc = auc_from_order(corrected, exact)
        if auc is not None:
            aucs.append(auc)

        proved_loss = sum(pmap[s]["probe_outcome"].strip().upper() == "LOSS" for s in children)
        proved_win = sum(pmap[s]["probe_outcome"].strip().upper() == "WIN" for s in children)
        unresolved = m - proved_loss - proved_win

        parent_rows.append({
            "parent": parent,
            "m": m,
            "loss_children": loss,
            "probe_proved_loss": proved_loss,
            "probe_unresolved": unresolved,
            "probe_proved_win": proved_win,
            "corrected_first_loss": r_corrected,
            "memo_desc_first_loss": r_desc,
            "default_first_loss": r_default,
            "reverse_first_loss": r_reverse,
            "random_expected_first_loss": expected_r,
            "random_exact_median": med,
            "corrected_vs_random_median": relation,
            "random_cdf_at_corrected_rank": q,
            "corrected_auc": auc,
        })

    extra_probe = set(probes) - expected_probe_keys
    if extra_probe:
        raise RuntimeError(f"probe CSV contains {len(extra_probe)} rows outside frozen holdout")

    better = sum(r["corrected_vs_random_median"] == "better" for r in parent_rows)
    tie = sum(r["corrected_vs_random_median"] == "tie" for r in parent_rows)
    worse = sum(r["corrected_vs_random_median"] == "worse" for r in parent_rows)
    p_sign = one_sided_sign_p(better, worse)

    summary = {
        "design": "preregistered fresh-memo 1M holdout",
        "parents": len(parent_rows),
        "better_vs_exact_random_median": better,
        "ties_vs_exact_random_median": tie,
        "worse_vs_exact_random_median": worse,
        "one_sided_exact_sign_p_ties_excluded": p_sign,
        "mean_corrected_first_loss": statistics.fmean(float(r["corrected_first_loss"]) for r in parent_rows),
        "median_corrected_first_loss": statistics.median(float(r["corrected_first_loss"]) for r in parent_rows),
        "mean_random_expected_first_loss": statistics.fmean(float(r["random_expected_first_loss"]) for r in parent_rows),
        "auc_parent_count": len(aucs),
        "mean_parent_auc": statistics.fmean(aucs) if aucs else None,
        "median_parent_auc": statistics.median(aucs) if aucs else None,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(parent_rows[0])
    with PARENT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(parent_rows)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

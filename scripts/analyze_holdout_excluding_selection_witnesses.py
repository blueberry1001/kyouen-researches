#!/usr/bin/env python3
"""Sensitivity analysis for the 10x10 holdout after removing pre-known witnesses.

This is deliberately a *minimum-contamination* analysis: it removes the LOSS
witness recorded in the exact proof CSV row that was used to select each
holdout parent.  The proof CSV is read from the preregistration base commit,
not from the post-outcome working tree.  D4-equivalent children are matched.

It does not claim to enumerate every LOSS label that may have existed anywhere
in pre-holdout history.  A later exhaustive history audit can only remove more.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import subprocess
from io import StringIO
from pathlib import Path

from analyze_probe_holdout_preregistered import (
    CHILDREN_DIR,
    OUT_DIR,
    SELECTION,
    auc_from_order,
    corrected_key,
    first_loss_rank,
    load_children,
    load_exact,
    load_probe,
    norm_state,
    one_sided_sign_p,
    random_median,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "9d2e4e6987e89c88b7f9cb591f1f7824ea806171"
OUT_CSV = OUT_DIR / "selection_witness_exclusion_sensitivity.csv"
OUT_JSON = OUT_DIR / "selection_witness_exclusion_sensitivity.json"


def ints(s: str) -> tuple[int, ...]:
    return tuple(sorted(int(x) for x in s.replace("-", ",").split(",") if x.strip()))


def d4_point(p: int, k: int, n: int = 10) -> int:
    x, y = p % n, p // n
    xy = [
        (x, y), (n - 1 - x, y), (x, n - 1 - y), (n - 1 - x, n - 1 - y),
        (y, x), (n - 1 - y, x), (y, n - 1 - x), (n - 1 - y, n - 1 - x),
    ][k]
    return xy[1] * n + xy[0]


def d4_states(state: str) -> set[str]:
    xs = ints(state)
    return {norm_state("-".join(str(d4_point(p, k)) for p in xs)) for k in range(8)}


def show_at_base(path: str) -> str:
    p = subprocess.run(
        ["git", "show", f"{BASE_SHA}:{path}"], cwd=REPO_ROOT,
        text=True, capture_output=True, check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(f"cannot read {path} at {BASE_SHA}: {p.stderr.strip()}")
    return p.stdout


def load_selection_rows() -> list[dict[str, str]]:
    with SELECTION.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def witness_for_selection_row(sel: dict[str, str]) -> tuple[str, str]:
    source_name = sel["source"].strip()
    source_path = f"results/10x10/{source_name}"
    rows = list(csv.DictReader(StringIO(show_at_base(source_path))))
    parent = sel["parent"].strip()
    parent_orbit = d4_states(parent)
    matches = []
    for row in rows:
        state = row.get("state", "").strip()
        loss_child = row.get("loss_child", "").strip()
        if not state or not loss_child:
            continue
        if d4_states(state) & parent_orbit:
            matches.append((state, loss_child))
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one selection-source row for {parent} in {source_path}, got {matches}"
        )
    return source_path, matches[0][1]


def literal_child_equivalent_to_witness(parent: str, witness: str, children: list[str]) -> str:
    orbit = d4_states(witness)
    hits = [s for s in children if s in orbit]
    if len(hits) != 1:
        raise RuntimeError(
            f"expected exactly one child of {parent} D4-equivalent to witness {witness}, got {hits}"
        )
    return hits[0]


def main() -> None:
    probes = load_probe()
    rows_out: list[dict[str, object]] = []
    before_aucs: list[float] = []
    after_aucs: list[float] = []

    for sel in load_selection_rows():
        parent = sel["parent"].strip()
        children = load_children(parent)
        exact = load_exact(parent)
        pmap = {(parent, s): probes[(parent, s)] for s in children}
        source_path, witness_rep = witness_for_selection_row(sel)
        witness_child = literal_child_equivalent_to_witness(parent, witness_rep, children)
        if exact[witness_child] != "LOSS":
            raise RuntimeError(f"pre-known witness is not LOSS in recomputed exact data: {parent} {witness_child}")

        order = sorted(children, key=lambda s: corrected_key(parent, s, pmap[(parent, s)]))
        before_rank = first_loss_rank(order, exact)
        witness_rank = order.index(witness_child) + 1
        before_auc = auc_from_order(order, exact)

        kept = [s for s in children if s != witness_child]
        kept_exact = {s: exact[s] for s in kept}
        remaining_loss = sum(v == "LOSS" for v in kept_exact.values())
        if remaining_loss:
            after_order = [s for s in order if s != witness_child]
            after_rank = first_loss_rank(after_order, kept_exact)
            after_med = random_median(len(kept), remaining_loss)
            relation = "better" if after_rank < after_med else "worse" if after_rank > after_med else "tie"
            after_auc = auc_from_order(after_order, kept_exact)
        else:
            after_rank = None
            after_med = None
            relation = "no_remaining_loss"
            after_auc = None

        if before_auc is not None:
            before_aucs.append(before_auc)
        if after_auc is not None:
            after_aucs.append(after_auc)

        rows_out.append({
            "parent": parent,
            "m_before": len(children),
            "loss_before": sum(exact[s] == "LOSS" for s in children),
            "selection_source_at_base": source_path,
            "preknown_witness_representative": witness_rep,
            "matched_literal_child": witness_child,
            "preknown_witness_memo_rank": witness_rank,
            "preknown_witness_was_first_loss": witness_rank == before_rank,
            "first_loss_rank_before": before_rank,
            "auc_before": before_auc,
            "m_after": len(kept),
            "loss_after": remaining_loss,
            "first_loss_rank_after": after_rank,
            "random_median_after": after_med,
            "after_vs_random_median": relation,
            "auc_after": after_auc,
        })

    eligible = [r for r in rows_out if r["after_vs_random_median"] != "no_remaining_loss"]
    better = sum(r["after_vs_random_median"] == "better" for r in eligible)
    tie = sum(r["after_vs_random_median"] == "tie" for r in eligible)
    worse = sum(r["after_vs_random_median"] == "worse" for r in eligible)
    summary = {
        "analysis": "minimum sensitivity: exclude one prereg-base selection-source LOSS witness per parent",
        "base_sha": BASE_SHA,
        "parents": len(rows_out),
        "parents_with_remaining_loss": len(eligible),
        "preknown_witness_was_first_loss_count": sum(bool(r["preknown_witness_was_first_loss"]) for r in rows_out),
        "better_after": better,
        "tie_after": tie,
        "worse_after": worse,
        "one_sided_sign_p_after": one_sided_sign_p(better, worse),
        "mean_auc_before": statistics.mean(before_aucs) if before_aucs else None,
        "mean_auc_after": statistics.mean(after_aucs) if after_aucs else None,
        "median_auc_before": statistics.median(before_aucs) if before_aucs else None,
        "median_auc_after": statistics.median(after_aucs) if after_aucs else None,
        "scope_warning": "Only the LOSS witness in each selected proof-source row is removed; this is not an exhaustive pre-holdout history audit.",
    }

    fields = list(rows_out[0])
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)
    OUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for r in rows_out:
        print(r["parent"], "witness-rank", r["preknown_witness_memo_rank"],
              "first-loss", r["first_loss_rank_before"], "->", r["first_loss_rank_after"],
              "relation", r["after_vs_random_median"])


if __name__ == "__main__":
    main()

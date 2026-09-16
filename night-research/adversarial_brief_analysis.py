#!/usr/bin/env python3
"""Adversarial re-analysis for overnight Kyouen hypotheses.

Corrects the prior structure-audit I=0 force condition and produces exact
counts needed to cheaply kill candidate claims. Read-only over artifacts/.
Writes night-research/adversarial_brief_analysis.json
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "adversarial_brief_analysis.json"


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_int(s: str | None) -> int | None:
    s = (s or "").strip()
    return int(s) if s else None


def binom_two_sided(k: int, n: int, p: float = 0.5) -> float:
    """Exact two-sided binomial p-value (equal-tail, conservative)."""
    if n == 0:
        return 1.0
    probs = [math.comb(n, i) * (p**i) * ((1 - p) ** (n - i)) for i in range(n + 1)]
    obs = probs[k]
    return min(1.0, sum(pr for pr in probs if pr <= obs + 1e-15))


def binom_one_sided_ge(k: int, n: int, p: float = 0.5) -> float:
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) * (p**i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


def cells(pairs: list[tuple[int, int]]) -> dict:
    n = len(pairs)
    if n == 0:
        return {"n": 0}
    both_loss = sum(1 for b, a in pairs if b == 1 and a == 1)
    both_win = sum(1 for b, a in pairs if b == 0 and a == 0)
    base_only = sum(1 for b, a in pairs if b == 1 and a == 0)
    add_only = sum(1 for b, a in pairs if b == 0 and a == 1)
    disc = base_only + add_only
    net = add_only - base_only
    delta = net / n
    return {
        "n": n,
        "both_loss": both_loss,
        "both_win": both_win,
        "baseline_only_loss": base_only,
        "added_only_loss": add_only,
        "discordant": disc,
        "net_count": net,
        "delta": delta,
        "mcnemar_two_sided_p": binom_two_sided(add_only, disc) if disc else None,
        "mcnemar_one_sided_p": binom_one_sided_ge(add_only, disc) if disc else None,
        # how many +1 flips to 0 would kill sign (net<=0)
        "flips_to_kill_positive_sign": max(0, net),
    }


def d4_transforms(p: tuple[int, ...], n: int = 8) -> list[tuple[int, ...]]:
    nm1 = n - 1
    out = []
    for g in range(8):
        q = []
        for v in p:
            x, y = v % n, v // n
            if g == 0:
                nx, ny = x, y
            elif g == 1:
                nx, ny = nm1 - y, x
            elif g == 2:
                nx, ny = nm1 - x, nm1 - y
            elif g == 3:
                nx, ny = y, nm1 - x
            elif g == 4:
                nx, ny = nm1 - x, y
            elif g == 5:
                nx, ny = x, nm1 - y
            elif g == 6:
                nx, ny = y, x
            else:
                nx, ny = nm1 - y, nm1 - x
            q.append(ny * n + nx)
        out.append(tuple(sorted(q)))
    return out


def parse_parent(s: str) -> tuple[int, ...]:
    return tuple(int(x) for x in s.strip('"').split(","))


def canonical_5(p4: tuple[int, ...], move: int, n: int = 8) -> tuple[int, ...]:
    p5 = tuple(sorted(p4 + (move,)))
    return min(d4_transforms(p5, n))


def main() -> None:
    parents = load(ROOT / "artifacts/8x8-o-parent-outcomes.csv")
    strata = load(ROOT / "artifacts/8x8-o-strata.csv")
    pop = load(ROOT / "artifacts/8x8-factorial-population.csv")
    outcomes = load(ROOT / "artifacts/8x8-o-census-outcomes.csv")
    roots = load(ROOT / "artifacts/8x8-o-required-roots.csv")

    pop_by = {r["canonical_parent"]: r for r in pop}
    outcome_keys = {(r["canonical_parent"], int(r["move"])): r["child_outcome"] for r in outcomes}
    required_keys = {(r["canonical_parent"], int(r["move"])) for r in roots}

    by_st: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in parents:
        by_st[r["stratum"]].append(r)

    result: dict = {}

    # ---------- Task 3: O1-only artifact checks ----------
    o1 = by_st["O1-only"]
    o0 = by_st["O0-only"]
    olap = by_st["O-overlap"]

    # required completeness
    req_missing = []
    optional_lookups_missing = 0
    for r in parents:
        st = r["stratum"]
        parent = r["canonical_parent"]
        need_moves = {
            "O0-only": ["top_T", "top_TO"],
            "O-overlap": ["top_T", "top_TO", "top_TE", "top_raw"],
            "O1-only": ["top_TE", "top_raw"],
        }[st]
        for field in need_moves:
            mv = int(r[field])
            if (parent, mv) not in outcome_keys:
                req_missing.append({"parent": parent, "field": field, "move": mv, "stratum": st})
        # optional: other tops not in required set
        for field in ["top_T", "top_TE", "top_TO", "top_raw"]:
            mv = int(r[field])
            if (parent, mv) not in outcome_keys and (parent, mv) not in required_keys:
                optional_lookups_missing += 1

    result["o1_artifact_checks"] = {
        "n_o1": len(o1),
        "o1_cells": cells([(int(r["y10"]), int(r["y11"])) for r in o1 if r["y10"] and r["y11"]]),
        "required_outcomes_missing_total": len(req_missing),
        "required_outcomes_missing_by_stratum": dict(Counter(x["stratum"] for x in req_missing)),
        "optional_top_lookups_missing": optional_lookups_missing,
        "note_missing_28": (
            "primary-summary missing_outcomes=28 counts ALL four top-move lookups per parent, "
            "including tops that are not required for that stratum. Required contrasts are complete."
        ),
        "solve_completion_roots": f"{len(outcome_keys)}/{len(required_keys)}",
        "census_rows": len(outcomes),
        "required_root_rows": len(roots),
    }

    # D4 / orbit weighting
    o1_orbits = Counter(int(strata_row["orbit_size"]) for strata_row in strata if strata_row["stratum"] == "O1-only")
    o1_orbits_from_pop = Counter(int(pop_by[r["canonical_parent"]]["orbit_size"]) for r in o1)
    # instance-weighted delta (same because all orbit_size=8)
    inst_pairs = []
    for r in o1:
        w = int(pop_by[r["canonical_parent"]]["orbit_size"])
        inst_pairs.extend([(int(r["y10"]), int(r["y11"]))] * w)
    result["o1_artifact_checks"]["orbit_size_hist_strata_csv"] = dict(o1_orbits)
    result["o1_artifact_checks"]["orbit_size_hist_pop"] = dict(o1_orbits_from_pop)
    result["o1_artifact_checks"]["orbit_weighted_cells"] = cells(inst_pairs)
    result["o1_artifact_checks"]["d4_weighting_is_artifact"] = (
        o1_orbits == Counter({8: len(o1)}) and cells(inst_pairs)["delta"] == cells(
            [(int(r["y10"]), int(r["y11"])) for r in o1 if r["y10"] and r["y11"]]
        )["delta"]
    )

    # eligibility / outcome-dependent filtering
    # population: unique-argmax + at least one top differs = outcome-free
    # count how population partitions into strata vs "no O change"
    pop_stratum = Counter()
    no_o_change = 0
    for r in pop:
        t, te, to, raw = r["top_T"], r["top_TE"], r["top_TO"], r["top_raw"]
        o_e0 = t != to
        o_e1 = te != raw
        if o_e0 and not o_e1:
            pop_stratum["O0-only"] += 1
        elif o_e0 and o_e1:
            pop_stratum["O-overlap"] += 1
        elif (not o_e0) and o_e1:
            pop_stratum["O1-only"] += 1
        else:
            no_o_change += 1
    result["o1_artifact_checks"]["population_partition"] = {
        "total_orbits": len(pop),
        "strata": dict(pop_stratum),
        "no_O_change_orbits": no_o_change,
        "eligibility_is_outcome_free": True,
        "o1_frac_of_population": pop_stratum["O1-only"] / len(pop),
        "o1_frac_of_O_changers": pop_stratum["O1-only"] / max(1, sum(pop_stratum.values())),
    }

    # secondary-descriptor multiplicity: how many strata/contrasts were looked at
    result["o1_artifact_checks"]["multiplicity"] = {
        "primary_contrasts": ["O0-only Δ_O@E0", "O-overlap Δ_O@E0", "gap G"],
        "secondary_contrasts": ["O1-only Δ_O@E1", "O-overlap Δ_O@E1", "O-overlap I"],
        "post_hoc_splits_in_prior_audit": [
            "O1 median split pair_E_sum_top_TE",
            "O1 median split pair_E_sum_top_raw",
            "O1 median split diff_E_at_O1",
            "O0 median split pair_E_sum_top_T",
        ],
        "o1_was_frozen_as_secondary": True,
        "primary_failed": True,
        "uncorrected_mcnemar_two_sided_p": cells(
            [(int(r["y10"]), int(r["y11"])) for r in o1 if r["y10"] and r["y11"]]
        )["mcnemar_two_sided_p"],
        "bonferroni_over_3_secondary": min(
            1.0,
            3 * cells([(int(r["y10"]), int(r["y11"])) for r in o1 if r["y10"] and r["y11"]])[
                "mcnemar_two_sided_p"
            ],
        ),
        "bonferroni_over_6_looks": min(
            1.0,
            6 * cells([(int(r["y10"]), int(r["y11"])) for r in o1 if r["y10"] and r["y11"]])[
                "mcnemar_two_sided_p"
            ],
        ),
    }

    # motif clustering among discordants
    disc_o1 = []
    for r in o1:
        d = int(r["y11"]) - int(r["y10"])
        if d == 0:
            continue
        pts = parse_parent(r["canonical_parent"])
        c5_base = canonical_5(pts, int(r["top_TE"]))
        c5_add = canonical_5(pts, int(r["top_raw"]))
        disc_o1.append(
            {
                "parent": r["canonical_parent"],
                "points": list(pts),
                "delta": d,
                "top_TE": int(r["top_TE"]),
                "top_raw": int(r["top_raw"]),
                "y10": int(r["y10"]),
                "y11": int(r["y11"]),
                "child5_TE": list(c5_base),
                "child5_raw": list(c5_add),
                "pair_E_TE": pop_by[r["canonical_parent"]]["pair_E_sum_top_TE"],
                "pair_O_TE": pop_by[r["canonical_parent"]]["pair_O_sum_top_TE"],
                "pair_E_raw": pop_by[r["canonical_parent"]]["pair_E_sum_top_raw"],
                "pair_O_raw": pop_by[r["canonical_parent"]]["pair_O_sum_top_raw"],
            }
        )

    # shared stones among +1 discordants
    pos = [d for d in disc_o1 if d["delta"] > 0]
    neg = [d for d in disc_o1 if d["delta"] < 0]
    stone_freq = Counter()
    for d in pos:
        for p in d["points"]:
            stone_freq[p] += 1
    shared_pairs = []
    for i in range(len(pos)):
        for j in range(i + 1, len(pos)):
            inter = set(pos[i]["points"]) & set(pos[j]["points"])
            if len(inter) >= 2:
                shared_pairs.append(
                    {
                        "a": pos[i]["parent"],
                        "b": pos[j]["parent"],
                        "shared_stones": sorted(inter),
                        "shared_count": len(inter),
                    }
                )

    # shared 5-stone children across ALL strata discordants
    child_map: dict[tuple[int, ...], list[str]] = defaultdict(list)
    for d in disc_o1:
        for key in ("child5_TE", "child5_raw"):
            child_map[tuple(d[key])].append(f"{d['parent']}:{key}:delta={d['delta']}")
    shared_children = {";".join(map(str, k)): v for k, v in child_map.items() if len(v) > 1}

    # collinear 3-subsets among +1 (cheap geometric motif)
    def collinear_triples(pts: list[int], n: int = 8) -> list[list[int]]:
        coords = [(p % n, p // n) for p in pts]
        out = []
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                for k in range(j + 1, len(pts)):
                    (x1, y1), (x2, y2), (x3, y3) = coords[i], coords[j], coords[k]
                    if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
                        out.append([pts[i], pts[j], pts[k]])
        return out

    col_pos = [
        {"parent": d["parent"], "collinear_triples": collinear_triples(d["points"])}
        for d in pos
        if collinear_triples(d["points"])
    ]

    # row/column concentration
    row_hist = Counter()
    col_hist = Counter()
    for d in pos:
        rows = sorted({p // 8 for p in d["points"]})
        cols = sorted({p % 8 for p in d["points"]})
        row_hist[len(rows)] += 1
        col_hist[len(cols)] += 1

    result["o1_motif_and_dependence"] = {
        "discordant_n": len(disc_o1),
        "pos_n": len(pos),
        "neg_n": len(neg),
        "top_stones_among_pos": stone_freq.most_common(10),
        "pos_pairs_sharing_ge2_stones": shared_pairs,
        "pos_pairs_sharing_ge2_count": len(shared_pairs),
        "shared_child5_among_discordants": shared_children,
        "pos_with_collinear_triple": col_pos,
        "distinct_rows_hist_among_pos": dict(row_hist),
        "distinct_cols_hist_among_pos": dict(col_hist),
        # leave-one-motif-family sensitivity: drop all +1 that share a stone pair
        "pos_parents": [d["parent"] for d in pos],
        "neg_parents": [d["parent"] for d in neg],
    }

    # leave-k-out sensitivity on the 13 positives
    sens = []
    for k in range(0, 14):
        net = 13 - 4 - k  # remove k of the +1
        n = 102 - k
        sens.append({"remove_k_positives": k, "net": net, "n": n, "delta": net / n})
    result["o1_sensitivity"] = {
        "leave_k_out_delta": sens,
        "kill_positive_sign_requires_removing": 9,
        "kill_p_lt_0.05_requires": (
            "two-sided McNemar with 13:4 is p≈0.049; "
            "removing any 1 positive makes 12:4 → p≈0.077"
        ),
        "p_after_remove_1_positive": binom_two_sided(12, 16),
        "p_after_remove_2_positives": binom_two_sided(11, 15),
    }

    # Compare O1-only vs O-overlap at same E=1 estimand (discriminating)
    olap_e1 = cells([(int(r["y10"]), int(r["y11"])) for r in olap if r["y10"] and r["y11"]])
    o0_e0 = cells([(int(r["y00"]), int(r["y01"])) for r in o0 if r["y00"] and r["y01"]])
    result["cross_stratum_same_estimand"] = {
        "O1_only_O_at_E1": result["o1_artifact_checks"]["o1_cells"],
        "O_overlap_O_at_E1": olap_e1,
        "O0_only_O_at_E0": o0_e0,
        "note": (
            "O-overlap Δ@E1 is identical to Δ@E0 because I=0 for every overlap parent "
            "(and 151/155 are algebraically forced). Comparing O1-only (+0.088) to "
            "O-overlap@E1 (−0.013) is the right structural contrast, not to O0-only@E0."
        ),
    }

    # ---------- Task 2b: I=0 force algebra (CORRECTED) ----------
    # I = y11 - y10 - y01 + y00
    # Force I=0 if (top_T==top_TE and top_TO==top_raw)  [y00=y10, y01=y11]
    # Partial if only one equality: I collapses to a single outcome difference.
    force_full = 0
    force_partial = 0
    free = 0
    force_patterns = Counter()
    free_parents = []
    for r in olap:
        t, te, to, raw = r["top_T"], r["top_TE"], r["top_TO"], r["top_raw"]
        I = to_int(r["interaction_I"])
        full = (t == te) and (to == raw)
        partial = (t == te) or (to == raw)
        if full:
            force_full += 1
            force_patterns["T==TE & TO==raw (I≡0)"] += 1
            if I not in (0, None):
                force_patterns["VIOLATION_full_force_but_I_nonzero"] += 1
        elif partial:
            force_partial += 1
            which = "T==TE only" if (t == te) else "TO==raw only"
            force_patterns[f"partial: {which}"] += 1
            if t == te and I != 0:
                # I = y01 - y11 wait: I = y11-y10-y01+y00, y00=y10 => I = y11-y01
                pass
            free_parents.append(
                {
                    "parent": r["canonical_parent"],
                    "tops": [t, te, to, raw],
                    "I": I,
                    "pattern": which,
                    "collapsed_I_formula": (
                        "I = y11 - y01  (because y00=y10)" if t == te else "I = y00 - y10  (because y01=y11)"
                    ),
                }
            )
        else:
            free += 1
            free_parents.append(
                {
                    "parent": r["canonical_parent"],
                    "tops": [t, te, to, raw],
                    "I": I,
                    "pattern": "fully free",
                    "collapsed_I_formula": "I = y11-y10-y01+y00",
                }
            )

    result["interaction_force_audit"] = {
        "o_overlap_n": len(olap),
        "fully_forced_I_always_0": force_full,
        "partially_collapsed": force_partial,
        "fully_free": free,
        "force_patterns": dict(force_patterns),
        "empirical_I_hist": dict(Counter(r["interaction_I"] for r in olap)),
        "informative_parents_for_deep_identity": free + force_partial,
        "prior_audit_bug": (
            "night-research/analyze_8x8_structure.py checked te==raw and t==to, "
            "which NEVER holds on O-overlap (definitional inequality). "
            "Correct force is t==te and to==raw → 151/155 fully forced."
        ),
        "residual_free_cases": free_parents,
        "conclusion": (
            "I=0 is an algebraic identity on 151/155 O-overlap parents. "
            "The remaining 4 (T!=TE, TO==raw) collapse to I=y00−y10; all 4 happen to be 0 "
            "(n=4, two-sided binomial p=0.125). There is no independent game-theoretic content."
        ),
    }

    # O-overlap alias patterns from tops
    alias = Counter()
    for r in olap:
        t, te, to, raw = r["top_T"], r["top_TE"], r["top_TO"], r["top_raw"]
        alias[f"T==TE:{t==te}|TO==raw:{to==raw}|T==TO:{t==to}|TE==raw:{te==raw}"] += 1
    result["o_overlap_alias_patterns"] = dict(alias)

    # ---------- O1-only top identity structure ----------
    o1_alias = Counter()
    for r in o1:
        t, te, to, raw = r["top_T"], r["top_TE"], r["top_TO"], r["top_raw"]
        o1_alias[f"T==TE:{t==te}|T==TO:{t==to}|TE==raw:{te==raw}|TO==raw:{to==raw}|distinct:{len({t,te,to,raw})}"] += 1
    result["o1_alias_patterns"] = dict(o1_alias)
    # definitional: O1-only requires T==TO and TE!=raw
    result["o1_definition_identity"] = {
        "T_eq_TO_by_def": sum(1 for r in o1 if r["top_T"] == r["top_TO"]),
        "TE_ne_raw_by_def": sum(1 for r in o1 if r["top_TE"] != r["top_raw"]),
        "T_eq_TE": sum(1 for r in o1 if r["top_T"] == r["top_TE"]),
        "interpretation": (
            "O1-only parents are exactly those where O is invisible at E=0 (same argmax) "
            "and only re-ranks at E=1. The measured estimand is therefore 'O flips the E=1 argmax', "
            "not a free geometric property of the 4-point set independent of the score decomposition."
        ),
    }

    # ---------- baseline LOSS rate differences (scale/regression trap) ----------
    o1c = result["o1_artifact_checks"]["o1_cells"]
    result["baseline_rate_trap"] = {
        "O1_only_baseline_loss_rate": (o1c["baseline_only_loss"] + o1c["both_loss"]) / o1c["n"],
        "O0_only_baseline_loss_rate": (o0_e0["baseline_only_loss"] + o0_e0["both_loss"]) / o0_e0["n"],
        "O_overlap_baseline_loss_rate": (olap_e1["baseline_only_loss"] + olap_e1["both_loss"]) / olap_e1["n"],
        "note": (
            "O1-only baseline LOSS rate is the lowest of the three strata. "
            "A positive Δ from a low baseline can be a floor/regression artifact rather than "
            "O-specific geometry. Compare added-LOSS rate absolute levels too."
        ),
        "O1_added_loss_rate": (o1c["added_only_loss"] + o1c["both_loss"]) / o1c["n"],
        "O0_added_loss_rate": (o0_e0["added_only_loss"] + o0_e0["both_loss"]) / o0_e0["n"],
        "O_overlap_added_loss_rate": (olap_e1["added_only_loss"] + olap_e1["both_loss"]) / olap_e1["n"],
    }

    # ---------- certificate complexity vs winner (d) ----------
    # already in structure audit; recompute ratios and monotonicity
    cert = [
        (1, 0, 2, "F"),
        (2, 1, 5, "F"),
        (3, 14, 28, "F"),
        (4, 194, 135, "S"),
        (5, 826, 1217, "F"),
        (6, 2491, 21712, "F"),
        (7, 6364, 393550, "S"),
        (8, 14564, 8744406, "S"),
        (9, 29152, 13457134, "F"),
    ]
    result["certificate_vs_winner"] = {
        "table": [
            {
                "n": n,
                "forbidden": f,
                "proof_nodes": p,
                "winner": w,
                "proof_per_forbidden": (p / f if f else None),
                "log_proof": math.log(p) if p else None,
            }
            for n, f, p, w in cert
        ],
        "proof_nodes_monotone": all(cert[i][2] < cert[i + 1][2] for i in range(len(cert) - 1)),
        "winner_alternation": "".join(c[3] for c in cert),
        "cheap_kills": [
            "proof_nodes grows monotonically with n regardless of winner — raw size cannot encode winner",
            "proof_nodes/forbidden drops from n=8 to n=9 while winner flips S→F — ratio not a winner function",
            "certificate size depends on witness selection / memo / search order, not game value alone",
            "only 9 labeled points (n=1..9); any fitted threshold is post-hoc with n=9",
            "WIN certificates retain ~1 LOSS witness; size is a property of the proof algorithm, not the game",
        ],
        "n9_vs_n8_ratio_drop": (cert[-1][2] / cert[-1][1]) / (cert[-2][2] / cert[-2][1]),
    }

    # ---------- safe-child / mobility (e) tautology risk ----------
    # From known results: 3-stone fixed rule == mobility == solver primary key.
    # LOSS node: ALL safe children are WIN. WIN: at least one LOSS child.
    result["safe_child_predictor_trap"] = {
        "definitional_coupling": (
            "Outcome is an AND/OR function of the child multiset. "
            "LOSS ⇔ every safe child is WIN. "
            "Any feature that counts safe children or their outcomes is a partial re-encoding of the label."
        ),
        "already_falsified_family": (
            "Immediate mobility / pair-mobility already failed as a general decision rule "
            "(9x9 pair-mobility scans; raw pair vs mobility disagree mainly via E)."
        ),
        "required_beyond_correlation": (
            "Must show residual predictive power AFTER conditioning on T/E/O scores and depth, "
            "and must beat 'argmax T' on a held-out board with a frozen threshold."
        ),
    }

    # ---------- (c) context-dependent pair strength ----------
    result["context_pair_trap"] = {
        "known_posthoc_pairs_10x10": {
            "3_stone": "{90,91}",
            "4_stone": "{61,66}",
            "5_stone": "{13,91}",
            "6_stone": "{61,66}",
        },
        "cheap_kills": [
            "pairs were selected AFTER looking at LOSS enrichment — not preregistered",
            "per-depth pair scan is a multiple-comparisons problem (C(100,2)*depths looks)",
            "static pair weight already fails because cores swap with depth; "
            "a free-form w(a,b| |P|, P\\ab) is unfalsifiable without a frozen parametric form",
            "10x10 subset labels inherit certificate sampling bias (WIN keeps 1 witness)",
        ],
        "discriminating_test": (
            "Freeze a parametric interaction (e.g. w0(pair) + w1(pair)*1[|P|=k] with "
            "shrinkage) BEFORE computing enrichment; require held-out depth or held-out board."
        ),
    }

    # ---------- population scale for overnight planning ----------
    result["population_scale"] = {
        "8x8_safe_4parents": 620812,
        "8x8_eligible_d4_orbits": 2340,
        "8x8_O_strata_orbits": 422,
        "note": (
            "Full 8x8 safe-parent census is 620812; factorial eligibility reduces to 2340 orbits. "
            "Overnight solvers on 8x8 children were 848 unique roots in 3.74s — cheap. "
            "9x9/10x10 full parent censuses are NOT cheap; use D4 orbits + unique child roots."
        ),
    }

    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # printable summary
    print(json.dumps({k: result[k] for k in [
        "o1_artifact_checks",
        "interaction_force_audit",
        "o_overlap_alias_patterns",
        "o1_alias_patterns",
        "o1_definition_identity",
        "baseline_rate_trap",
        "o1_sensitivity",
        "cross_stratum_same_estimand",
        "o1_motif_and_dependence",
        "certificate_vs_winner",
    ] if k in result}, indent=2, ensure_ascii=False)[:12000])


if __name__ == "__main__":
    main()

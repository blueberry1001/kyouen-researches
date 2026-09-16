#!/usr/bin/env python3
"""Analyze 8x8 O-stratum outcomes for cheap structural claims.

Read-only over committed artifacts. Writes summary JSON under night-research/.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_int(s: str) -> int | None:
    s = (s or "").strip()
    if s == "":
        return None
    return int(s)


def main() -> None:
    parents = load_csv(ROOT / "artifacts/8x8-o-parent-outcomes.csv")
    strata = load_csv(ROOT / "artifacts/8x8-o-strata.csv")
    pop = load_csv(ROOT / "artifacts/8x8-factorial-population.csv")

    pop_by_parent = {r["canonical_parent"]: r for r in pop}
    strata_by_parent = {r["canonical_parent"]: r for r in strata}

    by_stratum: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in parents:
        by_stratum[r["stratum"]].append(r)

    summary: dict = {"n_parents": len(parents), "strata_counts": {k: len(v) for k, v in by_stratum.items()}}

    # Completeness of outcomes
    missing = []
    for r in parents:
        ys = [r["y00"], r["y01"], r["y10"], r["y11"], r["y_top_T"], r["y_top_TE"], r["y_top_TO"], r["y_top_raw"]]
        if any((y or "").strip() == "" for y in ys[:4] if r["stratum"] == "O-overlap") or any(
            (r.get(f"y{i}", "") or "").strip() == "" for i in []
        ):
            pass
        # report rows with blank top-level y cells that are required for their stratum
        need = {
            "O0-only": ["y00", "y01"],
            "O1-only": ["y10", "y11"],
            "O-overlap": ["y00", "y01", "y10", "y11", "interaction_I"],
        }[r["stratum"]]
        blanks = [k for k in need if (r.get(k) or "").strip() == ""]
        if blanks:
            missing.append({"parent": r["canonical_parent"], "stratum": r["stratum"], "blanks": blanks,
                            "y_top_T": r["y_top_T"], "y_top_TE": r["y_top_TE"],
                            "y_top_TO": r["y_top_TO"], "y_top_raw": r["y_top_raw"]})
    summary["incomplete_rows"] = missing
    summary["incomplete_count"] = len(missing)

    # Recompute effects where possible
    def effect_rows(rows, y_base, y_add):
        pairs = []
        for r in rows:
            b = to_int(r[y_base])
            a = to_int(r[y_add])
            if b is None or a is None:
                continue
            pairs.append((b, a))
        n = len(pairs)
        if n == 0:
            return None
        both_loss = sum(1 for b, a in pairs if b == 1 and a == 1)
        both_win = sum(1 for b, a in pairs if b == 0 and a == 0)
        base_only = sum(1 for b, a in pairs if b == 1 and a == 0)
        add_only = sum(1 for b, a in pairs if b == 0 and a == 1)
        return {
            "n": n,
            "both_loss": both_loss,
            "both_win": both_win,
            "baseline_only_loss": base_only,
            "added_only_loss": add_only,
            "baseline_loss_rate": sum(b for b, _ in pairs) / n,
            "added_loss_rate": sum(a for _, a in pairs) / n,
            "delta": (sum(a for _, a in pairs) - sum(b for b, _ in pairs)) / n,
            "net": add_only - base_only,
        }

    summary["effects"] = {
        "O0-only_O@E0": effect_rows(by_stratum["O0-only"], "y00", "y01"),
        "O1-only_O@E1": effect_rows(by_stratum["O1-only"], "y10", "y11"),
        "overlap_O@E0": effect_rows(by_stratum["O-overlap"], "y00", "y01"),
        "overlap_O@E1": effect_rows(by_stratum["O-overlap"], "y10", "y11"),
    }

    # Interaction identity: when is I forced to 0 by top-move equality?
    forced_zero = 0
    free_I = []
    for r in by_stratum["O-overlap"]:
        I = to_int(r["interaction_I"])
        t, te, to, raw = r["top_T"], r["top_TE"], r["top_TO"], r["top_raw"]
        # If top_TE==top_raw and top_T==top_TO, then y10==y11 and y00==y01 => I=0
        # Actually I = y11 - y01 - y10 + y00
        # If TE==raw: y10==y11 => I = y00 - y01
        # If T==TO: y00==y01 => I = y11 - y10
        # If both: I=0
        if te == raw and t == to:
            forced_zero += 1
            if I not in (0, None):
                free_I.append({"parent": r["canonical_parent"], "I": I, "reason": "both_equal_but_I_nonzero"})
        elif te == raw or t == to:
            # one equality forces I to a single y-difference
            pass
        else:
            free_I.append({"parent": r["canonical_parent"], "I": I, "tops": [t, te, to, raw],
                           "reason": "four_distinct_or_partial"})

    summary["overlap_forced_zero_by_tops"] = forced_zero
    summary["overlap_n"] = len(by_stratum["O-overlap"])
    summary["overlap_not_forced"] = free_I[:50]
    summary["overlap_not_forced_count"] = len(free_I)

    # Pair score features by stratum from population
    feats = []
    for r in parents:
        p = pop_by_parent.get(r["canonical_parent"])
        s = strata_by_parent.get(r["canonical_parent"])
        if not p:
            continue
        feats.append({
            "stratum": r["stratum"],
            "pair_E_sum_top_T": float(p["pair_E_sum_top_T"]),
            "pair_O_sum_top_T": float(p["pair_O_sum_top_T"]),
            "pair_E_sum_top_TE": float(p["pair_E_sum_top_TE"]),
            "pair_O_sum_top_TE": float(p["pair_O_sum_top_TE"]),
            "pair_E_sum_top_TO": float(p["pair_E_sum_top_TO"]),
            "pair_O_sum_top_TO": float(p["pair_O_sum_top_TO"]),
            "pair_E_sum_top_raw": float(p["pair_E_sum_top_raw"]),
            "pair_O_sum_top_raw": float(p["pair_O_sum_top_raw"]),
            "diff_O_at_E0": float(p["diff_O_at_E0"]),
            "diff_O_at_E1": float(p["diff_O_at_E1"]),
            "diff_E_at_O0": float(p["diff_E_at_O0"]),
            "diff_E_at_O1": float(p["diff_E_at_O1"]),
            "distinct_top_moves": int(p["distinct_top_moves"]),
            "orbit_size": int(p["orbit_size"]),
            "parent": r["canonical_parent"],
            "y_effect": None,
        })
        if r["stratum"] == "O1-only":
            a, b = to_int(r["y10"]), to_int(r["y11"])
            if a is not None and b is not None:
                feats[-1]["y_effect"] = a - b  # baseline - added? wait: y11 - y10 = added - baseline LOSS
                # store added-baseline
                feats[-1]["delta_O_E1"] = b - a
        if r["stratum"] == "O0-only":
            a, b = to_int(r["y00"]), to_int(r["y01"])
            if a is not None and b is not None:
                feats[-1]["delta_O_E0"] = b - a

    def mean(xs):
        return sum(xs) / len(xs) if xs else None

    for st in ["O0-only", "O1-only", "O-overlap"]:
        rows = [f for f in feats if f["stratum"] == st]
        summary[f"features_{st}"] = {
            "n": len(rows),
            "mean_pair_E_top_T": mean([f["pair_E_sum_top_T"] for f in rows]),
            "mean_pair_O_top_T": mean([f["pair_O_sum_top_T"] for f in rows]),
            "mean_diff_O_at_E0": mean([f["diff_O_at_E0"] for f in rows]),
            "mean_diff_O_at_E1": mean([f["diff_O_at_E1"] for f in rows]),
            "mean_distinct": mean([f["distinct_top_moves"] for f in rows]),
            "mean_orbit": mean([f["orbit_size"] for f in rows]),
        }

    # Within O1-only: does delta correlate with pair scores?
    o1 = [f for f in feats if f["stratum"] == "O1-only" and "delta_O_E1" in f]
    if o1:
        # contingency: delta>0 vs pair_O at top_TE or top_raw
        for key in ["pair_O_sum_top_TE", "pair_O_sum_top_raw", "pair_E_sum_top_TE", "diff_O_at_E1", "diff_E_at_O1"]:
            hi = [f for f in o1 if f[key] >= sorted(f2[key] for f2 in o1)[len(o1)//2]]
            lo = [f for f in o1 if f[key] < sorted(f2[key] for f2 in o1)[len(o1)//2]]
            summary.setdefault("o1_delta_by_median_split", {})[key] = {
                "hi_n": len(hi), "hi_mean_delta": mean([f["delta_O_E1"] for f in hi]),
                "lo_n": len(lo), "lo_mean_delta": mean([f["delta_O_E1"] for f in lo]),
            }
        summary["o1_delta_hist"] = dict(Counter(f["delta_O_E1"] for f in o1))

    # O0-only same
    o0 = [f for f in feats if f["stratum"] == "O0-only" and "delta_O_E0" in f]
    if o0:
        summary["o0_delta_hist"] = dict(Counter(f["delta_O_E0"] for f in o0))
        for key in ["pair_O_sum_top_T", "pair_E_sum_top_T", "diff_O_at_E0"]:
            vals = sorted(f2[key] for f2 in o0)
            med = vals[len(vals)//2]
            hi = [f for f in o0 if f[key] >= med]
            lo = [f for f in o0 if f[key] < med]
            summary.setdefault("o0_delta_by_median_split", {})[key] = {
                "hi_n": len(hi), "hi_mean_delta": mean([f["delta_O_E0"] for f in hi]),
                "lo_n": len(lo), "lo_mean_delta": mean([f["delta_O_E0"] for f in lo]),
            }

    # Check: among O-overlap, is I nonzero only when 4 tops are not collapsed?
    i_nonzero = []
    for r in by_stratum["O-overlap"]:
        I = to_int(r["interaction_I"])
        if I:
            i_nonzero.append({
                "parent": r["canonical_parent"],
                "I": I,
                "tops": [r["top_T"], r["top_TE"], r["top_TO"], r["top_raw"]],
                "ys": [r["y00"], r["y01"], r["y10"], r["y11"]],
                "top_TE_eq_raw": r["top_TE"] == r["top_raw"],
                "top_T_eq_TO": r["top_T"] == r["top_TO"],
                "distinct": len(set([r["top_T"], r["top_TE"], r["top_TO"], r["top_raw"]])),
            })
    summary["overlap_I_nonzero"] = i_nonzero

    # Parent geometry: parse points and simple features
    def parse_parent(s: str) -> list[int]:
        return [int(x) for x in s.strip('"').split(",")]

    def coords(i: int) -> tuple[int, int]:
        return (i % 8, i // 8)

    def pair_dist(a: int, b: int) -> float:
        ax, ay = coords(a)
        bx, by = coords(b)
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5

    def geom_features(pts: list[int]) -> dict:
        dists = []
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                dists.append(pair_dist(pts[i], pts[j]))
        xs = [coords(p)[0] for p in pts]
        ys = [coords(p)[1] for p in pts]
        cx = sum(xs) / 4
        cy = sum(ys) / 4
        # symmetry under D4: check if set is invariant under some nontrivial transform
        s = set(pts)
        def t_rot90(p):
            x, y = coords(p)
            return (7 - y) * 8 + x  # (x,y)->(7-y,x) wait: rot90: (x,y)->(y, n-1-x)? Use (x,y)->(y,7-x) -> idx = y*8+(7-x)? 
            # simpler: map via coords
        def apply(pts, fn):
            out = []
            for p in pts:
                x, y = coords(p)
                nx, ny = fn(x, y)
                out.append(ny * 8 + nx)
            return set(out)
        transforms = {
            "id": lambda x, y: (x, y),
            "r90": lambda x, y: (y, 7 - x),
            "r180": lambda x, y: (7 - x, 7 - y),
            "r270": lambda x, y: (7 - y, x),
            "fx": lambda x, y: (7 - x, y),
            "fy": lambda x, y: (x, 7 - y),
            "fd": lambda x, y: (y, x),
            "fa": lambda x, y: (7 - y, 7 - x),
        }
        fixed_by = []
        for name, fn in transforms.items():
            if apply(pts, fn) == s:
                fixed_by.append(name)
        return {
            "mean_pair_dist": mean(dists),
            "max_pair_dist": max(dists),
            "min_pair_dist": min(dists),
            "centroid": (cx, cy),
            "centroid_in_board_center": abs(cx - 3.5) < 1e-9 and abs(cy - 3.5) < 1e-9,
            "d4_fixed_by": fixed_by,
            "orbit_size_expected": 8 // max(1, len(fixed_by)),
            "has_centerish": any(abs(coords(p)[0] - 3.5) <= 0.5 and abs(coords(p)[1] - 3.5) <= 0.5 for p in pts),
        }

    geom_by_stratum = defaultdict(list)
    for r in parents:
        pts = parse_parent(r["canonical_parent"])
        g = geom_features(pts)
        g["stratum"] = r["stratum"]
        g["parent"] = r["canonical_parent"]
        geom_by_stratum[r["stratum"]].append(g)

    summary["geom"] = {}
    for st, rows in geom_by_stratum.items():
        summary["geom"][st] = {
            "n": len(rows),
            "mean_pair_dist": mean([r["mean_pair_dist"] for r in rows]),
            "mean_max_pair_dist": mean([r["max_pair_dist"] for r in rows]),
            "frac_centroid_center": mean([1.0 if r["centroid_in_board_center"] else 0.0 for r in rows]),
            "frac_has_centerish": mean([1.0 if r["has_centerish"] else 0.0 for r in rows]),
            "orbit_size_hist": dict(Counter(r["orbit_size_expected"] for r in rows)),
            "d4_fixed_count_hist": dict(Counter(len(r["d4_fixed_by"]) for r in rows)),
        }

    # Certificate complexity vs winner (from README)
    cert = [
        (1, 0, 2, "F"), (2, 1, 5, "F"), (3, 14, 28, "F"), (4, 194, 135, "S"),
        (5, 826, 1217, "F"), (6, 2491, 21712, "F"), (7, 6364, 393550, "S"),
        (8, 14564, 8744406, "S"), (9, 29152, 13457134, "F"),
    ]
    summary["certificate_table"] = [
        {"n": n, "forbidden_4sets": f, "proof_nodes": p, "winner": w,
         "proof_nodes_per_forbidden": (p / f if f else None),
         "proof_nodes_per_point": p / (n * n)}
        for n, f, p, w in cert
    ]

    out_path = OUT / "8x8-structure-audit.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in [
        "n_parents", "strata_counts", "incomplete_count", "effects",
        "overlap_forced_zero_by_tops", "overlap_not_forced_count",
        "overlap_I_nonzero", "o1_delta_hist", "o0_delta_hist", "geom"
    ] if k in summary}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

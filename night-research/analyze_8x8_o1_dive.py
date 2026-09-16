#!/usr/bin/env python3
"""Confirm factorial aliasing identity and dig into 8x8 O1-only discordants."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_parent(s: str) -> list[int]:
    return [int(x) for x in s.strip('"').split(",")]


def coords(i: int, n: int = 8) -> tuple[int, int]:
    return (i % n, i // n)


def main() -> None:
    parents = load(ROOT / "artifacts/8x8-o-parent-outcomes.csv")
    pop = {r["canonical_parent"]: r for r in load(ROOT / "artifacts/8x8-factorial-population.csv")}

    # 1) Alias identity on O-overlap
    alias_patterns = Counter()
    i_vals = Counter()
    mismatched = []
    for r in parents:
        if r["stratum"] != "O-overlap":
            continue
        t, te, to, raw = r["top_T"], r["top_TE"], r["top_TO"], r["top_raw"]
        pattern = (
            f"T==TE:{t==te},TO==raw:{to==raw},T==TO:{t==to},TE==raw:{te==raw},"
            f"distinct:{len({t,te,to,raw})}"
        )
        alias_patterns[pattern] += 1
        i_vals[r["interaction_I"]] += 1
        y00, y01, y10, y11 = r["y00"], r["y01"], r["y10"], r["y11"]
        # If T==TE then y00 should equal y10; if TO==raw then y01==y11
        if t == te and y00 != y10:
            mismatched.append({"parent": r["canonical_parent"], "why": "T==TE but y00!=y10",
                               "y00": y00, "y10": y10, "tops": [t, te, to, raw]})
        if to == raw and y01 != y11:
            mismatched.append({"parent": r["canonical_parent"], "why": "TO==raw but y01!=y11",
                               "y01": y01, "y11": y11, "tops": [t, te, to, raw]})

    # 2) Same alias check on O0-only / O1-only
    def alias_only(rows, label, eq_left, eq_right):
        # For O0-only: by definition top_TE==top_raw (O does not change at E=1)
        # Does E leave T unchanged? top_T==top_TE?
        c = Counter()
        for r in rows:
            t, te, to, raw = r["top_T"], r["top_TE"], r["top_TO"], r["top_raw"]
            c[f"T==TE:{t==te},TE==raw:{te==raw},T==raw:{t==raw},TO==raw:{to==raw}"] += 1
        return c

    o0 = [r for r in parents if r["stratum"] == "O0-only"]
    o1 = [r for r in parents if r["stratum"] == "O1-only"]

    # 3) O1-only discordant parents deep dive
    disc = []
    for r in o1:
        y10, y11 = r["y10"], r["y11"]
        if y10 == "" or y11 == "":
            continue
        d = int(y11) - int(y10)  # added - baseline; +1 means O-added is LOSS and baseline WIN? wait LOSS=1
        # O_effect_E1 = y11 - y10; +1 means added becomes LOSS (worse for the player to move on that child)
        # Actually LOSS child means the mover who played into it... outcomes are of the child position from player to move.
        # If y=1 LOSS, the player to move at that child is in a losing position, so the PARENT player who moved there made a winning move.
        # So higher LOSS rate of selected child = heuristic is BETTER for the parent player.
        # delta = y11 - y10 > 0 means added (O) selects a LOSS child more often = O better.
        if d != 0:
            p = pop.get(r["canonical_parent"], {})
            pts = parse_parent(r["canonical_parent"])
            disc.append({
                "parent": r["canonical_parent"],
                "points": pts,
                "coords": [coords(i) for i in pts],
                "top_T": r["top_T"], "top_TE": r["top_TE"], "top_TO": r["top_TO"], "top_raw": r["top_raw"],
                "y10": y10, "y11": y11, "delta_O_E1": d,
                "pair_E_TE": p.get("pair_E_sum_top_TE"),
                "pair_O_TE": p.get("pair_O_sum_top_TE"),
                "pair_E_raw": p.get("pair_E_sum_top_raw"),
                "pair_O_raw": p.get("pair_O_sum_top_raw"),
                "diff_O_at_E1": p.get("diff_O_at_E1"),
                "diff_E_at_O1": p.get("diff_E_at_O1"),
            })

    # 4) Test: among O1-only, is O-effect larger when O actually changes the E=1 top AND the raw top has higher pair_O?
    # Also test whether T==TE on O1-only (E invariance at O=0)
    o1_T_eq_TE = sum(1 for r in o1 if r["top_T"] == r["top_TE"])
    o0_TE_eq_raw = sum(1 for r in o0 if r["top_TE"] == r["top_raw"])
    o1_TO_eq_raw = sum(1 for r in o1 if r["top_TO"] == r["top_raw"])
    o0_T_eq_TE = sum(1 for r in o0 if r["top_T"] == r["top_TE"])

    # 5) For O1-only: baseline is top_TE, added is top_raw. When d=+1, what differs?
    pos = [d for d in disc if d["delta_O_E1"] > 0]
    neg = [d for d in disc if d["delta_O_E1"] < 0]

    def mean(xs):
        return sum(xs) / len(xs) if xs else None

    result = {
        "overlap_alias_patterns": dict(alias_patterns),
        "overlap_I_hist": dict(i_vals),
        "overlap_mismatches": mismatched,
        "O1_only_n": len(o1),
        "O1_top_T_eq_TE": o1_T_eq_TE,
        "O1_top_TO_eq_raw": o1_TO_eq_raw,
        "O0_only_n": len(o0),
        "O0_top_T_eq_TE": o0_T_eq_TE,
        "O0_top_TE_eq_raw": o0_TE_eq_raw,
        "O1_discordant": disc,
        "O1_pos_n": len(pos),
        "O1_neg_n": len(neg),
        "O1_pos_mean_pair_O_raw": mean([float(d["pair_O_raw"]) for d in pos if d["pair_O_raw"] not in (None, "")]),
        "O1_neg_mean_pair_O_raw": mean([float(d["pair_O_raw"]) for d in neg if d["pair_O_raw"] not in (None, "")]),
        "O1_pos_mean_diff_O": mean([float(d["diff_O_at_E1"]) for d in pos if d["diff_O_at_E1"] not in (None, "")]),
        "O1_neg_mean_diff_O": mean([float(d["diff_O_at_E1"]) for d in neg if d["diff_O_at_E1"] not in (None, "")]),
        "O1_all_mean_pair_O_raw": mean([float(d["pair_O_raw"]) for d in disc if d["pair_O_raw"] not in (None, "")]),
        "binom_note": "13 vs 4 discordant, two-sided exact binomial p≈0.049 uncorrected",
    }

    (OUT / "8x8-o1-dive.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2)[:8000])


if __name__ == "__main__":
    main()

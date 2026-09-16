#!/usr/bin/env python3
"""Supplemental adversarial stats: Fisher, motif components, 9x9 availability."""
from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fisher_2x2(a: int, b: int, c: int, d: int) -> tuple[float, float]:
    n = a + b + c + d
    r1, c1 = a + b, a + c
    def p(x: int) -> float:
        return math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)
    lo = max(0, r1 - (n - c1))
    hi = min(r1, c1)
    probs = [(x, p(x)) for x in range(lo, hi + 1)]
    obs = p(a)
    two = sum(pr for _, pr in probs if pr <= obs + 1e-15)
    return two, obs


def parse(s: str) -> set[int]:
    return {int(x) for x in s.split(",")}


def main() -> None:
    out = {}

    out["fisher_o1_vs_overlap"] = fisher_2x2(13, 4, 7, 9)
    out["fisher_o1_vs_o0"] = fisher_2x2(13, 4, 5, 12)

    pos = [
        "0,11,33,38",
        "2,4,27,30",
        "2,4,36,41",
        "2,10,12,14",
        "2,17,35,43",
        "2,27,34,41",
        "3,14,21,28",
        "3,14,37,54",
        "9,10,27,46",
        "11,18,21,33",
        "11,20,34,43",
        "11,28,33,38",
        "11,28,36,43",
    ]
    parent = {p: p for p in pos}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(pos)):
        for j in range(i + 1, len(pos)):
            if len(parse(pos[i]) & parse(pos[j])) >= 2:
                union(pos[i], pos[j])
    comps: dict[str, list[str]] = defaultdict(list)
    for p in pos:
        comps[find(p)].append(p)
    out["pos_motif_components_share2"] = list(comps.values())

    # single-stone connected components (share >=1)
    parent1 = {p: p for p in pos}

    def find1(x: str) -> str:
        while parent1[x] != x:
            parent1[x] = parent1[parent1[x]]
            x = parent1[x]
        return x

    def union1(a: str, b: str) -> None:
        ra, rb = find1(a), find1(b)
        if ra != rb:
            parent1[rb] = ra

    for i in range(len(pos)):
        for j in range(i + 1, len(pos)):
            if parse(pos[i]) & parse(pos[j]):
                union1(pos[i], pos[j])
    comps1: dict[str, list[str]] = defaultdict(list)
    for p in pos:
        comps1[find1(p)].append(p)
    out["pos_motif_components_share1"] = list(comps1.values())

    stone_in = Counter()
    for p in pos:
        for s in parse(p):
            stone_in[s] += 1
    out["stones_in_ge3_pos"] = {s: c for s, c in stone_in.items() if c >= 3}
    out["stones_in_ge2_pos"] = {s: c for s, c in stone_in.items() if c >= 2}

    # 9x9 artifacts availability
    avail = {}
    for name in [
        "9x9-factorial-population.csv",
        "9x9-factorial-holdout.csv",
        "9x9-confirmatory-1024.csv",
    ]:
        p = ROOT / "artifacts" / name
        if not p.exists():
            avail[name] = "missing"
            continue
        with p.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        avail[name] = {"rows": len(rows), "cols": list(rows[0].keys()) if rows else []}
    out["nine_by_nine_artifacts"] = avail

    # population-level free I tops
    with (ROOT / "artifacts/8x8-factorial-population.csv").open(newline="", encoding="utf-8") as f:
        pop = list(csv.DictReader(f))
    free_tops = sum(1 for r in pop if r["top_T"] != r["top_TE"] and r["top_TO"] != r["top_raw"])
    t_eq_te_to_eq_raw = sum(1 for r in pop if r["top_T"] == r["top_TE"] and r["top_TO"] == r["top_raw"])
    out["population_top_identity"] = {
        "total": len(pop),
        "T_eq_TE_and_TO_eq_raw": t_eq_te_to_eq_raw,
        "fully_free_T_ne_TE_and_TO_ne_raw": free_tops,
        "note": (
            "Only orbits with both O-change flags are in O-overlap; "
            "the force T==TE & TO==raw is extremely common across the eligible population."
        ),
    }

    # within O1-only: T==TE subset delta
    parents = list(csv.DictReader((ROOT / "artifacts/8x8-o-parent-outcomes.csv").open(newline="", encoding="utf-8")))
    o1 = [r for r in parents if r["stratum"] == "O1-only"]
    for label, subset in [
        ("T_eq_TE", [r for r in o1 if r["top_T"] == r["top_TE"]]),
        ("T_ne_TE", [r for r in o1 if r["top_T"] != r["top_TE"]]),
        ("TO_eq_raw", [r for r in o1 if r["top_TO"] == r["top_raw"]]),
        ("TO_ne_raw", [r for r in o1 if r["top_TO"] != r["top_raw"]]),
    ]:
        pairs = [(int(r["y10"]), int(r["y11"])) for r in subset if r["y10"] and r["y11"]]
        if not pairs:
            continue
        pos_c = sum(1 for b, a in pairs if a - b == 1)
        neg_c = sum(1 for b, a in pairs if a - b == -1)
        n = len(pairs)
        out[f"o1_subset_{label}"] = {
            "n": n,
            "pos": pos_c,
            "neg": neg_c,
            "delta": (pos_c - neg_c) / n,
            "mcnemar_p": fisher_2x2(pos_c, neg_c, 0, 0)[0] if False else None,
        }
        # exact binomial two-sided on discordants
        disc = pos_c + neg_c
        if disc:
            probs = [math.comb(disc, i) / 2**disc for i in range(disc + 1)]
            obs = probs[pos_c]
            out[f"o1_subset_{label}"]["mcnemar_p"] = sum(pr for pr in probs if pr <= obs + 1e-15)

    # How many of the 13 positives involve a collinear triple of the 4 parent stones?
    def collinear_triples(pts: list[int], n: int = 8) -> list[list[int]]:
        coords = [(p % n, p // n) for p in pts]
        outt = []
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                for k in range(j + 1, len(pts)):
                    (x1, y1), (x2, y2), (x3, y3) = coords[i], coords[j], coords[k]
                    if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
                        outt.append([pts[i], pts[j], pts[k]])
        return outt

    n_col = sum(1 for p in pos if collinear_triples(list(parse(p))))
    out["pos_with_collinear_triple_count"] = n_col

    # Compare: among all 102 O1-only, how many have collinear triple?
    n_col_all = 0
    for r in o1:
        pts = [int(x) for x in r["canonical_parent"].strip('"').split(",")]
        if collinear_triples(pts):
            n_col_all += 1
    out["o1_all_with_collinear_triple"] = n_col_all

    # among the 13 positives vs remaining 89: enrichment of collinear
    # pos is subset of o1
    out["collinear_enrichment"] = {
        "pos_frac": n_col / 13,
        "all_o1_frac": n_col_all / 102,
    }

    path = Path(__file__).resolve().parent / "adversarial_brief_supplement.json"
    path.write_text(__import__("json").dumps(out, indent=2) + "\n", encoding="utf-8")
    print(__import__("json").dumps(out, indent=2))


if __name__ == "__main__":
    main()

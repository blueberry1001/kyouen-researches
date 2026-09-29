#!/usr/bin/env python3
"""Diagnostics for B468 orbit-vs-holes and B469 edge-balance fix."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from round5_geom_stats import best_triple_balance, holes_of, window_spectra  # noqa: E402

CENSUS = ROOT / "research" / "verification" / "round3_b451_census.json"


def main():
    with open(ROOT / "research/verification/round5_geom_stats.json", encoding="utf-8") as f:
        d = json.load(f)
    print("ORBIT vs HOLES (raw):")
    for k, v in sorted(d["B468"]["mean_holes_by_orbit"].items(), key=lambda x: int(x[0])):
        print(f"  orbit={k}: n={v['n']} mean_holes={v['mean']:.3f} range=[{v['min']},{v['max']}]")

    print("loading census for controlled pairs...")
    data = json.loads(CENSUS.read_text(encoding="utf-8"))
    pairs_by_ms = defaultdict(list)
    for n_str in ["4", "5", "6", "7", "8"]:
        n = int(n_str)
        rows = data["boards"][n_str].get("rows_m_ge5") or []
        for row in rows:
            pts = [tuple(p) for p in row["pts"]]
            m = row["m"]
            if m > 12:
                continue
            A_sq, _ = window_spectra(pts, n)
            hs = holes_of(A_sq, m)
            d4 = row["d4_orbit"]
            side = row["side"]
            pairs_by_ms[(m, side)].append((d4, len(hs), row.get("q"), row.get("ext")))

    hi = lo = tie = 0
    examples_hi = []
    examples_lo = []
    for key, lst in pairs_by_ms.items():
        if len(lst) < 2:
            continue
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                d1, h1, q1, e1 = lst[i]
                d2, h2, q2, e2 = lst[j]
                if d1 == d2 or h1 == h2:
                    tie += 1
                    continue
                # smaller orbit = more symmetric
                if (d1 < d2 and h1 > h2) or (d2 < d1 and h2 > h1):
                    lo += 1  # more-symmetric has more holes (claim direction)
                    if len(examples_lo) < 5:
                        examples_lo.append(
                            {"ms": key, "more_sym": (min(d1, d2), max(h1, h2) if d1 < d2 else h1),
                             "less_sym": (max(d1, d2), h2 if d1 < d2 else h1),
                             "raw": [(d1, h1, q1, e1), (d2, h2, q2, e2)]}
                        )
                else:
                    hi += 1  # less-symmetric has more holes (against claim)
                    if len(examples_hi) < 5:
                        examples_hi.append(
                            {"ms": key, "more_sym_orbit": min(d1, d2),
                             "more_sym_holes": h2 if d1 > d2 else h1,
                             "less_sym_orbit": max(d1, d2),
                             "less_sym_holes": h1 if d1 > d2 else h2,
                             "raw": [(d1, h1, q1, e1), (d2, h2, q2, e2)]}
                        )
    print("controlled (m,side) pairs among n<=8, m<=12:")
    print("  more-symmetric has MORE holes (claim):", lo)
    print("  less-symmetric has MORE holes (against):", hi)
    print("  ties/same-orbit:", tie)
    print("claim-direction examples:")
    for e in examples_lo:
        print(" ", e)
    print("against examples:")
    for e in examples_hi:
        print(" ", e)

    # B469 fix: require triple to touch all 4 edges? or maximize min edge count
    # Hypothesis: triples on max-m circles vs slightly smaller can forbid 4 borders more equally
    # Metric: among triples, min over 4 edges of occupation (want high min) then min spread
    def triple_score(pts, n):
        """return (min_edge_count, spread) of best triple: maximize min_edge, then min spread."""
        m = len(pts)
        best = None
        for i in range(m):
            for j in range(i + 1, m):
                for k in range(j + 1, m):
                    tri = [pts[i], pts[j], pts[k]]
                    c = [0, 0, 0, 0]
                    for x, y in tri:
                        if x == 0:
                            c[0] += 1
                        if x == n - 1:
                            c[1] += 1
                        if y == 0:
                            c[2] += 1
                        if y == n - 1:
                            c[3] += 1
                    mn = min(c)
                    sp = max(c) - min(c)
                    key = (-mn, sp)  # maximize min, then min spread
                    if best is None or key < best[0]:
                        best = (key, mn, sp, c)
        return best

    print("\nB469 fixed metric (max min-edge, then min spread):")
    b469 = {}
    for n_str in ["8", "9", "10"]:
        n = int(n_str)
        rows = data["boards"][n_str].get("rows_m_ge5") or []
        max_m = data["boards"][n_str]["M_n"]
        tops = [r for r in rows if r["m"] == max_m]
        below = [r for r in rows if max_m - 2 <= r["m"] < max_m]

        def mean_score(rs, cap=12):
            vals = []
            for r in rs[:cap]:
                b = triple_score([tuple(p) for p in r["pts"]], n)
                if b:
                    vals.append(b[1:])  # (min_edge, spread, counts)
            if not vals:
                return None
            return {
                "n": len(vals),
                "mean_min_edge": sum(v[0] for v in vals) / len(vals),
                "mean_spread": sum(v[1] for v in vals) / len(vals),
                "samples": vals[:6],
            }

        mt = mean_score(tops)
        mb = mean_score(below)
        b469[n_str] = {"M_n": max_m, "n_top": len(tops), "n_below": len(below), "top": mt, "below": mb}
        print(f"  n={n} M={max_m} top={mt} below={mb}")

    out = ROOT / "research/verification/round5_geom_stats_extra.json"
    out.write_text(
        json.dumps({"B468_controlled": {"more_sym_more_holes": lo, "less_sym_more_holes": hi, "ties": tie,
                                        "examples_claim": examples_lo, "examples_against": examples_hi},
                    "B469_fixed": b469}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print("wrote", out)


if __name__ == "__main__":
    main()

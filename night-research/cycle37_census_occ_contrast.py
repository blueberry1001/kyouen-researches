#!/usr/bin/env python3
"""Cycle 37 — census occupancy contrast n=6 vs n=7 (COMPLETE from bins)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, load_n6, load_n7, occupancy_vector, orbit_members, cell_key


def main() -> None:
    n7 = load_n7()
    n6 = load_n6()
    m7 = orbit_members(7)
    m6 = orbit_members(6)
    order7 = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3)]
    order6 = sorted(m6.keys())

    def occs(sets, members, order):
        c = Counter()
        empty = Counter()
        for s in sets:
            ov = occupancy_vector(s, 7 if len(members) == 10 or (3, 3) in members else 6)
            # use board size from members keys
            n = 7 if (3, 3) in members or (0, 3) in members else 6
            ov = occupancy_vector(s, n)
            key = tuple(ov.get(k, 0) for k in order)
            c[key] += 1
            for k in order:
                if ov.get(k, 0) == 0:
                    empty[k] += 1
        return c, empty

    # fix occupancy call with correct n
    def occ_n(sets, n, order):
        c = Counter()
        empty_at_max = Counter()
        for s in sets:
            ov = occupancy_vector(s, n)
            key = tuple(ov.get(k, 0) for k in order)
            c[key] += 1
            for k in order:
                if ov.get(k, 0) == 0:
                    empty_at_max[k] += 1
        return c, empty_at_max

    c7, e7 = occ_n(n7, 7, order7)
    c6, e6 = occ_n(n6, 6, order6)

    # shell usage: fraction of max sets using each orbit
    def use_rate(sets, n, order):
        rates = {}
        for k in order:
            used = 0
            for s in sets:
                ov = occupancy_vector(s, n)
                if ov.get(k, 0) > 0:
                    used += 1
            rates[f"{k[0]},{k[1]}"] = {"used": used, "rate": round(used / len(sets), 3)}
        return rates

    results = {
        "n7": {
            "n_sets": len(n7),
            "n_occ_vectors": len(c7),
            "occ_vectors": {",".join(map(str, k)): v for k, v in c7.items()},
            "empty_orbit_counts": {f"{a},{b}": e7.get((a, b), 0) for a, b in order7},
            "use_rate": use_rate(n7, 7, order7),
        },
        "n6": {
            "n_sets": len(n6),
            "n_occ_vectors": len(c6),
            "empty_orbit_counts": {f"{k[0]},{k[1]}": e6.get(k, 0) for k in order6},
            "use_rate": use_rate(n6, 6, order6),
        },
    }
    outp = RES / "cycle37_census_occ_contrast.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "# Cycle 37 — census occupancy contrast n=6 vs n=7 (COMPLETE bins)",
        "",
        f"- n=7: {len(n7)} max sets, **{len(c7)}** occupancy vectors",
        f"- n=6: {len(n6)} max sets, **{len(c6)}** occupancy vectors",
        "",
        "## n=7 occupancy vectors",
        "",
        "| occ (00,01,02,03,11,12,13,22,23,33) | count |",
        "|---|---:|",
    ]
    for k, v in c7.most_common():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Orbit use rate (fraction of max sets with occ>0)", "", "| orbit | n=7 rate | n=6 rate |", "|---|---:|---:|"]
    r7 = results["n7"]["use_rate"]
    r6 = results["n6"]["use_rate"]
    for k in r7:
        r6k = r6.get(k, {})
        lines.append(f"| {k} | {r7[k]['rate']} | {r6k.get('rate','—')} |")
    # n=6 orbits may have different keys
    lines += ["", "## n=6 orbits use rate", "", "| orbit | rate | used |", "|---|---:|---:|"]
    for k, v in r6.items():
        lines.append(f"| {k} | {v['rate']} | {v['used']} |")
    lines += [
        "",
        "n=7 crystallizes to 2 occupancy vectors with (2,2) empty in all;",
        "n=6 stays diffuse with no orbit empty in all max sets.",
        "",
        f"Artifact: `{outp.name}`",
    ]
    md = NR / "CYCLE37_CENSUS_OCC_CONTRAST.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("n7 occ", len(c7), "n6 occ", len(c6))
    print("n7 empty", results["n7"]["empty_orbit_counts"])
    print("n6 empty all?", {k: v for k, v in results["n6"]["empty_orbit_counts"].items() if v == len(n6)})
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()

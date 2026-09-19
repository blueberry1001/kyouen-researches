#!/usr/bin/env python3
"""Cycle 32 — cross-shell (multi-orbit) forbidden-quad census n=4..8."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, cell_key, forbidden_quads, xy


def main() -> None:
    results = {}
    for n in (4, 5, 6, 7, 8):
        quads = forbidden_quads(n)
        single = multi = 0
        by_nkeys = Counter()
        for q in quads:
            ks = {cell_key(n, *xy(p, n)) for p in q}
            if len(ks) == 1:
                single += 1
            else:
                multi += 1
                by_nkeys[len(ks)] += 1
        results[n] = {
            "n_quads": len(quads),
            "single_orbit": single,
            "multi_orbit": multi,
            "multi_pct": round(100 * multi / len(quads), 2) if quads else 0,
            "by_n_distinct_orbits": dict(sorted(by_nkeys.items())),
        }
        print(n, results[n], flush=True)
    outp = RES / "cycle32_cross_shell_quads.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# Cycle 32 — cross-shell forbidden quads (COMPLETE local)",
        "",
        "A quad is *cross-shell* if its four points lie in ≥2 distinct D4 orbits",
        "(radial shells about the board center).",
        "",
        "| n | #quads | single-orbit | multi-orbit | multi% | by #distinct orbits |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for n, r in results.items():
        lines.append(
            f"| {n} | {r['n_quads']} | {r['single_orbit']} | {r['multi_orbit']} | "
            f"{r['multi_pct']} | {r['by_n_distinct_orbits']} |"
        )
    lines += [
        "",
        "Interpretation: local orbit-circles (single-orbit quads) are the",
        "universal ceiling-3 mechanism. Cross-shell quads are what cut the",
        "naive Σ3 down to K_n and, on n=7 only, reorganize the maximum into",
        "a two-phase crystal with an empty shell (2,2).",
        "",
        "Artifacts: `results/cycle32_cross_shell_quads.json`",
    ]
    md = NR / "CYCLE32_CROSS_SHELL_QUADS.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()

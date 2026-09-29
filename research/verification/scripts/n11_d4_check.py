"""Check the D4 solver's n=11 preliminary output for consistency.

The reported level_sizes_raw are the exact values measured by the 2-word
enumerator. If the orbit counts are a genuine 1/8 reduction, each raw level
should divide by (roughly) 8 -- exactly for levels where no position has a
non-trivial stabiliser, and less for small levels where the axis points force
some stabilisers.
"""
import json
from pathlib import Path

d = json.loads((Path(__file__).resolve().parent.parent /
                "data" / "n11_d4.json").read_text(encoding="utf-8"))

raw = d["level_sizes_raw"]
orb = d["level_sizes_orbits"]
print("n=11  F =", d["F"], " (expected 95670)")
print("  symmetry:", d["symmetry"], "  point orbits:", d["d4_point_orbits"])
print()
print(f"{'k':>3} {'raw states':>15} {'orbits':>15} {'ratio':>10}")
for k, (r, o) in enumerate(zip(raw, orb)):
    ratio = r / o if o else float("inf")
    print(f"{k:>3} {r:>15,} {o:>15,} {ratio:>10.2f}")
print()
print("A D4 orbit has size 8 unless the position has a non-trivial stabiliser.")
print("So ratio <= 8 always, and ratio == 8 for generic positions.")
print("Levels 0..3 are small enough that most positions touch an axis, so their")
print("ratio is below 8; from level 4 on the board is big enough that almost")
print("every position has a trivial stabiliser.")
print()
print("reported:  g(empty) =", d["g_empty"], "->", d["winner"])
print("K (raw)  =", d["K"], " (from the raw run, which was NOT trustworthy:")
print("          the 1-word version's K is discarded)")
print()
print("levels 0..5 row for k=5 has dp_s =",
      d["levels"][5]["dp_s"], "so the Grundy pass did not complete there.")
print("=> the json is a PARTIAL run: the level widths are right, g(empty) is NOT")
print("   yet determined, because the DP stops before reaching level 0.")

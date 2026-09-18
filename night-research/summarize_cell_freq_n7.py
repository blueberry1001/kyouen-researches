#!/usr/bin/env python3
"""Summarize n=7 K=14 cell frequencies by D4 cell orbit."""

import csv
from collections import defaultdict

rows = list(csv.DictReader(open("results/maxsafe_cell_frequency_n7.csv")))
agg = defaultdict(lambda: {"orbit_size": 0, "freq": 0, "cells": 0})
for r in rows:
    key = (int(r["orbit_rep_x"]), int(r["orbit_rep_y"]))
    agg[key]["orbit_size"] = int(r["orbit_size"])
    agg[key]["freq"] += int(r["freq"])
    agg[key]["cells"] += 1

print("n=7 K=14 cell frequency by D4 cell orbit (16 maximal sets total):")
print(f"{'rep':>8} {'orbit_size':>10} {'cells':>6} {'total_freq':>10} {'per_cell_avg':>12} {'per_orbit_avg':>13}")
for k in sorted(agg, key=lambda t: (max(t), t)):
    v = agg[k]
    per_cell = v["freq"] / v["cells"]
    per_orbit = v["freq"] / v["orbit_size"]
    print(f"{str(k):>8} {v['orbit_size']:>10} {v['cells']:>6} {v['freq']:>10} {per_cell:>12.2f} {per_orbit:>13.2f}")

# also raw per-point for the two orbit reps
print()
print("raw frequencies at orbit representative cells:")
for r in rows:
    if (int(r["x"]), int(r["y"])) == (int(r["orbit_rep_x"]), int(r["orbit_rep_y"])):
        print(f"  cell ({r['x']},{r['y']}) orbit_size={r['orbit_size']} freq={r['freq']}")

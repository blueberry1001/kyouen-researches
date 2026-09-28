"""Locate the child-lookup in the prand solver and report the hot spots.

The n=7 run took 1225 s with ~1.5e9 edges. For n=8 the edge count is roughly
10x that, so the per-edge `std::lower_bound` over a 1.4e8-entry level is the
first thing to fix: it is O(log N) per edge with terrible cache behaviour.
"""
import re
from pathlib import Path

p = Path(__file__).resolve().parent / "round4_b501_prand.cpp"
src = p.read_text(encoding="utf-8")

for pat in ("lower_bound", "bn_add", "std::sort", "std::unique",
            "legal_level", "MAXL", "W_next", "W_acc"):
    n = src.count(pat)
    print(f"{pat:14s} occurrences: {n}")

print()
print("MAXL definition:")
for i, line in enumerate(src.splitlines(), 1):
    if "MAXL" in line and ("define" in line or "const int" in line or "static" in line):
        print(f"  {i}: {line.strip()}")

print()
print("hot-loop lines (lower_bound / bn_add inside omp):")
for i, line in enumerate(src.splitlines(), 1):
    if "lower_bound" in line or ("bn_add" in line and "a," in line):
        print(f"  {i}: {line.strip()}")

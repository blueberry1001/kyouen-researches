"""Cross-check the 2-word spill against the 1-word measurement.

The 1-word probe reported (n=11):
  [1,121,7007,228485,3863862,29108488,82177064,72669632,15795232,572800,1536]
The 2-word enumerator stores each state as 16 bytes, so the file size divided
by 16 must reproduce that sequence. Any disagreement means one of the two is
wrong, and the 1-word run is not usable for n=11 (it shifts by 64 when v >= 64).
"""
from pathlib import Path

SPILL = Path("/tmp/n11_121")
EXPECT_1WORD = [1, 121, 7007, 228485, 3863862, 29108488,
                82177064, 72669632, 15795232, 572800, 1536]

print(f"{'k':>3} {'bytes':>14} {'/16':>14} {'expected':>14}  match")
ok_all = True
for k, exp in enumerate(EXPECT_1WORD):
    p = SPILL / f"level_{k}.occ"
    if not p.exists():
        print(f"{k:>3} {'(absent)':>14} {'':>14} {exp:>14}")
        continue
    n = p.stat().st_size // 16
    # a trailing partial record would mean the file is still being written
    rem = p.stat().st_size % 16
    mark = "OK" if n == exp else "MISMATCH"
    if n != exp:
        ok_all = False
    print(f"{k:>3} {p.stat().st_size:>14,} {n:>14,} {exp:>14,}  {mark}"
          + (f"  (partial {rem} B)" if rem else ""))

print()
print("all levels agree" if ok_all else "DISAGREEMENT -- see MISMATCH rows")
print()
tot = 0
for k, exp in enumerate(EXPECT_1WORD):
    p = SPILL / f"level_{k}.occ"
    if p.exists():
        tot += exp
print(f"total states (from expected): {tot:,}")
print(f"total spill bytes on disk   : "
      f"{sum(p.stat().st_size for p in SPILL.glob('level_*.occ')):,}")

"""Project the n=8 p_rand cost from the exact n=7 figures.

n=7 ran with MAXL=48 and peaked at 10.5 GB RSS. Two independent estimates of
the n=8 requirement are produced: one from the forbidden-quad ratio, one from
the empirical level-growth ratio n=5 -> n=6 -> n=7.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d7 = json.loads((ROOT / "round4_b501_prand_n7.json").read_text(encoding="utf-8"))
lv7 = d7["level_sizes"]
print("n=7 levels:")
for x in d7["levels"]:
    print(f"  k={x['k']:2d} states={x['size']:>12,} edges={x['edges']:>13,}"
          f" P={x['n_P']:>10,} D_digits={x['D_digits']:>4}")
print(f"  total states {sum(lv7):>14,}")
print(f"  total edges  {d7['edge_total']:>14,}")
print()

# growth of the widest level across the sizes we have exactly
dref = json.loads((ROOT / "round4_b501_prand.json").read_text(encoding="utf-8"))
lv6 = dref["n6"]["level_sizes"]
print("widest level by n:")
for name, lv in (("n=5", json.loads((ROOT / "round4_b501_prand.json").read_text(encoding="utf-8"))["n5"]["level_sizes"]),
                 ("n=6", lv6), ("n=7", lv7)):
    print(f"  {name}: {max(lv):>12,}  at k={lv.index(max(lv))}  total={sum(lv):>13,}")
print()

peak6, peak7 = max(lv6), max(lv7)
r_peak = peak7 / peak6
r_tot = sum(lv7) / sum(lv6)
r_quad = 6364 / 2491
print(f"widest-level growth n6->n7 : {r_peak:.2f}x")
print(f"total-state  growth n6->n7 : {r_tot:.2f}x")
print(f"F_7/F_6                    : {r_quad:.2f}x")
print()

PEAK_RSS_N7_GB = 10.5
for name, r in (("widest-level ratio", r_peak), ("total-state ratio", r_tot),
                ("F ratio", r_quad)):
    print(f"  n=8 estimate via {name:20s}: {PEAK_RSS_N7_GB * r:6.1f} GB")
print()
print(f"  WSL box: 19.7 GB total, ~12 GB currently free (other agents running)")
print()
print("MAXL effect: numerator 48 limbs -> 20 limbs = 2.4x less per state.")
print("If the numerator dominates, n=8 at 30x needs 10.5*30/2.4 = 131 GB -> impossible.")
print("If the level vectors dominate (8 B/state) and only two levels are resident,")
print("the peak is ~ (1.4e8 * 8 B * 2 + 1.4e8 * 80 B) = 13.4 GB -> marginal.")
print()
print("Conclusion: n=8 p_rand needs a streaming two-level implementation with a")
print("compact numerator representation. A 128-bit *approximate* DP would not be")
print("exact, but a modular (CRT over several primes) DP is exact and needs only")
print("64-128 bits per state instead of 180 decimal digits.")

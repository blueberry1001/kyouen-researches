"""Project the n=11 state space from the measured layers so far.

Reads the live probe log, fits the growth, and reports what the peak layer and
total look like under two models (per-layer growth and the level-width ratio
that was calibrated on n=6 and n=7).
"""
import re
from pathlib import Path

LOG = Path("/tmp/n11_probe.log")
txt = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""
rows = re.findall(r"^  level (\d+): (\d+) states", txt, re.M)
lv = [(int(k), int(n)) for k, n in rows]
if not lv:
    print("no level lines yet")
    raise SystemExit

print("measured levels for n=11:")
tot = 0
for k, n in lv:
    tot += n
    print(f"  k={k:2d}  {n:>14,}   (cum {tot:,})")

# growth of the widest level, n=6 -> n=7 was 31.9x; the v-max probe at n=8
# suggested the *sorted* construction behaves differently, so report both.
ratios = [lv[i][1] / lv[i - 1][1] for i in range(1, len(lv))]
if ratios:
    print()
    print("level-to-level growth ratios:")
    print("  " + ", ".join(f"k{a[0]}->k{b[0]}: {b[1]/a[1]:.2f}x"
                          for a, b in zip(lv, lv[1:])))

widest_k, widest = max(lv, key=lambda t: t[1])
print()
print(f"widest so far: k={widest_k} with {widest:,} states")
print(f"  8 B/state  = {widest * 8 / 2**30:.2f} GiB")
print(f"  16 B/state = {widest * 16 / 2**30:.2f} GiB  (2-word masks)")

# simple extrapolation: assume the last observed growth ratio continues
if len(ratios) >= 2:
    g = ratios[-1]
    print()
    print(f"if the last ratio ({g:.2f}x) continues:")
    est = widest
    for k in range(widest_k + 1, 25):
        est *= g
        print(f"  k={k:2d}  ~{est:>16,.0f}   16 B = {est * 16 / 2**30:8.1f} GiB")
        if est * 16 / 2**30 > 200:
            print("      (exceeds any plausible disk budget)")
            break

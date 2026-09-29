"""Track the 2-word n=11 enumeration and project the peak level.

The 1-word run is discarded (it loses bits above 63). This reads the 2-word log
and reports the measured layers plus a projection that accounts for the
geometric decay of the growth ratio, which is what the n=11 data actually shows
rather than a constant-ratio guess.
"""
import re
from pathlib import Path

LOG = Path("/tmp/n11_121.log")
txt = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""
rows = re.findall(r"^  level (\d+): (\d+) states", txt, re.M)
lv = [(int(k), int(n)) for k, n in rows]
if not lv:
    print("no levels yet")
    raise SystemExit

print("n=11 measured layers (2-word, trustworthy):")
cum = 0
for k, n in lv:
    cum += n
    print(f"  k={k:2d}  {n:>16,}   cum {cum:>18,}")

ratios = [lv[i][1] / lv[i - 1][1] for i in range(1, len(lv))]
if ratios:
    print()
    print("growth ratios: " + ", ".join(f"{r:.2f}x" for r in ratios))

wk, wv = max(lv, key=lambda t: t[1])
print()
print(f"widest so far: k={wk}  {wv:,} states")
print(f"  16 B/state (2-word mask) = {wv * 16 / 2**30:.2f} GiB")
print(f"  plus a legal-move mask per state would be {wv * 24 / 2**30:.2f} GiB")

# The observed ratios decay roughly geometrically once past the peak, but on the
# rising side they also decay. Model r_{k+1} = r_k * q with q estimated from the
# last two ratios, which is the empirically observed shape.
if len(ratios) >= 2:
    q = (ratios[-1] / ratios[-2]) ** 0.5 if ratios[-2] else 1.0
    r = ratios[-1]
    est = lv[-1][1]
    print()
    print(f"modelled with ratio r_k = r_(k-1) * q, q = {q:.3f} (geometric decay of ratios):")
    for k in range(lv[-1][0] + 1, 26):
        r *= q
        est *= r
        gb = est * 16 / 2**30
        print(f"  k={k:2d}  ~{est:>18,.0f}   16 B = {gb:9.1f} GiB")
        if gb > 400:
            print("      (beyond any plausible budget)")
            break
        if r < 0.05:
            print("      (peak passed, layers now shrinking)")
            break

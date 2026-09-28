"""Locate the P_gt_2_3 discrepancy: CRT says 244, reference says 180.

P_gt_1_2 (11636) and P_gt_3_4 (4) match exactly, so the threshold logic itself
is right. 2/3 is the odd one out, which points at the test rather than the DP:
3*num > 2*D is not equivalent to num/D > 2/3 once the comparison is done in a
residue field, because 3*num and 2*D are both reduced mod P before comparing.
2/3 is exactly the threshold where the 3-vs-2 comparison can wrap.
"""
import json
from pathlib import Path

P1 = (1 << 61) - 1
d = json.loads(Path("/tmp/crt_n6.json").read_text(encoding="utf-8"))
ref = json.loads(
    Path("/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/"
         "round3_b502_pgrand_n6.json").read_text(encoding="utf-8"))["n6"]

print("field p =", P1)
print()
print("counts:  1/2   2/3   3/4")
print("  crt :", d["P_gt_1_2"], d["P_gt_2_3"], d["P_gt_3_4"])
print("  ref :", ref["P_gt_1_2"], ref["P_gt_2_3"], ref["P_gt_3_4"])
print()

# D_bits per level tells us where 2*Dbits >= 61, i.e. where the residue
# comparison stops being exact. The solver flags those levels.
print("per-level D_bits and exactness:")
for lev in d["levels"]:
    if lev["n_P"]:
        print(f"  k={lev['k']:2d} n_P={lev['n_P']:>9,} D_bits={lev['D_bits']:>6.1f} "
              f"thresholds_exact={lev['thresholds_exact']}")
print()
bad = [lev["k"] for lev in d["levels"] if lev["n_P"] and not lev["thresholds_exact"]]
print("levels where thresholds are NOT exact:", bad)
if bad:
    k0 = min(bad)
    print(f"  the lowest inexact level is k={k0}; its D has 2^{lev.D_bits:.0f} bits")
    print("  with P1 = 2^61-1, a value p/D compares exactly only while 2*D_bits < 61")
    print("  so every level from k=%d upward is reporting wrapped comparisons" % k0)

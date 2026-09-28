"""Estimate the n=7 layer widths and the memory the solver would need.

We extrapolate the layer-size sequence from the exact n=6 run and check
whether the two-adjacent-levels-only invariant in the solver is actually
respected, or whether enumerate_levels keeps every level resident.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "round4_b501_prand.json").read_text(encoding="utf-8"))

n6 = d["n6"]
lv6 = n6["level_sizes"]
dig6 = n6["per_level_denominator_digits"]
print("n=6 level sizes :", lv6)
print("n=6 D digits    :", dig6)
print("n=6 total states:", f"{sum(lv6):,}")
print()

# The forbidden-quad count scales like n^4; the number of safe sets is a
# weighted sum over layers. Empirically n=4->5->6 totals:
for f, n in (("n4", 4), ("n5", 5), ("n6", 6)):
    if f in d:
        tot = sum(d[f]["level_sizes"])
        print(f"n={n}: total {tot:>12,}  peak level {max(d[f]['level_sizes']):>10,}")

# ratio of consecutive peak levels
peaks = [max(d[f]["level_sizes"]) for f in ("n4", "n5", "n6") if f in d]
print("\npeak levels:", [f"{p:,}" for p in peaks])
print("peak growth n5->n6:", f"{peaks[-1]/peaks[-2]:.2f}x")

# n=7 estimate: the peak layer sits at k = K/2, and K_7 = 14, so the peak is
# near k=7. The n=6 peak was at k=7 with 1,783,296 states out of 5,081,289.
# Extrapolating the *share* of the peak level is safer than the absolute count.
share6 = peaks[-1] / sum(lv6)
print(f"\nn=6 peak share of total: {share6:.4f}")

# A conservative absolute estimate: quad count ratio F_7/F_6 = 6364/2491 = 2.555.
# The number of safe k-sets grows roughly like F^(k/4) for fixed k, so the
# peak layer should grow faster than linearly in F.
fq = 6364 / 2491
print(f"F_7/F_6 = {fq:.3f}")
for k, base in ((7, 1783296),):
    for mult, why in ((1.0, "linear in F"), (fq, "∝F"), (fq**2, "∝F^2"), (fq**3, "∝F^3")):
        est = base * mult
        print(f"  peak k={k} {why:12s}: {est:>15,.0f}")

print()
print("Memory per state in the hot loop:")
print("  legal-move mask  u64      8 B")
print("  bigint numerator 2-4 limbs (9 B each) + header  ~ 24-48 B")
print("  plus the level vector's own u64 mask          8 B")
print("  => roughly 40-64 B per state in the widest level")
print()
for label, n_states in (("n=6 peak", 1783296), ("n=7 optimistic", 1783296 * fq**2),
                        ("n=7 pessimistic", 1783296 * fq**3)):
    lo = n_states * 40 / 2**30
    hi = n_states * 64 / 2**30
    print(f"  {label:16s} {n_states:>14,.0f} states -> {lo:6.2f} .. {hi:6.2f} GiB")
print()
print("If ALL levels stay resident (not just two), multiply by total/peak.")
tot7_opt = 1783296 * fq**2 / share6
print(f"  all levels resident, n=7 total {tot7_opt:,.0f} states -> "
      f"{tot7_opt*40/2**30:.1f} .. {tot7_opt*64/2**30:.1f} GiB")

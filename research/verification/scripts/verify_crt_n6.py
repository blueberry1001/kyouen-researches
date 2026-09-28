"""Check the CRT solver's P_max against the reference, allowing for reduction.

The solver reports num mod P1 together with D mod P1. The reference value
a/b may be a *reduced* fraction of the same rational, so the comparison must be
done on the value num/D, not on the raw numerator. In the field mod P1 that
means num * inverse(D) == a * inverse(b), which is what this checks.
"""
import json
from pathlib import Path

P1 = (1 << 61) - 1
ROOT = Path(__file__).resolve().parent.parent


def inv(a, m):
    return pow(a % m, m - 2, m)


def check(tag, got_num, got_den, ref_num, ref_den, json_path):
    d = json.loads(Path(json_path).read_text(encoding="utf-8"))
    gn = int(d["P_max_num_mod_p1"])
    gd = int(d["P_max_den_Dbits"])
    # the solver also stores the level's best fraction exactly when it fits
    print(f"--- {tag} ---")
    print(f"  reference      = {ref_num}/{ref_den}")
    print(f"  solver num mod = {gn}")
    print(f"  D bits         = {gd}")
    # the global max is taken across levels, each with its own D_k; find the
    # level whose D is the one that produced the reported numerator
    for lev in d["levels"]:
        if lev.get("best_num_mod_p1") == str(gn):
            bd = int(lev["best_D_mod_p1"])
            print(f"  matching level k={lev['k']}  D mod P1 = {bd}")
            lhs = gn * inv(bd, P1) % P1
            rhs = ref_num * inv(ref_den, P1) % P1
            print(f"  value  = num*inv(D) = {lhs}")
            print(f"  want   = a*inv(b)   = {rhs}")
            print(f"  MATCH: {lhs == rhs}")
            return lhs == rhs
    print("  no level matched the reported numerator; level maxima:")
    for lev in d["levels"]:
        if lev.get("best_count"):
            print(f"    k={lev['k']:2d} num={lev['best_num_mod_p1']} "
                  f"D={lev['best_D_mod_p1']} count={lev['best_count']}")
    return False


# n=6: the solver ran to completion and the thresholds matched exactly
d6 = json.loads(Path("/tmp/crt_n6.json").read_text(encoding="utf-8")) if Path("/tmp/crt_n6.json").exists() else None
print("n=6 threshold check (exact, no CRT involved):")
if d6:
    print(f"  n_safe_subsets = {d6['n_safe_subsets']}  (expect 5081289)")
    print(f"  edge_total     = {d6['edge_total']}  (expect 36211148)")
    print(f"  P_gt_3_4       = {d6['P_gt_3_4']}  (expect 4)")
    print(f"  P_gt_2_3       = {d6['P_gt_2_3']}  (expect 180)")
    print(f"  P_gt_1_2       = {d6['P_gt_1_2']}  (expect 11636)")
    print(f"  n_P            = {d6['n_P']}  (expect 1265112)")
    print(f"  peak_rss_gb    = {d6['peak_rss_gb']}")

#!/usr/bin/env python3
"""Parse stream solver JSON and compare against known values."""
import json, sys, os

KNOWN = {
    6: {
        "n_safe_subsets": 5081289,
        "level_sizes": [1,36,630,7140,56414,301952,997796,1783296,1459292,438952,35316,464],
        "edge_total": 36211148,
        "n_P": 1265112,
        "n_N": 3816177,
        "P_max_level": 5,
    },
    7: {
        "n_safe_subsets": 179810350,
        "level_sizes": [1,49,1176,18424,205512,1633048,8796600,29688640,56927728,55173324,23478868,3707028,177760,2176,16],
        "edge_total": 1499354401,
        "n_P": 41264615,
        "n_N": 138545735,
        "P_max_level": 8,
    },
    8: {
        # unknown yet
    },
}

def main():
    path = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else None
    d = json.load(open(path))
    if n is None:
        n = d["n"]
    print(f"=== n={n} stream solver results ===")
    print(f"  n_safe_subsets  {d['n_safe_subsets']}")
    print(f"  level_sizes     {d['level_sizes']}")
    print(f"  edge_total      {d['edge_total']}")
    print(f"  n_P             {d['n_P']}")
    print(f"  n_N             {d['n_N']}")
    print(f"  P_max_level     {d.get('P_max_level')}")
    print(f"  P_max_filter    {d.get('P_max_filter_value')}")
    print(f"  thresholds_exact_all_levels {d.get('thresholds_exact_all_levels')}")
    print(f"  peak_rss_gb     {d.get('peak_rss_gb')}")
    print(f"  timing          {d.get('timing_s')}")
    print(f"  per-level:")
    for lv in d.get("levels", []):
        print(f"    k={lv['k']:2d} size={lv['size']:12d} edges={lv['edges']:12d} "
              f"nP={lv['n_P']:9d} nN={lv['n_N']:9d} Dbits={lv['D_bits']:6.1f} "
              f"exact={lv['thresholds_exact']} best={lv['best_filter']:.12f} x{lv['best_count']}")

    known = KNOWN.get(n, {})
    if known:
        print(f"\n=== CROSS-CHECK vs known n={n} ===")
        ok_all = True
        for key in ["n_safe_subsets", "edge_total", "n_P", "n_N", "P_max_level"]:
            if key in known:
                got = d.get(key)
                exp = known[key]
                ok = got == exp
                ok_all = ok_all and ok
                mark = "OK" if ok else "MISMATCH"
                print(f"  {key:20s} got={got}  expected={exp}  [{mark}]")
        if "level_sizes" in known:
            got = d["level_sizes"]
            exp = known["level_sizes"]
            ok = got == exp
            ok_all = ok_all and ok
            mark = "OK" if ok else "MISMATCH"
            print(f"  {'level_sizes':20s} [{mark}]")
            if not ok:
                print(f"    got: {got}")
                print(f"    exp: {exp}")
        print(f"\n  OVERALL: {'PASS' if ok_all else 'FAIL'}")
        return 0 if ok_all else 1
    else:
        print(f"\n  (no known values for n={n}; structural report only)")
        return 0

if __name__ == "__main__":
    sys.exit(main())

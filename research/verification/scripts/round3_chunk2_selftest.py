#!/usr/bin/env python3
"""Self-test for round3_chunk2_geom: verify F_n against PROTOCOL, collinear split."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round3_chunk2_geom import all_quads, det4, line_quads, circle_quads

EXPECT = {2: 1, 3: 14, 4: 194, 5: 826, 6: 2491, 7: 6364, 8: 14564, 9: 29152}
EXPECT_D = {2: 0, 3: 0, 4: 10, 5: 64, 6: 234, 7: 660, 8: 1524, 9: 3156,
            10: 5928, 11: 10428, 12: 17154}


def main() -> int:
    out = {}
    ok = True
    for n in range(2, 8):
        quads, st = all_quads(n, verify=True)
        lq = line_quads(n)
        out[n] = st
        f_exp = EXPECT.get(n)
        d_exp = EXPECT_D.get(n)
        if f_exp is not None and st["n_quads"] != f_exp:
            ok = False
            print(f"n={n}: F={st['n_quads']} != {f_exp}")
        if d_exp is not None and st["n_line_quads"] != d_exp:
            ok = False
            print(f"n={n}: D={st['n_line_quads']} != {d_exp}")
        print(f"n={n}: F={st['n_quads']} (exp {f_exp})  D={st['n_line_quads']}"
              f" (exp {d_exp})  C={st['n_circ_quads']}", flush=True)
    # n>=8: no full triple enumeration, use the line decomposition only
    for n in (8, 9, 10, 11, 12):
        lq = line_quads(n)
        print(f"n={n}: D={len(lq)} (exp {EXPECT_D[n]})", flush=True)
        if len(lq) != EXPECT_D[n]:
            ok = False
        out[f"D{n}"] = len(lq)
    print("VERIFY_OK" if ok else "VERIFY_FAIL")
    out["ok"] = ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

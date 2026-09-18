#!/usr/bin/env python3
"""Independent verification of Cycle 8–11 COMPLETE claims (no exe required)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import RES, cell_key, load_n6, load_n7, occupancy_vector, stones  # noqa: E402

N7, N6 = 7, 6
CORNERS7 = [0, 6, 42, 48]
CENTER7 = 24
O03 = [0 * 7 + 3, 6 * 7 + 3, 3 * 7 + 0, 3 * 7 + 6]
O23 = [2 * 7 + 3, 4 * 7 + 3, 3 * 7 + 2, 3 * 7 + 4]
O22 = [2 * 7 + 2, 4 * 7 + 2, 2 * 7 + 4, 4 * 7 + 4]


def orbits(n):
    mem = {}
    for y in range(n):
        for x in range(n):
            mem.setdefault(cell_key(n, x, y), []).append(y * n + x)
    return mem


def main():
    n7, n6 = load_n7(), load_n6()
    checks = []

    def rec(name, ok, detail):
        checks.append((name, ok, detail))

    rec("n7_count_16", len(n7) == 16, len(n7))
    rec("n6_count_464", len(n6) == 464, len(n6))

    # occupancy distinct
    mem7 = orbits(7)
    keys7 = sorted(mem7)
    vecs = Counter()
    for s in n7:
        vecs[tuple(occupancy_vector(s, 7)[k] for k in keys7)] += 1
    rec("n7_two_occupancy", len(vecs) == 2, len(vecs))

    # phase characterization
    A = [s for s in n7 if (s >> CENTER7) & 1]
    B = [s for s in n7 if not (s >> CENTER7) & 1]
    rec("n7_split_8_8", len(A) == 8 and len(B) == 8, (len(A), len(B)))
    okA = all(
        sum(1 for p in CORNERS7 if (s >> p) & 1) == 2
        and not any((s >> p) & 1 for p in O03 + O23 + O22)
        for s in A
    )
    okB = all(
        sum(1 for p in CORNERS7 if (s >> p) & 1) == 3
        and any((s >> p) & 1 for p in O03)
        and sum(1 for p in O23 if (s >> p) & 1) >= 2
        and not any((s >> p) & 1 for p in O22)
        for s in B
    )
    rec("n7_A_shape", okA, None)
    rec("n7_B_shape", okB, None)

    # mandatory / never on n=7
    mem = mem7
    mand7 = []
    never7 = []
    for k, pts in sorted(mem.items()):
        used = sum(1 for s in n7 if any((s >> p) & 1 for p in pts))
        if used == len(n7):
            mand7.append(k)
        if used == 0:
            never7.append(k)
    rec(
        "n7_mandatory_six",
        mand7 == [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (1, 3)],
        mand7,
    )
    rec("n7_never_22", never7 == [(2, 2)], never7)

    # n=6
    mem6 = orbits(6)
    vecs6 = Counter()
    for s in n6:
        vecs6[tuple(sum(1 for p in mem6[k] if (s >> p) & 1) for k in sorted(mem6))] += 1
    rec("n6_occupancy_22", len(vecs6) == 22, len(vecs6))
    used22 = sum(1 for s in n6 if any((s >> p) & 1 for p in mem6[(2, 2)]))
    rec("n6_uses22_360", used22 == 360, used22)
    mand6 = []
    never6 = []
    for k, pts in sorted(mem6.items()):
        used = sum(1 for s in n6 if any((s >> p) & 1 for p in pts))
        if used == len(n6):
            mand6.append(k)
        if used == 0:
            never6.append(k)
    rec("n6_mandatory_four", mand6 == [(0, 0), (0, 1), (0, 2), (1, 2)], mand6)
    rec("n6_never_empty", never6 == [], never6)

    # 1-swap
    s7 = set(n7)
    sw7 = 0
    for s in n7:
        for v in range(49):
            if (s >> v) & 1:
                continue
            for r in stones(s, 49):
                if ((s & ~(1 << r)) | (1 << v)) in s7:
                    sw7 += 1
    rec("n7_zero_1swap", sw7 == 0, sw7)

    out = {"checks": [], "all_pass": True}
    print("Cycle 8–11 independent verification")
    for name, ok, detail in checks:
        st = "PASS" if ok else "FAIL"
        print(f"  [{st}] {name}: {detail}")
        out["checks"].append({"name": name, "pass": bool(ok), "detail": detail})
        if not ok:
            out["all_pass"] = False
    path = RES / "cycle11_verify.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Wrote", path)
    if not out["all_pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

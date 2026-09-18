#!/usr/bin/env python3
"""Cycle 8 independent verification of main lemmas.

Does not import conclusions from analysis narratives; recomputes from bins
and re-runs cheap target searches.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (  # noqa: E402
    RES,
    apply_perm,
    d4_perms,
    is_safe,
    load_n6,
    load_n7,
    occupancy_vector,
    stones,
    forbidden_quads,
    det4,
)
from cycle8_exists_k import TargetSearch, build_triples  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    n7 = load_n7()
    n6 = load_n6()
    perms7 = d4_perms(7)
    quads7 = forbidden_quads(7)
    triples7, nq7 = build_triples(7)
    checks = []

    # 1. all 16 are safe K=14
    ok = all(s.bit_count() == 14 and is_safe(s, quads7) for s in n7)
    checks.append(("n7_16_safe_K14", ok, len(n7)))

    # 2. occupancy: exactly 2 distinct vectors
    keys = sorted(occupancy_vector(n7[0], 7).keys())
    vecs = {tuple(occupancy_vector(s, 7)[k] for k in keys) for s in n7}
    checks.append(("n7_two_occupancy_vectors", len(vecs) == 2, len(vecs)))

    # 3. (2,2) never used; center XOR exclusive with (0,3)/(2,3) on the 16
    o22 = [2 * 7 + 2, 4 * 7 + 2, 2 * 7 + 4, 4 * 7 + 4]
    center = 24
    o03 = [0 * 7 + 3, 6 * 7 + 3, 3 * 7 + 0, 3 * 7 + 6]
    o23 = [2 * 7 + 3, 4 * 7 + 3, 3 * 7 + 2, 3 * 7 + 4]
    never22 = all((s >> p) & 1 == 0 for s in n7 for p in o22)
    checks.append(("n7_orbit22_never", never22, 0))
    excl = True
    for s in n7:
        has_c = (s >> center) & 1
        has_o = any((s >> p) & 1 for p in o03 + o23)
        if has_c and has_o:
            excl = False
    checks.append(("n7_center_excl_03_23_on16", excl, None))

    # 4. d=5 template: pair (0,8) split and D4 uniqueness of exchange
    A, B = n7[0], n7[8]
    inter, onlyA, onlyB = A & B, A & ~B, B & ~A
    split_ok = (
        inter.bit_count() == 9
        and onlyA.bit_count() == 5
        and onlyB.bit_count() == 5
        and (A >> center) & 1
        and not (B >> center) & 1
    )
    checks.append(("d5_pair0_8_split_9_5_5", split_ok, (inter.bit_count(), onlyA.bit_count(), onlyB.bit_count())))

    # D4 uniqueness among all pairs at d=5
    def d(mask, other):
        return 14 - (mask & other).bit_count()

    d5 = [(i, j) for i in range(16) for j in range(i + 1, 16) if d(n7[i], n7[j]) == 5]
    checks.append(("d5_pair_count_8", len(d5) == 8, len(d5)))
    pair_keys = set()
    sym_keys = set()
    ex_keys = set()
    for i, j in d5:
        best_pair = min(
            (min(apply_perm(n7[i], p), apply_perm(n7[j], p)),
             max(apply_perm(n7[i], p), apply_perm(n7[j], p)))
            for p in perms7
        )
        pair_keys.add(best_pair)
        Si = n7[i] & n7[j]
        onlyi, onlyj = n7[i] & ~n7[j], n7[j] & ~n7[i]
        sym_keys.add(min(apply_perm(onlyi | onlyj, p) for p in perms7))
        ex_keys.add((min(apply_perm(onlyi, p) for p in perms7),
                     min(apply_perm(onlyj, p) for p in perms7)))
    checks.append(("d5_pair_d4_unique", len(pair_keys) == 1, len(pair_keys)))
    checks.append(("d5_symdiff_d4_unique", len(sym_keys) == 1, len(sym_keys)))
    checks.append(("d5_exchange_oriented_unique_or_2", len(ex_keys) <= 2, len(ex_keys)))

    # 5. unique 13-subset completion among the 16
    # for each 13-subset of a max set, count how many of the 16 contain it
    nonunique = 0
    total = 0
    for s in n7:
        pts = stones(s, 49)
        for r in pts:
            sub = s & ~(1 << r)
            total += 1
            cnt = sum(1 for t in n7 if (t & sub) == sub)
            if cnt != 1:
                nonunique += 1
    checks.append(("unique_13_completion_224", nonunique == 0 and total == 224, (total, nonunique)))

    # 6. min_det=2 on all 16; min_det>=3 on n=6 sample of all
    def min_det(S, family):
        pts = stones(S, 49 if S.bit_count() == 14 else 36)
        # pairwise
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                pair = (1 << pts[i]) | (1 << pts[j])
                if sum(1 for t in family if (t & pair) == pair) == 1:
                    return 2, (pts[i], pts[j])
        # size 3
        from itertools import combinations

        for comb in combinations(pts, 3):
            m = 1 << comb[0] | 1 << comb[1] | 1 << comb[2]
            if sum(1 for t in family if (t & m) == m) == 1:
                return 3, comb
        return 99, None

    md7 = [min_det(s, n7)[0] for s in n7]
    checks.append(("min_det_all_2_n7", all(x == 2 for x in md7), md7))
    # n=6: compute min_det for all 464 (C(11,2)=55 pairs + maybe triples) — do pairs first
    def min_det_fast(S, family, n):
        pts = stones(S, n * n)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                pair = (1 << pts[i]) | (1 << pts[j])
                if sum(1 for t in family if (t & pair) == pair) == 1:
                    return 2
        return 3  # lower bound if no unique pair; exact may be higher

    md6_pairs = [min_det_fast(s, n6, 6) for s in n6]
    n6_pair_unique = sum(1 for x in md6_pairs if x == 2)
    checks.append(("n6_no_min_det_le2", n6_pair_unique == 0, n6_pair_unique))

    # 7. (2,2) K=13 witness safe
    eng = TargetSearch(7, triples7, 13, forced=1 << o22[0], stop_at_first=True, node_budget=2_000_000)
    r = eng.run()
    wit_ok = r["result"] == "found" and r["example_xy"] is not None
    if wit_ok:
        mask = 0
        for x, y in r["example_xy"]:
            mask |= 1 << (y * 7 + x)
        wit_ok = is_safe(mask, quads7) and mask.bit_count() == 13 and (mask >> o22[0]) & 1
    checks.append(("k13_witness_with_22", wit_ok, r["result"]))

    # 8. n=7 all rho-like: no set is 1-swap to another in the list
    n7set = set(n7)
    swaps = 0
    for s in n7:
        empties = [p for p in range(49) if not (s >> p) & 1]
        occ = stones(s, 49)
        for v in empties:
            for r in occ:
                s2 = (s & ~(1 << r)) | (1 << v)
                if s2 in n7set:
                    swaps += 1
    checks.append(("n7_zero_1swap", swaps == 0, swaps))

    out = {"checks": [], "all_pass": True}
    print("Cycle 8 independent verification")
    print(f"quads n7={nq7}")
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")
        out["checks"].append({"name": name, "pass": ok, "detail": detail if not isinstance(detail, tuple) else list(detail)})
        if not ok:
            out["all_pass"] = False
    path = RES / "cycle8_verify.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Wrote", path)
    if not out["all_pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

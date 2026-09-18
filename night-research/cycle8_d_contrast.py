#!/usr/bin/env python3
"""Package D — n=6 contrast for n=7-universal invariants.

Evidence: complete enumerations
  n=7 K=14: 16 max safe sets (2 D4 orbits)
  n=6 K=11: 464 max safe sets (58 D4 orbits)

Main-result filter: only properties TRUE for all 16 n=7 max sets that FAIL
for a large fraction of the 464 n=6 max sets (or the converse).
Mere average differences are not main results.

Outputs:
  results/cycle8_d_contrast.json
  night-research/cycle8_cd_result.json  (merged C + D)
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (  # noqa: E402
    NR,
    RES,
    canon,
    cell_key,
    cell_orbits,
    d4_perms,
    load_n6,
    load_n7,
    occupancy_vector,
    stones,
    xy,
)


def load_exchange(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_tau_hist(s: str) -> dict[int, int]:
    out: dict[int, int] = {}
    if not s:
        return out
    for part in s.split(";"):
        if not part:
            continue
        a, b = part.split(":")
        out[int(a)] = int(b)
    return out


def board_block(sets: list[int], n: int) -> dict:
    v = n * n
    k = sets[0].bit_count()
    N = len(sets)
    perms = d4_perms(n)
    ords = cell_orbits(n)
    omembers = {ok: [] for ok in ords}
    for y in range(n):
        for x in range(n):
            omembers[cell_key(n, x, y)].append(y * n + x)

    # D4 orbit labels
    keys = [canon(s, perms) for s in sets]
    key_to_label: dict[int, int] = {}
    orbit_of = []
    for kk in keys:
        if kk not in key_to_label:
            key_to_label[kk] = len(key_to_label)
        orbit_of.append(key_to_label[kk])
    n_d4 = len(key_to_label)

    # cell freq + orbit occupancy
    cell_freq = [0] * v
    for s in sets:
        for p in stones(s, v):
            cell_freq[p] += 1
    orbit_freq_cells = {ok: [0] * len(omembers[ok]) for ok in ords}
    orbit_used_setcount = {ok: 0 for ok in ords}  # #sets with >=1 stone in orbit
    orbit_occ_hist = {ok: Counter() for ok in ords}  # stones-in-orbit histogram
    for s in sets:
        for ok, pts in omembers.items():
            c = sum(1 for p in pts if (s >> p) & 1)
            orbit_occ_hist[ok][c] += 1
            if c > 0:
                orbit_used_setcount[ok] += 1
            for j, p in enumerate(pts):
                if (s >> p) & 1:
                    orbit_freq_cells[ok][j] += 1

    # occupancy vectors
    occ_vecs = []
    occ_hist: Counter[tuple] = Counter()
    occ_by_d4: dict[int, set[tuple]] = defaultdict(set)
    for i, s in enumerate(sets):
        ov = occupancy_vector(s, n)
        tup = tuple(ov[ok] for ok in ords)
        occ_vecs.append(tup)
        occ_hist[tup] += 1
        occ_by_d4[orbit_of[i]].add(tup)
    d4_with_mixed_occ = sum(1 for _, ts in occ_by_d4.items() if len(ts) > 1)

    # corner-count support
    corner_pts = [0, n - 1, (n - 1) * n, n * n - 1]
    corner_counts = Counter()
    for s in sets:
        corner_counts[sum(1 for p in corner_pts if (s >> p) & 1)] += 1

    # pair distances
    masks = sets
    dist_hist: Counter[int] = Counter()
    same_hist: Counter[int] = Counter()
    inter_hist: Counter[int] = Counter()
    d_min_same = None
    d_min_inter = None
    d_min_same_pair = None
    d_min_inter_pair = None
    has_d1 = has_d2 = has_d3 = has_d4 = 0
    per_set_dmin = [10**9] * N
    per_set_has_1swap = [False] * N
    n_edges_by_d: Counter[int] = Counter()
    for i in range(N):
        si = masks[i]
        for j in range(i + 1, N):
            inter = (si & masks[j]).bit_count()
            d = k - inter
            dist_hist[d] += 1
            n_edges_by_d[d] += 1
            same = orbit_of[i] == orbit_of[j]
            if same:
                same_hist[d] += 1
            else:
                inter_hist[d] += 1
            if d < per_set_dmin[i]:
                per_set_dmin[i] = d
            if d < per_set_dmin[j]:
                per_set_dmin[j] = d
            if d == 1:
                per_set_has_1swap[i] = True
                per_set_has_1swap[j] = True
            if same:
                if d_min_same is None or d < d_min_same:
                    d_min_same = d
                    d_min_same_pair = (i, j)
            else:
                if d_min_inter is None or d < d_min_inter:
                    d_min_inter = d
                    d_min_inter_pair = (i, j)
    for d in dist_hist:
        if d == 1:
            has_d1 += dist_hist[d]
        elif d == 2:
            has_d2 += dist_hist[d]
        elif d == 3:
            has_d3 += dist_hist[d]
        elif d == 4:
            has_d4 += dist_hist[d]

    # min_det from package C CSV if present, else recompute quickly
    min_det_path = RES / f"cycle8_c_determining_n{n}.csv"
    min_dets: list[int | None] = [None] * N
    min_det_hist: Counter[int] = Counter()
    if min_det_path.exists():
        with min_det_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                min_dets[int(row["id"])] = int(row["min_det"])
        for d in min_dets:
            if d is not None:
                min_det_hist[d] += 1

    never_used_orbits = [ok for ok in ords if orbit_used_setcount[ok] == 0]
    always_used_orbits = [ok for ok in ords if orbit_used_setcount[ok] == N]

    return {
        "n": n,
        "K": k,
        "n_sets": N,
        "evidence": "complete enumeration",
        "d4_orbits": n_d4,
        "orbit_of": orbit_of,
        "keys": keys,
        "cell_orbits": [list(ok) for ok in ords],
        "orbit_sizes": {f"{a},{b}": len(omembers[(a, b)]) for a, b in ords},
        "cell_freq_minmax": [min(cell_freq), max(cell_freq)],
        "cells_never_used": sum(1 for f in cell_freq if f == 0),
        "cells_always_used": sum(1 for f in cell_freq if f == N),
        "orbit_used_setcount": {f"{a},{b}": orbit_used_setcount[(a, b)] for a, b in ords},
        "orbit_occ_hist": {
            f"{a},{b}": {str(c): h for c, h in sorted(orbit_occ_hist[(a, b)].items())}
            for a, b in ords
        },
        "never_used_orbits": [list(ok) for ok in never_used_orbits],
        "always_used_orbits": [list(ok) for ok in always_used_orbits],
        "n_never_used_orbits": len(never_used_orbits),
        "n_always_used_orbits": len(always_used_orbits),
        "corner_count_support": {str(c): h for c, h in sorted(corner_counts.items())},
        "n_distinct_occupancy_vectors": len(occ_hist),
        "occupancy_vector_hist": [
            {
                "vector_on_orbits": {f"{a},{b}": tup[i] for i, (a, b) in enumerate(ords)},
                "count": c,
            }
            for tup, c in sorted(occ_hist.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "d4_orbits_with_mixed_occupancy": d4_with_mixed_occ,
        "pair_distance_hist": {str(d): c for d, c in sorted(dist_hist.items())},
        "pair_distance_same_orbit_hist": {str(d): c for d, c in sorted(same_hist.items())},
        "pair_distance_inter_orbit_hist": {str(d): c for d, c in sorted(inter_hist.items())},
        "d_min_same_orbit": d_min_same,
        "d_min_inter_orbit": d_min_inter,
        "d_min_same_pair": list(d_min_same_pair) if d_min_same_pair else None,
        "d_min_inter_pair": list(d_min_inter_pair) if d_min_inter_pair else None,
        "n_pairs_d1": has_d1,
        "n_pairs_d2": has_d2,
        "n_pairs_d3": has_d3,
        "n_pairs_d4": has_d4,
        "n_pairs_d_le_4": has_d1 + has_d2 + has_d3 + has_d4,
        "n_sets_with_dmin_ge_5": sum(1 for d in per_set_dmin if d >= 5),
        "n_sets_with_dmin_ge_3": sum(1 for d in per_set_dmin if d >= 3),
        "n_sets_with_1swap": sum(1 for x in per_set_has_1swap if x),
        "n_sets_without_1swap": sum(1 for x in per_set_has_1swap if not x),
        "per_set_dmin_hist": {str(d): c for d, c in sorted(Counter(per_set_dmin).items())},
        "recomputed_rho_proxy_hist": {
            "has_1swap": sum(1 for x in per_set_has_1swap if x),
            "no_1swap": sum(1 for x in per_set_has_1swap if not x),
        },
        "min_det_hist": {str(d): c for d, c in sorted(min_det_hist.items())} if min_det_hist else None,
        "min_det_cutoff": {
            str(t): sum(c for d, c in min_det_hist.items() if d <= t)
            for t in range(1, (k if min_det_hist else 0) + 1)
        }
        if min_det_hist
        else None,
        "n_min_det_eq_1": min_det_hist.get(1, 0) if min_det_hist else None,
        "n_min_det_le_2": (
            sum(c for d, c in min_det_hist.items() if d <= 2) if min_det_hist else None
        ),
        "n_min_det_le_3": (
            sum(c for d, c in min_det_hist.items() if d <= 3) if min_det_hist else None
        ),
        "min_det_min": min(min_det_hist) if min_det_hist else None,
        "min_det_max": max(min_det_hist) if min_det_hist else None,
        "occ_vecs": occ_vecs,
        "ords": ords,
    }


def exchange_stats(path: Path, n_sets: int) -> dict:
    rows = load_exchange(path)
    if not rows:
        return {"available": False, "path": str(path)}
    rho = Counter(int(r["rho"]) for r in rows)
    swap_pairs = Counter(int(r["swap_pairs"]) for r in rows)
    tau1 = Counter(int(r["tau1_empty"]) for r in rows)
    min_block = Counter(int(r["min_blockers"]) for r in rows)
    # min tau over empty-cell blocker families (= min positive tau_hist key)
    min_tau_vals = []
    for r in rows:
        th = parse_tau_hist(r.get("tau_hist", ""))
        pos = [t for t in th if th[t] > 0]
        min_tau_vals.append(min(pos) if pos else 0)
    min_tau_hist = Counter(min_tau_vals)
    return {
        "available": True,
        "path": str(path),
        "n_rows": len(rows),
        "rho_hist": {str(k): v for k, v in sorted(rho.items())},
        "n_rho_eq_1": rho.get(1, 0),
        "n_rho_ge_2": sum(v for k, v in rho.items() if k >= 2),
        "frac_rho_eq_1": rho.get(1, 0) / len(rows),
        "swap_pairs_hist": {str(k): v for k, v in sorted(swap_pairs.items())},
        "tau1_empty_hist": {str(k): v for k, v in sorted(tau1.items())},
        "min_blockers_hist": {str(k): v for k, v in sorted(min_block.items())},
        "min_tau_hist": {str(k): v for k, v in sorted(min_tau_hist.items())},
        "n_tau1_empty_gt_0": sum(v for k, v in tau1.items() if k > 0),
        "n_min_tau_eq_1": min_tau_hist.get(1, 0),
        "n_min_tau_eq_0": min_tau_hist.get(0, 0),
    }


def main() -> None:
    n7_sets = load_n7()
    n6_sets = load_n6()
    print("=== Package D: n=6 contrast for n=7-universal invariants ===")
    print("Evidence: COMPLETE enumeration both boards "
          f"(n=7 K=14: {len(n7_sets)} sets; n=6 K=11: {len(n6_sets)} sets)")

    b7 = board_block(n7_sets, 7)
    b6 = board_block(n6_sets, 6)

    ex7 = exchange_stats(RES / "maxsafe_exchange_n7.csv", len(n7_sets))
    ex6 = exchange_stats(RES / "maxsafe_exchange_n6.csv", len(n6_sets))

    def strip_internal(b: dict) -> dict:
        return {kk: vv for kk, vv in b.items() if kk not in ("occ_vecs", "ords", "orbit_of", "keys")}

    # ---- universal vs refuted ----
    universals = []
    contrasts = []

    def univ(name: str, statement: str, n7_ok_frac: float, n6_ok_frac: float, detail: dict):
        entry = {
            "name": name,
            "statement": statement,
            "n7_frac_holds": n7_ok_frac,
            "n6_frac_holds": n6_ok_frac,
            "detail": detail,
        }
        if n7_ok_frac == 1.0 and n6_ok_frac < 0.5:
            entry["label"] = "UNIVERSAL_n7_large_fraction_FAIL_n6"
            universals.append(entry)
        elif n6_ok_frac == 1.0 and n7_ok_frac < 0.5:
            entry["label"] = "UNIVERSAL_n6_large_fraction_FAIL_n7"
            universals.append(entry)
        elif n7_ok_frac == 1.0 and n6_ok_frac == 1.0:
            entry["label"] = "UNIVERSAL_both"
            universals.append(entry)
        else:
            entry["label"] = "contrast_partial"
            contrasts.append(entry)
        return entry

    # 1. min_det
    n7_le2 = b7["n_min_det_le_2"] or 0
    n6_le2 = b6["n_min_det_le_2"] or 0
    n7_ge5 = sum(c for d, c in (b7["min_det_hist"] or {}).items() if int(d) >= 5)
    n6_ge5 = sum(c for d, c in (b6["min_det_hist"] or {}).items() if int(d) >= 5)
    univ(
        "min_det_le_2",
        "min_det(S) <= 2",
        n7_le2 / b7["n_sets"],
        n6_le2 / b6["n_sets"],
        {
            "n7_count": n7_le2,
            "n6_count": n6_le2,
            "n7_hist": b7["min_det_hist"],
            "n6_hist": b6["min_det_hist"],
        },
    )
    univ(
        "min_det_ge_5",
        "min_det(S) >= 5",
        n7_ge5 / b7["n_sets"],
        n6_ge5 / b6["n_sets"],
        {"n7_count": n7_ge5, "n6_count": n6_ge5},
    )
    univ(
        "min_det_ge_3",
        "min_det(S) >= 3",
        sum(c for d, c in (b7["min_det_hist"] or {}).items() if int(d) >= 3) / b7["n_sets"],
        sum(c for d, c in (b6["min_det_hist"] or {}).items() if int(d) >= 3) / b6["n_sets"],
        {},
    )
    univ(
        "min_det_eq_1",
        "min_det(S) = 1",
        b7["n_min_det_eq_1"] / b7["n_sets"],
        b6["n_min_det_eq_1"] / b6["n_sets"],
        {"n7": b7["n_min_det_eq_1"], "n6": b6["n_min_det_eq_1"]},
    )

    # 2. 1-swap / rho
    n7_1s = b7["n_sets_with_1swap"] / b7["n_sets"]
    n6_1s = b6["n_sets_with_1swap"] / b6["n_sets"]
    univ(
        "has_1swap",
        "exists another max safe set at d=1 (1-swap edge)",
        n7_1s,
        n6_1s,
        {
            "n7_with": b7["n_sets_with_1swap"],
            "n7_without": b7["n_sets_without_1swap"],
            "n6_with": b6["n_sets_with_1swap"],
            "n6_without": b6["n_sets_without_1swap"],
            "exchange_rho_n7": ex7.get("rho_hist"),
            "exchange_rho_n6": ex6.get("rho_hist"),
        },
    )
    univ(
        "no_1swap_rigid",
        "no 1-swap partner (exchange-rigid locally)",
        b7["n_sets_without_1swap"] / b7["n_sets"],
        b6["n_sets_without_1swap"] / b6["n_sets"],
        {"n7": b7["n_sets_without_1swap"], "n6": b6["n_sets_without_1swap"]},
    )

    # 3. pair-distance: no pair at d<=4
    n7_le4_pairs = b7["n_pairs_d_le_4"]
    n6_le4_pairs = b6["n_pairs_d_le_4"]
    n7_all_le4 = int(n7_le4_pairs == 0)  # "all sets have all pairs d>=5" is not per-set
    # per-set: every other set at d>=5
    frac_n7_dmin_ge5 = b7["n_sets_with_dmin_ge_5"] / b7["n_sets"]
    frac_n6_dmin_ge5 = b6["n_sets_with_dmin_ge_5"] / b6["n_sets"]
    univ(
        "all_pairs_dmin_ge_5",
        "every other max safe set is at exchange-distance d >= 5",
        frac_n7_dmin_ge5,
        frac_n6_dmin_ge5,
        {
            "n7": b7["n_sets_with_dmin_ge_5"],
            "n6": b6["n_sets_with_dmin_ge_5"],
            "n7_pairs_d_le_4": n7_le4_pairs,
            "n6_pairs_d_le_4": n6_le4_pairs,
        },
    )
    univ(
        "all_pairs_dmin_ge_3",
        "every other max safe set is at d >= 3",
        b7["n_sets_with_dmin_ge_3"] / b7["n_sets"],
        b6["n_sets_with_dmin_ge_3"] / b6["n_sets"],
        {"n7": b7["n_sets_with_dmin_ge_3"], "n6": b6["n_sets_with_dmin_ge_3"]},
    )

    # 4. never-used cell orbit
    univ(
        "exists_never_used_cell_orbit",
        "some D4 cell-orbit is used by 0 max safe sets",
        int(b7["n_never_used_orbits"] > 0),
        int(b6["n_never_used_orbits"] > 0),
        {
            "n7_never": b7["never_used_orbits"],
            "n6_never": b6["never_used_orbits"],
            "n7_orbit_used_setcount": b7["orbit_used_setcount"],
            "n6_orbit_used_setcount": b6["orbit_used_setcount"],
        },
    )
    univ(
        "orbit_22_always_empty",
        "cell-orbit (2,2) is empty in every max safe set",
        # n=7: orbit (2,2) never used
        float(
            (b7["orbit_used_setcount"].get("2,2", 0) == 0)
            if "2,2" in b7["orbit_used_setcount"]
            else False
        ),
        float(
            (b6["orbit_used_setcount"].get("2,2", 0) == 0)
            if "2,2" in b6["orbit_used_setcount"]
            else False
        ),
        {
            "n7_used_count_22": b7["orbit_used_setcount"].get("2,2"),
            "n6_used_count_22": b6["orbit_used_setcount"].get("2,2"),
            "n7_orbit_occ_22": b7["orbit_occ_hist"].get("2,2"),
            "n6_orbit_occ_22": b6["orbit_occ_hist"].get("2,2"),
        },
    )

    # 5. occupancy vectors
    univ(
        "occupancy_vectors_le_2",
        "at most 2 distinct cell-orbit occupancy vectors",
        int(b7["n_distinct_occupancy_vectors"] <= 2),
        int(b6["n_distinct_occupancy_vectors"] <= 2),
        {
            "n7_n_distinct": b7["n_distinct_occupancy_vectors"],
            "n6_n_distinct": b6["n_distinct_occupancy_vectors"],
            "n7_hist": b7["occupancy_vector_hist"],
        },
    )
    univ(
        "d4_orbit_homogeneous_occupancy",
        "every D4 orbit of max sets has a single occupancy vector",
        int(b7["d4_orbits_with_mixed_occupancy"] == 0),
        int(b6["d4_orbits_with_mixed_occupancy"] == 0),
        {
            "n7_mixed": b7["d4_orbits_with_mixed_occupancy"],
            "n6_mixed": b6["d4_orbits_with_mixed_occupancy"],
        },
    )

    # 6. corner-count support
    n7_corner = set(b7["corner_count_support"].keys())
    n6_corner = set(b6["corner_count_support"].keys())
    univ(
        "corner_count_in_23",
        "number of corner stones is in {2,3}",
        float(sum(b7["corner_count_support"].get(c, 0) for c in ("2", "3")) / b7["n_sets"]),
        float(sum(b6["corner_count_support"].get(c, 0) for c in ("2", "3")) / b6["n_sets"]),
        {
            "n7_support": b7["corner_count_support"],
            "n6_support": b6["corner_count_support"],
        },
    )

    # 7. exchange rho / min tau
    univ(
        "exchange_rho_eq_2",
        "exchange rho = 2 (from maxsafe_exchange CSV)",
        float(ex7.get("n_rho_eq_1", 0) == 0 and ex7.get("rho_hist", {}).get("2", 0) == ex7.get("n_rows", 0))
        if ex7.get("available")
        else -1.0,
        float(ex6.get("rho_hist", {}).get("2", 0) / ex6.get("n_rows", 1))
        if ex6.get("available")
        else -1.0,
        {"exchange_n7": ex7, "exchange_n6": ex6},
    )
    univ(
        "exchange_rho_eq_1",
        "exchange rho = 1",
        float(ex7.get("n_rho_eq_1", 0) / ex7.get("n_rows", 1)) if ex7.get("available") else -1.0,
        float(ex6.get("n_rho_eq_1", 0) / ex6.get("n_rows", 1)) if ex6.get("available") else -1.0,
        {},
    )
    univ(
        "some_empty_cell_tau1",
        "at least one empty cell has blocker-family tau = 1",
        float(ex7.get("n_tau1_empty_gt_0", 0) / ex7.get("n_rows", 1)) if ex7.get("available") else -1.0,
        float(ex6.get("n_tau1_empty_gt_0", 0) / ex6.get("n_rows", 1)) if ex6.get("available") else -1.0,
        {
            "n7_tau1_empty_hist": ex7.get("tau1_empty_hist"),
            "n6_tau1_empty_hist": ex6.get("tau1_empty_hist"),
            "n7_min_tau_hist": ex7.get("min_tau_hist"),
            "n6_min_tau_hist": ex6.get("min_tau_hist"),
        },
    )

    # always-used orbits (inverse never)
    univ(
        "no_always_empty_orbit",
        "every cell-orbit is used by at least one max safe set",
        int(b7["n_never_used_orbits"] == 0),
        int(b6["n_never_used_orbits"] == 0),
        {},
    )

    contrast_payload = {
        "package": "D",
        "evidence": "complete enumeration",
        "counts": {
            "n7": {"n_sets": 16, "K": 14, "d4_orbits": b7["d4_orbits"]},
            "n6": {"n_sets": 464, "K": 11, "d4_orbits": b6["d4_orbits"]},
        },
        "filter": (
            "main results = properties TRUE for all 16 n=7 max sets that FAIL for a large "
            "fraction of 464 n=6 max sets, or the converse; not mere averages"
        ),
        "n7": strip_internal(b7),
        "n6": strip_internal(b6),
        "exchange": {"n7": ex7, "n6": ex6},
        "universal_invariants": universals,
        "partial_contrasts": contrasts,
    }

    res_path = RES / "cycle8_d_contrast.json"
    res_path.write_text(json.dumps(contrast_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # merge into night-research/cycle8_cd_result.json
    cd_path = NR / "cycle8_cd_result.json"
    if cd_path.exists():
        cd = json.loads(cd_path.read_text(encoding="utf-8"))
    else:
        cd = {"package": "C+D", "note": "C section missing; run cycle8_c_determining.py first"}
    cd["package_D"] = {
        "counts": contrast_payload["counts"],
        "filter": contrast_payload["filter"],
        "n7_summary": strip_internal(b7),
        "n6_summary": strip_internal(b6),
        "exchange": contrast_payload["exchange"],
        "universal_invariants": universals,
        "partial_contrasts": contrasts,
    }
    cd["evidence"] = "complete enumeration"
    cd_path.write_text(json.dumps(cd, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- stdout compact summary ----
    print("\n--- pair-distance spectrum (independent recompute) ---")
    for tag, b in (("n=7", b7), ("n=6", b6)):
        print(f"  {tag} K={b['K']} sets={b['n_sets']} d4_orbits={b['d4_orbits']}")
        print(f"    d-hist: {b['pair_distance_hist']}")
        print(f"    same-orbit d-hist: {b['pair_distance_same_orbit_hist']}")
        print(f"    inter-orbit d-hist: {b['pair_distance_inter_orbit_hist']}")
        print(f"    d_min same={b['d_min_same_orbit']} inter={b['d_min_inter_orbit']}")
        print(f"    pairs d=1..4: {b['n_pairs_d1']},{b['n_pairs_d2']},{b['n_pairs_d3']},{b['n_pairs_d4']} "
              f"(<=4 total {b['n_pairs_d_le_4']})")
        print(f"    sets with all-pairs dmin>=5: {b['n_sets_with_dmin_ge_5']}/{b['n_sets']}")
        print(f"    1-swap: yes={b['n_sets_with_1swap']} no={b['n_sets_without_1swap']}")

    print("\n--- cell-orbit occupancy ---")
    for tag, b in (("n=7", b7), ("n=6", b6)):
        print(f"  {tag} orbits={b['cell_orbits']}")
        print(f"    never-used orbits ({b['n_never_used_orbits']}): {b['never_used_orbits']}")
        print(f"    always-used orbits ({b['n_always_used_orbits']}): {b['always_used_orbits']}")
        print(f"    corner-count support: {b['corner_count_support']}")
        print(f"    distinct occupancy vectors: {b['n_distinct_occupancy_vectors']}  "
              f"D4-orbits with mixed occ: {b['d4_orbits_with_mixed_occupancy']}")
        if tag == "n=7":
            for item in b["occupancy_vector_hist"]:
                print(f"      occ x{item['count']}: {item['vector_on_orbits']}")
        print(f"    orbit used-setcount: {b['orbit_used_setcount']}")

    print("\n--- exchange CSV rho / min-tau ---")
    for tag, ex in (("n=7", ex7), ("n=6", ex6)):
        if not ex.get("available"):
            print(f"  {tag}: CSV missing")
            continue
        print(f"  {tag} rho={ex['rho_hist']}  frac_rho=1:{ex['frac_rho_eq_1']:.3f}  "
              f"min_blockers={ex['min_blockers_hist']}  min_tau={ex['min_tau_hist']}  "
              f"tau1_empty>0: {ex['n_tau1_empty_gt_0']}/{ex['n_rows']}")

    print("\n--- min_det contrast ---")
    for tag, b in (("n=7", b7), ("n=6", b6)):
        print(f"  {tag} hist={b['min_det_hist']}  <=2:{b['n_min_det_le_2']}  "
              f"<=3:{b['n_min_det_le_3']}  eq1:{b['n_min_det_eq_1']}  "
              f"range=[{b['min_det_min']},{b['min_det_max']}]")

    print("\n=== UNIVERSAL / REFUTED (main results) ===")
    for e in universals + contrasts:
        if e["label"] == "contrast_partial":
            continue
        print(f"  [{e['label']}] {e['name']}: n7_frac={e['n7_frac_holds']:.3f}  "
              f"n6_frac={e['n6_frac_holds']:.3f}")
        print(f"      {e['statement']}")

    print("\n=== partial contrasts (not main results) ===")
    for e in contrasts:
        print(f"  {e['name']}: n7_frac={e['n7_frac_holds']:.3f}  n6_frac={e['n6_frac_holds']:.3f}  "
              f"({e['statement']})")

    print(f"\nWrote {res_path}")
    print(f"Wrote {cd_path}")


if __name__ == "__main__":
    main()

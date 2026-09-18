#!/usr/bin/env python3
"""Cycle 8 package B finalizer — fast path.

Occupancy from complete 16-set enum + node-capped conditional searches.
No long UNSAT grinds.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (
    NR, RES, cell_orbits, centers, corners, forbidden_quads,
    is_safe, load_n7, occupancy_vector, orbit_members, pid,
)

N = 7
EXE = str(NR / "cycle8_b_maxsafe.exe")
CAP = 8_000_000
TO = 22


def occ_json(occ):
    return {f"({k[0]},{k[1]})": int(v) for k, v in sorted(occ.items())}


def run(args, cap=CAP, timeout=TO):
    cmd = [EXE] + [str(a) for a in args] + ["--max-nodes", str(cap)]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "complete": False, "cmd": args, "runtime_s": timeout,
                "count": None, "max_size": None}
    dt = round(time.time() - t0, 3)
    out = (p.stdout or "").strip()
    if not out:
        return {"error": f"no stdout rc={p.returncode}", "complete": False, "cmd": args,
                "runtime_s": dt, "stderr": (p.stderr or "")[-300:]}
    try:
        rec = json.loads(out.splitlines()[-1])
    except json.JSONDecodeError:
        return {"error": "bad json", "complete": False, "cmd": args, "runtime_s": dt,
                "stdout": out[-300:]}
    rec["cmd"] = args
    rec["runtime_s"] = dt
    rec.setdefault("complete", False)
    return rec


def brief(rec, keys=("count", "max_size", "complete", "nodes", "first", "runtime_s", "error")):
    return {k: rec.get(k) for k in keys if k in rec or k in ("count", "max_size", "complete")}


def main():
    t0 = time.time()
    RES.mkdir(parents=True, exist_ok=True)
    sets = load_n7()
    quads = forbidden_quads(N)
    om = orbit_members(N)
    ords = cell_orbits(N)
    center = centers(N)[0]
    cn = corners(N)
    pids = {"center": center, "o03": pid(3, 0, N), "o23": pid(3, 2, N), "o22": pid(2, 2, N)}

    # ---- occupancy / validation ----
    occ_list, sums, unsafe = [], [], []
    for i, s in enumerate(sets):
        if not is_safe(s, quads):
            unsafe.append(i)
        o = occupancy_vector(s, N)
        occ_list.append(o)
        sums.append(sum(o.values()))

    groups = {}
    for i, o in enumerate(occ_list):
        groups.setdefault(json.dumps(occ_json(o), sort_keys=True), []).append(i)

    vectors = []
    for sig, idxs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        occ = json.loads(sig)
        ot = {tuple(int(x) for x in k.strip("()").split(",")): int(v) for k, v in occ.items()}
        has_c = ot.get((3, 3), 0) > 0
        vectors.append({
            "label": "A_center" if has_c else "B_nocenter",
            "occupancy": occ,
            "sum": sum(occ.values()),
            "n_sets": len(idxs),
            "set_ids": idxs,
            "center_occupied": has_c,
            "corners": ot.get((0, 0), 0),
            "uses_0_3": ot.get((0, 3), 0),
            "uses_2_2": ot.get((2, 2), 0),
            "uses_2_3": ot.get((2, 3), 0),
        })

    expected_A = {"(0,0)":2,"(0,1)":3,"(0,2)":2,"(0,3)":0,"(1,1)":1,"(1,2)":3,"(1,3)":2,"(2,2)":0,"(2,3)":0,"(3,3)":1}
    expected_B = {"(0,0)":3,"(0,1)":1,"(0,2)":2,"(0,3)":1,"(1,1)":1,"(1,2)":3,"(1,3)":1,"(2,2)":0,"(2,3)":2,"(3,3)":0}
    by_label = {v["label"]: v["occupancy"] for v in vectors}
    match_A = by_label.get("A_center") == expected_A
    match_B = by_label.get("B_nocenter") == expected_B

    excl = {
        "center_sets": 0, "nocenter_sets": 0,
        "center_and_0_3": 0, "center_and_2_3": 0, "center_and_2_2": 0,
        "any_2_2": 0,
        "corner_hist": {0: 0, 1: 0, 2: 0, 3: 0, 4: 0},
        "sets_with_0_3": 0, "sets_with_2_3": 0,
    }
    for s, o in zip(sets, occ_list):
        has_c = o[(3, 3)] > 0
        excl["center_sets" if has_c else "nocenter_sets"] += 1
        if o[(0, 3)] > 0:
            excl["sets_with_0_3"] += 1
        if o[(2, 3)] > 0:
            excl["sets_with_2_3"] += 1
        if has_c and o[(0, 3)] > 0:
            excl["center_and_0_3"] += 1
        if has_c and o[(2, 3)] > 0:
            excl["center_and_2_3"] += 1
        if has_c and o[(2, 2)] > 0:
            excl["center_and_2_2"] += 1
        if o[(2, 2)] > 0:
            excl["any_2_2"] += 1
        c = sum(1 for p in cn if (s >> p) & 1)
        excl["corner_hist"][c] += 1

    def kh(pred):
        ids = [i for i, o in enumerate(occ_list) if pred(o)]
        return {"n_hits": len(ids), "hit_ids": ids, "max_among_known": 14 if ids else 0}

    kf = {
        "force_center": kh(lambda o: o[(3, 3)] > 0),
        "forbid_center": kh(lambda o: o[(3, 3)] == 0),
        "force_0_3": kh(lambda o: o[(0, 3)] > 0),
        "forbid_0_3": kh(lambda o: o[(0, 3)] == 0),
        "force_2_3": kh(lambda o: o[(2, 3)] > 0),
        "forbid_2_3": kh(lambda o: o[(2, 3)] == 0),
        "force_2_2": kh(lambda o: o[(2, 2)] > 0),
        "forbid_2_2": kh(lambda o: o[(2, 2)] == 0),
        "force_0_3_and_center": kh(lambda o: o[(0, 3)] > 0 and o[(3, 3)] > 0),
        "force_2_3_and_center": kh(lambda o: o[(2, 3)] > 0 and o[(3, 3)] > 0),
        "force_2_2_and_center": kh(lambda o: o[(2, 2)] > 0 and o[(3, 3)] > 0),
        "corners_0": kh(lambda o: o[(0, 0)] == 0),
        "corners_1": kh(lambda o: o[(0, 0)] == 1),
        "corners_2": kh(lambda o: o[(0, 0)] == 2),
        "corners_3": kh(lambda o: o[(0, 0)] == 3),
        "corners_4": kh(lambda o: o[(0, 0)] == 4),
    }

    # ---- targeted solver runs (node-capped) ----
    solver = {}
    print("running targeted solver queries...", flush=True)

    def S(name, args, **kw):
        rec = run(args, **kw)
        solver[name] = brief(rec)
        solver[name]["full_keys"] = {k: rec.get(k) for k in rec if k not in ("cmd",)}
        solver[name]["cmd"] = args
        print(f"  {name}: {brief(rec)}", flush=True)
        return rec

    # a force center — known 8
    S("count14_force_center", ["count", N, 14, "--force", pids["center"]])
    # g force (2,2) — expect 0
    S("count14_force_22", ["count", N, 14, "--force", pids["o22"]])
    S("first13_force_22", ["first", N, 13, "--force", pids["o22"]])
    S("max_force_22_seed13", ["max", N, "--force", pids["o22"], "--seed", 13, "--known-upper", 14])
    # require-orbit (2,2)
    S("count14_require_orbit_22", ["count", N, 14, "--require-orbit", "2,2"])
    S("first13_require_orbit_22", ["first", N, 13, "--require-orbit", "2,2"])
    S("max_require_orbit_22_seed13", ["max", N, "--require-orbit", "2,2", "--seed", 13, "--known-upper", 14])
    # d/f/h forbid orbits
    S("count14_forbid_orbit_03", ["count", N, 14, "--forbid-orbit", "0,3"])
    S("count14_forbid_orbit_23", ["count", N, 14, "--forbid-orbit", "2,3"])
    S("count14_forbid_orbit_22", ["count", N, 14, "--forbid-orbit", "2,2"])
    # c/e force orbit reps
    S("count14_force_03", ["count", N, 14, "--force", pids["o03"]])
    S("count14_force_23", ["count", N, 14, "--force", pids["o23"]])
    # exclusivity
    S("count14_force_03_and_center", ["count", N, 14, "--force", pids["center"], "--force", pids["o03"]])
    S("count14_force_23_and_center", ["count", N, 14, "--force", pids["center"], "--force", pids["o23"]])
    S("count14_force_22_and_center", ["count", N, 14, "--force", pids["center"], "--force", pids["o22"]])
    S("first13_force_03_and_center", ["first", N, 13, "--force", pids["center"], "--force", pids["o03"]])
    S("first13_force_23_and_center", ["first", N, 13, "--force", pids["center"], "--force", pids["o23"]])
    # corners
    for c in (0, 2, 3, 4):
        S(f"count14_corners_{c}", ["count", N, 14, "--corners", c])
    S("count14_corners_1", ["count", N, 14, "--corners", 1], cap=6_000_000)
    # first@13 under corner caps that have no 14-set
    for c in (0, 1, 4):
        S(f"first13_corners_{c}", ["first", N, 13, "--corners", c])
    # b forbid center — may be incomplete
    S("count14_forbid_center", ["count", N, 14, "--forbid", pids["center"]], cap=6_000_000)
    # unconstrained sanity (capped; no K15 grind)
    S("first14_unc", ["first", N, 14], cap=4_000_000)
    S("max_unc_seed14", ["max", N, "--seed", 14, "--known-upper", 14], cap=3_000_000)
    # occ @14
    S("occ14", ["occ", N, 14, "--limit", "1000"], cap=15_000_000, timeout=25)

    # ---- derive conditional table ----
    def case(key, label, args, count14_name=None, first13_name=None, max_name=None):
        hit = kf[key]
        ev = []
        max_size = None
        status = "PARTIAL"
        c14 = solver.get(count14_name) if count14_name else None
        if hit["n_hits"] > 0:
            max_size = 14
            ev.append(f"COMPLETE_via_full_K14_enum_filter: hits={hit['n_hits']}/16")
            if c14 and c14.get("complete") and (c14.get("count") or 0) > 0:
                ev.append(f"COMPLETE_independent_count@14: {c14.get('count')} nodes={c14.get('nodes')}")
                status = "COMPLETE"
            elif c14 and c14.get("complete") and c14.get("count") == 0:
                ev.append("DISAGREE independent count@14=0")
                status = "DISAGREE"
            else:
                status = "COMPLETE_ENUM_FILTER"
                if c14:
                    ev.append(f"INCOMPLETE_independent_count@14: {brief(c14)}")
        else:
            if c14 and c14.get("complete") and c14.get("count") == 0:
                ev.append(f"COMPLETE_independent_no14: nodes={c14.get('nodes')} => max<=13")
                upper = 13
            elif c14 and c14.get("count") == 0:
                ev.append("BOUND_no14 via complete K14-enum filter (0 hits); independent search incomplete or 0")
                upper = 13
            else:
                upper = 13
                ev.append(f"count@14 info: {c14}")
            f13 = solver.get(first13_name) if first13_name else None
            if f13 and f13.get("count"):
                ev.append(f"LOWER_BOUND_13: first={f13.get('first')} nodes={f13.get('nodes')}")
                max_size = 13
                if c14 and c14.get("complete"):
                    ev.append("COMPLETE_max=13 (independent no14 + witness)")
                    status = "COMPLETE"
                else:
                    ev.append("COMPLETE_max=13 (enum-filter no14 + witness)")
                    status = "COMPLETE_ENUM_FILTER_PLUS_WITNESS"
            else:
                max_size = upper
                if f13:
                    ev.append(f"first13: {f13}")
                status = "PARTIAL_NO_WITNESS"
            recmax = solver.get(max_name) if max_name else None
            if recmax and recmax.get("complete") and recmax.get("max_size") is not None:
                if recmax.get("max_size") == max_size:
                    ev.append(f"CONFIRM_max_mode={recmax.get('max_size')} nodes={recmax.get('nodes')}")
                elif recmax.get("max_size") > (max_size or 0):
                    ev.append(f"DISAGREE max_mode={recmax.get('max_size')}")
                    max_size = recmax.get("max_size")
            elif recmax:
                ev.append(f"max_mode incomplete: {recmax}")
        return {
            "label": label,
            "constraint_args": args,
            "known_filter": hit,
            "max_size": max_size,
            "search_status": status,
            "evidence": ev,
            "count_at_14": c14,
            "first_at_13": solver.get(first13_name) if first13_name else None,
            "max_mode": solver.get(max_name) if max_name else None,
            "input_counts": {"known_sets": 16, "known_hits": hit["n_hits"], "quads": len(quads)},
        }

    cases = [
        case("force_center", "a_force_center_(3,3)", ["--force", str(center)],
             "count14_force_center"),
        case("forbid_center", "b_forbid_center", ["--forbid", str(center)],
             "count14_forbid_center"),
        case("force_0_3", f"c_force_{pids['o03']}_(3,0)_orbit_(0,3)", ["--force", str(pids["o03"])],
             "count14_force_03"),
        case("forbid_0_3", "d_forbid_orbit_(0,3)", ["--forbid-orbit", "0,3"],
             "count14_forbid_orbit_03"),
        case("force_2_3", f"e_force_{pids['o23']}_(3,2)_orbit_(2,3)", ["--force", str(pids["o23"])],
             "count14_force_23"),
        case("forbid_2_3", "f_forbid_orbit_(2,3)", ["--forbid-orbit", "2,3"],
             "count14_forbid_orbit_23"),
        case("force_2_2", f"g_force_{pids['o22']}_(2,2)_orbit_(2,2)", ["--force", str(pids["o22"])],
             "count14_force_22", "first13_force_22", "max_force_22_seed13"),
        case("forbid_2_2", "h_forbid_orbit_(2,2)", ["--forbid-orbit", "2,2"],
             "count14_forbid_orbit_22"),
        case("corners_0", "i_corners_exact_0", ["--corners", "0"],
             "count14_corners_0", "first13_corners_0"),
        case("corners_1", "i_corners_exact_1", ["--corners", "1"],
             "count14_corners_1", "first13_corners_1"),
        case("corners_2", "i_corners_exact_2", ["--corners", "2"],
             "count14_corners_2"),
        case("corners_3", "i_corners_exact_3", ["--corners", "3"],
             "count14_corners_3"),
        case("corners_4", "i_corners_exact_4", ["--corners", "4"],
             "count14_corners_4", "first13_corners_4"),
        case("force_0_3_and_center", "excl_center+_(0,3)",
             ["--force", str(center), "--force", str(pids["o03"])],
             "count14_force_03_and_center", "first13_force_03_and_center"),
        case("force_2_3_and_center", "excl_center+_(2,3)",
             ["--force", str(center), "--force", str(pids["o23"])],
             "count14_force_23_and_center", "first13_force_23_and_center"),
        case("force_2_2_and_center", "excl_center+_(2,2)",
             ["--force", str(center), "--force", str(pids["o22"])],
             "count14_force_22_and_center"),
    ]

    # corners=2 has known hits (A sets); forbid_center has known hits (B sets)
    # force_0_3 known hits: B has (0,3)=1 so some sets — actually occupancy is orbit-level.
    # force specific cell (3,0): cell freq was 2/16, so known hits at orbit level >0.
    # kf["force_0_3"] uses orbit occupancy o[(0,3)]>0 which is B sets (8).

    task3 = {
        "known_intersect_2_2": kf["force_2_2"],
        "verdict_known_filter": "no K=14 set contains any (2,2) cell (0/16)" if kf["force_2_2"]["n_hits"] == 0 else "UNEXPECTED",
        "require_orbit_2_2_count_at_14": solver.get("count14_require_orbit_22"),
        "require_orbit_2_2_first_at_13": solver.get("first13_require_orbit_22"),
        "require_orbit_2_2_max_seed13": solver.get("max_require_orbit_22_seed13"),
        "specific_cell_force_2_2": next(c for c in cases if c["label"].startswith("g_force")),
        "verdict": None,
    }
    c22 = solver.get("count14_require_orbit_22") or {}
    f22 = solver.get("first13_require_orbit_22") or {}
    if kf["force_2_2"]["n_hits"] == 0 and c22.get("complete") and c22.get("count") == 0 and f22.get("count"):
        task3["verdict"] = (
            "max safe size with any (2,2) occupied = 13. "
            "COMPLETE: independent require-orbit count@14=0 + K13 witness + complete 16-set filter 0 hits."
        )
    elif kf["force_2_2"]["n_hits"] == 0 and c22.get("count") == 0 and f22.get("count"):
        task3["verdict"] = (
            "max safe size with any (2,2) occupied = 13. "
            "Complete 16-set filter 0 hits + require-orbit count@14=0 (search "
            f"complete={c22.get('complete')}) + K13 witness mask={f22.get('first')}."
        )
    else:
        task3["verdict"] = f"see components; c22={c22} f22={f22}"

    def parse_patterns(raw):
        out = []
        for p in (raw or {}).get("patterns") or []:
            s = p.get("occ") or ""
            occ = {}
            for part in s.split(";"):
                if not part:
                    continue
                k, v = part.split(":")
                occ[f"({k})"] = int(v)
            out.append({"occupancy": occ, "count": p.get("count")})
        return out

    runtime = round(time.time() - t0, 3)

    occupancy_out = {
        "task": "cycle8_b_occupancy_vectors",
        "n": N,
        "K": 14,
        "n_sets": len(sets),
        "n_distinct_vectors": len(vectors),
        "vectors": vectors,
        "expected_A": expected_A,
        "expected_B": expected_B,
        "match_expected_A": match_A,
        "match_expected_B": match_B,
        "match_expected": match_A and match_B,
        "validation": {
            "n_sets": len(sets),
            "n_quads": len(quads),
            "all_is_safe": len(unsafe) == 0,
            "unsafe_ids": unsafe,
            "all_sum_14": all(x == 14 for x in sums),
            "sums": sums,
        },
        "exclusivity_on_known": excl,
        "orbit_members": {f"({k[0]},{k[1]})": om[k] for k in ords},
        "orbit_keys": [f"({k[0]},{k[1]})" for k in ords],
        "compress": {
            "size_14_achievable_patterns": {
                "source": "complete 16-set enum occupancy + optional solver occ",
                "n_distinct": len(vectors),
                "patterns": [
                    {"label": v["label"], "occupancy": v["occupancy"], "n_sets": v["n_sets"]}
                    for v in vectors
                ],
                "note": "exactly A and B; (2,2) never used",
            },
            "size_13": {
                "note": "full K=13 occupancy census NOT run (not cheap; node-capped searches only). "
                        "Size-13 structure evidenced by conditional maxima (e.g. force-(2,2)=13).",
                "count_attempt": solver.get("first13_force_22"),
            },
        },
        "runtime_s": runtime,
    }

    conditional = {
        "task": "cycle8_b_conditional_max",
        "n": N,
        "K7": 14,
        "exe": EXE,
        "node_cap_default": CAP,
        "n_quads": len(quads),
        "rep_pids": pids,
        "cases": cases,
        "task3_independent_2_2": task3,
        "task4_exclusivity_known_sets": excl,
        "unconstrained_sanity": {
            "note": "K7=14 from prior complete enum (16 sets); K=15 UNSAT not re-run",
            "all_is_safe": len(unsafe) == 0,
            "all_sum_14": all(x == 14 for x in sums),
            "solver_first_at_14": solver.get("first14_unc"),
            "solver_max_seed14": solver.get("max_unc_seed14"),
            "interpretation": "max>=14 via known examples; max=14 via established K7=14 complete enum",
        },
        "solver_runs": solver,
        "runtime_s": runtime,
        "method_notes": [
            "cycle8_lib.max_safe_under() NOT used.",
            "COMPLETE_via_full_K14_enum_filter = filter of complete 16-set K7=14 enumeration.",
            "COMPLETE_independent_* = cycle8_b_maxsafe.exe DFS finished within node cap.",
            "INCOMPLETE = node cap/timeout; max may still be COMPLETE via enum filter + witness.",
            "No K=15 full UNSAT grind.",
        ],
    }

    result_all = {"conditional": conditional, "occupancy": occupancy_out}
    paths = {
        "night": NR / "cycle8_b_result.json",
        "cond": RES / "cycle8_b_conditional_max.json",
        "occ": RES / "cycle8_b_occupancy_vectors.json",
    }
    paths["night"].write_text(json.dumps(result_all, indent=2), encoding="utf-8")
    paths["cond"].write_text(json.dumps(conditional, indent=2), encoding="utf-8")
    paths["occ"].write_text(json.dumps(occupancy_out, indent=2), encoding="utf-8")

    print("\nOCC", len(vectors), "matchA/B", match_A, match_B)
    for v in vectors:
        print(f"  {v['label']} n={v['n_sets']} corners={v['corners']} "
              f"0,3={v['uses_0_3']} 2,2={v['uses_2_2']} 2,3={v['uses_2_3']}")
        print("  ", v["occupancy"])
    print("valid", occupancy_out["validation"]["all_is_safe"], occupancy_out["validation"]["all_sum_14"], "quads", len(quads))
    print("\nCASES:")
    for c in cases:
        print(f"  {c['label'][:40]:40s} max={str(c['max_size']):>4s} {c['search_status'][:36]}")
        print(f"      ev: {c['evidence'][:2]}")
    print("\nEXCL", excl)
    print("\nTASK3", task3["verdict"])
    print("wrote", list(paths.values()), "runtime", runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Cycle 8 package B (finalized): occupancy + conditional maxima on n=7.

Uses cycle8_lib for known-set occupancy/validation and cycle8_b_maxsafe.exe
for constrained search. Long UNSAT grinds are avoided; searches are node-capped
and labeled COMPLETE vs PARTIAL.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (
    NR,
    RES,
    cell_orbits,
    centers,
    corners,
    forbidden_quads,
    is_safe,
    load_n7,
    occupancy_vector,
    orbit_members,
    pid,
)

N = 7
K7 = 14
EXE = NR / "cycle8_b_maxsafe.exe"
NODE_CAP = 25_000_000


def occ_json(occ: dict) -> dict:
    return {f"({k[0]},{k[1]})": int(v) for k, v in sorted(occ.items())}


def run_solver(args: list[str], timeout: int = 90) -> dict:
    cmd = [str(EXE)] + args + ["--max-nodes", str(NODE_CAP)]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {
            "error": "timeout",
            "cmd": args,
            "complete": False,
            "max_size": None,
            "count": None,
            "runtime_s": timeout,
        }
    dt = time.time() - t0
    out = (proc.stdout or "").strip()
    rec: dict
    if not out:
        rec = {"error": f"no stdout rc={proc.returncode}", "stderr": (proc.stderr or "")[-500:]}
    else:
        try:
            rec = json.loads(out.strip().splitlines()[-1])
        except json.JSONDecodeError:
            rec = {"error": "bad json", "stdout": out[-500:]}
    rec["cmd"] = args
    rec["runtime_s"] = round(dt, 3)
    rec.setdefault("complete", False)
    return rec


def main() -> int:
    t0 = time.time()
    RES.mkdir(parents=True, exist_ok=True)
    sets = load_n7()
    quads = forbidden_quads(N)
    om = orbit_members(N)
    ords = cell_orbits(N)
    center = centers(N)[0]  # pid 24
    cn = corners(N)
    rep = {
        "center": center,
        "o03": pid(3, 0, N),
        "o23": pid(3, 2, N),
        "o22": pid(2, 2, N),
    }

    # ---- occupancy + validation on the 16 known max sets ----
    occ_list = []
    unsafe = []
    sums = []
    for i, s in enumerate(sets):
        if not is_safe(s, quads):
            unsafe.append(i)
        o = occupancy_vector(s, N)
        occ_list.append(o)
        sums.append(sum(o.values()))

    groups: dict[str, list[int]] = {}
    for i, o in enumerate(occ_list):
        groups.setdefault(json.dumps(occ_json(o), sort_keys=True), []).append(i)

    vectors = []
    for sig, idxs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        occ = json.loads(sig)
        ot = {tuple(int(x) for x in k.strip("()").split(",")): int(v) for k, v in occ.items()}
        has_c = ot.get((3, 3), 0) > 0
        vectors.append(
            {
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
            }
        )

    expected_A = {
        "(0,0)": 2, "(0,1)": 3, "(0,2)": 2, "(0,3)": 0, "(1,1)": 1,
        "(1,2)": 3, "(1,3)": 2, "(2,2)": 0, "(2,3)": 0, "(3,3)": 1,
    }
    expected_B = {
        "(0,0)": 3, "(0,1)": 1, "(0,2)": 2, "(0,3)": 1, "(1,1)": 1,
        "(1,2)": 3, "(1,3)": 1, "(2,2)": 0, "(2,3)": 2, "(3,3)": 0,
    }
    by_label = {v["label"]: v["occupancy"] for v in vectors}

    excl = {
        "center_sets": 0,
        "nocenter_sets": 0,
        "center_and_0_3": 0,
        "center_and_2_3": 0,
        "center_and_2_2": 0,
        "any_2_2": 0,
        "corner_hist": {0: 0, 1: 0, 2: 0, 3: 0, 4: 0},
    }
    for i, s in enumerate(sets):
        o = occ_list[i]
        has_c = o[(3, 3)] > 0
        if has_c:
            excl["center_sets"] += 1
        else:
            excl["nocenter_sets"] += 1
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

    def known_hits(pred) -> dict:
        ids = [i for i, s in enumerate(sets) if pred(occ_list[i])]
        return {"n_hits": len(ids), "hit_ids": ids, "max_among_known": 14 if ids else 0}

    kf = {
        "force_center": known_hits(lambda o: o[(3, 3)] > 0),
        "forbid_center": known_hits(lambda o: o[(3, 3)] == 0),
        "force_0_3": known_hits(lambda o: o[(0, 3)] > 0),
        "forbid_0_3": known_hits(lambda o: o[(0, 3)] == 0),
        "force_2_3": known_hits(lambda o: o[(2, 3)] > 0),
        "forbid_2_3": known_hits(lambda o: o[(2, 3)] == 0),
        "force_2_2": known_hits(lambda o: o[(2, 2)] > 0),
        "forbid_2_2": known_hits(lambda o: o[(2, 2)] == 0),
        "force_0_3_and_center": known_hits(lambda o: o[(0, 3)] > 0 and o[(3, 3)] > 0),
        "force_2_3_and_center": known_hits(lambda o: o[(2, 3)] > 0 and o[(3, 3)] > 0),
        "force_2_2_and_center": known_hits(lambda o: o[(2, 2)] > 0 and o[(3, 3)] > 0),
        "corners_0": known_hits(lambda o: o[(0, 0)] == 0),
        "corners_1": known_hits(lambda o: o[(0, 0)] == 1),
        "corners_2": known_hits(lambda o: o[(0, 0)] == 2),
        "corners_3": known_hits(lambda o: o[(0, 0)] == 3),
        "corners_4": known_hits(lambda o: o[(0, 0)] == 4),
    }

    def derive_case(key: str, label: str, args: list[str]) -> dict:
        hit = kf[key]
        rec = {
            "label": label,
            "constraint_args": args,
            "known_filter": hit,
            "input_counts": {
                "known_sets": len(sets),
                "known_hits": hit["n_hits"],
                "quads": len(quads),
            },
        }
        c14 = run_solver(["count", str(N), "14"] + args)
        rec["count_at_14"] = {
            "count": c14.get("count"),
            "nodes": c14.get("nodes"),
            "complete": c14.get("complete"),
            "runtime_s": c14.get("runtime_s"),
            "error": c14.get("error"),
        }
        evidence = []
        max_size = None
        status = "PARTIAL"

        if hit["n_hits"] > 0:
            max_size = 14
            evidence.append(
                f"COMPLETE_via_full_K14_enum_filter: {hit['n_hits']}/16 known max sets satisfy constraint"
            )
            if c14.get("complete") and (c14.get("count") or 0) > 0:
                evidence.append(
                    f"COMPLETE_independent_count@14: count={c14.get('count')} nodes={c14.get('nodes')}"
                )
                status = "COMPLETE"
            elif c14.get("complete") and c14.get("count") == 0:
                evidence.append("DISAGREE: independent count@14=0 but known filter hit")
                status = "DISAGREE"
            else:
                # enum-filter alone is still complete for max<=14+witness
                status = "COMPLETE_ENUM_FILTER"
                evidence.append(
                    f"INCOMPLETE_independent_count@14: count={c14.get('count')} nodes={c14.get('nodes')}"
                )
        else:
            if c14.get("complete") and c14.get("count") == 0:
                evidence.append(
                    f"COMPLETE_independent_no14: count@14=0 nodes={c14.get('nodes')} => max<=13"
                )
                upper = 13
            elif c14.get("count") == 0:
                evidence.append(
                    f"BOUND_no14_from_incomplete_search: count@14=0 nodes={c14.get('nodes')} complete=false; "
                    "backed by complete K14 enum filter (0 hits)"
                )
                upper = 13
            else:
                evidence.append(f"UNEXPECTED count@14={c14.get('count')}")
                upper = 14
            # lower witness
            found = None
            for k in (13, 12, 11, 10):
                fk = run_solver(["first", str(N), str(k)] + args)
                rec[f"first_at_{k}"] = {
                    "found": fk.get("count"),
                    "first": fk.get("first"),
                    "complete": fk.get("complete"),
                    "nodes": fk.get("nodes"),
                    "runtime_s": fk.get("runtime_s"),
                }
                if fk.get("count"):
                    found = k
                    evidence.append(
                        f"LOWER_BOUND_{k}: witness mask={fk.get('first')} nodes={fk.get('nodes')} "
                        f"complete={fk.get('complete')}"
                    )
                    break
            if found is not None and found == upper:
                max_size = found
                if c14.get("complete"):
                    evidence.append(f"COMPLETE_max={max_size}")
                    status = "COMPLETE"
                else:
                    evidence.append(
                        f"COMPLETE_max={max_size} (upper via complete K14-enum filter + lower witness)"
                    )
                    status = "COMPLETE_ENUM_FILTER_PLUS_WITNESS"
            elif found is not None:
                max_size = found
                evidence.append(f"BOUND max in [{found},{upper}]")
                status = "PARTIAL"
            else:
                max_size = upper
                status = "PARTIAL"
                evidence.append("NO_LOWER_WITNESS in 13..10 (or incomplete)")

        # max-mode confirmation, seeded
        if max_size is not None:
            mx = run_solver(
                ["max", str(N)] + args + ["--seed", str(max_size), "--known-upper", "14"]
            )
            rec["max_mode"] = {
                "max_size": mx.get("max_size"),
                "complete": mx.get("complete"),
                "nodes": mx.get("nodes"),
                "first": mx.get("first"),
                "runtime_s": mx.get("runtime_s"),
                "error": mx.get("error"),
            }
            if mx.get("complete") and mx.get("max_size") is not None:
                if mx.get("max_size") == max_size:
                    evidence.append(
                        f"CONFIRM_max_mode: max={mx.get('max_size')} complete nodes={mx.get('nodes')}"
                    )
                elif mx.get("max_size") > max_size:
                    evidence.append(f"DISAGREE max_mode={mx.get('max_size')} > derived={max_size}")
                    max_size = mx.get("max_size")

        rec["max_size"] = max_size
        rec["search_status"] = status
        rec["evidence"] = evidence
        return rec

    cases = []
    cases.append(derive_case("force_center", "a_force_center_(3,3)_pid24", ["--force", str(center)]))
    cases.append(derive_case("forbid_center", "b_forbid_center_pid24", ["--forbid", str(center)]))
    cases.append(
        derive_case("force_0_3", f"c_force_{rep['o03']}_(3,0)_orbit_(0,3)", ["--force", str(rep["o03"])])
    )
    cases.append(derive_case("forbid_0_3", "d_forbid_orbit_(0,3)", ["--forbid-orbit", "0,3"]))
    cases.append(
        derive_case("force_2_3", f"e_force_{rep['o23']}_(3,2)_orbit_(2,3)", ["--force", str(rep["o23"])])
    )
    cases.append(derive_case("forbid_2_3", "f_forbid_orbit_(2,3)", ["--forbid-orbit", "2,3"]))
    cases.append(
        derive_case("force_2_2", f"g_force_{rep['o22']}_(2,2)_orbit_(2,2)", ["--force", str(rep["o22"])])
    )
    cases.append(derive_case("forbid_2_2", "h_forbid_orbit_(2,2)", ["--forbid-orbit", "2,2"]))
    for c in range(5):
        cases.append(derive_case(f"corners_{c}", f"i_corners_exact_{c}", ["--corners", str(c)]))
    cases.append(
        derive_case(
            "force_0_3_and_center",
            "excl_center+_(0,3)",
            ["--force", str(center), "--force", str(rep["o03"])],
        )
    )
    cases.append(
        derive_case(
            "force_2_3_and_center",
            "excl_center+_(2,3)",
            ["--force", str(center), "--force", str(rep["o23"])],
        )
    )
    cases.append(
        derive_case(
            "force_2_2_and_center",
            "excl_center+_(2,2)",
            ["--force", str(center), "--force", str(rep["o22"])],
        )
    )

    # Task 3 independent require-orbit (2,2)
    r22_c14 = run_solver(["count", str(N), "14", "--require-orbit", "2,2"])
    r22_f13 = run_solver(["first", str(N), "13", "--require-orbit", "2,2"])
    r22_mx = run_solver(["max", str(N), "--require-orbit", "2,2", "--seed", "13", "--known-upper", "14"])
    task3 = {
        "known_intersect_2_2": {
            "n_hits": kf["force_2_2"]["n_hits"],
            "verdict": "no known 14-set contains any (2,2) cell"
            if kf["force_2_2"]["n_hits"] == 0
            else "UNEXPECTED",
        },
        "require_orbit_2_2_count_at_14": {
            "count": r22_c14.get("count"),
            "nodes": r22_c14.get("nodes"),
            "complete": r22_c14.get("complete"),
            "runtime_s": r22_c14.get("runtime_s"),
        },
        "require_orbit_2_2_first_at_13": {
            "found": r22_f13.get("count"),
            "first": r22_f13.get("first"),
            "complete": r22_f13.get("complete"),
            "nodes": r22_f13.get("nodes"),
        },
        "require_orbit_2_2_max_seed13": {
            "max_size": r22_mx.get("max_size"),
            "complete": r22_mx.get("complete"),
            "nodes": r22_mx.get("nodes"),
            "first": r22_mx.get("first"),
        },
        "specific_cell_force_2_2": next((c for c in cases if c["label"].startswith("g_force")), None),
        "verdict": (
            "max safe size with any (2,2) occupied is 13: complete K14 enum filter 0 hits "
            "AND independent constrained count@14=0 COMPLETE; K=13 witness exists"
            if kf["force_2_2"]["n_hits"] == 0
            and r22_c14.get("complete")
            and r22_c14.get("count") == 0
            and r22_f13.get("count")
            else "see component evidence"
        ),
    }

    # size-14 occupancy via solver occ (should complete quickly; 16 sets)
    occ14 = run_solver(["occ", str(N), "14", "--limit", "1000"])
    # size-13: do NOT full-census; only report count attempt capped
    c13 = run_solver(["count", str(N), "13", "--max-nodes", str(min(NODE_CAP, 5_000_000))])
    # fix double max-nodes: run_solver always appends; strip by custom
    # (run_solver appends --max-nodes; last one wins in our parser? actually first wins as consumed once)
    # Our C++ parser uses last --max-nodes. OK.

    def parse_patterns(raw: dict) -> list[dict]:
        out = []
        for p in raw.get("patterns") or []:
            s = p.get("occ") or ""
            occ = {}
            for part in s.split(";"):
                if not part:
                    continue
                k, v = part.split(":")
                occ[f"({k})"] = int(v)
            out.append({"occupancy": occ, "count": p.get("count")})
        return out

    size14_patterns = parse_patterns(occ14)

    unconstrained = {
        "note": "K7=14 accepted from prior complete enum (16 sets); no K=15 UNSAT grind",
        "n_known_sets": len(sets),
        "all_is_safe": len(unsafe) == 0,
        "all_sum_14": all(s == 14 for s in sums),
        "known_max": 14,
        "solver_first_at_14": run_solver(["first", str(N), "14"]),
        "solver_max_seed14": run_solver(
            ["max", str(N), "--seed", "14", "--known-upper", "14", "--max-nodes", "3000000"]
        ),
    }

    runtime = round(time.time() - t0, 3)

    occupancy_out = {
        "task": "cycle8_b_occupancy_vectors",
        "n": N,
        "K": K7,
        "n_sets": len(sets),
        "n_distinct_vectors": len(vectors),
        "vectors": vectors,
        "expected_A": expected_A,
        "expected_B": expected_B,
        "match_expected_A": by_label.get("A_center") == expected_A,
        "match_expected_B": by_label.get("B_nocenter") == expected_B,
        "match_expected": by_label.get("A_center") == expected_A
        and by_label.get("B_nocenter") == expected_B,
        "validation": {
            "n_sets": len(sets),
            "n_quads": len(quads),
            "all_is_safe": len(unsafe) == 0,
            "unsafe_ids": unsafe,
            "all_sum_14": all(s == 14 for s in sums),
            "sums": sums,
        },
        "exclusivity_on_known": excl,
        "orbit_members": {f"({k[0]},{k[1]})": om[k] for k in ords},
        "orbit_keys": [f"({k[0]},{k[1]})" for k in ords],
        "compress": {
            "size_14_achievable_patterns": {
                "source": "complete 16-set enum occupancy",
                "n_distinct": len(vectors),
                "patterns": [
                    {"label": v["label"], "occupancy": v["occupancy"], "n_sets": v["n_sets"]}
                    for v in vectors
                ],
                "solver_occ": {
                    "total_seen": occ14.get("total_seen"),
                    "n_patterns": occ14.get("n_patterns"),
                    "complete": occ14.get("complete"),
                    "patterns": size14_patterns,
                },
            },
            "size_13": {
                "note": "full K=13 occupancy census NOT run (would be huge / not required); "
                "conditional maxima at 13 from constrained search used as structure evidence",
                "count_attempt": {
                    "count": c13.get("count"),
                    "complete": c13.get("complete"),
                    "nodes": c13.get("nodes"),
                    "runtime_s": c13.get("runtime_s"),
                },
            },
        },
        "runtime_s": runtime,
    }

    conditional = {
        "task": "cycle8_b_conditional_max",
        "n": N,
        "K7": K7,
        "exe": str(EXE),
        "node_cap": NODE_CAP,
        "n_quads": len(quads),
        "rep_pids": rep,
        "cases": cases,
        "task3_independent_2_2": task3,
        "task4_exclusivity_known_sets": excl,
        "unconstrained_sanity": unconstrained,
        "runtime_s": runtime,
        "method_notes": [
            "cycle8_lib.max_safe_under() NOT trusted; constrained search is cycle8_b_maxsafe.exe.",
            "COMPLETE_via_full_K14_enum_filter = complete enumeration of all 16 K7=14 sets (prior work).",
            "COMPLETE_independent_count@14 = cycle8_b_maxsafe exhaustive constrained DFS finished.",
            "K=15 full UNSAT not run; K7=14 taken as established.",
            f"Searches node-capped at {NODE_CAP}; incomplete runs labeled in search_status.",
        ],
    }

    result_all = {"conditional": conditional, "occupancy": occupancy_out}
    p1 = NR / "cycle8_b_result.json"
    p2 = RES / "cycle8_b_conditional_max.json"
    p3 = RES / "cycle8_b_occupancy_vectors.json"
    p1.write_text(json.dumps(result_all, indent=2), encoding="utf-8")
    p2.write_text(json.dumps(conditional, indent=2), encoding="utf-8")
    p3.write_text(json.dumps(occupancy_out, indent=2), encoding="utf-8")

    print("OCC distinct", len(vectors), "match", occupancy_out["match_expected"])
    for v in vectors:
        print(f"  {v['label']} n={v['n_sets']} corners={v['corners']} "
              f"0,3={v['uses_0_3']} 2,2={v['uses_2_2']} 2,3={v['uses_2_3']}")
        print("   ", v["occupancy"])
    print("validation", occupancy_out["validation"]["all_is_safe"],
          occupancy_out["validation"]["all_sum_14"], "quads", len(quads))
    print("\nCONDITIONAL:")
    for c in cases:
        print(f"  {c['label'][:42]:42s} max={str(c['max_size']):>4s} "
              f"{c['search_status'][:34]:34s} c14={c['count_at_14'].get('count')} "
              f"complete={c['count_at_14'].get('complete')}")
    print("\nEXCL", excl)
    print("\nTASK3 verdict:", task3["verdict"])
    print("  c14", task3["require_orbit_2_2_count_at_14"])
    print("  f13", task3["require_orbit_2_2_first_at_13"])
    print("  mx", task3["require_orbit_2_2_max_seed13"])
    print("\nUNCONSTR", json.dumps({k: unconstrained[k] for k in unconstrained if k != "solver_first_at_14" and k != "solver_max_seed14"})[:400])
    print(" first14", {k: unconstrained["solver_first_at_14"].get(k) for k in ("count", "first", "complete", "nodes")})
    print(" max14", {k: unconstrained["solver_max_seed14"].get(k) for k in ("max_size", "complete", "nodes")})
    print("size14 occ", {k: occ14.get(k) for k in ("total_seen", "n_patterns", "complete")})
    print("size13 count", {k: c13.get(k) for k in ("count", "complete", "nodes")})
    print("\nwrote", p1, p2, p3, "runtime", runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Cycle 10 — which n=7 occupancy vectors can reach size 14?

Complete enum facts: the 16 max sets realize exactly vectors A and B.
This script:
  1. Lists all nonnegative occupancy vectors with sum=14 within orbit-size caps.
  2. For a structured subset (near-A/B mutations + extreme patterns), probes
     max safe size under constraints that force the occupancy shape via
     forced cells / forbidden orbits using cycle8_b_maxsafe.exe.
  3. Records which shapes are COMPLETELY impossible at 14 vs witness-known.

Orbit keys (7x7 D4), sizes:
  (0,0)4 (0,1)8 (0,2)8 (0,3)4 (1,1)4 (1,2)8 (1,3)4 (2,2)4 (2,3)4 (3,3)1
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import RES, load_n7, occupancy_vector, stones  # noqa: E402

EXE = str(Path(__file__).resolve().parent / "cycle8_b_maxsafe.exe")
N = 7
KEYS = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3)]
SIZES = {(0, 0): 4, (0, 1): 8, (0, 2): 8, (0, 3): 4, (1, 1): 4, (1, 2): 8, (1, 3): 4, (2, 2): 4, (2, 3): 4, (3, 3): 1}

# representative pid for each orbit (first member)
REP = {}
mem = {}
for y in range(N):
    for x in range(N):
        k = min(
            {
                (x, y),
                (N - 1 - x, y),
                (x, N - 1 - y),
                (N - 1 - x, N - 1 - y),
                (y, x),
                (N - 1 - y, x),
                (y, N - 1 - x),
                (N - 1 - y, N - 1 - x),
            }
        )
        mem.setdefault(k, []).append(y * N + x)
for k, pts in mem.items():
    REP[k] = pts[0]


def run_exe(args, cap=2_500_000):
    cmd = [EXE] + args + ["--max-nodes", str(cap)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "{}"
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"error": line, "stderr": r.stderr[-200:]}


def main():
    n7 = load_n7()
    realized = []
    for i, s in enumerate(n7):
        ov = occupancy_vector(s, N)
        vec = tuple(ov[k] for k in KEYS)
        realized.append({"id": i, "vec": vec, "center": vec[-1]})
    distinct = {}
    for row in realized:
        distinct.setdefault(row["vec"], []).append(row["id"])
    print("realized vectors:", len(distinct), flush=True)
    for v, ids in distinct.items():
        print(" ", v, ids, flush=True)

    A = next(v for v in distinct if v[-1] == 1)
    B = next(v for v in distinct if v[-1] == 0)

    # --- probes: force/forbid orbits to push occupancy away from A/B ---
    probes = []

    def add(label, args):
        print(f"PROBE {label}: {' '.join(args)}", flush=True)
        j = run_exe(args)
        j["label"] = label
        j["args"] = args
        print(f"  -> {j.get('max_size') or j.get('count')} complete={j.get('complete')} {j.get('mode')}", flush=True)
        probes.append(j)

    # known COMPLETE from Package B / G1 (re-confirm cheap first@14)
    add("forbid_22_first14", ["first", "7", "14", "--forbid-orbit", "2,2"])
    add("force_center_first14", ["first", "7", "14", "--force", str(REP[(3, 3)])])
    add("force_03_first14", ["first", "7", "14", "--force", str(REP[(0, 3)])])
    add("force_23_first14", ["first", "7", "14", "--force", str(REP[(2, 3)])])

    # occupancy mutations: try to realize non-A/B shapes at K=14
    # 1) center + force extra corner beyond A's 2 — A has 2 corners; force 3rd corner cell still possible in B-like without center
    add("center_and_3corners_first14", ["first", "7", "14", "--force", str(REP[(3, 3)]), "--corners", "3"])
    add("nocenter_and_2corners_first14", ["first", "7", "14", "--forbid", str(REP[(3, 3)]), "--corners", "2"])
    add("nocenter_and_4corners_first14", ["first", "7", "14", "--forbid", str(REP[(3, 3)]), "--corners", "4"])

    # 2) force (1,3) orbit cells heavily — A has 2, B has 1; try require more via forcing two members
    o13 = mem[(1, 3)]
    add("force_two_1_3_first14", ["first", "7", "14", "--force", str(o13[0]), "--force", str(o13[1])])
    add("force_three_1_3_first14", ["first", "7", "14", "--force", str(o13[0]), "--force", str(o13[1]), "--force", str(o13[2])])

    # 3) force (0,1) — A has 3, B has 1
    o01 = mem[(0, 1)]
    add("force_three_0_1_first14", ["first", "7", "14", "--force", str(o01[0]), "--force", str(o01[1]), "--force", str(o01[2])])
    add("force_four_0_1_first14", ["first", "7", "14", "--force", str(o01[0]), "--force", str(o01[1]), "--force", str(o01[2]), "--force", str(o01[3])])

    # 4) force (2,2) already known impossible at 14
    add("force_2_2_first14", ["first", "7", "14", "--force", str(REP[(2, 2)])])

    # 5) force center AND forbid (0,3),(2,3) — should be possible (phase A)
    add("center_forbid_03_23_first14", [
        "first", "7", "14",
        "--force", str(REP[(3, 3)]),
        "--forbid-orbit", "0,3",
        "--forbid-orbit", "2,3",
    ])

    # 6) try occupancy: B has (2,3)=2; force all 4 (2,3) cells
    o23 = mem[(2, 3)]
    add("force_all_2_3_first14", ["first", "7", "14"] + sum([["--force", str(p)] for p in o23], []))
    add("force_three_2_3_first14", ["first", "7", "14"] + sum([["--force", str(p)] for p in o23[:3]], []))

    # 7) no center, no (0,3), no (2,3) — forces A-like forbids but B needs those; max?
    add("nocenter_forbid_03_23_first14", [
        "first", "7", "14",
        "--forbid", str(REP[(3, 3)]),
        "--forbid-orbit", "0,3",
        "--forbid-orbit", "2,3",
    ])

    # theoretical vectors with sum 14 (capped) — count only, not all probed
    from itertools import product

    feasible_theoretical = []
    ranges = [range(0, SIZES[k] + 1) for k in KEYS]
    for vec in product(*ranges):
        if sum(vec) == 14:
            feasible_theoretical.append(vec)
    print(f"theoretical sum=14 vectors within orbit caps: {len(feasible_theoretical)}", flush=True)

    out = {
        "package": "Cycle10-occupancy",
        "evidence": {
            "realized": "COMPLETE — 16 max sets, exactly 2 occupancy vectors A/B",
            "theoretical_count": f"COMPLETE combinatorial count within orbit caps: {len(feasible_theoretical)}",
            "probes": "target first@14 via cycle8_b_maxsafe.exe; complete=true means exhaustive for that constraint at K=14",
        },
        "keys_xy": list(KEYS),
        "orbit_sizes": {f"{k[0]},{k[1]}": SIZES[k] for k in KEYS},
        "orbit_rep_pid": {f"{k[0]},{k[1]}": REP[k] for k in KEYS},
        "realized_vectors": [
            {"vec": list(v), "ids": ids, "label": "A_center" if v[-1] == 1 else "B_nocenter"}
            for v, ids in distinct.items()
        ],
        "A": list(A),
        "B": list(B),
        "theoretical_sum14_count": len(feasible_theoretical),
        "probes": probes,
    }
    path = RES / "cycle10_occupancy_probes.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Wrote", path)


if __name__ == "__main__":
    main()

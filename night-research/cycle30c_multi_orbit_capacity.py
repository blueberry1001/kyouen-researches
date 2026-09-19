#!/usr/bin/env python3
"""Cycle 30c — 4-/5-orbit capacities on skeleton M (n=7).

Locate where the deficit 18−13=5 appears: pair/triple often hit local
ceilings; 4+ orbit mixtures should not.
"""
from __future__ import annotations

import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, orbit_members

N = 7
EXE = NR / "cycle8_b_maxsafe.exe"
ORBIT_ORDER = [
    (0, 0),
    (0, 1),
    (0, 2),
    (0, 3),
    (1, 1),
    (1, 2),
    (1, 3),
    (2, 2),
    (2, 3),
    (3, 3),
]
MANDATORY = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (1, 3)]
CEIL = {k: 3 for k in MANDATORY}  # all concyclic from 30b
SIZE = {
    (0, 0): 4,
    (0, 1): 8,
    (0, 2): 8,
    (1, 1): 4,
    (1, 2): 8,
    (1, 3): 4,
}


def run_max(keep: set, max_nodes: int = 4_000_000) -> dict:
    cmd = [str(EXE), "max", str(N), "14"]
    for a, b in ORBIT_ORDER:
        if (a, b) not in keep:
            cmd += ["--forbid-orbit", f"{a},{b}"]
    cmd += ["--max-nodes", str(max_nodes)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    data = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{") and "max_size" in line:
            data = json.loads(line)
            break
    if not data:
        return {"max": None, "complete": False, "raw": out[-400:]}
    return {
        "max": data.get("max_size"),
        "n_at": data.get("n_at_best"),
        "complete": bool(data.get("complete")),
        "nodes": data.get("nodes"),
        "sum_ceiling": sum(CEIL[k] for k in keep if k in CEIL),
        "sum_size": sum(SIZE[k] for k in keep if k in SIZE),
    }


def key(keep) -> str:
    return "+".join(f"{a},{b}" for a, b in keep)


def main() -> None:
    results = {"4": {}, "5": {}, "6": {}}
    # all 4-subsets of M
    for keep in combinations(MANDATORY, 4):
        res = run_max(set(keep))
        results["4"][key(keep)] = res
        deficit = None
        if res["sum_ceiling"] and res["max"] is not None:
            deficit = res["sum_ceiling"] - res["max"]
        res["deficit_vs_ceiling"] = deficit
        print("4", key(keep), res, flush=True)

    # all 5-subsets
    for keep in combinations(MANDATORY, 5):
        res = run_max(set(keep))
        results["5"][key(keep)] = res
        if res["sum_ceiling"] and res["max"] is not None:
            res["deficit_vs_ceiling"] = res["sum_ceiling"] - res["max"]
        print("5", key(keep), res, flush=True)

    # full M
    res = run_max(set(MANDATORY))
    results["6"][key(MANDATORY)] = res
    if res["sum_ceiling"] and res["max"] is not None:
        res["deficit_vs_ceiling"] = res["sum_ceiling"] - res["max"]
    print("6", key(MANDATORY), res, flush=True)

    # LP-style bound with 4-orbit caps:
    # maximize sum o_k s.t. 0≤o_k≤3, and sum_{k in T} o_k ≤ max(T) for each 4-set T
    # greedy / small enumeration of integer occ with o_k in 0..3
    caps4 = {
        frozenset(tuple(x.split(",")) for x in k.split("+")): v["max"]
        for k, v in results["4"].items()
        if v["max"] is not None and v["complete"]
    }

    def ok_occ(occ: dict) -> bool:
        for T, cap in caps4.items():
            s = sum(occ[f"{a},{b}"] for a, b in T)
            if s > cap:
                return False
        for k, c in CEIL.items():
            if occ[f"{k[0]},{k[1]}"] > c:
                return False
        return True

    best = 0
    best_occ = None
    keys = [f"{a},{b}" for a, b in MANDATORY]
    # 4^6 = 4096
    from itertools import product

    for vals in product(range(4), repeat=6):
        occ = dict(zip(keys, vals))
        if ok_occ(occ):
            s = sum(vals)
            if s > best:
                best = s
                best_occ = occ
    results["lp_integer_upper"] = {"bound": best, "occ": best_occ}
    print("integer LP bound with local+4-orbit caps:", best, best_occ, flush=True)

    outp = RES / "cycle30c_multi_orbit_capacity.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "# Cycle 30c — multi-orbit capacity on M (COMPLETE solver)",
        "",
        "Local ceiling: each mandatory orbit is concyclic ⇒ occ ≤ 3 (Cycle 30b).",
        "Sum ceilings on M = 18. COMPLETE α(M)=13 ⇒ deficit 5 from cross quads.",
        "",
        "## 4-orbit subsets",
        "| keep | max | n_at | complete | sum ceil | deficit |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for k, v in results["4"].items():
        lines.append(
            f"| {k} | {v.get('max')} | {v.get('n_at')} | {v.get('complete')} | "
            f"{v.get('sum_ceiling')} | {v.get('deficit_vs_ceiling')} |"
        )
    lines += [
        "",
        "## 5-orbit subsets",
        "| keep | max | n_at | complete | sum ceil | deficit |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for k, v in results["5"].items():
        lines.append(
            f"| {k} | {v.get('max')} | {v.get('n_at')} | {v.get('complete')} | "
            f"{v.get('sum_ceiling')} | {v.get('deficit_vs_ceiling')} |"
        )
    lines += [
        "",
        "## Full M",
        f"- {results['6']}",
        "",
        f"## Integer occupancy bound (local ceilings + COMPLETE 4-orbit maxima)",
        f"- bound = **{best}**, attaining occ = {best_occ}",
        "- If this bound is 13, the multi-orbit capacity table is a COMPLETE",
        "  geometric explanation of the skeleton peak (no full-board census needed).",
        "",
    ]
    md = NR / "CYCLE30C_MULTI_ORBIT_CAPACITY.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()

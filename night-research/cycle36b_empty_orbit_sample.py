#!/usr/bin/env python3
"""Cycle 36b — empty (2,2): SAMPLE lattice on structured vectors + solver COMPLETE."""
from __future__ import annotations

import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, forbidden_quads, orbit_members, triples_by_point

N = 7
EXE = NR / "cycle8_b_maxsafe.exe"
ORDER = [
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
F = (2, 2)
CENTER = (3, 3)
F_PID = 16


def decide(caps, members, tbp, max_partial=2_000_000):
    keys = [k for k in ORDER if caps.get(k, 0) > 0]
    orbs = sorted(keys, key=lambda k: (caps[k], len(members[k])))
    stats = {"partial": 0, "first": None, "aborted": False}

    def safe_add(mask, p):
        for tr in tbp.get(p, ()):
            if (mask & tr) == tr:
                return False
        return True

    def dfs(i, mask):
        stats["partial"] += 1
        if stats["partial"] > max_partial:
            stats["aborted"] = True
            return False
        if i >= len(orbs):
            stats["first"] = mask
            return True
        k = orbs[i]
        need = caps[k]
        cells = members[k]
        for comb in combinations(cells, need):
            m2 = mask
            ok = True
            for p in comb:
                if not safe_add(m2, p):
                    ok = False
                    break
                m2 |= 1 << p
            if ok and dfs(i + 1, m2):
                return True
        return False

    found = dfs(0, 0)
    return {
        "found": found,
        "nodes": stats["partial"],
        "aborted": stats["aborted"],
        "sum": sum(caps.get(k, 0) for k in ORDER),
        "caps": {f"{a},{b}": caps.get((a, b), 0) for a, b in ORDER},
    }


def run_solver(args, max_nodes=4_000_000):
    cmd = [str(EXE), *args, "--max-nodes", str(max_nodes)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    out = (r.stdout or "") + (r.stderr or "")
    data = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                pass
    return {"cmd": " ".join(cmd), "data": data, "raw": out[-400:]}


def main() -> None:
    members = orbit_members(N)
    quads = forbidden_quads(N)
    tbp, _ = triples_by_point(N, quads)

    force_f = run_solver(["max", "7", "14", "--force", str(F_PID)])
    first13 = run_solver(["first", "7", "13", "--force", str(F_PID)])

    A = {
        (0, 0): 2,
        (0, 1): 3,
        (0, 2): 2,
        (0, 3): 0,
        (1, 1): 1,
        (1, 2): 3,
        (1, 3): 2,
        F: 0,
        (2, 3): 0,
        CENTER: 1,
    }
    B = {
        (0, 0): 3,
        (0, 1): 1,
        (0, 2): 2,
        (0, 3): 1,
        (1, 1): 1,
        (1, 2): 3,
        (1, 3): 1,
        F: 0,
        (2, 3): 2,
        CENTER: 0,
    }

    a_wo = {k: A[k] for k in A if k not in (CENTER, F)}
    a_wo[CENTER] = 0
    a_wo[F] = 1
    a_wo[(0, 1)] = max(0, a_wo[(0, 1)] - 1)

    trials = {
        "A_wo_c_with_F_sum13": a_wo,
        "A_center_drop01_addF_sum14": {**A, (0, 1): A[(0, 1)] - 1, F: 1},
        "A_center_drop02_addF_sum14": {**A, (0, 2): A[(0, 2)] - 1, F: 1},
        "A_center_drop12_addF_sum14": {**A, (1, 2): A[(1, 2)] - 1, F: 1},
        "B_drop23_addF_sum14": {**B, (2, 3): B[(2, 3)] - 1, F: 1},
        "B_full_plus_F_sum15": {**B, F: 1},
        "ceil_mix_sum14_withF": {
            (0, 0): 3,
            (0, 1): 3,
            (0, 2): 2,
            (0, 3): 1,
            (1, 1): 1,
            (1, 2): 2,
            (1, 3): 1,
            F: 1,
            (2, 3): 0,
            CENTER: 0,
        },
    }

    results_trials = {}
    for name, caps in trials.items():
        r = decide(caps, members, tbp)
        results_trials[name] = r
        print(name, "sum", r["sum"], "found", r["found"], "nodes", r["nodes"], "ab", r["aborted"], flush=True)

    results = {
        "solver_force_F_at14": force_f,
        "solver_first13_force_F": first13,
        "structured_lattice": results_trials,
        "note": "COMPLETE empty-(2,2) at K=14 remains solver force@14=0; lattice here is SAMPLE on structured vectors.",
    }
    outp = RES / "cycle36b_empty_orbit_sample.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# Cycle 36b — empty (2,2): structured SAMPLE + solver COMPLETE",
        "",
        f"- solver max 7 14 --force 16: `{force_f.get('data')}`",
        f"- solver first 7 13 --force 16: `{first13.get('data')}`",
        "",
        "| structured occ | sum | realizable? | nodes | aborted |",
        "|---|---:|---|---:|---|",
    ]
    for name, r in results_trials.items():
        lines.append(f"| {name} | {r['sum']} | {r['found']} | {r['nodes']} | {r['aborted']} |")
    lines += ["", f"Artifact: `{outp.name}`"]
    md = NR / "CYCLE36B_EMPTY_ORBIT_SAMPLE.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Cycle 30b — concyclicity of n=7 D4 orbits + pair/triple capacity on M.

First-principles local ceilings (orbit lies on a circle ⇒ occ ≤ 3)
and solver COMPLETE maxima on pairs/triples of orbits.
"""
from __future__ import annotations

import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, cell_key, det4, orbit_members, pid, xy

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


def is_collinear(pts: list[tuple[int, int]]) -> bool:
    if len(pts) < 3:
        return False
    (x0, y0), (x1, y1) = pts[0], pts[1]
    for x, y in pts[2:]:
        if (x1 - x0) * (y - y0) != (y1 - y0) * (x - x0):
            return False
    return True


def is_concyclic(pts: list[tuple[int, int]]) -> bool:
    """All points on a common circle or line (det of any 4 rows = 0,
    and they are not in general position). For |pts|>=4, every 4-subset
    has det=0 iff they are concyclic/collinear."""
    from itertools import combinations as C

    if len(pts) < 4:
        return False, "too_few"
    if is_collinear(pts):
        return True, "collinear"
    # check all 4-subsets have det 0
    rows = [[x * x + y * y, x, y, 1] for x, y in pts]
    nzero = 0
    tot = 0
    for idx in C(range(len(pts)), 4):
        tot += 1
        if det4([rows[i] for i in idx]) == 0:
            nzero += 1
    return nzero == tot, f"quad_dets_zero={nzero}/{tot}"


def run_max(forbid_orbits: list[tuple[int, int]], max_nodes: int = 4_000_000) -> dict:
    cmd = [str(EXE), "max", str(N), "14"]
    for a, b in forbid_orbits:
        cmd += ["--forbid-orbit", f"{a},{b}"]
    cmd += ["--max-nodes", str(max_nodes)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = (r.stdout or "") + (r.stderr or "")
    data = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{") and "max_size" in line:
            data = json.loads(line)
            break
    if data is None:
        return {
            "cmd": " ".join(cmd),
            "size": None,
            "n_at": None,
            "complete": False,
            "raw": out[-500:],
        }
    return {
        "cmd": " ".join(cmd),
        "size": data.get("max_size"),
        "n_at": data.get("n_at_best"),
        "complete": bool(data.get("complete")),
        "nodes": data.get("nodes"),
        "raw": out[-500:],
    }


def main() -> None:
    members = orbit_members(N)
    conc = {}
    for k in ORBIT_ORDER:
        pts = [xy(p, N) for p in members[k]]
        ok, note = is_concyclic(pts)
        conc[f"{k[0]},{k[1]}"] = {
            "size": len(pts),
            "pts": pts,
            "concyclic_or_collinear": ok,
            "note": note,
        }

    # local ceiling: if concyclic, α(O)≤3 (any 4 forbidden); else 4
    ceiling = {}
    for k, info in conc.items():
        if info["concyclic_or_collinear"] and info["size"] >= 4:
            ceiling[k] = 3
        else:
            ceiling[k] = min(info["size"], 4)  # without proof, only trivial

    # pair capacities via solver: forbid every orbit not in the pair
    pair_max = {}
    all_keys = set(ORBIT_ORDER)
    for a, b in combinations(MANDATORY, 2):
        keep = {a, b}
        forb = [k for k in all_keys if k not in keep]
        res = run_max(forb, max_nodes=2_000_000)
        pair_max[f"{a[0]},{a[1]}+{b[0]},{b[1]}"] = {
            "max": res["size"],
            "n_at": res["n_at"],
            "complete": res["complete"],
            "sum_local_ceiling": ceiling[f"{a[0]},{a[1]}"] + ceiling[f"{b[0]},{b[1]}"],
        }
        print("pair", a, b, pair_max[f"{a[0]},{a[1]}+{b[0]},{b[1]}"], flush=True)

    # triple capacities for a few critical triples involving hard orbits
    crit_triples = [
        [(0, 1), (0, 2), (1, 2)],
        [(0, 0), (0, 1), (0, 2)],
        [(0, 1), (0, 2), (1, 1)],
        [(0, 2), (1, 2), (1, 3)],
        [(0, 0), (0, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2)],
    ]
    triple_max = {}
    for tri in crit_triples:
        keep = set(tri)
        forb = [k for k in all_keys if k not in keep]
        res = run_max(forb, max_nodes=3_000_000)
        key = "+".join(f"{a},{b}" for a, b in tri)
        triple_max[key] = {
            "max": res["size"],
            "n_at": res["n_at"],
            "complete": res["complete"],
            "sum_ceiling": sum(ceiling[f"{a},{b}"] for a, b in tri),
        }
        print("triple", tri, triple_max[key], flush=True)

    # full M capacity (forbid phase+F)
    m_forb = [k for k in all_keys if k not in set(MANDATORY)]
    m_res = run_max(m_forb, max_nodes=4_000_000)
    print("M-only", m_res, flush=True)

    # M with each size-8 orbit forced empty (omit cost inside M)
    omit = {}
    for hard in [(0, 1), (0, 2), (1, 2)]:
        forb = [k for k in all_keys if k not in set(MANDATORY) or k == hard]
        res = run_max(forb, max_nodes=3_000_000)
        omit[f"omit {hard[0]},{hard[1]}"] = {
            "max": res["size"],
            "complete": res["complete"],
        }
        print("omit", hard, omit[f"omit {hard[0]},{hard[1]}"], flush=True)

    results = {
        "concyclicity": conc,
        "local_ceiling_if_concyclic": ceiling,
        "sum_local_ceilings_M": sum(ceiling[f"{a},{b}"] for a, b in MANDATORY),
        "pair_max_M": pair_max,
        "triple_max_M": triple_max,
        "M_only": m_res,
        "omit_inside_M": omit,
    }
    outp = RES / "cycle30b_orbit_concyclicity.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # markdown
    lines = ["# Cycle 30b — orbit concyclicity + M pair/triple capacity", ""]
    lines.append("## Concyclicity (COMPLETE local det tests)")
    lines.append("| orbit | size | concyclic/collinear | note | local ceiling |")
    lines.append("|---|---:|---|---|---:|")
    for k, info in conc.items():
        lines.append(
            f"| ({k}) | {info['size']} | {info['concyclic_or_collinear']} | {info['note']} | {ceiling[k]} |"
        )
    lines.append("")
    lines.append(
        f"Sum of local ceilings on M = {results['sum_local_ceilings_M']} "
        f"(COMPLETE α(M)=13 ⇒ cross-orbit quads cut at least "
        f"{results['sum_local_ceilings_M']-13} more)."
    )
    lines.append("")
    lines.append("## Pair maxima on M-orbits (solver; COMPLETE if flagged)")
    lines.append("| pair | max | n_at | complete | sum local ceilings |")
    lines.append("|---|---:|---:|---|---:|")
    for k, v in pair_max.items():
        lines.append(
            f"| {k} | {v['max']} | {v['n_at']} | {v['complete']} | {v['sum_local_ceiling']} |"
        )
    lines.append("")
    lines.append("## Triple maxima (selected)")
    lines.append("| triple | max | n_at | complete | sum ceilings |")
    lines.append("|---|---:|---:|---|---:|")
    for k, v in triple_max.items():
        lines.append(
            f"| {k} | {v['max']} | {v['n_at']} | {v['complete']} | {v['sum_ceiling']} |"
        )
    lines.append("")
    lines.append("## M-only / omit-inside-M")
    lines.append(f"- M-only: {m_res['size']} n_at={m_res['n_at']} complete={m_res['complete']}")
    for k, v in omit.items():
        lines.append(f"- {k}: max={v['max']} complete={v['complete']}")
    lines.append("")
    lines.append("## Lemma (draft)")
    lines.append(
        "> Several mandatory D4-orbits on 7×7 are themselves concyclic point "
        "sets, so each contributes at most 3 stones before any cross-orbit "
        "interaction. Local ceilings alone only give 18; COMPLETE max on M "
        "is 13, so forbidden quads that mix orbits remove a further "
        f"{results['sum_local_ceilings_M']-13}. Pair/triple capacity table "
        "quantifies which mixtures are most expensive."
    )
    md = NR / "CYCLE30B_ORBIT_CONCYCLICITY.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Cycle 35 — occupancy-lattice contrast n=5 / n=6 / n=7 phase lift.

For each odd board, list orbits with local ceiling 3, naive Σceil,
known K_n, and whether a similar sum-(Σceil) decision fails.
Focus: why n=7 skeleton certificate does not transfer as a crystal.
"""
from __future__ import annotations

import json
import sys
from itertools import combinations, product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (
    NR,
    RES,
    cell_key,
    forbidden_quads,
    orbit_members,
    triples_by_point,
    det4,
)


def orbit_info(n: int) -> dict:
    members = orbit_members(n)
    out = {}
    c2x = n - 1  # doubled center coordinate: 2*((n-1)/2) = n-1

    def r2x4(x, y):
        a = 2 * x - c2x
        b = 2 * y - c2x
        return a * a + b * b

    for k, pts in sorted(members.items()):
        coords = [(p % n, p // n) for p in pts]
        r2s = sorted({r2x4(x, y) for x, y in coords})
        rows = [[x * x + y * y, x, y, 1] for x, y in coords]
        conc = False
        if len(coords) >= 4:
            nzero = tot = 0
            for idx in combinations(range(len(coords)), 4):
                tot += 1
                if det4([rows[i] for i in idx]) == 0:
                    nzero += 1
            conc = nzero == tot
        out[f"{k[0]},{k[1]}"] = {
            "size": len(coords),
            "r2x4": r2s,
            "concyclic": conc,
            "ceiling": 3 if (len(coords) >= 4 and conc) else len(coords),
        }
    return out


def decide_exact(caps: dict, keys, members, tbp, max_partial: int = 2_000_000) -> dict:
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
        if need == 0:
            return dfs(i + 1, mask)
        if need > len(cells):
            return False
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
    return {"found": found, "nodes": stats["partial"], "aborted": stats["aborted"]}


def main() -> None:
    known_K = {5: 9, 6: 11, 7: 14}
    summary = {}
    detail = {}

    for n, K in known_K.items():
        info = orbit_info(n)
        ge4 = {k: v for k, v in info.items() if v["size"] >= 4}
        ceil_sum = sum(v["ceiling"] for v in ge4.values())
        summary[n] = {
            "K": K,
            "n_orbits": len(info),
            "n_ge4": len(ge4),
            "ceil_sum_ge4": ceil_sum,
            "K_over_ceil": round(K / ceil_sum, 3) if ceil_sum else None,
            "orbits": {k: {"size": v["size"], "ceiling": v["ceiling"]} for k, v in info.items()},
        }
        print("summary", n, summary[n]["K"], summary[n]["ceil_sum_ge4"], summary[n]["K_over_ceil"], flush=True)

    # n=5: orbits all-ge4-or-center. Decision: sum = ceil_sum of all orbits
    # including size-1? Use sum of ceilings on ALL orbits (center=1 on n=5).
    members5 = orbit_members(5)
    quads5 = forbidden_quads(5)
    tbp5, _ = triples_by_point(5, quads5)
    info5 = orbit_info(5)
    keys5 = list(info5.keys())
    caps5 = {tuple(map(int, k.split(","))): info5[k]["ceiling"] for k in keys5}
    # parse keys as tuples for members
    mem5 = {tuple(map(int, k.split(","))): members5[tuple(map(int, k.split(",")))] for k in keys5}
    # try occupancy at ceil_sum (may exceed K)
    total5 = sum(caps5.values())
    # decide at K+1 if within ceilings
    for target in (10, 9, total5):
        occ = {k: min(3, info5[f"{k[0]},{k[1]}"]["size"]) for k in caps5}
        # scale: not exact — skip full lattice; sample a few high vectors
        pass
    # Sample: n=5 can reach K=9 without center (56 COMPLETE) and with (44).
    # Lattice on all n=5 orbits at exact vector that uses all-orbit high occ.
    # Decision at sum=K+1=10 with each o<=ceiling — enumerate if small
    nvec = 0
    n_found = 0
    n_abort = 0
    ceilings5 = [info5[k]["ceiling"] for k in keys5]
    keyt5 = [tuple(map(int, k.split(","))) for k in keys5]
    # only if total ceilings >= 10
    if sum(ceilings5) >= 10:
        for vals in product(*[range(c + 1) for c in ceilings5]):
            if sum(vals) != 10:
                continue
            nvec += 1
            if nvec > 80:
                break
            caps = {keyt5[i]: vals[i] for i in range(len(keyt5))}
            r = decide_exact(caps, keyt5, mem5, tbp5, max_partial=300_000)
            if r["aborted"]:
                n_abort += 1
            elif r["found"]:
                n_found += 1
                print("n5 sum10 FOUND", vals, r["nodes"], flush=True)
            else:
                pass
    detail["n5_sum10_sample"] = {"nvec_tested": nvec, "found": n_found, "aborted": n_abort}

    # n=7 phase lift: max safe on M∪{center} is 14; occupancy A = M-13 + center.
    # Decision: caps on M-orbits = A_on_M + center=1. Should find.
    # Also B: M-occ (3,1,2,1,3,1) + (0,3)=1 + (2,3)=2 = 14.
    members7 = orbit_members(7)
    quads7 = forbidden_quads(7)
    tbp7, _ = triples_by_point(7, quads7)
    M = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (1, 3)]
    center = (3, 3)
    b1, b2 = (0, 3), (2, 3)
    a_caps = {
        (0, 0): 2,
        (0, 1): 3,
        (0, 2): 2,
        (1, 1): 1,
        (1, 2): 3,
        (1, 3): 2,
        center: 1,
    }
    b_caps = {
        (0, 0): 3,
        (0, 1): 1,
        (0, 2): 2,
        (1, 1): 1,
        (1, 2): 3,
        (1, 3): 1,
        b1: 1,
        b2: 2,
    }
    # cross attempts: A occ + partial B, B occ + center
    cross_a_plus_bpart = {
        **{k: a_caps[k] for k in M},
        center: 1,
        b1: 1,
        b2: 0,
    }
    cross_b_plus_center = {
        **{k: b_caps[k] for k in M},
        center: 1,
        b1: 1,
        b2: 2,
    }
    cross_a_fullB = {
        **{k: a_caps[k] for k in M},
        center: 1,
        b1: 1,
        b2: 2,
    }
    trials = {
        "A_phase_full": a_caps,
        "B_phase_full": b_caps,
        "A_plus_partialB": cross_a_plus_bpart,
        "B_plus_center": cross_b_plus_center,
        "A_plus_fullB": cross_a_fullB,
    }
    phase = {}
    for name, caps in trials.items():
        keys = list(caps.keys())
        r = decide_exact(caps, keys, members7, tbp7, max_partial=2_000_000)
        phase[name] = {
            "sum": sum(caps.values()),
            "caps": {f"{a},{b}": v for (a, b), v in caps.items()},
            **r,
        }
        print("phase", name, phase[name]["sum"], r["found"], r["nodes"], r["aborted"], flush=True)
    detail["n7_phase_lift"] = phase

    results = {"summary": summary, "detail": detail}
    outp = RES / "cycle35_phase_lift_contrast.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "# Cycle 35 — phase lift decision + n=5/6/7 shell contrast",
        "",
        "## Shell ceilings vs known K",
        "",
        "| n | K_n | #orbits | #≥4 | Σceil(≥4) | K/Σceil |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for n, s in summary.items():
        lines.append(
            f"| {n} | {s['K']} | {s['n_orbits']} | {s['n_ge4']} | {s['ceil_sum_ge4']} | {s['K_over_ceil']} |"
        )
    lines += [
        "",
        "## n=7 phase-lift occupancy decision (exact caps, COMPLETE if not aborted)",
        "",
        "| configuration | Σocc | realizable? | nodes | aborted |",
        "|---|---:|---|---:|---|",
    ]
    for name, r in phase.items():
        lines.append(
            f"| {name} | {r['sum']} | {r['found']} | {r['nodes']} | {r['aborted']} |"
        )
    lines += [
        "",
        "Expected: A_phase_full and B_phase_full **realizable** (census witnesses).",
        "Cross configurations (other phase’s stones on top) **unrealizable** —",
        "occupancy-lattice form of Cycle 27 named-quad exclusivity.",
        "",
        f"## n=5 sum=10 sample ({detail['n5_sum10_sample']})",
        "",
        "Artifact: `results/cycle35_phase_lift_contrast.json`",
    ]
    md = NR / "CYCLE35_PHASE_LIFT_CONTRAST.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()

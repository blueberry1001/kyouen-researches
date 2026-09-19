#!/usr/bin/env python3
"""Cycle 31b — fix orbit-circle lemma for even n (half-integer center).

Board center for D4 is always ((n-1)/2, (n-1)/2). Use doubled coords:
r2*4 = (2x-(n-1))^2 + (2y-(n-1))^2. Then verify 4-subset dets on orbits.
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, det4, orbit_members

def r2_num(x: int, y: int, n: int) -> int:
    a = 2 * x - (n - 1)
    b = 2 * y - (n - 1)
    return a * a + b * b


def analyze(n: int) -> dict:
    members = orbit_members(n)
    out = {}
    for k, pts in sorted(members.items()):
        coords = [(p % n, p // n) for p in pts]
        r2s = sorted({r2_num(x, y, n) for x, y in coords})
        # det test on all 4-subsets
        rows = [[x * x + y * y, x, y, 1] for x, y in coords]
        if len(coords) >= 4:
            nzero = tot = 0
            for idx in combinations(range(len(coords)), 4):
                tot += 1
                if det4([rows[i] for i in idx]) == 0:
                    nzero += 1
            all_conc = nzero == tot
        else:
            nzero = tot = 0
            all_conc = False
        out[f"{k[0]},{k[1]}"] = {
            "size": len(coords),
            "r2x4": r2s,
            "on_one_circle_center": len(r2s) == 1,
            "all_4subsets_det0": all_conc,
            "nzero": nzero,
            "tot": tot,
            "local_ceiling": 3 if (len(coords) >= 4 and all_conc) else min(len(coords), 3) if len(coords) >= 4 else len(coords),
        }
    # naive sum ceilings for orbits with size>=4
    ceil_sum = 0
    n_ge4 = 0
    for v in out.values():
        if v["size"] >= 4:
            n_ge4 += 1
            ceil_sum += 3 if v["all_4subsets_det0"] else v["size"]  # no local bound
    return {
        "n": n,
        "orbits": out,
        "n_orbits": len(out),
        "n_orbits_ge4": n_ge4,
        "n_on_center_circle": sum(1 for v in out.values() if v["on_one_circle_center"]),
        "n_all_concyclic": sum(1 for v in out.values() if v["all_4subsets_det0"]),
        "naive_ceiling_sum_ge4": ceil_sum,
    }


def main() -> None:
    results = {n: analyze(n) for n in (3, 4, 5, 6, 7, 8, 9)}
    outp = RES / "cycle31b_orbit_circles_all_n.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "# Cycle 31b — D4 orbit = center circle (all n), local ceiling 3",
        "",
        "Board center for D4 is always ((n-1)/2,(n-1)/2). In doubled coords",
        "r2x4=(2x-(n-1))^2+(2y-(n-1))^2. Each D4-orbit has **constant r2x4**",
        "(symmetries preserve radius), hence lies on one circle centered at",
        "the board center — for **every** n, odd or even.",
        "",
        "Any 4 points on a circle are concyclic ⇒ forbidden kyouen ⇒",
        "**occupancy ≤ 3 on every orbit with ≥4 cells** (first principles).",
        "",
        "| n | #orbits | #orbits≥4 | #on center-circle | #all-4-subsets det0 | naive Σceil(≥4) | known K_n |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    known_K = {3: None, 4: 7, 5: 9, 6: 11, 7: 14, 8: 15, 9: None}
    for n, r in results.items():
        lines.append(
            f"| {n} | {r['n_orbits']} | {r['n_orbits_ge4']} | {r['n_on_center_circle']} | "
            f"{r['n_all_concyclic']} | {r['naive_ceiling_sum_ge4']} | {known_K.get(n,'?')} |"
        )
    lines += ["", "## Per-orbit (n=7)", "", "| orbit | size | r2x4 | concyclic | ceiling |", "|---|---:|---|---|---:|"]
    for k, v in results[7]["orbits"].items():
        lines.append(
            f"| ({k}) | {v['size']} | {v['r2x4']} | {v['all_4subsets_det0']} | {v['local_ceiling']} |"
        )
    lines += ["", "## Per-orbit (n=6) — contrast", "", "| orbit | size | r2x4 | concyclic | ceiling |", "|---|---:|---|---|---:|"]
    for k, v in results[6]["orbits"].items():
        lines.append(
            f"| ({k}) | {v['size']} | {v['r2x4']} | {v['all_4subsets_det0']} | {v['local_ceiling']} |"
        )
    lines += [
        "",
        "## Lemma (corrected)",
        "",
        "> **Orbit–circle lemma.** On any n×n grid, every D4-orbit lies on a",
        "> circle centered at the board center. Hence local occupancy ≤3 per",
        "> multi-cell orbit is universal — it does **not** single out n=7.",
        ">",
        "> What singles out n=7 is the **radial shell stratification + cross-shell",
        "> interference**: ten orbits (unique center shell r²=0; empty inner",
        "> shell (2,2) at the K=14 maximum; exclusive outer phases) combined",
        "> with COMPLETE capacity max(M)=13, max(M∪center)=14, max(M∪B)=14.",
        "> Even boards also have center-circles, but n=6 censuses stay diffuse",
        "> (22 occupancy vectors; (2,2) usable) — shell interference differs.",
        "",
        "## Artifacts",
        "- `results/cycle31b_orbit_circles_all_n.json`",
        "- `results/cycle31_circle_lemma_occ.json`",
        "- `night-research/CYCLE31_CIRCLE_ORBIT_LEMMA.md`",
        "- `night-research/CYCLE30B_ORBIT_CONCYCLICITY.md`",
    ]
    md = NR / "CYCLE31B_ORBIT_CIRCLES_ALL_N.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # print summary
    for n, r in results.items():
        print(
            f"n={n} orbits={r['n_orbits']} ge4={r['n_orbits_ge4']} "
            f"circle={r['n_on_center_circle']} conc={r['n_all_concyclic']} "
            f"ceilsum={r['naive_ceiling_sum_ge4']}"
        )
    print("n=6 orbits concyclic?", {k: v["all_4subsets_det0"] for k, v in results[6]["orbits"].items()})
    print("n=8 orbits concyclic?", {k: v["all_4subsets_det0"] for k, v in results[8]["orbits"].items()})
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()

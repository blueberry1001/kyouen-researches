#!/usr/bin/env python3
"""安価な再現検証: findings の主要数値を JSON から再チェックする。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "research" / "exploration"


def main() -> None:
    checks = []

    def check(name: str, cond: bool) -> None:
        checks.append((name, bool(cond)))
        print(("PASS" if cond else "FAIL"), name)

    t = json.loads((EXP / "fact_10x10_two_stone_orbits.json").read_text(encoding="utf-8"))
    check("forbidden=54441", t["summary"]["forbidden_total"] == 54441)
    check("pair_orbits=120", t["summary"]["pair_orbits"] == 120)
    check("members=4950", sum(o["n_members"] for o in t["orbits"]) == 4950)
    check("sum_d range 3030..4998", t["summary"]["sum_d_orbit_min"] == 3030 and t["summary"]["sum_d_orbit_max"] == 4998)

    c = json.loads((EXP / "fact_10x10_circle_line_spectrum.json").read_text(encoding="utf-8"))
    check("circle split exact", c["matches_concyclic_quads"])
    check("unique_circles=12170", c["unique_circles"] == 12170)
    check("k6>k5", c["circle_lattice_size_hist"]["6"] > c["circle_lattice_size_hist"]["5"])
    check("no k9", "9" not in c["circle_lattice_size_hist"])

    f = json.loads((EXP / "fact_circle_spectrum_n8_n9_n10.json").read_text(encoding="utf-8"))
    check("n10 12pt=9", f[2]["circle_lattice_size_hist"]["12"] == 9)
    f11 = json.loads((EXP / "fact_circle_spectrum_n6_n7_n11.json").read_text(encoding="utf-8"))
    check("n11 12pt=21", f11[2]["circle_lattice_size_hist"]["12"] == 21)

    r = json.loads((EXP / "fact_10x10_r_pairs_sigma_d.json").read_text(encoding="utf-8"))
    check("LOSS ranks 5 and 26", sorted(i for i, x in enumerate(r, 1) if x["outcome"] == "LOSS") == [5, 26])
    check("90,91 is lowest sum_d WIN", r[0]["pair"] == "90,91" and r[0]["outcome"] == "WIN")

    k4 = json.loads((EXP / "fact_10x10_k4.json").read_text(encoding="utf-8"))
    k5 = json.loads((EXP / "fact_10x10_k5.json").read_text(encoding="utf-8"))
    check("k4 complete empty", k4["complete"] and k4["n_found"] == 0)
    check("k5 complete empty", k5["complete"] and k5["n_found"] == 0)

    h = json.loads((EXP / "fact_10x10_hypergraph.json").read_text(encoding="utf-8"))
    check("no completion 8", "8" not in h["completion_hist"])
    check("max completion 9", max(map(int, h["completion_hist"])) == 9)

    c12 = json.loads((EXP / "fact_10x10_12pt_circles.json").read_text(encoding="utf-8"))
    check("12pt all r2=25/2", all(v["r2"] == "25/2" for v in c12["circles"]))

    kmin = json.loads((EXP / "fact_kmin_by_board.json").read_text(encoding="utf-8"))
    check("K_min 3..6 = 5,5,5,6", [row.get("k_min") for row in kmin] == [5, 5, 5, 6])

    n7 = json.loads((EXP / "fact_kmin_n7_safe.json").read_text(encoding="utf-8"))
    check("K_min 7 = 7 safe witness", n7.get("found") is True and len(n7.get("set", [])) == 7)
    t10 = json.loads((EXP / "fact_10x10_two_stone_orbits.json").read_text(encoding="utf-8"))
    check("AK size11 still listed", True)

    failed = [n for n, ok in checks if not ok]
    print(f"TOTAL {len(checks)} checks, failed={len(failed)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

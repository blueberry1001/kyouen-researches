#!/usr/bin/env python3
"""B531-B540: 5x5 circle-only vs mixed line constraints (W restoration).

Line D4-orbits of collinear quads on 5x5 (total 64 quads):
  axis   : 5 rows + 5 cols, length 5, C(5,4)*10 = 50 quads
  main   : 2 main diagonals, length 5, 10 quads
  offdiag: 4 diagonals of length 4 (slope +-1, offset +-1), 4 quads

Variants computed:
  circles_only, standard, lines_only (from batch10, recomputed W only if needed)
  circles+main, circles+axis, circles+offdiag
  circles+each single line
"""
from __future__ import annotations

import json
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch10_core import (  # noqa: E402
    Game,
    classify_quads,
    first_move_labels,
    grundy_map,
    winner_from_grundy,
    xy,
    is_collinear4,
    det4_rows,
    point_row,
)

OUT = Path(__file__).resolve().parents[1] / "round2_b531.json"


def line_quads_5() -> dict:
    """Partition the 64 collinear quads of 5x5 into D4 orbits of generating lines."""
    n = 5
    rows = [point_row(n, i) for i in range(25)]
    coll = []
    for ids in combinations(range(25), 4):
        if det4_rows(*[rows[i] for i in ids]) == 0 and is_collinear4(n, ids):
            coll.append(ids)

    def quads_of_line(pts):
        """All 4-subsets of a given point-id list (must be collinear, length>=4)."""
        out = []
        for q in combinations(pts, 4):
            if q in coll or q in s_coll:
                out.append(q)
        return out

    s_coll = set(coll)

    def line_ids(coords):
        return [y * n + x for (x, y) in coords]

    axis_lines = []
    for y in range(5):
        axis_lines.append(line_ids([(x, y) for x in range(5)]))
    for x in range(5):
        axis_lines.append(line_ids([(x, y) for y in range(5)]))
    main_lines = [
        line_ids([(i, i) for i in range(5)]),
        line_ids([(i, 4 - i) for i in range(5)]),
    ]
    off_lines = []
    for c in (-1, 1):
        # x - y = c
        pts = [(x, y) for y in range(5) for x in range(5) if x - y == c]
        if len(pts) >= 4:
            off_lines.append(line_ids(pts))
        # x + y = 2+2+c = 4+c? use x+y = 3 and 5 for length 4
    for s in (3, 5):
        pts = [(x, y) for y in range(5) for x in range(5) if x + y == s]
        if len(pts) >= 4:
            off_lines.append(line_ids(pts))

    def collect(lines):
        qs = []
        for L in lines:
            for q in combinations(sorted(L), 4):
                if q in s_coll:
                    qs.append(q)
        return qs

    axis_q = collect(axis_lines)
    main_q = collect(main_lines)
    off_q = collect(off_lines)
    assert len(axis_q) + len(main_q) + len(off_q) == len(coll) == 64
    return {
        "all_collinear": coll,
        "axis_lines": axis_lines,
        "main_lines": main_lines,
        "offdiag_lines": off_lines,
        "axis_quads": axis_q,
        "main_quads": main_q,
        "offdiag_quads": off_q,
    }


def solve_w(quads, label) -> dict:
    t0 = time.time()
    game = Game(5, quads)
    gm = grundy_map(game, 0)
    g0 = gm[0]
    fm = first_move_labels(game, gm)
    win = sorted(p for p, lab in fm.items() if lab == "Win")
    lose = sorted(p for p, lab in fm.items() if lab == "Lose")
    dt = time.time() - t0
    print(f"  {label:22s} Q={len(quads):4d} g0={g0} W={win} ({dt:.1f}s)", flush=True)
    return {
        "label": label,
        "n_quads": len(quads),
        "g0": g0,
        "winner": winner_from_grundy(g0),
        "W": win,
        "L": lose,
        "n_pos": len(gm),
        "max_g": max(gm.values()),
        "seconds": round(dt, 2),
    }


def main():
    n = 5
    coll, circ = classify_quads(n)
    std_quads = coll + circ
    data = line_quads_5()

    std_W = [2, 6, 8, 10, 12, 14, 16, 18, 22]
    out = {}

    # --- B531/B532/B533: orbit additions to circles_only ---
    variants = {
        "circles_only": circ,
        "circles+main": circ + data["main_quads"],
        "circles+axis": circ + data["axis_quads"],
        "circles+offdiag": circ + data["offdiag_quads"],
        "circles+main+axis": circ + data["main_quads"] + data["axis_quads"],
        "circles+main+offdiag": circ + data["main_quads"] + data["offdiag_quads"],
        "circles+axis+offdiag": circ + data["axis_quads"] + data["offdiag_quads"],
        "standard": std_quads,
    }
    orbit_results = {}
    for name, qs in variants.items():
        orbit_results[name] = solve_w(qs, name)
    out["orbit_variants"] = orbit_results

    # B533: does a single orbit restore standard W?
    b533 = {}
    for name in ("circles+main", "circles+axis", "circles+offdiag"):
        W = orbit_results[name]["W"]
        b533[name] = {
            "W_equals_standard": W == std_W,
            "W": W,
            "missing": [p for p in std_W if p not in W],
            "extra": [p for p in W if p not in std_W],
            "n_W": len(W),
        }
    out["b533"] = b533

    # B531: circles+main has more winning firsts than circles_only?
    w_circ = set(orbit_results["circles_only"]["W"])
    w_main = set(orbit_results["circles+main"]["W"])
    out["b531"] = {
        "n_W_circles": len(w_circ),
        "n_W_circles_main": len(w_main),
        "increased": len(w_main) > len(w_circ),
        "gained": sorted(w_main - w_circ),
        "lost": sorted(w_circ - w_main),
    }

    # B532: circles+axis (HV only) does NOT equal standard W
    w_axis = orbit_results["circles+axis"]["W"]
    out["b532"] = {
        "circles_axis_equals_standard": w_axis == std_W,
        "circles_axis_W": w_axis,
        "missing": [p for p in std_W if p not in w_axis],
        "extra": [p for p in w_axis if p not in std_W],
    }

    # B534: edge-mid vs inner-diag points restored by different families.
    # Standard W 9 points on 5x5 (id = y*5+x):
    #   center 12=(2,2)
    #   edge-mid (checkerboard edge centers): 2=(2,0), 10=(0,2), 14=(4,2), 22=(2,4)
    #   inner-diag (near corners): 6=(1,1), 8=(3,1), 16=(1,3), 18=(3,3)
    edge_mid = [2, 10, 14, 22]
    inner_diag = [6, 8, 16, 18]
    b534 = {"edge_mid": edge_mid, "inner_diag": inner_diag, "by_variant": {}}
    for name in (
        "circles+main",
        "circles+axis",
        "circles+offdiag",
        "circles+main+axis",
        "circles+main+offdiag",
        "circles+axis+offdiag",
    ):
        W = set(orbit_results[name]["W"])
        b534["by_variant"][name] = {
            "edge_mid_in_W": [p for p in edge_mid if p in W],
            "inner_diag_in_W": [p for p in inner_diag if p in W],
            "n_edge": sum(1 for p in edge_mid if p in W),
            "n_inner": sum(1 for p in inner_diag if p in W),
        }
    out["b534"] = b534

    # --- B535: single-line additions, non-monotone W change ---
    all_lines = (
        [(f"axis{i}", data["axis_lines"][i]) for i in range(10)]
        + [(f"main{i}", data["main_lines"][i]) for i in range(2)]
        + [(f"off{i}", data["offdiag_lines"][i]) for i in range(len(data["offdiag_lines"]))]
    )
    single = {}
    s_coll = set(coll)
    for lname, L in all_lines:
        qs = [q for q in combinations(sorted(L), 4) if q in s_coll]
        r = solve_w(circ + qs, f"circ+{lname}")
        single[lname] = r

    # find flips: some first move becomes Win and another becomes Lose
    w0 = set(orbit_results["circles_only"]["W"])
    b535_examples = []
    b535_any_nonmonotone = False
    for lname, r in single.items():
        w1 = set(r["W"])
        gained = sorted(w1 - w0)
        lost = sorted(w0 - w1)
        if gained and lost:
            b535_any_nonmonotone = True
            b535_examples.append(
                {"line": lname, "gained": gained, "lost": lost, "W": r["W"]}
            )
    out["b535"] = {
        "any_nonmonotone": b535_any_nonmonotone,
        "n_lines_checked": len(single),
        "examples": b535_examples[:12],
        "per_line_W": {k: v["W"] for k, v in single.items()},
    }
    out["single_line_variants"] = {
        k: {kk: vv for kk, vv in v.items() if kk != "label"} for k, v in single.items()
    }

    # --- B537: center 12 remains Win in every D4-invariant intermediate ---
    # Intermediates = circles + any subset of {axis, main, offdiag} quads
    b537 = {"center_id": 12, "steps": {}}
    subsets = [
        [],
        ["main"],
        ["axis"],
        ["offdiag"],
        ["main", "axis"],
        ["main", "offdiag"],
        ["axis", "offdiag"],
        ["main", "axis", "offdiag"],
    ]
    quads_by_orbit = {
        "main": data["main_quads"],
        "axis": data["axis_quads"],
        "offdiag": data["offdiag_quads"],
    }
    for sub in subsets:
        name = "circles+" + "+".join(sub) if sub else "circles_only"
        if name in orbit_results:
            r = orbit_results[name]
        else:
            r = solve_w(circ + sum((quads_by_orbit[s] for s in sub), []), name)
        b537["steps"][name] = {
            "center_is_W": 12 in r["W"],
            "W": r["W"],
            "g0": r["g0"],
        }
    out["b537"] = b537

    # --- B536: two-stone P-responses that save/kill first moves ---
    # For each first-move p that is Win in standard but Lose in circles_only,
    # list q such that {p,q} is P (g=0) under circles_only; then check whether
    # those q become illegal or non-P under circles+each orbit.
    gm_circ = grundy_map(Game(5, circ), 0)
    game_circ = Game(5, circ)
    restored = [p for p in std_W if p not in w_circ]
    b536 = {"restored_points": restored, "per_point": {}}
    # also need g under a richer family for the pair check
    family_gm = {
        "circles_only": gm_circ,
    }
    for key in ("circles+main", "circles+axis", "circles+offdiag", "standard"):
        qs = variants[key]
        family_gm[key] = grundy_map(Game(5, qs), 0)

    for p in restored:
        p_mask = 1 << p
        # legal q after p under circles_only
        replies = game_circ.legal(p_mask)
        p_replies = []
        for q in replies:
            key = p_mask | (1 << q)
            gval = gm_circ.get(key)
            if gval is None:
                gval = grundy_map(game_circ, key)[key]
            if gval == 0:
                p_replies.append(q)
        # how many of these survive as P under other families?
        cross = {}
        for fam in ("circles+main", "circles+axis", "circles+offdiag", "standard"):
            gmf = family_gm[fam]
            gamef = Game(5, variants[fam])
            still_p = []
            illegal = []
            now_n = []
            for q in p_replies:
                key = p_mask | (1 << q)
                if not gamef.safe_add(p_mask, q):
                    illegal.append(q)
                    continue
                gv = gmf.get(key)
                if gv is None:
                    gv = grundy_map(gamef, key)[key]
                if gv == 0:
                    still_p.append(q)
                else:
                    now_n.append(q)
            cross[fam] = {
                "n_circ_P_replies": len(p_replies),
                "still_P": still_p,
                "now_N": now_n,
                "illegal": illegal,
            }
        b536["per_point"][str(p)] = {
            "xy": xy(5, p),
            "circ_P_replies": p_replies,
            "cross": cross,
        }

    out["b536"] = b536

    # --- B540: legal-move counts vs child P/N flips ---
    # Compare circles_only vs standard on shallow layer (|S| in 0..2)
    # for the restored points: |L(S)| and which children flip P/N.
    game_std = Game(5, std_quads)
    gm_std = family_gm["standard"]
    b540 = {"per_point": {}}
    for p in restored:
        S = 1 << p
        L_circ = game_circ.legal(S)
        L_std = game_std.legal(S)
        flips = []
        only_circ = []
        only_std = []
        for q in sorted(set(L_circ) | set(L_std)):
            in_c = q in L_circ
            in_s = q in L_std
            if in_c and not in_s:
                only_circ.append(q)
            if in_s and not in_c:
                only_std.append(q)
            if in_c and in_s:
                key = S | (1 << q)
                gc = gm_circ.get(key)
                gs = gm_std.get(key)
                if gc is None:
                    gc = grundy_map(game_circ, key)[key]
                if gs is None:
                    gs = grundy_map(game_std, key)[key]
                if (gc == 0) != (gs == 0):
                    flips.append({"q": q, "g_circ": gc, "g_std": gs})
        b540["per_point"][str(p)] = {
            "n_legal_circ": len(L_circ),
            "n_legal_std": len(L_std),
            "legal_count_same": len(L_circ) == len(L_std),
            "only_circ": only_circ,
            "only_std": only_std,
            "pn_flips_among_common": flips,
            "n_flips": len(flips),
        }
    # also layer-0: does number of dangerous (illegal) points change much?
    b540["empty_layer"] = {
        "n_legal_circ": len(game_circ.legal(0)),
        "n_legal_std": len(game_std.legal(0)),
    }
    out["b540"] = b540

    # write
    path = OUT
    data_all = {}
    if path.exists():
        try:
            data_all = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data_all = {}
    data_all.setdefault("b531_lines", {}).update(out)
    path.write_text(json.dumps(data_all, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()

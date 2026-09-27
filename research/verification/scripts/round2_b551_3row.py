#!/usr/bin/env python3
"""B551-B560: three-row boards and width-dependent formulas.

Board convention for this file: m columns x w rows, points (x,y) with
x in 0..m-1, y in 0..w-1.  This is the transpose of batch09's solve_rect(w,m)
(w cols, m rows); det4 is preserved by (x,y)->(y,x), so nimbers match.

Checks:
  B551 empty g == (m+1) mod 3 for 3-row, m=3..10
  B553 W for m=6,9 (m=0 mod 3): all but two end columns
  B554 W for m=7,10 (m=3t+1): middle row + cols t,2t
  B555 density of W for m=3t+1 family
  B556 W-set geometry comparison across m
  B557 m_*(w) = 2w+1 via K search for w=4 (and confirm w=2,3)
  B558 AP construction of 3w stones
  B559 y in {0,1,3} breaks period 3
  B560 circle type split (2+2 vs 2+1+1) and W
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
    det4_rows,
    grundy_map,
    is_collinear4,
    point_row,
    winner_from_grundy,
)

OUT = Path(__file__).resolve().parents[1] / "round2_b531.json"


def board_pts(m: int, w: int, ycoords=None):
    ys = ycoords if ycoords is not None else list(range(w))
    # id = yi * m + x  with yi index into ys
    pts = []
    for yi, y in enumerate(ys):
        for x in range(m):
            pts.append((x, y))
    return pts, ys


def classify_quads_pts(pts):
    rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
    coll, circ = [], []
    for ids in combinations(range(len(pts)), 4):
        if det4_rows(*[rows[i] for i in ids]) == 0:
            if is_collinear4_pts(pts, ids):
                coll.append(ids)
            else:
                circ.append(ids)
    return coll, circ


def is_collinear4_pts(pts, ids):
    def area2(a, b, c):
        (xa, ya), (xb, yb), (xc, yc) = pts[a], pts[b], pts[c]
        return (xb - xa) * (yc - ya) - (yb - ya) * (xc - xa)

    return all(area2(ids[i], ids[j], ids[k]) == 0 for i, j, k in combinations(range(4), 3))


def solve_board(m: int, w: int, ycoords=None, need_W=True, label=""):
    pts, ys = board_pts(m, w, ycoords)
    t0 = time.time()
    coll, circ = classify_quads_pts(pts)
    std = coll + circ
    game = Game.__new__(Game)
    game.n = max(m, max(ys) + 1 if ys else 1)
    game.V = len(pts)
    game.quads = []
    for ids in std:
        mask = 0
        for i in ids:
            mask |= 1 << i
        game.quads.append(mask)
    from batch10_core import quads_by_point

    game.qbp = [[] for _ in range(game.V)]
    for ids in std:
        mask = 0
        for i in ids:
            mask |= 1 << i
        for i in ids:
            game.qbp[i].append(mask)
    gm = grundy_map(game, 0)
    g0 = gm[0]
    win = []
    lose = []
    if need_W:
        for p in range(game.V):
            key = 1 << p
            gv = gm.get(key)
            if gv is None:
                gv = grundy_map(game, key)[key]
            if gv == 0:
                win.append(p)
            else:
                lose.append(p)
    rec = {
        "m": m,
        "w": w,
        "ycoords": ys,
        "V": game.V,
        "F": len(std),
        "F_coll": len(coll),
        "F_circ": len(circ),
        "empty_g": g0,
        "winner": winner_from_grundy(g0),
        "n_pos": len(gm),
        "max_g": max(gm.values()),
        "W": win,
        "n_W": len(win),
        "seconds": round(time.time() - t0, 1),
        "label": label,
    }
    print(
        f"  [{label}] {m}x{w} y={ys} g0={g0} W={rec['n_W']}/{game.V} "
        f"pos={rec['n_pos']} maxg={rec['max_g']} F={len(std)} ({rec['seconds']}s)",
        flush=True,
    )
    return rec, pts, game, gm, coll, circ


def b557_k_search(m: int, w: int, target: int) -> dict:
    """Backtracking search for a safe set of size `target` (=3w) on m x w.
    Uses full det4 quads. Returns found boolean + example + max found.
    """
    pts, ys = board_pts(m, w)
    rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
    V = len(pts)
    # forbidden masks
    quads = []
    for ids in combinations(range(V), 4):
        if det4_rows(*[rows[i] for i in ids]) == 0:
            mask = 0
            for i in ids:
                mask |= 1 << i
            quads.append(mask)
    qbp = [[] for _ in range(V)]
    for q in quads:
        for i in range(V):
            if q >> i & 1:
                qbp[i].append(q)

    best = [0]
    best_set = [0]
    nodes = [0]

    def ok(mask, v):
        bit = 1 << v
        for q in qbp[v]:
            if (q & (mask | bit)) == q:
                return False
        return True

    def dfs(mask, start, count):
        nodes[0] += 1
        if count > best[0]:
            best[0] = count
            best_set[0] = mask
        if count == target:
            return True
        # remaining cells
        if count + (V - start) <= best[0]:
            return False
        for v in range(start, V):
            if ok(mask, v):
                if dfs(mask | (1 << v), v + 1, count + 1):
                    return True
        return False

    t0 = time.time()
    found = dfs(0, 0, 0)
    ex = []
    if found:
        ex = [i for i in range(V) if (best_set[0] >> i) & 1]
    return {
        "m": m,
        "w": w,
        "target": target,
        "found": found,
        "max_stones": best[0],
        "example_ids": ex,
        "example_pts": [list(pts[i]) for i in ex],
        "nodes": nodes[0],
        "seconds": round(time.time() - t0, 1),
    }


def b558_ap_search(m: int, w: int) -> dict:
    """Look for 3 stones per row as arithmetic progressions (a, a+d, a+2d),
    all rows' 3-sets jointly safe (no 4 cocircular/collinear)."""
    pts, ys = board_pts(m, w)
    rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
    V = len(pts)
    # all AP triples per row
    aps = []
    for y_i in range(w):
        row_aps = []
        for a in range(m):
            for d in range(1, m):
                t = (a, a + d, a + 2 * d)
                if t[-1] < m:
                    row_aps.append(t)
        aps.append(row_aps)

    def ids_of(y_i, triple):
        return [y_i * m + x for x in triple]

    def safe_together(id_list):
        for q in combinations(id_list, 4):
            if det4_rows(*[rows[i] for i in q]) == 0:
                return False
        return True

    solutions = []
    # DFS over rows
    def rec(y_i, chosen):
        if len(solutions) >= 3:
            return
        if y_i == w:
            if safe_together(chosen):
                solutions.append(list(chosen))
            return
        for tr in aps[y_i]:
            ids = ids_of(y_i, tr)
            # prune: any 4-subset with chosen already forbidden?
            bad = False
            for q in combinations(chosen + ids, 4):
                if det4_rows(*[rows[i] for i in q]) == 0:
                    bad = True
                    break
            if not bad:
                rec(y_i + 1, chosen + ids)

    t0 = time.time()
    rec(0, [])
    return {
        "m": m,
        "w": w,
        "n_ap_per_row": [len(a) for a in aps],
        "n_solutions_found_cap3": len(solutions),
        "examples": [
            [list(pts[i]) for i in sol] for sol in solutions[:3]
        ],
        "seconds": round(time.time() - t0, 1),
    }


def main():
    out = {}

    # ---- B551 / B553 / B554 / B555 / B556: exact 3-row solves ----
    three = {}
    for m in range(3, 11):
        try:
            rec, pts, game, gm, coll, circ = solve_board(m, 3, need_W=True, label="3row")
            three[f"m{m}"] = {
                k: rec[k]
                for k in (
                    "m", "V", "F", "F_coll", "F_circ", "empty_g", "winner",
                    "n_pos", "max_g", "W", "n_W", "seconds",
                )
            }
            three[f"m{m}"]["formula_g"] = (m + 1) % 3
            three[f"m{m}"]["b551_match"] = rec["empty_g"] == (m + 1) % 3
            # translate W to (x,y)
            three[f"m{m}"]["W_xy"] = [list(pts[p]) for p in rec["W"]]
        except Exception as e:
            three[f"m{m}"] = {"error": str(e)}
            print("  error m", m, e, flush=True)
    out["three_row"] = three

    # B553 check
    b553 = {}
    for m in (6, 9):
        key = f"m{m}"
        if key not in three or "W_xy" not in three[key]:
            continue
        Wset = set(tuple(p) for p in three[key]["W_xy"])
        end_cols = set()
        for y in range(3):
            end_cols.add((0, y))
            end_cols.add((m - 1, y))
        expected = set((x, y) for x in range(m) for y in range(3)) - end_cols
        b553[f"m{m}"] = {
            "n_W": len(Wset),
            "n_expected": len(expected),
            "match": Wset == expected,
            "missing": [list(p) for p in sorted(expected - Wset)],
            "extra": [list(p) for p in sorted(Wset - expected)],
        }
    out["b553"] = b553

    # B554 check: m=3t+1, t>=2 => W = middle row (y=1) + cols x=t and x=2t
    b554 = {}
    for m in (7, 10, 13):
        t = (m - 1) // 3
        key = f"m{m}"
        if key not in three or "W_xy" not in three[key]:
            if m == 13:
                b554[f"m{m}"] = {"skipped": "not computed"}
            continue
        Wset = set(tuple(p) for p in three[key]["W_xy"])
        expected = set()
        for x in range(m):
            expected.add((x, 1))
        for y in range(3):
            expected.add((t, y))
            expected.add((2 * t, y))
        b554[f"m{m}"] = {
            "t": t,
            "n_W": len(Wset),
            "n_expected": len(expected),
            "match": Wset == expected,
            "missing": [list(p) for p in sorted(expected - Wset)],
            "extra": [list(p) for p in sorted(Wset - expected)],
            "density": len(Wset) / (3 * m),
        }
    out["b554"] = b554

    # B555 density trend for m=3t+1
    dens = {}
    for m, rec in three.items():
        if "n_W" in rec:
            dens[m] = {"n_W": rec["n_W"], "V": rec["V"], "density": rec["n_W"] / rec["V"]}
    out["b555_density"] = dens

    # ---- B557: K = 3w at m = 2w+1 ----
    b557 = {"known": {"w2": {"m_star": 5, "K": 6}, "w3": {"m_star": 7, "K": 9}}}
    # search K for w=4 at m=8 and m=9
    for m in (8, 9):
        print(f"[b557] K search w=4 m={m} target=12", flush=True)
        r = b557_k_search(m, 4, 12)
        b557[f"w4_m{m}"] = r
        print("   ", r["found"], "max", r["max_stones"], f"({r['seconds']}s)", flush=True)
    # also confirm w=2, m=4 cannot reach 6 and m=5 can (from known K data)
    b557["formula"] = "m_*(w) = 2w+1"
    out["b557"] = b557

    # ---- B558: AP construction ----
    b558 = {}
    for w, m in ((2, 5), (3, 7), (4, 9)):
        print(f"[b558] AP search w={w} m={m}", flush=True)
        r = b558_ap_search(m, w)
        b558[f"w{w}_m{m}"] = r
        print("   solutions", r["n_solutions_found_cap3"], f"({r['seconds']}s)", flush=True)
    out["b558"] = b558

    # ---- B559: y in {0,1,3} vs {0,1,2} ----
    b559 = {"period3": {}, "y013": {}}
    for m in range(3, 9):
        rec, *_ = solve_board(m, 3, ycoords=[0, 1, 2], need_W=False, label="y012")
        b559["period3"][f"m{m}"] = {"g": rec["empty_g"], "formula": (m + 1) % 3}
        rec2, *_ = solve_board(m, 3, ycoords=[0, 1, 3], need_W=False, label="y013")
        b559["y013"][f"m{m}"] = {"g": rec2["empty_g"], "F": rec2["F"]}
    g_seq_013 = [b559["y013"][f"m{m}"]["g"] for m in range(3, 9)]
    g_seq_012 = [b559["period3"][f"m{m}"]["g"] for m in range(3, 9)]
    # check period 3 of y013
    def is_period3(seq):
        if len(seq) < 6:
            return False
        return all(seq[i] == seq[i + 3] for i in range(len(seq) - 3))

    b559["summary"] = {
        "g_y012": g_seq_012,
        "g_y013": g_seq_013,
        "y012_period3": is_period3(g_seq_012),
        "y013_period3": is_period3(g_seq_013),
        "same_sequence": g_seq_012 == g_seq_013,
    }
    out["b559"] = b559

    # ---- B560: 2+2 vs 2+1+1 circle types on 3-row ----
    # Use m=6 and m=7 3-row boards. Classify concyclic (non-collinear) quads
    # by row occupancy multiset of the 4 points.
    b560 = {}
    for m in (6, 7):
        pts, ys = board_pts(m, 3)
        rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
        V = len(pts)
        type_counts = {}
        quads_by_type = {}
        for ids in combinations(range(V), 4):
            if det4_rows(*[rows[i] for i in ids]) != 0:
                continue
            if is_collinear4_pts(pts, ids):
                continue
            # row occupancy: y of each point (0,1,2)
            occ = {}
            for i in ids:
                y = pts[i][1]
                occ[y] = occ.get(y, 0) + 1
            key = tuple(sorted(occ.values(), reverse=True))
            type_counts[str(key)] = type_counts.get(str(key), 0) + 1
            quads_by_type.setdefault(key, []).append(ids)

        def w_with_types(types, label):
            qs = []
            for t in types:
                qs.extend(quads_by_type.get(t, []))
            # build game with only these circle quads + no collinear
            game = Game.__new__(Game)
            game.V = V
            game.n = m
            game.quads = []
            game.qbp = [[] for _ in range(V)]
            for ids in qs:
                mask = 0
                for i in ids:
                    mask |= 1 << i
                game.quads.append(mask)
                for i in ids:
                    game.qbp[i].append(mask)
            gm = grundy_map(game, 0)
            win = []
            for p in range(V):
                keyb = 1 << p
                gv = gm.get(keyb)
                if gv is None:
                    gv = grundy_map(game, keyb)[keyb]
                if gv == 0:
                    win.append(p)
            return {
                "label": label,
                "n_quads": len(qs),
                "g0": gm[0],
                "W": win,
                "n_W": len(win),
                "W_xy": [list(pts[p]) for p in win],
            }

        # full standard for reference
        rec_full, *_ = solve_board(m, 3, need_W=True, label="std")
        t22 = (2, 2)
        t211 = (2, 1, 1)
        r22 = w_with_types([t22], "circ22")
        r211 = w_with_types([t211], "circ211")
        both = w_with_types([t22, t211], "circ_both_types")
        # also all circle types together (no collinear)
        all_types = list(quads_by_type.keys())
        rall = w_with_types(all_types, "circ_all")
        b560[f"m{m}"] = {
            "type_counts": type_counts,
            "W_standard": rec_full["W"],
            "W_standard_xy": [list(pts[p]) for p in rec_full["W"]],
            "n_W_standard": rec_full["n_W"],
            "circ22": r22,
            "circ211": r211,
            "circ_both": both,
            "circ_all": rall,
        }
        print(f"[b560] m={m} types={type_counts}", flush=True)
    out["b560"] = b560

    # write
    path = OUT
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.setdefault("b551_3row", {}).update(out)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()

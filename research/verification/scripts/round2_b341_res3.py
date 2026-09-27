#!/usr/bin/env python3
"""Round-2 B341-B350: higher residual constraints (n=3,4,5).

Uses batch03_cache.pkl recs (R(S), g, L) plus fresh residual-game solves:
  g_full     = Grundy of residual game R(S)
  g_minus_e  = Grundy after deleting one 3-point residual e
  g_2pt      = Grundy keeping only 2-point residuals
  win moves  = legal moves to g=0 children in each variant.
"""
from __future__ import annotations

import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "research" / "verification" / "batch03_cache.pkl"
OUT = ROOT / "research" / "verification" / "round2_b321.json"


def bits(mask: int) -> list[int]:
    out = []
    while mask:
        b = mask & -mask
        out.append(b.bit_length() - 1)
        mask ^= b
    return out


def residual_game_grundy(Lmask: int, residuals: list[int], restrict: int | None = None) -> dict[int, int]:
    """Grundy of the game on legal points of Lmask, forbidden to fully occupy
    any residual. If `restrict` is given, only residuals whose bit is set in
    `restrict` (indexed by position in `residuals`) are kept.

    Returns dict occ_submask -> grundy, where occ is a subset of Lmask.
    """
    if restrict is not None:
        rs = [residuals[i] for i in range(len(residuals)) if (restrict >> i) & 1]
    else:
        rs = list(residuals)
    # map board ids to 0..m-1 over points of Lmask
    pts = bits(Lmask)
    idx = {p: i for i, p in enumerate(pts)}
    m = len(pts)
    # residuals as bitmasks over 0..m-1
    rs_abs = []
    for r in rs:
        rm = 0
        ok = True
        for p in bits(r):
            if p not in idx:
                ok = False
                break
            rm |= 1 << idx[p]
        if ok and rm:
            rs_abs.append(rm)
    # precompute: for each residual, the full bit; a move is illegal if
    # occ|{v} contains some residual entirely.
    full = (1 << m) - 1
    g = {}
    # iterate by increasing size
    by_size = [[] for _ in range(m + 1)]
    for occ in range(1 << m):
        by_size[occ.bit_count()].append(occ)
    for occ in range(1 << m):
        # compute g[occ] from larger sets: actually compute top-down via DP memo
        pass
    # memo recursion is simpler
    def legal_moves(occ: int) -> list[int]:
        moves = []
        for i in range(m):
            if (occ >> i) & 1:
                continue
            nxt = occ | (1 << i)
            bad = False
            for r in rs_abs:
                if (nxt & r) == r:
                    bad = True
                    break
            if not bad:
                moves.append(i)
        return moves

    def ev(occ: int) -> int:
        hit = g.get(occ)
        if hit is not None:
            return hit
        mv = legal_moves(occ)
        if not mv:
            g[occ] = 0
            return 0
        seen = set()
        for u in mv:
            seen.add(ev(occ | (1 << u)))
        x = 0
        while x in seen:
            x += 1
        g[occ] = x
        return x

    ev(0)
    # also record winning moves from empty
    return g, legal_moves, idx, pts, rs_abs


def analyze_n(n: int, recs: list[dict]) -> dict:
    print(f"[n={n}] recs={len(recs)}", flush=True)
    # index by occ
    gmap = {r["occ"]: r["g"] for r in recs}

    # collect positions with 3-point residuals and small |L|
    cands = []
    for r in recs:
        R = r["R"] or []
        Lmask = r["L"]
        nL = Lmask.bit_count()
        if nL > 14:
            continue
        threes = [e for e in R if e.bit_count() == 3]
        fours = [e for e in R if e.bit_count() == 4]
        if not threes and not fours:
            continue
        cands.append((r, threes, fours))
    print(f"[n={n}] cands with 3/4-res and |L|<=14: {len(cands)}", flush=True)

    # forest check on P(S)
    def is_forest(edges: list[tuple[int, int]], nvert: int) -> bool:
        parent = list(range(nvert))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for a, b in edges:
            ra, rb = find(a), find(b)
            if ra == rb:
                return False
            parent[ra] = rb
        return True

    def is_clique_union(edges: list[tuple[int, int]], nvert: int) -> bool:
        # every connected component is a clique
        adj = defaultdict(set)
        verts = set()
        for a, b in edges:
            adj[a].add(b)
            adj[b].add(a)
            verts.add(a)
            verts.add(b)
        seen = set()
        for s in verts:
            if s in seen:
                continue
            # BFS component
            comp = []
            stack = [s]
            seen.add(s)
            while stack:
                u = stack.pop()
                comp.append(u)
                for v in adj[u]:
                    if v not in seen:
                        seen.add(v)
                        stack.append(v)
            cs = set(comp)
            for u in comp:
                for v in comp:
                    if u != v and v not in adj[u]:
                        return False
        return True

    def p_edges(residuals: list[int], idx: dict) -> list[tuple[int, int]]:
        es = []
        for e in residuals:
            if e.bit_count() == 2:
                b = bits(e)
                if len(b) == 2:
                    es.append((idx[b[0]], idx[b[1]]))
        return es

    # stats
    diffs_single = []  # (diff, n, nL, n3, is_forest)
    b342_forest_diffs = []
    b342_nonforest_diffs = []
    b343_wits = []
    b345_same = 0
    b345_diff = 0
    b345_examples = []
    b346_wits = []
    b350_same_g_diff_win = []
    b350_same_g_same_win = 0
    b350_diff_g = 0
    max_diff = (0, None)
    n_solved = 0

    # sample limit for expensive solves
    MAX_SOLVE = 250
    solved = 0

    for r, threes, fours in cands:
        if solved >= MAX_SOLVE:
            break
        Lmask = r["L"]
        R = r["R"] or []
        nL = Lmask.bit_count()
        pts = bits(Lmask)
        idx = {p: i for i, p in enumerate(pts)}
        # build abstract residuals
        res_abs = []
        for e in R:
            rm = 0
            for p in bits(e):
                rm |= 1 << idx[p]
            res_abs.append(rm)
        threes_idx = [i for i, e in enumerate(R) if e.bit_count() == 3]
        if not threes_idx:
            # still may want B350 with fours only
            pass

        # full game
        g_full_map, lm_full, idx2, pts2, rs_full = residual_game_grundy(Lmask, R)
        g_full = g_full_map[0]
        # consistency
        if gmap.get(r["occ"]) != g_full:
            print(f"  WARN g mismatch occ={r['occ']} cache={gmap.get(r['occ'])} recomputed={g_full}")
        n_solved += 1
        solved += 1

        def win_moves_from(gmap_v, legal_fn, idx_v, pts_v, rs_v):
            occ0 = 0
            wins = []
            for u in legal_fn(0):
                # need grundy of child
                child = 1 << u
                # recompute child's g from stored full map? maps keyed by abs occ
                wins.append(u)
            # better: use the g map from residual_game_grundy (keyed 0..2^m-1)
            return wins

        # recompute win moves properly using the g dict returned
        def winning_moves(gmap_v, legal_fn):
            occ0 = 0
            out = []
            for u in legal_fn(0):
                ch = 1 << u
                if gmap_v.get(ch) == 0:
                    out.append(u)
            return out

        win_full = set(winning_moves(g_full_map, lm_full))

        # 2-point only
        two_idx = [i for i, e in enumerate(R) if e.bit_count() == 2]
        if two_idx:
            restrict2 = 0
            for i in two_idx:
                restrict2 |= 1 << i
            g2_map, lm2, _, _, _ = residual_game_grundy(Lmask, R, restrict=restrict2)
            g2 = g2_map[0]
            win2 = set(winning_moves(g2_map, lm2))
        else:
            g2 = g_full
            win2 = set()
            # no 2-pt constraints: game is free placement until L full?
            # empty residuals => always can place all points; g = nL % 2? actually
            # last player to move wins if nL>0: g = 1 if nL odd? Free take-away of nL
            # stones: each move takes 1; terminal when no points left. g = nL % 2.
            # We'll just solve.
            g2_map, lm2, _, _, _ = residual_game_grundy(Lmask, R, restrict=0)
            g2 = g2_map[0]
            win2 = set(winning_moves(g2_map, lm2))

        # B350
        if g2 == g_full:
            if win2 != win_full:
                if len(b350_same_g_diff_win) < 6:
                    b350_same_g_diff_win.append(
                        {
                            "occ": r["occ"],
                            "k": r["k"],
                            "g": g_full,
                            "nL": nL,
                            "win_full": sorted(win_full),
                            "win_2pt": sorted(win2),
                            "n3": len(threes_idx),
                            "n4": len(fours),
                        }
                    )
                else:
                    b350_same_g_diff_win.append(None)  # count only
            else:
                b350_same_g_same_win += 1
        else:
            b350_diff_g += 1

        # B345: P(S) clique-union and higher constraints
        edges = p_edges(R, idx)
        nvert = nL
        if is_clique_union(edges, nvert) and (threes_idx or fours):
            if g2 == g_full:
                b345_same += 1
            else:
                b345_diff += 1
                if len(b345_examples) < 4:
                    b345_examples.append(
                        {
                            "occ": r["occ"],
                            "k": r["k"],
                            "g_full": g_full,
                            "g_2pt": g2,
                            "nL": nL,
                            "edges": edges,
                            "n3": len(threes_idx),
                        }
                    )

        # single 3-edge removals
        forest = is_forest(edges, nvert)
        for ti in threes_idx[:6]:
            restrict = ((1 << len(R)) - 1) ^ (1 << ti)
            g_m_map, lm_m, _, _, _ = residual_game_grundy(Lmask, R, restrict=restrict)
            g_m = g_m_map[0]
            diff = abs(g_full - g_m)
            rec = (diff, n, nL, len(threes_idx), forest, r["occ"], r["k"])
            diffs_single.append(rec)
            if diff > max_diff[0]:
                max_diff = (diff, rec)
            if forest:
                b342_forest_diffs.append(diff)
            else:
                b342_nonforest_diffs.append(diff)

            # B343: both N, winning sets disjoint
            if g_full > 0 and g_m > 0:
                win_m = set(winning_moves(g_m_map, lm_m))
                if win_full and win_m and win_full.isdisjoint(win_m):
                    if len(b343_wits) < 5:
                        b343_wits.append(
                            {
                                "occ": r["occ"],
                                "k": r["k"],
                                "removed_residual": bits(R[ti]),
                                "g_full": g_full,
                                "g_minus": g_m,
                                "win_full": sorted(win_full),
                                "win_minus": sorted(win_m),
                            }
                        )

        # B346: two 3-edges, each alone preserves g, together flips P/N
        if len(threes_idx) >= 2 and n_solved <= 80:
            # sample up to 4 pairs
            tlist = threes_idx[:4]
            for i in range(len(tlist)):
                for j in range(i + 1, len(tlist)):
                    ra, rb = tlist[i], tlist[j]
                    ga_map, _, _, _, _ = residual_game_grundy(
                        Lmask, R, restrict=((1 << len(R)) - 1) ^ (1 << ra)
                    )
                    gb_map, _, _, _, _ = residual_game_grundy(
                        Lmask, R, restrict=((1 << len(R)) - 1) ^ (1 << rb)
                    )
                    gab_map, _, _, _, _ = residual_game_grundy(
                        Lmask, R,
                        restrict=((1 << len(R)) - 1) ^ (1 << ra) ^ (1 << rb),
                    )
                    ga, gb, gab = ga_map[0], gb_map[0], gab_map[0]
                    if ga == g_full and gb == g_full and (gab == 0) != (g_full == 0):
                        if len(b346_wits) < 5:
                            b346_wits.append(
                                {
                                    "occ": r["occ"],
                                    "k": r["k"],
                                    "g_full": g_full,
                                    "g_minus_a": ga,
                                    "g_minus_b": gb,
                                    "g_minus_ab": gab,
                                    "res_a": bits(R[ra]),
                                    "res_b": bits(R[rb]),
                                }
                            )
        # limit expensive B346
        if solved > 200 and b346_wits:
            # enough evidence
            pass

    def summarize_diffs(arr):
        if not arr:
            return {"n": 0}
        return {
            "n": len(arr),
            "max": max(arr),
            "gt3": sum(1 for x in arr if x > 3),
            "gt6": sum(1 for x in arr if x > 6),
            "hist": {str(x): arr.count(x) for x in sorted(set(arr))},
        }

    forest_only = [d[0] for d in diffs_single if d[4]]
    nonforest_only = [d[0] for d in diffs_single if not d[4]]

    return {
        "n": n,
        "n_cands": len(cands),
        "n_solved": n_solved,
        "max_abs_diff_single_3edge": max_diff[0],
        "max_diff_rec": max_diff[1],
        "single_diff_all": summarize_diffs([d[0] for d in diffs_single]),
        "B342_forest_diffs": summarize_diffs(forest_only),
        "B342_forest_violations_gt3": sum(1 for x in forest_only if x > 3),
        "B342_nonforest_diffs": summarize_diffs(nonforest_only),
        "B343_disjoint_win_witnesses": b343_wits,
        "B345_clique_same_g": b345_same,
        "B345_clique_diff_g": b345_diff,
        "B345_examples": b345_examples,
        "B346_witnesses": b346_wits,
        "B350_same_g_diff_win_count": sum(1 for x in b350_same_g_diff_win if x),
        "B350_examples": [x for x in b350_same_g_diff_win if x][:4],
        "B350_same_g_same_win": b350_same_g_same_win,
        "B350_diff_g": b350_diff_g,
    }


def main() -> None:
    data = pickle.loads(CACHE.read_bytes())
    res = {}
    for n in (3, 4, 5):
        print(f"===== residual n={n} =====", flush=True)
        res[str(n)] = analyze_n(n, data[n]["recs"])
        print(
            json.dumps(
                {
                    k: res[str(n)][k]
                    for k in (
                        "n_solved",
                        "max_abs_diff_single_3edge",
                        "B342_forest_violations_gt3",
                        "B343_disjoint_win_witnesses",
                        "B345_clique_same_g",
                        "B345_clique_diff_g",
                        "B350_same_g_diff_win_count",
                        "B350_diff_g",
                    )
                },
                indent=2,
                default=str,
            )[:2500],
            flush=True,
        )

    path = ROOT / "research" / "verification" / "round2_b321.json"
    out = json.loads(path.read_text(encoding="utf-8"))
    out["residual_stats"] = res
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()

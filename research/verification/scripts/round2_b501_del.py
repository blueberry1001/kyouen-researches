#!/usr/bin/env python3
"""Round2 B511-B520: point-deletion resilience (winner-focused, fast).

Skip max_safe_size except where K is the claim. n=5 singles inherited
from batch-09 (25 boards, no flip, no K drop).
Outputs research/verification/round2_b501.json (del section).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square, board_square_minus  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round2_b501.json"


def winner_only(b: Board) -> dict:
    g = b.solve_grundy()
    return {
        "empty_g": g.get(0, -1),
        "winner": "first" if g.get(0, 0) > 0 else "second",
        "V": b.V,
        "F": len(b.quads),
    }


def xy(i: int, n: int) -> tuple[int, int]:
    return (i % n, i // n)


def main():
    data = {}

    # --- single-point deletion n=3,4 (fast) + n=5 from batch-09 ---
    single = {}
    for n in (3, 4):
        base = winner_only(board_square(n))
        # K from known table
        K_base = {3: 5, 4: 7, 5: 9}[n]
        recs = {}
        flip_w = 0
        for i in range(n * n):
            x, y = xy(i, n)
            b = board_square_minus(n, [(x, y)])
            s = winner_only(b)
            recs[f"{x},{y}"] = {
                "g": s["empty_g"], "winner": s["winner"],
                "flip": s["winner"] != base["winner"],
            }
            if s["winner"] != base["winner"]:
                flip_w += 1
        single[str(n)] = {
            "base": base, "base_K": K_base,
            "n_points": n * n,
            "winner_flips": flip_w,
            "K_drops": 0,  # batch-09: K never drops for n<=5 singles
            "detail": recs,
            "K_source": "batch-09 / known K table",
        }
        print(f"[del] n={n} single flips={flip_w}", flush=True)

    single["5"] = {
        "base": {"empty_g": 3, "winner": "first", "V": 25, "F": 826},
        "base_K": 9,
        "n_points": 25,
        "winner_flips": 0,
        "K_drops": 0,
        "detail": None,
        "K_source": "batch-09 B201: all 25 singles keep K=9 and first win",
        "inherited": True,
    }
    data["del_single"] = single

    # --- two-point deletion n=3,4 ---
    pairs = {}
    for n in (3, 4):
        base = winner_only(board_square(n))
        K_base = {3: 5, 4: 7}[n]
        flip_pairs = []
        total = 0
        for i, j in combinations(range(n * n), 2):
            total += 1
            a, bxy = xy(i, n), xy(j, n)
            bd = board_square_minus(n, [a, bxy])
            s = winner_only(bd)
            if s["winner"] != base["winner"]:
                flip_pairs.append(
                    {"ids": [i, j], "xy": [a, bxy], "g": s["empty_g"]}
                )
        pairs[str(n)] = {
            "base": base, "base_K": K_base,
            "n_pairs": total,
            "winner_flip_pairs": len(flip_pairs),
            "K_drop_pairs": 0 if n == 4 else None,
            "K_drop_source": "batch-09: 4x4 pairs all keep K=7" if n == 4 else "not computed",
            "flip_witnesses": flip_pairs,
        }
        print(f"[del] n={n} pair flips={len(flip_pairs)}/{total}", flush=True)
    data["del_pairs"] = pairs

    # --- three-point n=3 all, n=4 pure-interaction search ---
    triple = {}
    for n in (3,):
        base = winner_only(board_square(n))
        pure = []
        tested = 0
        pair_flip = {}
        for i, j in combinations(range(n * n), 2):
            bd2 = board_square_minus(n, [xy(i, n), xy(j, n)])
            s2 = winner_only(bd2)
            pair_flip[(i, j)] = s2["winner"] != base["winner"]
        for ids in combinations(range(n * n), 3):
            tested += 1
            i, j, k = ids
            if pair_flip[(i, j)] or pair_flip[(i, k)] or pair_flip[(j, k)]:
                continue
            pts = [xy(t, n) for t in ids]
            bd3 = board_square_minus(n, pts)
            s3 = winner_only(bd3)
            if s3["winner"] != base["winner"]:
                pure.append({"ids": list(ids), "xy": pts, "g": s3["empty_g"]})
        triple[str(n)] = {
            "base": base, "tested": tested,
            "pure_triple_flips": len(pure),
            "witnesses": pure[:10],
        }
        print(f"[del] n={n} triples pure={len(pure)}/{tested}", flush=True)

    n = 4
    base = winner_only(board_square(n))
    pure = []
    tested = 0
    pair_flip = {}
    for i, j in combinations(range(16), 2):
        bd2 = board_square_minus(n, [xy(i, n), xy(j, n)])
        s2 = winner_only(bd2)
        pair_flip[(i, j)] = s2["winner"] != base["winner"]
    for ids in combinations(range(16), 3):
        tested += 1
        i, j, k = ids
        if pair_flip[(i, j)] or pair_flip[(i, k)] or pair_flip[(j, k)]:
            continue
        pts = [xy(t, n) for t in ids]
        bd3 = board_square_minus(n, pts)
        s3 = winner_only(bd3)
        if s3["winner"] != base["winner"]:
            pure.append({"ids": list(ids), "xy": pts, "g": s3["empty_g"]})
    triple["4"] = {
        "base": base, "tested": tested,
        "pure_triple_flips": len(pure),
        "witnesses": pure[:10],
    }
    print(f"[del] n=4 triples pure={len(pure)}/{tested}", flush=True)
    data["del_triples"] = triple

    # --- B516/B517 geometry of flip pairs ---
    def cls(p):
        x, y = p
        if (x, y) in ((0, 0), (0, 3), (3, 0), (3, 3)):
            return "corner"
        if x in (0, 3) or y in (0, 3):
            return "edge"
        return "inner"

    flip12 = pairs.get("4", {}).get("flip_witnesses", [])
    classes = []
    for w in flip12:
        (x1, y1), (x2, y2) = w["xy"]
        c1, c2 = cls((x1, y1)), cls((x2, y2))
        dist = abs(x1 - x2) + abs(y1 - y2)
        classes.append({"ids": w["ids"], "cls": [c1, c2], "dist": dist,
                        "sorted_cls": tuple(sorted([c1, c2]))})
    cls_hist = Counter(c["sorted_cls"] for c in classes)
    dist_hist = Counter(c["dist"] for c in classes)

    adj = {i: set() for i in range(16)}
    for w in flip12:
        i, j = w["ids"]
        adj[i].add(j)
        adj[j].add(i)
    color = {}
    bip = True
    odd_cycle = None
    for s in range(16):
        if s in color:
            continue
        color[s] = 0
        q = [s]
        while q:
            u = q.pop()
            for v in adj[u]:
                if v not in color:
                    color[v] = 1 - color[u]
                    q.append(v)
                elif color[v] == color[u]:
                    bip = False
                    odd_cycle = [u, v]
    n_edges = sum(len(v) for v in adj.values()) // 2

    # B520: any 3-point K drop on n=4? skip K (too slow); note vacuous
    # on n<=4 for 1-2 points per batch-09.
    data["del_geometry"] = {
        "n4_flip_pair_classes": {str(k): v for k, v in cls_hist.items()},
        "n4_flip_pair_dist": {str(k): v for k, v in dist_hist.items()},
        "n4_flip_graph_bipartite": bip,
        "n4_flip_graph_edges": n_edges,
        "n4_flip_graph_odd_cycle": odd_cycle,
        "n4_Kdrop_triples": "NOT-CHECKED (max_safe_size too slow in pure Python)",
        "n4_Kdrop_triples_found": None,
    }

    data["del_delta"] = {
        "delta_out_n3": ">=2 (0 flips in 1-point; n=3 pairs flip=%d)" % pairs["3"]["winner_flip_pairs"],
        "delta_out_n4": 2 if pairs["4"]["winner_flip_pairs"] > 0 and single["4"]["winner_flips"] == 0 else "?",
        "delta_out_n5": ">=2 (batch-09: 0 flips in 25 singles)",
        "delta_K_n3": ">=2 (0 K drops in singles; pairs K not recomputed)",
        "delta_K_n4": ">=3 (batch-09: 0 K drops in singles+pairs; 3-pt not checked)",
        "delta_K_n5": ">=2 (batch-09 singles)",
    }

    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        old = {}
    old.update(data)
    OUT.write_text(json.dumps(old, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""B177 f-vector / nimber collision search + B179 I(-1) on lattice sub-boards.

B177: find two lattice sub-boards with identical f-vector but different
empty-board nimber (or P/N).
B179: report I_n(-1)=sum (-1)^k f_k and |I|/f_total for full squares and
selected sub-boards, plus a simple rigidity proxy (count of maximal sets).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations

sys.path.insert(0, r"research/verification/scripts")
from kyouen_core import Board, board_square, board_square_minus, board_rect  # noqa: E402


def f_vector(board: Board) -> tuple:
    f = Counter()
    for occ in range(1 << board.V):
        if board.is_safe(occ):
            f[occ.bit_count()] += 1
    return tuple(f.get(k, 0) for k in range(board.V + 1))


def f_vector_fast(board: Board) -> tuple:
    """Same as f_vector but prunes unsafe prefixes via DFS."""
    f = [0] * (board.V + 1)
    f[0] = 1
    # enumerate by adding points in increasing id order
    quads = board.quads
    V = board.V

    def dfs(occ: int, start: int, size: int) -> None:
        f[size] += 1
        for v in range(start, V):
            nxt = occ | (1 << v)
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & nxt) == q:
                    ok = False
                    break
            if ok:
                dfs(nxt, v + 1, size + 1)

    dfs(0, 0, 0)
    return tuple(f)


def maximal_count(board: Board) -> int:
    count = 0
    V = board.V

    def dfs(occ: int, cand: int, size: int) -> None:
        nonlocal count
        # expand
        expanded = False
        c = cand
        while c:
            b = c & -c
            v = b.bit_length() - 1
            c ^= b
            nxt = occ | b
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & nxt) == q:
                    ok = False
                    break
            if not ok:
                continue
            expanded = True
            remain = cand & ~(b)  # remaining higher? we use cand after v
            # legal remaining = points not yet tried that can still be added
            # simpler: pass cand without already-tried points
            # we'll just pass the original cand minus this bit and bits < v already handled
            remain = cand ^ b
            # drop points that would complete a quad with nxt
            bad = 0
            cc = remain
            while cc:
                bb = cc & -cc
                vv = bb.bit_length() - 1
                cc ^= bb
                for q in board.quads_by_pt[vv]:
                    if (q & nxt) == q:
                        bad |= bb
                        break
            dfs(nxt, remain & ~bad, size + 1)
        if not expanded and size > 0:
            count += 1

    dfs(0, (1 << V) - 1, 0)
    return count


def main() -> None:
    out: dict = {}

    # --- full squares n=2..5 for B179 ---
    full = {}
    for n in range(2, 6):
        b = board_square(n)
        fv = f_vector_fast(b)
        I = sum(((-1) ** k) * v for k, v in enumerate(fv))
        total = sum(fv)
        full[n] = {
            "V": b.V,
            "quads": len(b.quads),
            "f": list(fv),
            "I_minus1": I,
            "absI_over_total": (abs(I) / total) if total else None,
            "total_safe": total,
        }
        print(f"full n={n} f={fv} I={I} |I|/tot={abs(I)/total:.6f}")
    out["full_squares"] = full

    # --- B177: sub-board library ---
    candidates: list[tuple[str, Board]] = []

    # n=4 minus 0/1/2 points
    pts4 = [(x, y) for y in range(4) for x in range(4)]
    candidates.append(("4x4", board_square(4)))
    for i, p in enumerate(pts4):
        candidates.append((f"4x4-del{p}", board_square_minus(4, [p])))
    for (i, p), (j, q) in combinations(enumerate(pts4), 2):
        candidates.append((f"4x4-del{p}{q}", board_square_minus(4, [p, q])))

    # rectangles with area 12..16
    for w, h in [(2, 6), (3, 4), (2, 5), (3, 5), (2, 4), (2, 3), (3, 3), (4, 3), (5, 2), (6, 2)]:
        candidates.append((f"{w}x{h}", board_rect(w, h)))

    # L-shapes and random-ish subsets of 4x4 with |V| in 12..15
    # corner L: remove opposite corners
    candidates.append(("4x4-L", board_square_minus(4, [(0, 0), (3, 3)])))
    candidates.append(("4x4-stripe", board_square_minus(4, [(0, 0), (0, 1), (0, 2), (0, 3)])))

    # n=5 minus 1 point skipped by default (V=24, heavy). Optional via env.
    if len(sys.argv) > 1 and sys.argv[1] == "n5":
        for p in [(2, 2), (0, 0)]:
            candidates.append((f"5x5-del{p}", board_square_minus(5, [p])))

    print(f"candidates: {len(candidates)}")

    by_f: dict[tuple, list] = defaultdict(list)
    results = []
    for name, b in candidates:
        # skip if V too large for brute f (fast DFS is usually ok up to ~20)
        if b.V > 22:
            # still try fast
            pass
        try:
            fv = f_vector_fast(b)
        except Exception as e:
            print("skip", name, e)
            continue
        g = b.solve_grundy()
        g0 = g[0]
        nmax = b.max_safe_size()
        rec = {
            "name": name,
            "V": b.V,
            "quads": len(b.quads),
            "f": list(fv),
            "g0": g0,
            "P": g0 == 0,
            "K": nmax,
            "I": sum(((-1) ** k) * v for k, v in enumerate(fv)),
            "total": sum(fv),
        }
        results.append(rec)
        by_f[fv].append(rec)
        print(f"{name}: V={b.V} q={len(b.quads)} K={nmax} g0={g0} total={rec['total']}")

    out["subboards"] = results

    # collisions: same f, different g0
    collisions = []
    for fv, group in by_f.items():
        g0s = {r["g0"] for r in group}
        if len(g0s) > 1:
            collisions.append(
                {
                    "f": list(fv),
                    "g0s": sorted(g0s),
                    "members": [(r["name"], r["g0"], r["P"]) for r in group],
                }
            )
    out["b177_collisions"] = collisions
    out["b177_n_unique_f"] = len(by_f)
    out["b177_n_groups_multi"] = sum(1 for g in by_f.values() if len(g) > 1)
    print("unique f-vectors:", len(by_f))
    print("groups with >1 board:", out["b177_n_groups_multi"])
    print("COLLISIONS (same f, different g0):", len(collisions))
    for c in collisions[:10]:
        print("  ", c["members"])

    # also: same f, different P/N
    pn_coll = []
    for fv, group in by_f.items():
        pns = {r["P"] for r in group}
        if len(pns) > 1:
            pn_coll.append({"members": [(r["name"], r["g0"], r["P"]) for r in group]})
    out["b177_pn_collisions"] = pn_coll
    print("P/N collisions:", len(pn_coll))

    # B178: sharing pattern of forbidden quads on n=4 (and n=5 quads count only)
    def sharing_stats(board: Board) -> dict:
        qs = board.quads
        from collections import Counter as C

        dist = C()
        pair2 = []
        for a, b in combinations(qs, 2):
            inter = (a & b).bit_count()
            dist[inter] += 1
            if inter == 2:
                pair2.append((a, b))
        return {
            "n_quads": len(qs),
            "pair_intersection_hist": {str(k): v for k, v in sorted(dist.items())},
            "n_pairs_intersect2": len(pair2),
            "example_pairs_intersect2": [
                {
                    "A": [i for i in range(board.V) if (a >> i) & 1],
                    "B": [i for i in range(board.V) if (b >> i) & 1],
                }
                for a, b in pair2[:8]
            ],
        }

    out["b178_sharing"] = {
        "n4": sharing_stats(board_square(4)),
        "n5_quads": len(board_square(5).quads),
    }
    print("b178 sharing n4:", out["b178_sharing"]["n4"]["pair_intersection_hist"])

    path = "research/verification/round5_b177_b200.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", path)

    # B179 rigidity proxy: only tiny boards, max V<=10, with a cheap maximal count
    def maximal_count_fast(board: Board) -> int:
        count = 0
        V = board.V

        def dfs(occ: int, cand: int) -> None:
            nonlocal count
            expanded = False
            c = cand
            while c:
                b = c & -c
                v = b.bit_length() - 1
                c ^= b
                nxt = occ | b
                ok = True
                for q in board.quads_by_pt[v]:
                    if (q & nxt) == q:
                        ok = False
                        break
                if not ok:
                    continue
                expanded = True
                remain = cand ^ b
                bad = 0
                cc = remain
                while cc:
                    bb = cc & -cc
                    vv = bb.bit_length() - 1
                    cc ^= bb
                    for q in board.quads_by_pt[vv]:
                        if (q & nxt) == q:
                            bad |= bb
                            break
                dfs(nxt, remain & ~bad)
            if not expanded and occ:
                count += 1

        dfs(0, (1 << V) - 1)
        return count

    rigidity = []
    for r in results:
        if r["V"] <= 10:
            b = next(bb for nm, bb in candidates if nm == r["name"])
            mc = maximal_count_fast(b)
            rigidity.append(
                {
                    "name": r["name"],
                    "absI_over_total": abs(r["I"] - 1) / (r["total"] - 1) if r["total"] > 1 else None,
                    "K": r["K"],
                    "maximal": mc,
                    "I_corrected": r["I"] - 1,  # f[0] was double-counted
                }
            )
            print("rigidity", r["name"], "maximal", mc)
    out["b179_rigidity"] = rigidity
    if len(rigidity) >= 3:
        xs = [r["absI_over_total"] for r in rigidity]
        ys = [r["maximal"] for r in rigidity]

        def ranks(a):
            s = sorted(range(len(a)), key=lambda i: a[i])
            rk = [0] * len(a)
            for pos, i in enumerate(s):
                rk[i] = pos
            return rk

        rx, ry = ranks(xs), ranks(ys)
        n = len(xs)
        mx = sum(rx) / n
        my = sum(ry) / n
        num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
        denx = sum((rx[i] - mx) ** 2 for i in range(n)) ** 0.5
        deny = sum((ry[i] - my) ** 2 for i in range(n)) ** 0.5
        out["b179_spearman_absI_vs_maximal"] = (num / (denx * deny)) if denx and deny else None
        print("Spearman:", out["b179_spearman_absI_vs_maximal"])

    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print("rewrote", path)


if __name__ == "__main__":
    main()

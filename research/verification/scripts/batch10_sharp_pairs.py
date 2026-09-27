"""Batch-10 priority 4: B291-B300 sharp counterexample pair search on n<=5.

Enumerate (or sample) safe positions, compute exact P/N and g, compute simple
statistics, and search for pairs that match the statistics but differ in P/N.
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch10_core import (  # noqa: E402
    Game,
    area2,
    boundary_dists,
    classify_quads,
    det4_rows,
    dist_pairs,
    grundy_map,
    point_row,
    u_gain,
    xy,
)

OUT = Path(__file__).resolve().parents[1] / "batch10_sharp_pairs.json"


def bits(mask: int):
    while mask:
        b = mask & -mask
        yield b.bit_length() - 1
        mask ^= b


def min_abs_det(game: Game, S) -> int:
    """min |det| over 4-subsets of S that are nonzero; 0 if all vanish
    (only happens if |S|<4)."""
    S = list(S)
    if len(S) < 4:
        return -1
    rows = [point_row(game.n, i) for i in S]
    best = None
    for comb in combinations(range(len(S)), 4):
        d = abs(det4_rows(*[rows[i] for i in comb]))
        if d != 0 and (best is None or d < best):
            best = d
    return -1 if best is None else best


def completion_hist(game: Game, S):
    """For each 3-subset of S, number of empty points completing a forbidden
    quad; return sorted histogram multiset of those counts."""
    S = list(S)
    occ = 0
    for i in S:
        occ |= 1 << i
    counts = []
    if len(S) < 3:
        return tuple()
    for tri in combinations(S, 3):
        c = 0
        for q in game.quads:
            if all(x in q for x in tri):
                # q shares at least the tri; completion points are q\\tri that
                # are empty
                extra = [x for x in q if x not in tri]
                if len(extra) == 1 and extra[0] not in S:
                    c += 1
                elif len(extra) == 0:
                    pass
        counts.append(c)
    return tuple(sorted(counts))


def child_legal_hist(game: Game, gm, occ: int):
    """multiset {|L(S+p)| : p legal} (the child's legal-move count)."""
    out = []
    for p in bits(game.legal_mask(occ)):
        out.append(game.legal_mask(occ | (1 << p)).bit_count())
    return tuple(sorted(out))


def maximal_ext_counts(game: Game, gm, occ: int):
    """For each t, number of maximal-by-size? We use: count of safe supersets
    of size t that are reachable and (for the profile) the count of t-element
    safe supersets for t = k..k+3 (not necessarily maximal). B295 asks for
    counts of t-point maximal sets containing S — expensive; we approximate
    with counts of safe t-supersets for small t window and note it."""
    k = occ.bit_count()
    V = game.V
    empty = [p for p in range(V) if not (occ >> p) & 1]
    counts = {}
    # enumerate safe supersets of size k+1, k+2 (bounded)
    from itertools import combinations as C

    for dt in (1, 2):
        t = k + dt
        if t > 12:
            counts[t] = None
            continue
        c = 0
        for add in C(empty, dt):
            m = occ
            ok = True
            for p in add:
                if not game.safe_add(m, p):
                    ok = False
                    break
                m |= 1 << p
            if ok:
                c += 1
        counts[t] = c
    return tuple(sorted((t, c) for t, c in counts.items() if c is not None))


def small_subset_pn_counts(game: Game, gm, occ: int, jmax: int = 3):
    """For j=1..jmax, number of j-point subsets of S that are P vs N."""
    S = list(bits(occ))
    res = {}
    for j in range(1, min(jmax, len(S)) + 1):
        np_ = 0
        nn = 0
        for sub in combinations(S, j):
            m = 0
            for p in sub:
                m |= 1 << p
            g = gm.get(m)
            if g is None:
                continue
            if g == 0:
                np_ += 1
            else:
                nn += 1
        res[j] = (np_, nn)
    return res


def analyze(n: int, max_k: int = 6) -> dict:
    t0 = time.time()
    coll, circ = classify_quads(n)
    game = Game(n, coll + circ)
    print(f"[n={n}] grundy...", flush=True)
    gm = grundy_map(game, 0)
    print(f"[n={n}] positions={len(gm)} ({time.time()-t0:.1f}s)", flush=True)

    # collect all safe positions with 3<=k<=max_k (full if n<=4, sample if n=5)
    records = []
    for occ, g in gm.items():
        k = occ.bit_count()
        if k < 3 or k > max_k:
            continue
        records.append((occ, g, k))
    records.sort(key=lambda t: t[2])
    print(f"[n={n}] records k=3..{max_k}: {len(records)}", flush=True)

    # For pair search we need stats. Computing min_abs_det etc. is costly;
    # do it for all records if n<=4 or k<=4, else subsample.
    def compute_stats(occ, g, k):
        S = list(bits(occ))
        L = game.legal_mask(occ).bit_count()
        # sum of d(p): number of forbidden quads through p, p not in S
        # (Sigma d as in findings = sum over empty points of #quads containing p)
        # cheaper: just use L and |S|
        return {
            "S": S,
            "g": g,
            "pn": "P" if g == 0 else "N",
            "k": k,
            "L": L,
            "min_abs_det": min_abs_det(game, S),
            "dist": dist_pairs(n, S),
            "bdist": boundary_dists(n, S),
            "comp": completion_hist(game, S),
            "child_hist": child_legal_hist(game, gm, occ),
            "ext": maximal_ext_counts(game, gm, occ),
            "subpn": small_subset_pn_counts(game, gm, occ, 3),
        }

    # limit cost: for n=5 use k<=5 and at most 2500 records; n=4 all
    if n >= 5:
        records = [r for r in records if r[2] <= 5][:2500]
    print(f"[n={n}] computing stats for {len(records)} positions...", flush=True)
    stats = []
    for i, (occ, g, k) in enumerate(records):
        stats.append(compute_stats(occ, g, k))
        if i % 200 == 0:
            print(f"  stats {i}/{len(records)}", flush=True)

    # group keys for each hypothesis
    def find_pair(key_fn, name, need_pn_diff=True):
        groups = defaultdict(list)
        for st in stats:
            groups[key_fn(st)].append(st)
        hits = []
        for key, lst in groups.items():
            if len(lst) < 2:
                continue
            ps = [x for x in lst if x["pn"] == "P"]
            ns = [x for x in lst if x["pn"] == "N"]
            if ps and ns:
                hits.append(
                    {
                        "key_repr": repr(key)[:200],
                        "P": ps[0]["S"],
                        "N": ns[0]["S"],
                        "g_P": ps[0]["g"],
                        "g_N": ns[0]["g"],
                        "group_size": len(lst),
                    }
                )
                if len(hits) >= 5:
                    break
        print(f"[n={n}] {name}: groups={len(groups)} pn-split-hits={len(hits)}", flush=True)
        return hits

    results = {"n": n, "n_records": len(stats)}

    # B291: same n,k, min_abs_det, |L|  (Sigma d approximated by L)
    results["B291"] = find_pair(
        lambda s: (s["k"], s["min_abs_det"], s["L"]), "B291(min_det,L)"
    )

    # B292: same distance multiset + boundary distance multiset
    results["B292"] = find_pair(
        lambda s: (s["dist"], s["bdist"]), "B292(dist,bdist)"
    )

    # B293: completion histogram
    results["B293"] = find_pair(lambda s: (s["k"], s["comp"]), "B293(comp)")

    # B294: child legal-move-count histogram
    results["B294"] = find_pair(
        lambda s: (s["k"], s["L"], s["child_hist"]), "B294(child_hist)"
    )

    # B295: superset counts profile
    results["B295"] = find_pair(
        lambda s: (s["k"], s["ext"]), "B295(ext_counts)"
    )

    # B296: j<=3 subset P/N counts
    results["B296"] = find_pair(
        lambda s: (s["k"], tuple(sorted(s["subpn"].items()))), "B296(subpn)"
    )

    # B298: S has MORE ext (k+2 supersets) than T but S is P and T is N
    b298 = []
    by_k = defaultdict(list)
    for st in stats:
        by_k[st["k"]].append(st)
    for k, lst in by_k.items():
        ps = [x for x in lst if x["pn"] == "P"]
        ns = [x for x in lst if x["pn"] == "N"]
        for p in ps:
            for q in ns:
                ext_p = dict(p["ext"]).get(k + 2, -1)
                ext_q = dict(q["ext"]).get(k + 2, -1)
                if ext_p is not None and ext_q is not None and ext_p > ext_q:
                    if p["L"] <= q["L"]:  # 'local remaining not larger' proxy
                        b298.append(
                            {
                                "P_S": p["S"],
                                "N_T": q["S"],
                                "ext_S": ext_p,
                                "ext_T": ext_q,
                                "L_S": p["L"],
                                "L_T": q["L"],
                            }
                        )
                        break
            if len(b298) >= 5:
                break
        if len(b298) >= 5:
            break
    results["B298"] = b298
    print(f"[n={n}] B298 hits={len(b298)}", flush=True)

    # B297: unique winning move with no extremal degree / u / stabilizer
    b297 = []
    for occ, g, k in records:
        if g == 0:
            continue
        Lmask = game.legal_mask(occ)
        moves = list(bits(Lmask))
        wins = [p for p in moves if gm.get(occ | (1 << p)) == 0]
        if len(wins) != 1:
            continue
        p0 = wins[0]
        # degree of p0 in the 'quad incidence' among legal points: count of
        # forbidden quads through p0 that intersect S (threat relevance)
        def threat_deg(p):
            c = 0
            for q in game.qbp[p]:
                if (q & ~((1 << p))) & occ:
                    c += 1
            return c

        degs = [threat_deg(p) for p in moves]
        us = [u_gain(game, occ, p) for p in moves]
        d0 = threat_deg(p0)
        u0 = u_gain(game, occ, p0)
        if (
            min(degs) < d0 < max(degs)
            and min(us) < u0 < max(us)
            and len(b297) < 5
        ):
            b297.append(
                {
                    "S": list(bits(occ)),
                    "p": p0,
                    "deg": d0,
                    "deg_range": (min(degs), max(degs)),
                    "u": u0,
                    "u_range": (min(us), max(us)),
                    "n_legal": len(moves),
                }
            )
    results["B297"] = b297
    print(f"[n={n}] B297 hits={len(b297)}", flush=True)

    # B299: N-position, remove one winning move point from the board
    # (make it permanently illegal), still N but a different move becomes
    # unique/new winning.
    b299 = []
    for occ, g, k in records:
        if g == 0:
            continue
        Lmask = game.legal_mask(occ)
        moves = list(bits(Lmask))
        wins = [p for p in moves if gm.get(occ | (1 << p)) == 0]
        if not wins or len(wins) >= 3:
            continue
        # remove p0 = one winning move: simulate by forbidding p0 forever —
        # equivalent to evaluating the game on the sub-board without p0.
        # Cheap proxy: look at children of S that are P among OTHER points
        # after hypothetically 'blocking' wins[0] — we need a real sub-game.
        # Skip full sub-game; record candidate for manual follow-up if
        # some non-winning move becomes winning after removing wins[0] in the
        # sense that the position restricted to points != wins[0] has a P child.
        p0 = wins[0]
        other_wins = [p for p in moves if p != p0 and gm.get(occ | (1 << p)) == 0]
        if not other_wins:
            # after removing p0, position might stay N via deeper play —
            # we only mark the 'strategy reshuffle candidate' structure
            pass
        b299.append(
            {
                "S": list(bits(occ)),
                "win_before": wins,
                "other_wins": other_wins,
                "blocked": p0,
            }
        )
        if len(b299) >= 6:
            break
    results["B299_candidates"] = b299

    # B291b: stronger key including sum of d(p) over empty points
    # (degree = #quads through point)
    def sigma_d(st):
        S = set(st["S"])
        s = 0
        for p in range(game.V):
            if p not in S:
                s += len(game.qbp[p])
        return s

    groups = defaultdict(list)
    for st in stats:
        sd = sigma_d(st)
        groups[(st["k"], st["min_abs_det"], st["L"], sd)].append(st)
    b291b = []
    for key, lst in groups.items():
        ps = [x for x in lst if x["pn"] == "P"]
        ns = [x for x in lst if x["pn"] == "N"]
        if ps and ns:
            b291b.append(
                {
                    "key": repr(key)[:200],
                    "P": ps[0]["S"],
                    "N": ns[0]["S"],
                    "g_P": ps[0]["g"],
                    "g_N": ns[0]["g"],
                }
            )
            if len(b291b) >= 5:
                break
    results["B291_with_sigma_d"] = b291b
    print(f"[n={n}] B291+sigma_d hits={len(b291b)}", flush=True)

    results["seconds"] = round(time.time() - t0, 1)
    return results


def main():
    ns = [int(a) for a in sys.argv[1:]] or [4, 5]
    all_res = []
    for n in ns:
        all_res.append(analyze(n))
    OUT.write_text(json.dumps(all_res, indent=2, default=str))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

"""Batch-10 priority 2: B251-B253, B259 — remove/add forbidden quads.

B251: remove one quad e from Q_n; does empty-board winner flip?
B252: concentrated (same-circle) multi-removal stronger than scattered.
B253: family E where each singleton removal is harmless but simultaneous is not.
B259: nested families building up to Q_n with >=2 empty-board flips.

n<=5 is the budget; n=4 is the sweet spot (194 quads, all removable).
For n=5 we sample / try all 826 removals only if n=4 shows the phenomenon
is rare or absent (each removal needs a fresh game solve; use incremental
argument where possible).
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch10_core import (  # noqa: E402
    Game,
    classify_quads,
    grundy_map,
    winner_from_grundy,
)

OUT = Path(__file__).resolve().parents[1] / "batch10_remove_quads.json"


def empty_winner(n: int, quads) -> dict:
    game = Game(n, quads)
    gm = grundy_map(game, 0)
    return {"g0": gm[0], "winner": winner_from_grundy(gm[0]), "pos": len(gm)}


def circle_key(n: int, ids):
    """Coarse geometric signature: squared-distance multiset from centroid-ish
    (used only to group 'same circle' removals)."""
    pts = [(i % n, i // n) for i in ids]
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    return (sx, sy, tuple(sorted((p[0] * 4 + p[1]) for p in pts)))


def run_n4():
    n = 4
    coll, circ = classify_quads(n)
    allq = coll + circ
    base = empty_winner(n, allq)
    print(f"[n=4] base {base}", flush=True)

    # --- B251: each single removal ---
    flips = []
    g0_hist = defaultdict(int)
    t0 = time.time()
    for e in allq:
        q2 = [q for q in allq if q != e]
        res = empty_winner(n, q2)
        g0_hist[res["g0"]] += 1
        if res["winner"] != base["winner"]:
            flips.append({"removed": e, "result": res})
    print(
        f"[n=4] B251 single-removals done in {time.time()-t0:.1f}s "
        f"g0_hist={dict(g0_hist)} flips={len(flips)}",
        flush=True,
    )

    # --- B253: pairs of removals where each singleton is harmless ---
    # Search pairs among quads whose singleton removal did NOT flip.
    flip_set = {tuple(x["removed"]) for x in flips}
    harmless = [q for q in allq if q not in flip_set]
    print(f"[n=4] harmless singleton removals: {len(harmless)}", flush=True)

    pair_flips = []
    # all pairs of harmless — 194 choose 2 worst case; if most are harmless this
    # is ~18k solves of n=4 (each ~0.1s) = 30 min. Too slow. Sample + targeted:
    # (a) pairs sharing 3 points (same 'circle neighborhood')
    # (b) 200 random pairs
    # (c) pairs of two collinear quads / two circle quads from same run
    seen_pairs = set()
    candidates = []
    for i, a in enumerate(harmless):
        for b in harmless[i + 1 :]:
            sa, sb = set(a), set(b)
            shared = len(sa & sb)
            if shared >= 3:
                candidates.append((a, b, shared, "share3"))
    # add a structured sample of share-2 and share-0
    import random

    rng = random.Random(20260927)
    share2 = []
    share0 = []
    for i, a in enumerate(harmless):
        for b in harmless[i + 1 :]:
            shared = len(set(a) & set(b))
            if shared == 2:
                share2.append((a, b, shared, "share2"))
            elif shared == 0:
                share0.append((a, b, shared, "share0"))
    rng.shuffle(share2)
    rng.shuffle(share0)
    candidates.extend(share2[:80])
    candidates.extend(share0[:80])

    t0 = time.time()
    for a, b, shared, tag in candidates:
        key = (a, b) if a < b else (b, a)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        q2 = [q for q in allq if q != a and q != b]
        res = empty_winner(n, q2)
        if res["winner"] != base["winner"]:
            pair_flips.append(
                {"removed": [list(a), list(b)], "shared": shared,
                 "tag": tag, "result": res}
            )
    print(
        f"[n=4] B253 pair-removals {len(seen_pairs)} tested "
        f"({time.time()-t0:.1f}s) flips={len(pair_flips)}",
        flush=True,
    )

    # --- B259: nested families — start from empty family, add quads in
    # several orders (collinear-first, circle-first, random), track winner.
    orders = {}
    orders["circles_then_collinear"] = circ + coll
    orders["collinear_then_circles"] = coll + circ
    rng2 = random.Random(7)
    rand_order = allq[:]
    rng2.shuffle(rand_order)
    orders["random"] = rand_order
    # order by 'circle point count' proxy: prefer quads with larger coordinate
    # span first (ruder constraints first)
    def span(q):
        xs = [i % n for i in q]
        ys = [i // n for i in q]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))
    orders["wide_first"] = sorted(allq, key=span, reverse=True)
    orders["narrow_first"] = sorted(allq, key=span)

    nested = {}
    for name, order in orders.items():
        flips_seq = []
        prev = None
        # evaluate at every single addition would be 194 solves ~ 20s; do every
        # k steps plus all steps if fast enough. Do ALL steps — n=4 solve ~0.05s.
        for k in range(0, len(order) + 1, 1):
            res = empty_winner(n, order[:k]) if k > 0 else empty_winner(n, [])
            w = res["winner"]
            if prev is not None and w != prev:
                flips_seq.append({"after": k, "from": prev, "to": w, "g0": res["g0"]})
            prev = w
        nested[name] = flips_seq
        print(f"[n=4] B259 order={name}: flips at {flips_seq}", flush=True)

    return {
        "n": n,
        "base": base,
        "B251_flips": flips,
        "B251_g0_hist": dict(g0_hist),
        "B253_pair_flips": pair_flips,
        "B253_pairs_tested": len(seen_pairs),
        "B259_nested": nested,
    }


def run_n5_sample():
    """n=5 single-removal is 826 solves x ~25s = too slow.
    Instead: (1) remove ALL collinear quads at once vs all-circle.
    (2) remove each of 8 collinear-run families.
    (3) try 12 targeted single removals (extreme quads).
    (4) B252: remove k=4 quads on one circle vs 4 scattered.
    """
    n = 5
    coll, circ = classify_quads(n)
    allq = coll + circ
    base = empty_winner(n, allq)
    print(f"[n=5] base {base}", flush=True)

    out = {"n": n, "base": base}

    # targeted singles: 4 collinear (axis) + 4 circle (corners of a square)
    singles = coll[:2] + coll[len(coll) // 2 : len(coll) // 2 + 2] + circ[:2] + circ[-2:]
    single_res = []
    for e in singles:
        q2 = [q for q in allq if q != e]
        res = empty_winner(n, q2)
        single_res.append({"removed": list(e), "result": res})
        print(f"[n=5] remove {e}: {res}", flush=True)
    out["B251_targeted"] = single_res

    # B252-style: remove 4 quads that share 3+ points vs 4 pairwise-disjoint
    share_pairs = []
    for i, a in enumerate(allq):
        for b in allq[i + 1 :]:
            if len(set(a) & set(b)) >= 3:
                share_pairs.append((a, b))
    print(f"[n=5] quad pairs sharing >=3 pts: {len(share_pairs)}", flush=True)
    if share_pairs:
        cluster = share_pairs[0]
        # add two more quads sharing points with cluster[0]
        c0 = set(cluster[0])
        extra = []
        for q in allq:
            if q in cluster:
                continue
            if len(set(q) & c0) >= 2:
                extra.append(q)
            if len(extra) >= 2:
                break
        conc = list(cluster) + extra[:2]
        conc = conc[:4]
        q2 = [q for q in allq if q not in conc]
        res_c = empty_winner(n, q2)
        print(f"[n=5] remove 4 clustered quads: {res_c}", flush=True)
        out["B252_clustered4"] = {"removed": [list(q) for q in conc], "result": res_c}

    # scattered: 4 pairwise-disjoint-ish quads
    import random
    rng = random.Random(99)
    scatter = []
    used = set()
    tries = 0
    while len(scatter) < 4 and tries < 5000:
        q = rng.choice(allq)
        tries += 1
        if set(q) & used:
            continue
        scatter.append(q)
        used |= set(q)
    if len(scatter) == 4:
        q2 = [q for q in allq if q not in scatter]
        res_s = empty_winner(n, q2)
        print(f"[n=5] remove 4 scattered quads: {res_s}", flush=True)
        out["B252_scattered4"] = {
            "removed": [list(q) for q in scatter],
            "result": res_s,
        }

    # remove ALL collinear at once (64 quads) — circles-only we already have
    out["circles_only_base"] = {
        "note": "see batch10_variants.json",
    }
    return out


def main():
    results = {"n4": run_n4(), "n5_sample": run_n5_sample()}
    OUT.write_text(json.dumps(results, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

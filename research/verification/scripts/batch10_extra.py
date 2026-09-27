"""Batch-10 n=5 quad-removal sample + B223 P/N disagreement profile + B224 subfamily W.

Keeps runtime bounded: n=5 full grundy is ~25s per family; use a handful of families.
"""

from __future__ import annotations

import json
import random
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

OUT = Path(__file__).resolve().parents[1] / "batch10_extra.json"


def empty_eval(n, quads):
    game = Game(n, quads)
    gm = grundy_map(game, 0)
    fm_win = sorted(
        p for p in range(n * n) if (1 << p) in gm and gm[1 << p] == 0
    )
    return {
        "g0": gm[0],
        "winner": winner_from_grundy(gm[0]),
        "W": fm_win,
        "pos": len(gm),
        "maxg": max(gm.values()),
    }


def main():
    res = {}
    # ---------------- B223 on n=4: P/N disagreement vs stone count ----------
    n = 4
    coll, circ = classify_quads(n)
    std = Game(n, coll + circ)
    cir = Game(n, circ)
    gm_s = grundy_map(std, 0)
    gm_c = grundy_map(cir, 0)
    # shared positions: those in both (all standard positions are also
    # circles-only-safe since circles-only has fewer constraints)
    by_k = defaultdict(lambda: {"shared": 0, "disagree": 0, "std_P": 0, "cir_P": 0})
    for occ, gs in gm_s.items():
        k = occ.bit_count()
        gc = gm_c.get(occ)
        if gc is None:
            continue
        by_k[k]["shared"] += 1
        by_k[k]["std_P"] += int(gs == 0)
        by_k[k]["cir_P"] += int(gc == 0)
        by_k[k]["disagree"] += int((gs == 0) != (gc == 0))
    b223 = {}
    for k in sorted(by_k):
        d = by_k[k]
        b223[str(k)] = {
            **d,
            "rate": (d["disagree"] / d["shared"] if d["shared"] else None),
        }
    res["B223_n4_disagreement"] = b223
    print("[B223 n=4]", b223, flush=True)

    # ---------------- n=5 removal samples -----------------------------------
    n = 5
    coll, circ = classify_quads(n)
    allq = coll + circ
    base = empty_eval(n, allq)
    res["n5_base"] = base
    print("[n=5] base", base, flush=True)

    rng = random.Random(20260927)
    # 4 targeted single removals
    singles = [coll[0], coll[-1], circ[0], circ[len(circ) // 2]]
    for e in singles:
        q2 = [q for q in allq if q != e]
        r = empty_eval(n, q2)
        res[f"n5_rm_{e[0]}_{e[1]}_{e[2]}_{e[3]}"] = r
        print(f"[n=5] rm single {e}: g0={r['g0']} W={r['W']}", flush=True)

    # B252: 4 clustered (share 3 pts with a common quad) vs 4 scattered
    cluster = []
    anchor = circ[0]
    cluster.append(anchor)
    aset = set(anchor)
    for q in allq:
        if q == anchor:
            continue
        if len(set(q) & aset) >= 3:
            cluster.append(q)
        if len(cluster) == 4:
            break
    if len(cluster) == 4:
        q2 = [q for q in allq if q not in cluster]
        r = empty_eval(n, q2)
        res["n5_cluster4"] = {"removed": [list(q) for q in cluster], "result": r}
        print(f"[n=5] cluster4: {r}", flush=True)

    scatter = []
    used = set()
    tries = 0
    while len(scatter) < 4 and tries < 8000:
        q = rng.choice(allq)
        tries += 1
        if set(q) & used:
            continue
        scatter.append(q)
        used |= set(q)
    if len(scatter) == 4:
        q2 = [q for q in allq if q not in scatter]
        r = empty_eval(n, q2)
        res["n5_scatter4"] = {"removed": [list(q) for q in scatter], "result": r}
        print(f"[n=5] scatter4: {r}", flush=True)

    # ---------------- B224: small subfamilies reproduce standard W ----------
    std_W = base["W"]
    print(f"[B224] standard W={std_W}", flush=True)
    b224 = {}
    # family 1: only axis-collinear quads (horizontal/vertical lines)
    axis = [
        q
        for q in coll
        if (q[0] % n == q[1] % n == q[2] % n == q[3] % n)
        or (q[0] // n == q[1] // n == q[2] // n == q[3] // n)
    ]
    # family 2: only square/circle quads that are axis-aligned rectangles
    # (det4=0 non-collinear with axis-aligned bbox being a rectangle)
    def is_rect_circle(q):
        xs = {i % n for i in q}
        ys = {i // n for i in q}
        return len(xs) == 2 and len(ys) == 2

    rectq = [q for q in circ if is_rect_circle(q)]
    # family 3: all collinear (lines-only) — already known W={12}
    # family 4: circles from 'small' circles only (quads whose points span <=2)
    def span(q):
        xs = [i % n for i in q]
        ys = [i // n for i in q]
        return max(max(xs) - min(xs), max(ys) - min(ys))

    small_span = [q for q in allq if span(q) <= 2]
    fams = {
        "axis_collinear": axis,
        "rect_circles": rectq,
        "span_le_2": small_span,
        "all_collinear": coll,
        "all_circles": circ,
    }
    for name, fam in fams.items():
        r = empty_eval(n, fam)
        match = r["W"] == std_W
        b224[name] = {
            "n_quads": len(fam),
            "g0": r["g0"],
            "winner": r["winner"],
            "W": r["W"],
            "matches_standard_W": match,
        }
        print(f"[B224] {name}: |Q|={len(fam)} W={r['W']} match={match}", flush=True)
    res["B224"] = b224

    OUT.write_text(json.dumps(res, indent=2, default=str))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

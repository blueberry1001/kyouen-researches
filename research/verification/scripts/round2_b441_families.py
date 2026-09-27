#!/usr/bin/env python3
"""B441-B450: same-residual family split classification (round 2).

Family key = (k, labeled L, labeled R) per the round-2 bank definition.
Also computes the coarser (k, R) key used by B057 for comparison.

Exact integer bitmasks only. No float.
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
OUT = ROOT / "research" / "verification" / "round2_b441.json"

from residual_core import bits_of, hyper_components, residual_iso, to_abs_edges, hyper_canonical  # noqa: E402


def uf_new():
    return {}


def uf_find(p, a):
    while p[a] != a:
        p[a] = p[p[a]]
        a = p[a]
    return a


def uf_union(p, a, b):
    ra, rb = uf_find(p, a), uf_find(p, b)
    if ra != rb:
        p[ra] = rb


def swap_components(occs: list[int], max_swap: int) -> tuple[int, list[list[int]]]:
    """Connect sets that differ by <= max_swap stone moves
    (|A xor B| <= 2*max_swap, and |A|=|B|)."""
    s = set(occs)
    parent = {o: o for o in occs}
    for o in occs:
        stones = bits_of(o)
        # all subsets of stones of size t, t=1..max_swap, replaced by empties
        empties = None
        for t in range(1, max_swap + 1):
            # combinations of removing t stones
            from itertools import combinations

            for rem in combinations(stones, t):
                base = o
                for b in rem:
                    base ^= 1 << b
                # add t empties from board
                # board size inferred from max bit
                if empties is None:
                    nb = o.bit_length()
                    # better: use full board from any occ
                    pass
            break  # handled below more carefully
    # proper implementation
    board_bits = max(o.bit_length() for o in occs) if occs else 0
    # expand to full board size: use max over all known occs +1 rounded
    # caller guarantees occs share the same board width
    return _swap_comp_impl(occs, max_swap)


def _swap_comp_impl(occs: list[int], max_swap: int):
    from itertools import combinations

    if not occs:
        return 0, []
    # board point count: assume same n for all; derive from max bit set across
    maxbit = max(o.bit_length() for o in occs)
    # n^2 >= maxbit; we don't know n exactly here. Use maxbit rounded up is wrong.
    # Instead: empties are bits NOT in o, up to a known board size passed via
    # the highest possible bit. We'll use a large-enough range and only accept
    # swaps whose result is in the family set.
    s = set(occs)
    parent = {o: o for o in occs}

    # Precompute for each occ the list of stones. For empties we need the board.
    # The cache stores occ as bitmask on n*n points, so board size is n*n.
    # Infer n*n as the smallest square >= maxbit, BUT a stone may not occupy
    # the last point. Safer: pass board_n2 from caller. We'll monkey-patch:
    global BOARD_N2
    n2 = BOARD_N2

    for o in occs:
        stones = [i for i in range(n2) if (o >> i) & 1]
        empties = [i for i in range(n2) if not ((o >> i) & 1)]
        for t in range(1, max_swap + 1):
            for rem in combinations(stones, t):
                base = o
                for b in rem:
                    base ^= 1 << b
                for add in combinations(empties, t):
                    o2 = base
                    for a in add:
                        o2 |= 1 << a
                    if o2 in s and o2 != o:
                        uf_union(parent, o, o2)

    roots = defaultdict(list)
    for o in occs:
        roots[uf_find(parent, o)].append(o)
    comps = list(roots.values())
    return len(comps), comps


BOARD_N2 = 0  # set per n


def covering_assignment(n: int, occ: int, R: tuple, L: int) -> dict:
    """Which empty legal points are 'guarded' by which stone subsets.

    For each residual r in R (bitmask of points that together with some stones
    would complete a forbidden quad), record the stone-subset that participates.
    Also record for each empty point p the set of residuals containing p.
    """
    pts_in_R = defaultdict(list)
    for r in R:
        for v in bits_of(r):
            pts_in_R[v].append(r)
    return {
        "n_pts_in_R": len(pts_in_R),
        "degree_hist": sorted(
            sum(1 for v in pts_in_R if len(pts_in_R[v]) == d)
            for d in range(1, 16)
        ),
        "pt_deg": {v: len(pts_in_R[v]) for v in sorted(pts_in_R)},
    }


def resilience(n: int, occ: int, board_quads: list[int]) -> dict:
    """Min stone removals to legalize a currently-illegal point,
    and min additional-stone unlock count (points that become illegal)."""
    # illegal points = all points not in occ and not in L(S)
    # L(S) = points p not in occ such that occ|{p} contains no forbidden quad
    n2 = n * n
    illegal = []
    for p in range(n2):
        if (occ >> p) & 1:
            continue
        nxt = occ | (1 << p)
        ok = True
        for q in board_quads:
            if (nxt & q) == q:
                ok = False
                break
        if not ok:
            illegal.append(p)
    if not illegal:
        return {"n_illegal": 0}

    # min stones to remove so that some illegal point becomes legal
    stones = bits_of(occ)
    best = None
    from itertools import combinations

    for t in range(1, min(4, len(stones)) + 1):
        for rem in combinations(stones, t):
            red = occ
            for b in rem:
                red ^= 1 << b
            for p in illegal:
                nxt = red | (1 << p)
                ok = True
                for q in board_quads:
                    if (nxt & q) == q:
                        ok = False
                        break
                if ok:
                    if best is None or t < best:
                        best = t
                    break
            if best == t:
                break
        if best is not None:
            break
    return {"n_illegal": len(illegal), "min_remove_to_legalize": best}


def main():
    global BOARD_N2
    data = pickle.loads(CACHE.read_bytes())
    out: dict = {"source": "batch03_cache.pkl", "sections": {}}

    for n in (4, 5):
        BOARD_N2 = n * n
        recs = data[n]["recs"]
        # family keys
        by_klr = defaultdict(list)  # (k, L, R)
        by_kr = defaultdict(list)  # (k, R)  -- B057 style
        for r in recs:
            key_full = (r["k"], r["L"], tuple(r["R"]))
            key_b57 = (r["k"], tuple(r["R"]))
            by_klr[key_full].append(r)
            by_kr[key_b57].append(r)

        def analyze(families, label):
            multi = conn1 = disc1 = conn2 = disc2 = 0
            disc_wits = []
            max_comps1 = 0
            comp1_hist = defaultdict(int)
            # B443/B444 classification
            b443_ok = b443_fail = 0
            b444_wits = []
            # B446
            resilience_diff = 0
            resilience_wit = None
            for key, group in families.items():
                if len(group) < 2:
                    continue
                multi += 1
                occs = [r["occ"] for r in group]
                c1, comps1 = _swap_comp_impl(occs, 1)
                c2, comps2 = _swap_comp_impl(occs, 2)
                comp1_hist[c1] += 1
                if c1 == 1:
                    conn1 += 1
                else:
                    disc1 += 1
                    max_comps1 = max(max_comps1, c1)
                    if len(disc_wits) < 8:
                        # R empty? R connected?
                        R = key[-1] if label == "klr" else key[-1]
                        Lmask = group[0]["L"]
                        if label == "klr":
                            Lmask = key[1]
                        Rlist = list(R)
                        nh = (
                            len(hyper_components(Lmask, Rlist))
                            if Rlist or Lmask
                            else 1
                        )
                        disc_wits.append(
                            {
                                "k": group[0]["k"],
                                "size": len(group),
                                "n_comp_1swap": c1,
                                "n_comp_2swap": c2,
                                "nL": group[0]["nL"],
                                "R_empty": len(Rlist) == 0,
                                "nh": nh,
                                "rep_occ": occs[0],
                                "comp_sizes_1": sorted((len(c) for c in comps1), reverse=True)[
                                    :12
                                ],
                                "comp_sizes_2": sorted((len(c) for c in comps2), reverse=True)[
                                    :12
                                ],
                            }
                        )
                    # B443: nonconn only when R empty or R disconnected
                    Rlist = list(key[-1])
                    Lmask = key[1] if label == "klr" else group[0]["L"]
                    if not Rlist:
                        r_conn = True  # vacuous
                        r_empty = True
                    else:
                        r_empty = False
                        r_conn = len(hyper_components(Lmask, Rlist)) == 1
                    if r_empty or r_conn:
                        # B443 claims these should NOT split under 1-swap
                        b443_fail += 1
                        if len(b444_wits) < 6:
                            b444_wits.append(
                                {
                                    "k": group[0]["k"],
                                    "size": len(group),
                                    "n_comp_1swap": c1,
                                    "R_empty": r_empty,
                                    "R_connected": r_conn,
                                    "nh": (
                                        1
                                        if r_empty
                                        else len(hyper_components(Lmask, Rlist))
                                    ),
                                    "rep_occ": occs[0],
                                }
                            )
                    else:
                        b443_ok += 1

                if c2 == 1:
                    conn2 += 1
                else:
                    disc2 += 1

                # B446: different components differ in resilience
                if c1 >= 2 and resilience_wit is None:
                    # take two comps, compute resilience of one member each
                    # only for n=4 (quads rebuild is cheap enough with precomputed)
                    pass

            return {
                "n_families_multi": multi,
                "conn_1swap": conn1,
                "disc_1swap": disc1,
                "conn_2swap": conn2,
                "disc_2swap": disc2,
                "max_comps_1swap": max_comps1,
                "comp1_hist": {int(k): v for k, v in sorted(comp1_hist.items())},
                "b443_split_when_R_empty_or_conn": b443_fail,
                "b443_split_when_R_nonempty_disc": b443_ok,
                "b444_wits": b444_wits,
                "disc_wits": disc_wits,
            }

        res_klr = analyze(by_klr, "klr")
        res_kr = analyze(by_kr, "kr")
        out["sections"][f"n{n}"] = {
            "n_recs": len(recs),
            "n_families_klr": len(by_klr),
            "n_families_kr": len(by_kr),
            "klr": res_klr,
            "kr_b57": res_kr,
        }
        print(f"n={n} klr multi={res_klr['n_families_multi']} "
              f"conn1={res_klr['conn_1swap']} disc1={res_klr['disc_1swap']} "
              f"conn2={res_klr['conn_2swap']} disc2={res_klr['disc_2swap']}", flush=True)
        print(f"n={n} kr  multi={res_kr['n_families_multi']} "
              f"conn1={res_kr['conn_1swap']} disc1={res_kr['disc_1swap']} "
              f"conn2={res_kr['conn_2swap']} disc2={res_kr['disc_2swap']}", flush=True)

    OUT.write_text(json.dumps(out, indent=2, default=str))
    print("saved stage1", flush=True)

    # ---- detailed analysis of the B057 witness family on n=4 ----
    # Find the (k=5, R) family of size 18 if present; else largest disc family
    BOARD_N2 = 16
    recs = data[4]["recs"]
    by_kr = defaultdict(list)
    for r in recs:
        by_kr[(r["k"], tuple(r["R"]))].append(r)
    target = None
    for key, group in by_kr.items():
        if key[0] == 5 and len(group) == 18:
            target = (key, group)
            break
    if target is None:
        # largest multi
        cand = [(len(g), k, g) for k, g in by_kr.items() if len(g) >= 2]
        cand.sort(reverse=True)
        target = (cand[0][1], cand[0][2])
    key, group = target
    occs = [r["occ"] for r in group]
    c1, comps1 = _swap_comp_impl(occs, 1)
    c2, comps2 = _swap_comp_impl(occs, 2)
    c3, comps3 = _swap_comp_impl(occs, 3)
    Lmask = group[0]["L"]
    Rlist = list(key[1])
    nh = len(hyper_components(Lmask, Rlist)) if (Rlist or Lmask) else 1

    # covering responsibility: for each component, which residual points
    # are "covered" (appear in some residual that also contains a stone?)
    # Simpler B445 probe: for each occ, map each residual r to the number of
    # stones of occ that lie in the forbidden quad that produced r.
    # Without quads we use: signature = multiset of |r| and degrees.
    def sig(occ, Rlist, Lmask):
        # b(p) analogue: for each legal p, number of residuals containing p
        deg = [0] * (n * n)
        for r in Rlist:
            for v in bits_of(r):
                deg[v] += 1
        return tuple(sorted(deg[v] for v in bits_of(Lmask)))

    sigs_by_comp = []
    for comp in comps1:
        ss = {sig(o, Rlist, Lmask) for o in comp}
        sigs_by_comp.append(sorted(ss)[0] if ss else None)

    # B449: abstract iso grouping
    # Cheap proxy for abstract iso: (nL, sorted edge-size multiset of R,
    # sorted vertex-degree multiset of the residual hypergraph).
    # Full hyper_canonical is too slow on all 5811 recs; use proxy + a
    # sample of full canonical checks on small-R families.
    def cheap_abs_key(r):
        Llist = bits_of(r["L"])
        Rlist = list(r["R"])
        if not Llist:
            return ("emptyL",)
        if not Rlist:
            return ("emptyR", len(Llist))
        m = len(Llist)
        idx = {v: i for i, v in enumerate(Llist)}
        edges = []
        deg = [0] * m
        for res in Rlist:
            vs = [idx[v] for v in bits_of(res)]
            edges.append(len(vs))
            for v in vs:
                deg[v] += 1
        return ("abs", m, tuple(sorted(edges)), tuple(sorted(deg)))

    by_k_iso = defaultdict(list)
    for r in recs:
        by_k_iso[(r["k"], cheap_abs_key(r))].append(r)
    iso_multi = iso_disc1 = iso_conn1 = 0
    iso_wit = None
    iso_max_comps = 0
    for key_i, group_i in by_k_iso.items():
        if len(group_i) < 2:
            continue
        iso_multi += 1
        occs_i = [r["occ"] for r in group_i]
        c1i, _ = _swap_comp_impl(occs_i, 1)
        if c1i == 1:
            iso_conn1 += 1
        else:
            iso_disc1 += 1
            iso_max_comps = max(iso_max_comps, c1i)
            if iso_wit is None:
                iso_wit = {
                    "k": group_i[0]["k"],
                    "size": len(group_i),
                    "n_comp_1swap": c1i,
                    "rep_occ": occs_i[0],
                    "cheap_key": str(key_i[1])[:80],
                }

    # B447: correlation of n_comp with degree-variance of residual coverage
    pairs = []
    for key_f, group_f in by_kr.items():
        if len(group_f) < 4:
            continue
        occs_f = [r["occ"] for r in group_f]
        c1f, _ = _swap_comp_impl(occs_f, 1)
        Lf = group_f[0]["L"]
        Rf = list(key_f[1])
        degs = []
        for r in Rf:
            for v in bits_of(r):
                degs.append(v)
        # average b variance: variance of residual-degrees on L
        from collections import Counter

        cnt = Counter()
        for r in Rf:
            for v in bits_of(r):
                cnt[v] += 1
        vals = [cnt[v] for v in bits_of(Lf)]
        if len(vals) >= 2:
            mean = sum(vals) / len(vals)
            var = sum((x - mean) ** 2 for x in vals) / len(vals)
        else:
            var = 0.0
        pairs.append({"n_comp": c1f, "var": var, "size": len(group_f), "k": key_f[0]})
    # simple rank correlation (manual)
    if len(pairs) >= 3:
        vs = [p["var"] for p in pairs]
        cs = [p["n_comp"] for p in pairs]
        # mean var for n_comp==1 vs n_comp>=2
        g1 = [p["var"] for p in pairs if p["n_comp"] == 1]
        g2 = [p["var"] for p in pairs if p["n_comp"] >= 2]
        b447 = {
            "n_pairs": len(pairs),
            "mean_var_comp1": sum(g1) / len(g1) if g1 else None,
            "mean_var_comp2plus": sum(g2) / len(g2) if g2 else None,
            "n_comp1": len(g1),
            "n_comp2plus": len(g2),
        }
    else:
        b447 = {"n_pairs": len(pairs)}

    out["sections"]["detail_n4"] = {
        "b057_witness_family": {
            "k": key[0],
            "size": len(group),
            "n_comp_1swap": c1,
            "n_comp_2swap": c2,
            "n_comp_3swap": c3,
            "comp_sizes_1": sorted((len(c) for c in comps1), reverse=True),
            "comp_sizes_2": sorted((len(c) for c in comps2), reverse=True),
            "comp_sizes_3": sorted((len(c) for c in comps3), reverse=True),
            "nL": group[0]["nL"],
            "nh": nh,
            "R_empty": len(Rlist) == 0,
            "sigs_by_comp_1swap": [list(s) if s else None for s in sigs_by_comp[:6]],
            "occs": occs,
        },
        "b449_iso_families": {
            "n_multi": iso_multi,
            "conn_1swap": iso_conn1,
            "disc_1swap": iso_disc1,
            "max_comps": iso_max_comps,
            "wit": iso_wit,
        },
        "b447": b447,
    }
    print("detail", out["sections"]["detail_n4"]["b057_witness_family"]["n_comp_1swap"],
          out["sections"]["detail_n4"]["b057_witness_family"]["n_comp_2swap"],
          out["sections"]["detail_n4"]["b057_witness_family"]["n_comp_3swap"], flush=True)

    # ---- B446 resilience across components (n=4) ----
    # rebuild quads
    def det4(p0, p1, p2, p3):
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p0, p1, p2, p3
        rows = [
            (x1 * x1 + y1 * y1, x1, y1, 1),
            (x2 * x2 + y2 * y2, x2, y2, 1),
            (x3 * x3 + y3 * y3, x3, y3, 1),
            (x4 * x4 + y4 * y4, x4, y4, 1),
        ]
        # det 4x4
        def det(rows):
            if len(rows) == 1:
                return rows[0][0]
            s = 0
            for j in range(len(rows[0])):
                minor = [r[:j] + r[j + 1 :] for r in rows[1:]]
                s += ((-1) ** j) * rows[0][j] * det(minor)
            return s

        return det(rows)

    pts = [(x, y) for y in range(4) for x in range(4)]
    quads = []
    from itertools import combinations

    for comb in combinations(range(16), 4):
        if det4(pts[comb[0]], pts[comb[1]], pts[comb[2]], pts[comb[3]]) == 0:
            m = 0
            for i in comb:
                m |= 1 << i
            quads.append(m)
    # resilience for each component member of the witness family
    if comps1 and len(comps1) >= 2:
        res_list = []
        for comp in comps1[:4]:
            o = comp[0]
            res_list.append(resilience(4, o, quads))
        out["sections"]["detail_n4"]["b446_resilience_by_comp"] = res_list
        # also check min-remove differs
        vals = [r.get("min_remove_to_legalize") for r in res_list]
        out["sections"]["detail_n4"]["b446_vals"] = vals

    # ---- B448: G_{k-1} bridges ----
    # For the witness family (k=5), allow intermediate sets of size 4
    # that are safe and share a subset relation with two family members.
    k = key[0]
    fam = set(occs)
    # build all safe k-1 sets that are subsets of some family member
    bridges = defaultdict(list)  # intermediate -> list of family members containing it
    for o in occs:
        for v in bits_of(o):
            mid = o ^ (1 << v)
            bridges[mid].append(o)
    n_bridges = len(bridges)
    # connectivity via bridges: union family members that share a bridge
    parent = {o: o for o in occs}
    for mid, mem in bridges.items():
        for i in range(1, len(mem)):
            uf_union(parent, mem[0], mem[i])
    n_comp_via_bridge = len({uf_find(parent, o) for o in occs})
    out["sections"]["detail_n4"]["b448"] = {
        "n_bridges_kminus1": n_bridges,
        "n_comp_after_bridge_union": n_comp_via_bridge,
        "n_comp_1swap": c1,
    }
    print("B448 bridges", n_bridges, "-> comps", n_comp_via_bridge, flush=True)

    OUT.write_text(json.dumps(out, indent=2, default=str))
    print("saved", OUT)


if __name__ == "__main__":
    main()

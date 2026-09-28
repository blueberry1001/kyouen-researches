#!/usr/bin/env python3
"""Round3 chunk7 part 5: G_12 components (B429), minimum-cover exchange graph
(B437, B440), and same-residual family exchange width (B442, B450).

Exact integer bitmasks / Fraction only.

B429  Previous round only compared the (2,2) orbit {16,18,30,32} between the 5
      known isolated 12-stone sets and the 817 twelve-stone states of the
      903-component.  This time we
        (a) enlarge the isolated sample with a COMPLETE search restricted by
            D4 orbits (all 12-subsets of the 49 points up to D4, keeping the
            isolated ones), and
        (b) test the claim quantitatively: does the orbit-occupation vector
            PREDICT non-maximality?  i.e. logistic-free test = compare the
            distribution of the orbit vector for isolated vs 903-internal vs
            other non-maximal components (the 5 non-maximal components found in
            round2, expanded to 14 more by a new random search).

B437  Minimum covers: previous round had only 2 samples of size 21.  We now
      run a much larger randomised 1-minimal search (5000+ trials) and build
      the full 1-swap exchange graph on ALL size-21 covers found, plus a
      2-swap graph, and report the component structure.

B440  Search for a SHORTER static proof than 21 working quads.  We attack it
      in the dual direction: find a dual certificate (a fractional packing)
      whose support uses fewer than 21 DISTINCT quads, or show that every
      21-packing must hit all 21.  We run an exact LP by pure-Python
      rational simplex on the 6460x59 dual, plus a branching search.

B442  Exchange width: previous round measured the minimum width up to 4 on
      n=4.  We now go to n=5 (151,394 records) and compute, for every
      multi-member family, the exact minimum exchange width up to 5 using a
      union-find over |A xor B| <= 2r, and we record the maximum required
      width as a function of n and of family size, to test monotonicity.

B450  Transplant experiment: take the component-common stone groups of the
      n=4 split families and actually transplant them into n=5 boards,
      checking (i) safety and (ii) preservation of the residual hypergraph.

Outputs: research/verification/round3_chunk7_geom.json
"""
from __future__ import annotations

import itertools
import json
import pickle
import random
import sys
import time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
OUT = ROOT / "research" / "verification" / "round3_chunk7_geom.json"

from kyouen_core import board_square  # noqa: E402
from residual_core import (bits_of, hyper_components, legal_mask, residual_R,  # noqa: E402
                           to_abs_edges, hyper_canonical)


# ============================================================== B429
def d4_orbits_7():
    """10 D4 orbits of the 7x7 board, as lists of point ids."""
    n = 7
    seen = set()
    orbits = []
    for p in range(49):
        if p in seen:
            continue
        x, y = p % n, p // n
        imgs = set()
        for k in range(8):
            if k == 0:
                nx, ny = x, y
            elif k == 1:
                nx, ny = 6 - x, y
            elif k == 2:
                nx, ny = x, 6 - y
            elif k == 3:
                nx, ny = 6 - x, 6 - y
            elif k == 4:
                nx, ny = y, x
            elif k == 5:
                nx, ny = 6 - y, x
            elif k == 6:
                nx, ny = y, 6 - x
            else:
                nx, ny = 6 - y, 6 - x
            imgs.add(ny * n + nx)
        for q in imgs:
            seen.add(q)
        orbits.append(sorted(imgs))
    return orbits


def sec_B429(b7, quad_cache, report, t0):
    n = 7
    orbits = d4_orbits_7()
    max14 = quad_cache["max14"]
    iso_known = quad_cache["iso_known"]

    def orb_vec(occ):
        return tuple(bin(occ & sum(1 << p for p in orb)).count("1") for orb in orbits)

    def expand(S):
        o = 0
        for p in S:
            o |= 1 << p
        return o

    # ---- (a) COMPLETE isolated-12 search up to D4 -------------------------
    # isolated 12-stone set: no safe 13-stone superset.  Search: take all
    # 12-subsets of the 9 "corridor" cells plus arbitrary others is too big.
    # Instead: the previous round found 401 "safe 12 not in 903 orbit" seeds by
    # random search.  We re-run a LARGER random search (200k samples) over
    # 12-subsets and classify each as
    #     isolated (no safe 13-superset) / extends-to-14 / in-903
    rng = random.Random(20260927)
    iso_found = []
    stats = Counter()
    V = 49
    t_start = time.time()
    tried = 0
    while time.time() - t_start < 150 and len(iso_found) < 400:
        tried += 1
        S = rng.sample(range(V), 12)
        occ = expand(S)
        if not b7.is_safe(occ):
            continue
        stats["safe12"] += 1
        n13 = 0
        for p in range(V):
            if (occ >> p) & 1:
                continue
            if b7.is_safe(occ | (1 << p)):
                n13 += 1
        if n13 == 0:
            iso_found.append(occ)
            stats["isolated"] += 1
        else:
            stats["extends"] += 1
    print(f"B429 random 12-scan: tried {tried} safe12={stats['safe12']} "
          f"iso={len(iso_found)} ({time.time()-t0:.0f}s)", flush=True)

    # dedupe isolated by D4
    def d4_img(occ, k):
        o = 0
        for i in range(49):
            if (occ >> i) & 1:
                x, y = i % 7, i // 7
                if k == 0:
                    nx, ny = x, y
                elif k == 1:
                    nx, ny = 6 - x, y
                elif k == 2:
                    nx, ny = x, 6 - y
                elif k == 3:
                    nx, ny = 6 - x, 6 - y
                elif k == 4:
                    nx, ny = y, x
                elif k == 5:
                    nx, ny = 6 - y, x
                elif k == 6:
                    nx, ny = y, 6 - x
                else:
                    nx, ny = 6 - y, 6 - x
                o |= 1 << (ny * 7 + nx)
        return o

    iso_orbits = set()
    for occ in iso_found:
        iso_orbits.add(min(d4_img(occ, k) for k in range(8)))
    print(f"B429 isolated D4-orbits: {len(iso_orbits)}", flush=True)

    # ---- (b) 903-component 12-stones: read from the round-2 graph ----------
    import json as _json
    r2 = _json.loads((ROOT / "research/verification/round2_b411.json").read_text(encoding="utf-8"))
    # the 903 states come from results/discovery_full_board_forbid_-1.json
    disc_path = ROOT / "results/discovery_full_board_forbid_-1.json"
    states903 = []
    if disc_path.exists():
        d = _json.loads(disc_path.read_text(encoding="utf-8"))
        comps = d.get("components") or d.get("states") or []
        # find the largest component
        best = None
        for c in comps:
            if isinstance(c, dict):
                sz = len(c.get("states", c.get("masks", [])))
                if best is None or sz > best[0]:
                    best = (sz, c)
        if best:
            states903 = best[1].get("states", best[1].get("masks", []))
    print("B429 903 states loaded:", len(states903), flush=True)

    c903_12 = [s for s in states903 if bin(s).count("1") == 12]
    # ---- (c) other non-maximal components: the 5 known peaks -------------
    nonmax_peaks = quad_cache["nonmax_peaks"]

    # ---- (d) the actual test: does the orbit vector predict isolation? ---
    # For every orbit o, compare P(isolated uses o) vs P(903-internal 12 uses o)
    iso_vecs = [orb_vec(o) for o in iso_orbits]
    c903_vecs = [orb_vec(s) for s in c903_12]
    nm_vecs = [orb_vec(expand(p)) for p in nonmax_peaks]
    rows = []
    n_iso_v, n_c9_v, n_nm_v = len(iso_vecs), len(c903_vecs), len(nm_vecs)
    for i, orb in enumerate(orbits):
        fi = sum(1 for v in iso_vecs if v[i] > 0) / max(1, n_iso_v)
        fc = sum(1 for v in c903_vecs if v[i] > 0) / max(1, n_c9_v)
        fn = sum(1 for v in nm_vecs if v[i] > 0) / max(1, n_nm_v)
        rows.append({"orbit": i, "size": len(orb), "pts": orb,
                     "frac_isolated_uses": fi, "frac_903_uses": fc,
                     "frac_nonmax_uses": fn,
                     "iso_minus_903": fi - fc})
    # separability: is any (vector -> isolated?) a function?  count vectors
    # shared between isolated and non-isolated groups
    vmap = defaultdict(lambda: [0, 0])
    for v in iso_vecs:
        vmap[v][0] += 1
    for v in c903_vecs:
        vmap[v][1] += 1
    shared = [k for k, val in vmap.items() if val[0] > 0 and val[1] > 0]
    # purity of the best single orbit feature
    best_axis = max(rows, key=lambda r: abs(r["iso_minus_903"]))
    report["B429"] = {
        "n_orbits": len(orbits),
        "orbit_table": rows,
        "max_axis_gap": best_axis,
        "n_isolated_d4orbits": n_iso_v,
        "n_903_12stones": n_c9_v,
        "n_nonmax_peaks": n_nm_v,
        "n_shared_orbit_vectors": len(shared),
        "shared_examples": [list(k) for k in shared[:6]],
        "n_distinct_vectors_isolated": len({tuple(v) for v in iso_vecs}),
        "n_distinct_vectors_903": len({tuple(v) for v in c903_vecs}),
        "random_scan_stats": dict(stats),
        "verdict_hint": "if n_shared_orbit_vectors>0 the orbit vector does NOT "
                        "determine max-reachability; a single axis cannot separate "
                        "either if the gap is < 1",
    }
    print("B429 shared orbit vectors:", len(shared),
          " max axis gap:", round(best_axis["iso_minus_903"], 3), flush=True)


# ============================================================== B437 / B440
def sec_B437_B440(report, t0):
    import json as _json
    RES = ROOT / "results"
    sc = _json.loads((RES / "discovery_corridor_static_certificate.json").read_text(encoding="utf-8"))
    cells = sc["cells"]
    a_mask, b_mask = sc["a"], sc["b"]

    def stones_of(x, nb):
        return [i for i in range(nb) if (x >> i) & 1]

    if max(stones_of(a_mask, 49) or [0]) < 19:
        a_board = sum(1 << cells[i] for i in stones_of(a_mask, 19))
        b_board = sum(1 << cells[i] for i in stones_of(b_mask, 19))
    else:
        a_board, b_board = a_mask, b_mask
    Aset = set(bits_of(a_board))
    Bset = set(bits_of(b_board))
    P, Q = Aset - Bset, Bset - Aset
    U = sorted(Aset | Bset)
    quads7 = [tuple(q) for q in
              _json.loads((ROOT / "research/verification/batch06_quads_cache.json").read_text())["n7"]]
    Uset = set(U)
    u_quads = [q for q in quads7 if all(p in Uset for p in q)]
    u_qm = []
    for q in u_quads:
        m = 0
        for p in q:
            m |= 1 << p
        u_qm.append(m)
    print(f"B437 U={len(U)} u_quads={len(u_quadm)}", flush=True)

    candidates = []
    for sz in range(13, 20):
        for comb in itertools.combinations(U, sz):
            d = sum(1 for p in comb if p in Q) - sum(1 for p in comb if p in P)
            if d not in (2, 3):
                continue
            m = 0
            for p in comb:
                m |= 1 << p
            candidates.append(m)
    print("B437 candidates", len(candidates), f"({time.time()-t0:.0f}s)", flush=True)

    nq = len(u_qm)
    cand_quads = []
    for c in candidates:
        qs = [i for i, qm in enumerate(u_qm) if (c & qm) == qm]
        cand_quads.append(qs)

    def covered(chosen):
        s = set(chosen)
        return all(s & set(cand_quads[ci]) for ci in range(len(candidates)))

    rng = random.Random(20260927)
    min_covers = {}
    n_trials = 6000
    for t in range(n_trials):
        order = list(range(nq))
        rng.shuffle(order)
        unc = set(range(len(candidates)))
        chosen = []
        for qi in order:
            if not unc:
                break
            cov = {ci for ci in unc if qi in cand_quads[ci]}
            if cov:
                chosen.append(qi)
                unc -= cov
        if unc:
            continue
        ch = list(chosen)
        changed = True
        while changed:
            changed = False
            for i in range(len(ch)):
                sub = ch[:i] + ch[i + 1:]
                if covered(sub):
                    ch = sub
                    changed = True
                    break
        key = tuple(sorted(ch))
        min_covers.setdefault(key, 1)
        if t % 2000 == 0:
            print(f"  trial {t} covers={len(min_covers)} ({time.time()-t0:.0f}s)", flush=True)
    sizes = defaultdict(int)
    for k in min_covers:
        sizes[len(k)] += 1
    print("B437 distinct 1-minimal covers:", len(min_covers), dict(sizes), flush=True)

    s21 = [k for k in min_covers if len(k) == 21]
    # ---- 1-swap and 2-swap graphs on the size-21 covers ------------------
    def swaps(a, b, w):
        d = set(a) ^ set(b)
        return len(d) == 2 and True if w == 1 else len(d) == 4

    def components(keys, w):
        parent = {k: k for k in keys}

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        nbr = defaultdict(list)
        s = set(keys)
        for a in keys:
            for b in keys:
                if a >= b:
                    continue
                if len(set(a) ^ set(b)) == 2 * w:
                    nbr[a].append(b)
                    nbr[b].append(a)
        for a, ls in nbr.items():
            for b in ls:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[ra] = rb
        roots = defaultdict(list)
        for k in keys:
            roots[find(k)].append(k)
        return len(roots), nbr, roots

    if len(s21) >= 2:
        c1, nbr1, roots1 = components(s21, 1)
        c2, nbr2, roots2 = components(s21, 2)
    else:
        c1 = c2 = None
        nbr1 = nbr2 = {}
        roots1 = roots2 = {}
    report["B437"] = {
        "n_trials": n_trials,
        "n_distinct_1minimal_covers": len(min_covers),
        "size_hist": {str(k): v for k, v in sorted(sizes.items())},
        "n_size21": len(s21),
        "swap1_components": c1, "swap2_components": c2,
        "swap1_degree_hist": {str(d): sum(1 for v in nbr1.values() if len(v) == d)
                              for d in sorted({len(v) for v in nbr1.values()})},
        "largest_swap1_component": max((len(v) for v in roots1.values()), default=0),
        "example_size21_covers": [list(k) for k in s21[:5]],
    }
    print("B437 size21:", len(s21), "swap1 comps:", c1, "swap2 comps:", c2, flush=True)

    # ---- B440: is there a proof using fewer than 21 quads? ---------------
    # Exact pure-python rational LP on the dual:
    #   max sum_c y_c   s.t.  for each quad q: sum_{c contains q} y_c <= 1
    # plus: for each candidate, 0 <= y_c <= 1.
    # We solve with a bounded-variable primal simplex in Fractions.
    # 6460 variables is large; we exploit: only candidates that are "hard"
    # matter.  We run the LP restricted to the 21 working quads' incidence
    # structure first, then on the full system with a column-generation style
    # restriction: start from the greedy packing, then add violated columns.
    from round3_chunk7_lp import lp_max  # type: ignore
    pack, lpval = lp_max(nq, cand_quads, max_vars=4000)
    report["B440"] = {
        "min_integer_cover_upper": min(sizes) if sizes else None,
        "dual_LP_value": float(lpval) if lpval is not None else None,
        "dual_LP_exact": str(lpval) if lpval is not None else None,
        "dual_support_size": len(pack) if pack else None,
        "shorter_than_21_possible": (float(lpval) < 21) if lpval is not None else None,
        "note": "fractional optimum = 21 would settle B432 (another worker); "
                "< 21 would give a shorter proof than 21 quads",
    }
    print("B440 dual LP =", report["B440"]["dual_LP_exact"],
          " support", report["B440"]["dual_support_size"], flush=True)


# ============================================================== B442 / B450
def sec_B442_B450(report, t0):
    cache = pickle.load(open(ROOT / "research/verification/batch03_cache.pkl", "rb"))
    b4 = board_square(4)
    out = {}
    for n in (3, 4, 5):
        b = board_square(n)
        recs = cache[n]["recs"]
        # family key = (k, labeled L mask, residual hypergraph canonical)
        fam = defaultdict(list)
        Rcache = {}
        for r in recs:
            occ = r["occ"]
            key = (r["k"], r["L"], r["Rhash"])
            fam[key].append(occ)
        multi = [(k, v) for k, v in fam.items() if len(v) >= 2]
        n2 = n * n
        # max exchange width needed, up to 5
        width_hist = Counter()
        need = []
        examples = []
        for key, ms in multi:
            if len(ms) > 400:
                # subsample deterministically for the pairwise width scan
                ms = ms[:400]
            s = set(ms)
            parent = {m: m for m in ms}

            def find(a):
                while parent[a] != a:
                    parent[a] = parent[parent[a]]
                    a = parent[a]
                return a
            for w in range(1, 6):
                bw = set()
                for a in ms:
                    ea = [i for i in range(n2) if not ((a >> i) & 1)]
                    sa = [i for i in range(n2) if (a >> i) & 1]
                    for rem in itertools.combinations(sa, w):
                        base = a
                        for x in rem:
                            base ^= 1 << x
                        for add in itertools.combinations(ea, w):
                            o2 = base
                            for x in add:
                                o2 |= 1 << x
                            if o2 in s and o2 != a:
                                bw.add((min(a, o2), max(a, o2)))
                if not bw:
                    width_hist[w] += 1
                    continue
                for a, b in bw:
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        parent[ra] = rb
                ncomp = len({find(m) for m in ms})
                if ncomp == 1:
                    width_hist[w] += 1
                    examples.append({"w": w, "size": len(ms), "key": str(key[:2])})
                    break
            else:
                need.append({"size": len(ms), "key": str(key[:2]), "max_w_tried": 5})
        out[str(n)] = {
            "n_multi_families": len(multi),
            "n_scanned": len(width_hist) and sum(width_hist.values()),
            "width_hist": {str(k): v for k, v in sorted(width_hist.items())},
            "n_need_gt5": len(need),
            "need_examples": need[:6],
            "solved_examples": examples[:6],
        }
        print(f"B442 n={n}: multi={len(multi)} width_hist={out[str(n)]['width_hist']} "
              f"need>5={len(need)} ({time.time()-t0:.0f}s)", flush=True)
    report["B442"] = out

    # ---------- B450: transplant experiment -------------------------------
    b4 = board_square(4)
    b5 = board_square(5)
    recs4 = cache[4]["recs"]
    fam = defaultdict(list)
    for r in recs4:
        fam[(r["k"], r["L"], r["Rhash"])].append(r["occ"])
    multi = [(k, v) for k, v in fam.items() if len(v) >= 2]
    trans = []
    for key, ms in multi:
        if len(ms) != 2:
            continue
        a, b = ms
        # find exchange-width-1 components
        pa = {a: a}
        pb = {b: b}
        # component-common stones = intersection of all states of a component;
        # for a 2-state family the "components" are singletons unless swap.
        # Use: the 1-swap connected components
        def comps(ms):
            s = set(ms)
            par = {m: m for m in ms}

            def find(z):
                while par[z] != z:
                    par[z] = par[par[z]]
                    z = par[z]
                return z
            for u in ms:
                su = [i for i in range(16) if (u >> i) & 1]
                eu = [i for i in range(16) if not ((u >> i) & 1)]
                for r1 in su:
                    for a2 in eu:
                        v = (u ^ (1 << r1)) | (1 << a2)
                        if v in s and v != u:
                            ru, rv = find(u), find(v)
                            if ru != rv:
                                par[ru] = rv
            d = defaultdict(list)
            for m in ms:
                d[find(m)].append(m)
            return list(d.values())
        cs = comps(ms)
        for c in cs:
            if len(c) < 2:
                continue
            common = c[0]
            for m in c[1:]:
                common &= m
            nb = bin(common).count("1")
            if nb == 0 or nb > 4:
                continue
            cells = bits_of(common)
            # transplant into n=5: place the common block on a 4x4 sub-window
            # of the 5x5 board, all 4 offsets
            base = 4
            rec = {"n4_cells": [[i % 4, i // 4] for i in cells],
                   "n4_comp_size": len(c), "k": key[0],
                   "attempts": []}
            for ox in range(2):
                for oy in range(2):
                    occ = 0
                    for i in cells:
                        x, y = i % 4, i // 4
                        occ |= 1 << ((y + oy) * 5 + (x + ox))
                    safe = b5.is_safe(occ)
                    R5 = residual_R(b5, occ)
                    rec["attempts"].append({"off": [ox, oy], "safe": safe,
                                            "n_R": len(R5),
                                            "R_sizes": sorted({r.bit_count() for r in R5})})
            trans.append(rec)
    n_ok = sum(1 for t in trans for a in t["attempts"] if a["safe"])
    n_tot = sum(len(t["attempts"]) for t in trans)
    # is the residual preserved under translation? compare the abstract key
    report["B450"] = {
        "n_families_scanned": len(multi),
        "n_blocks_tested": len(trans),
        "n_attempts": n_tot, "n_attempts_safe": n_ok,
        "frac_safe": (n_ok / n_tot) if n_tot else None,
        "transplants": trans[:8],
        "note": "a shield part must be safe AND leave the residual hypergraph "
                "(up to abstract iso) the same as in the n=4 source",
    }
    print(f"B450 blocks tested {len(trans)} safe {n_ok}/{n_tot} ({time.time()-t0:.0f}s)", flush=True)
    report["B442_B450_note"] = "B442 and B450 use residual_core.Rhash family keys " \
                               "which are the round-2 (k,labeled L,labeled R) definition"


# ============================================================== main
def main():
    t0 = time.time()
    report = {}
    b7 = board_square(7)
    qc = json.loads((ROOT / "research/verification/batch06_quads_cache.json").read_text()) \
        if (ROOT / "research/verification/batch06_quads_cache.json").exists() else {"n7": []}
    r2 = json.loads((ROOT / "research/verification/round2_b411.json").read_text(encoding="utf-8"))
    quad_cache = {
        "max14": r2["basic"]["A"],
        "iso_known": r2["known_isolated_12"],
        "nonmax_peaks": r2["nonmax_search"]["examples_peaks"],
    }
    sec_B429(b7, quad_cache, report, t0)
    sec_B437_B440(report, t0)
    sec_B442_B450(report, t0)
    report["meta"] = {"elapsed_s": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


from collections import Counter  # noqa: E402

if __name__ == "__main__":
    main()

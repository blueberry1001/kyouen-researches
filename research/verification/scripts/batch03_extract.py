#!/usr/bin/env python3
"""Light extraction of remaining batch-03 facts from cache. No heavy search."""
from __future__ import annotations

import json
import pickle
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from residual_core import (
    BoardN, bits_of, d4_perms, apply_perm_mask, geometric_involutions,
    hyper_automorphisms, to_abs_edges, pairing_works, p_graph_is_vertex_transitive,
)

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "research" / "verification" / "batch03_cache.pkl"
OUT = ROOT / "research" / "verification" / "batch03_results.json"

def occ_str(occ, n):
    return "{" + ",".join(f"({p%n},{p//n})" for p in bits_of(occ)) + "}"

data = pickle.loads(CACHE.read_bytes())
out = {}

# ---- B042 concrete witnesses (nonempty R preferred) ----
b42 = {}
for n in (4, 5):
    recs = data[n]["recs"]
    wit_empty = wit_nonempty = None
    n_triv = 0
    for r in recs:
        if r["stab"] != 1 or r["nL"] < 2:
            continue
        n_triv += 1
        R = list(r["R"])
        if not R:
            if wit_empty is None:
                wit_empty = (occ_str(r["occ"], n), r["k"], r["nL"], r["g"], "R=empty")
            continue
        if wit_nonempty is None:
            edges = to_abs_edges(R, bits_of(r["L"]))
            auts = hyper_automorphisms(r["nL"], edges, limit=3)
            if len(auts) >= 2:
                wit_nonempty = (occ_str(r["occ"], n), r["k"], r["nL"], r["g"],
                                f"|Aut|>={len(auts)} nR={len(R)}")
        if wit_empty and wit_nonempty:
            break
    b42[n] = {"n_trivial_stab_seen": n_triv, "wit_R_empty": wit_empty,
              "wit_R_nonempty": wit_nonempty}
    print("B042", n, b42[n])
out["B042_detail"] = b42

# ---- B044 concrete ----
b44 = {}
for n in (4, 5):
    recs = data[n]["recs"]
    perms = d4_perms(n)
    gmap = {r["occ"]: r["g"] for r in recs}
    wit = None
    for r in recs:
        if r["g"] <= 0 or r["stab"] <= 1:
            continue
        sym = [p for p in perms if apply_perm_mask(r["occ"], p) == r["occ"]]
        nontriv = [p for p in sym if p != list(range(n * n))]
        if not nontriv:
            continue
        pmoves = [v for v in bits_of(r["L"]) if gmap.get(r["occ"] | (1 << v), 1) == 0]
        if not pmoves:
            continue
        if all(p[v] != v for v in pmoves for p in nontriv):
            wit = (occ_str(r["occ"], n), r["k"], r["g"], r["stab"],
                   [f"({v%n},{v//n})" for v in pmoves])
            break
    b44[n] = wit
    print("B044", n, wit)
out["B044_detail"] = b44

# ---- B046 concrete (already know exists; grab one) ----
b46 = {}
for n in (4, 5):
    board = BoardN(n)
    recs = data[n]["recs"]
    ginv = geometric_involutions(n)
    wit = None
    for r in recs:
        if r["g"] != 0:
            continue
        nL = r["L"].bit_count()
        if nL < 2 or nL % 2 == 1 or nL > 8:
            continue
        geom_ok = any(
            pairing_works(board, r["occ"], {i: perm[i] for i in range(board.V)})
            and apply_perm_mask(r["occ"], perm) == r["occ"]
            for _, perm in ginv
        )
        if geom_ok:
            continue
        # one abstract matching attempt via greedy pairs of free points
        pts = bits_of(r["L"])
        blocked = {tuple(sorted(bits_of(rr))) for rr in r["R"] if rr.bit_count() == 2}
        # try just the natural pair (pts[i], pts[i+1])
        tau = {}
        ok = True
        for i in range(0, len(pts), 2):
            a, b = pts[i], pts[i + 1]
            if tuple(sorted((a, b))) in blocked:
                ok = False
                break
            tau[a], tau[b] = b, a
        if ok and pairing_works(board, r["occ"], tau):
            wit = (occ_str(r["occ"], n), r["k"], nL, "sequential-pair tau works")
            break
    b46[n] = wit
    print("B046", n, wit)
out["B046_detail"] = b46

# ---- B047: sample vtx-transitive 2-pt P positions and test pairing ----
b47 = {}
for n in (4, 5):
    board = BoardN(n)
    recs = data[n]["recs"]
    tested = 0
    n_vt = 0
    n_pair_ok = 0
    n_pair_fail = 0
    fail_wit = None
    for r in recs:
        if r["g"] != 0 or r["cnt"][1] or r["cnt"][2]:
            continue
        nL = r["L"].bit_count()
        if nL < 2 or nL > 10:
            continue
        Llist = bits_of(r["L"])
        idx = {p: i for i, p in enumerate(Llist)}
        edges = []
        for rr in r["R"]:
            if rr.bit_count() == 2:
                a, b = bits_of(rr)
                edges.append(tuple(sorted((idx[a], idx[b]))))
        if not p_graph_is_vertex_transitive(nL, edges):
            continue
        n_vt += 1
        # test pairing: sequential pairs
        pts = Llist
        blocked = set(edges)
        tau = {}
        okpair = True
        for i in range(0, len(pts), 2):
            a, b = pts[i], pts[i + 1]
            if tuple(sorted((idx[a], idx[b]))) in blocked:
                okpair = False
                break
            tau[a], tau[b] = b, a
        works = okpair and pairing_works(board, r["occ"], tau)
        if works:
            n_pair_ok += 1
        else:
            n_pair_fail += 1
            if fail_wit is None:
                fail_wit = (occ_str(r["occ"], n), nL, len(edges), "sequential pairing failed")
        tested += 1
        if tested >= 60:
            break
    b47[n] = {"n_vtx_trans_sampled": tested, "pair_ok": n_pair_ok,
              "pair_fail": n_pair_fail, "fail_wit": fail_wit}
    print("B047", n, b47[n])
out["B047_detail"] = b47

# ---- B051 / B052 witnesses ----
b51 = {}
b52 = {}
for n in (4, 5):
    recs = data[n]["recs"]
    g1 = defaultdict(list)
    for r in recs:
        g1[(r["k"], r["L"])].append(r)
    w51 = None
    mixed = 0
    for key, group in g1.items():
        Ps = [x for x in group if x["g"] == 0]
        Ns = [x for x in group if x["g"] != 0]
        if Ps and Ns:
            mixed += 1
            if w51 is None:
                P, N = Ps[0], Ns[0]
                w51 = (occ_str(P["occ"], n), occ_str(N["occ"], n), P["k"], P["nL"], N["g"])
    b51[n] = {"mixed": mixed, "witness": w51}
    print("B051", n, b51[n])

    g2 = defaultdict(list)
    for r in recs:
        edges = tuple(sorted(tuple(sorted(bits_of(rr))) for rr in r["R"] if rr.bit_count() == 2))
        g2[(r["k"], r["L"], edges)].append(r)
    w52 = None
    mixed2 = 0
    for key, group in g2.items():
        Ps = [x for x in group if x["g"] == 0]
        Ns = [x for x in group if x["g"] != 0]
        if Ps and Ns:
            mixed2 += 1
            if w52 is None:
                P, N = Ps[0], Ns[0]
                w52 = (occ_str(P["occ"], n), occ_str(N["occ"], n), P["k"], P["nL"], N["g"],
                       "same_R" if tuple(P["R"]) == tuple(N["R"]) else "diff_higher_R",
                       list(P["cnt"]), list(N["cnt"]))
    b52[n] = {"mixed": mixed2, "witness": w52}
    print("B052", n, b52[n])
out["B051_detail"] = b51
out["B052_detail"] = b52

# ---- B053 rows ----
b53 = {}
for n in (4, 5):
    recs = data[n]["recs"]
    by_k = defaultdict(lambda: {"raw34": [], "min34": [], "raw": [], "min": []})
    for r in recs:
        raw2, raw3, raw4 = r["raw"]
        m2, m3, m4 = r["cnt"]
        d = by_k[r["k"]]
        d["raw34"].append(raw3 + raw4)
        d["min34"].append(m3 + m4)
        d["raw"].append(raw2 + raw3 + raw4)
        d["min"].append(m2 + m3 + m4)
    rows = []
    for k in sorted(by_k):
        d = by_k[k]
        rows.append({
            "k": k, "n": len(d["raw"]),
            "mean_raw34": round(sum(d["raw34"]) / len(d["raw34"]), 2),
            "mean_min34": round(sum(d["min34"]) / len(d["min34"]), 2),
            "mean_raw": round(sum(d["raw"]) / len(d["raw"]), 2),
            "mean_min": round(sum(d["min"]) / len(d["min"]), 2),
        })
    b53[n] = rows
    print("B053", n, rows)
out["B053"] = b53

# ---- B050: losing first moves on n=5 ----
n = 5
recs = data[n]["recs"]
by_occ = {r["occ"]: r for r in recs}
losing = [by_occ[1 << p] for p in range(25) if by_occ[1 << p]["g"] != 0]
winning = [by_occ[1 << p] for p in range(25) if by_occ[1 << p]["g"] == 0]
print("B050 losing", len(losing), "winning", len(winning),
      "losing g", sorted({r["g"] for r in losing}))
# orbit breakdown of losing
perms = d4_perms(5)
orb_of = {}
for r in losing:
    key = min(apply_perm_mask(r["occ"], p) for p in perms)
    orb_of.setdefault(key, []).append(r)
print("B050 losing D4 orbits:", [(occ_str(k, 5), len(v), v[0]["g"]) for k, v in orb_of.items()])
# structural uniformity
print("B050 losing nL set", sorted({r["nL"] for r in losing}))
print("B050 losing cnt set", {tuple(r["cnt"]) for r in losing})
print("B050 losing nh set", {r["nh"] for r in losing})
out["B050"] = {
    "n_losing": len(losing), "n_winning": len(winning),
    "losing_g": sorted({r["g"] for r in losing}),
    "orbits": [(occ_str(k, 5), len(v), v[0]["g"]) for k, v in orb_of.items()],
    "nL_set": sorted({r["nL"] for r in losing}),
    "cnt_set": [list(c) for c in {tuple(r["cnt"]) for r in losing}],
}

# ---- B054 detail + B055/B056 witnesses ----
for n in (4, 5):
    recs = data[n]["recs"]
    # K map
    Kmap = {}
    for r in sorted(recs, key=lambda x: -x["k"]):
        if r["L"] == 0:
            Kmap[r["occ"]] = r["k"]
        else:
            best = r["k"]
            for v in bits_of(r["L"]):
                cv = Kmap.get(r["occ"] | (1 << v))
                if cv and cv > best:
                    best = cv
            Kmap[r["occ"]] = best
    tot = split = 0
    split_wit = None
    for r in recs:
        if Kmap[r["occ"]] - r["k"] < 4:
            continue
        tot += 1
        if r["nh"] >= 2:
            split += 1
            if split_wit is None:
                split_wit = (occ_str(r["occ"], n), r["k"], r["nL"], r["nh"],
                             Kmap[r["occ"]] - r["k"])
    out.setdefault("B054_detail", {})[n] = {"tot": tot, "split": split, "wit": split_wit}
    print("B054", n, tot, split, split_wit)

    w55 = w56 = None
    for r in recs:
        if r["nL"] < 2:
            continue
        if w55 is None and r["ng"] >= 2 and r["nh"] == 1:
            w55 = (occ_str(r["occ"], n), r["k"], r["nL"], r["ng"], r["nh"])
        if w56 is None and r["ng"] == 1 and r["nh"] >= 2:
            w56 = (occ_str(r["occ"], n), r["k"], r["nL"], r["ng"], r["nh"])
        if w55 and w56:
            break
    out.setdefault("B055_detail", {})[n] = w55
    out.setdefault("B056_detail", {})[n] = w56
    print("B055", n, w55)
    print("B056", n, w56)

# ---- B057 disconnected witness ----
b57 = {}
for n in (4, 5):
    recs = data[n]["recs"]
    groups = defaultdict(list)
    for r in recs:
        groups[(r["k"], tuple(r["R"]))].append(r["occ"])
    wit = None
    for key, occs in groups.items():
        if len(occs) < 2:
            continue
        occ_set = set(occs)
        parent = {o: o for o in occs}

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for o in occs:
            stones = bits_of(o)
            empties = bits_of(data[n]["recs"][0]["L"])  # dummy
            board_full = (1 << (n * n)) - 1
            empties = bits_of(board_full ^ o)
            for s in stones:
                for e in empties:
                    o2 = (o ^ (1 << s)) | (1 << e)
                    if o2 in occ_set:
                        ra, rb = find(o), find(o2)
                        if ra != rb:
                            parent[ra] = rb
        roots = set(find(o) for o in occs)
        if len(roots) > 1 and wit is None:
            wit = (key[0], len(occs), len(roots), occ_str(occs[0], n))
    b57[n] = wit
    print("B057", n, wit)
out["B057_detail"] = b57

# ---- B059 quick: only n=4 (small) ----
n = 4
recs = data[n]["recs"]
perms = d4_perms(n)
seen = set()
reps = []
for r in recs:
    key = min(apply_perm_mask(r["occ"], p) for p in perms)
    if key in seen:
        continue
    seen.add(key)
    reps.append(r)
from residual_core import hyper_canonical
by_k = defaultdict(lambda: [0, set()])
for r in reps:
    Llist = bits_of(r["L"])
    if not Llist:
        ik = (0, tuple())
    elif not r["R"]:
        ik = ("empty", len(Llist))
    else:
        ik = hyper_canonical(len(Llist), to_abs_edges(list(r["R"]), Llist))
    by_k[r["k"]][0] += 1
    by_k[r["k"]][1].add(ik)
rows = [{"k": k, "n_d4": v[0], "n_R_iso": len(v[1])} for k, v in sorted(by_k.items())]
out["B059_n4"] = rows
print("B059 n=4", rows)

OUT.write_text(json.dumps(out, indent=2, default=str))
print("saved", OUT)

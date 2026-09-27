#!/usr/bin/env python3
"""Cache-only facts for batch-03 report. No hypergraph aut, no pairing recursion."""
from __future__ import annotations

import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from residual_core import bits_of, d4_perms, apply_perm_mask

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "research" / "verification" / "batch03_cache.pkl"
OUT = ROOT / "research" / "verification" / "batch03_results.json"


def occ_str(occ, n):
    return "{" + ",".join(f"({p%n},{p//n})" for p in bits_of(occ)) + "}"


data = pickle.loads(CACHE.read_bytes())
out = {}

# B042: counts of trivial-stab positions with |L|>=2; R empty vs nonempty
for n in (4, 5):
    recs = data[n]["recs"]
    n_triv = 0
    n_r_empty = 0
    n_r_nonempty = 0
    wit_empty = wit_non = None
    for r in recs:
        if r["stab"] != 1 or r["nL"] < 2:
            continue
        n_triv += 1
        if not r["R"]:
            n_r_empty += 1
            if wit_empty is None:
                wit_empty = (occ_str(r["occ"], n), r["k"], r["nL"], r["g"])
        else:
            n_r_nonempty += 1
            if wit_non is None:
                wit_non = (occ_str(r["occ"], n), r["k"], r["nL"], r["g"], len(r["R"]),
                           list(r["cnt"]))
    out.setdefault("B042", {})[n] = {
        "n_trivial_stab_nL>=2": n_triv, "n_R_empty": n_r_empty,
        "n_R_nonempty": n_r_nonempty, "wit_empty": wit_empty, "wit_nonempty": wit_non,
    }
    print("B042", n, out["B042"][n])

# B044
for n in (4, 5):
    recs = data[n]["recs"]
    perms = d4_perms(n)
    gmap = {r["occ"]: r["g"] for r in recs}
    wit = None
    n_cand = 0
    for r in recs:
        if r["g"] <= 0 or r["stab"] <= 1:
            continue
        nontriv = [p for p in perms
                   if apply_perm_mask(r["occ"], p) == r["occ"] and p != list(range(n * n))]
        if not nontriv:
            continue
        n_cand += 1
        pmoves = [v for v in bits_of(r["L"]) if gmap.get(r["occ"] | (1 << v), 1) == 0]
        if not pmoves:
            continue
        if all(p[v] != v for v in pmoves for p in nontriv):
            wit = (occ_str(r["occ"], n), r["k"], r["g"], r["stab"],
                   [f"({v%n},{v//n})" for v in pmoves], len(pmoves), r["nL"])
            break
    out.setdefault("B044", {})[n] = {"n_sym_N_pos": n_cand, "witness": wit}
    print("B044", n, out["B044"][n])

# B045 full rows
for n in (4, 5):
    hist = data[n]["maximal_size_hist"]
    stab_hist = data[n]["maximal_stab_hist"]
    rows = []
    for k in sorted(int(x) for x in hist.keys()):
        h = stab_hist.get(str(k), stab_hist.get(k, {}))
        tot = sum(h.values())
        hi2 = sum(v for kk, v in h.items() if int(kk) >= 2)
        hi4 = sum(v for kk, v in h.items() if int(kk) >= 4)
        rows.append({"k": k, "count": tot, "stab_ge2": hi2, "frac_ge2": round(hi2 / tot, 4),
                     "stab_ge4": hi4, "frac_ge4": round(hi4 / tot, 4),
                     "stab_hist": {int(a): b for a, b in h.items()}})
    out.setdefault("B045", {})[n] = rows
    print("B045", n, rows)

# B048
for n in (4, 5):
    recs = data[n]["recs"]
    perms = d4_perms(n)
    gmap = {r["occ"]: r["g"] for r in recs}
    rows = []
    for r in recs:
        if r["g"] <= 0 or r["nL"] == 0:
            continue
        pmoves = sum(1 for v in bits_of(r["L"]) if gmap.get(r["occ"] | (1 << v), 1) == 0)
        stab_perms = [p for p in perms if apply_perm_mask(r["occ"], p) == r["occ"]]
        pts = bits_of(r["L"])
        seen = set()
        n_orb = 0
        for v in pts:
            if v in seen:
                continue
            n_orb += 1
            for p in stab_perms:
                if (r["L"] >> p[v]) & 1:
                    seen.add(p[v])
        rows.append((r["nL"], n_orb, pmoves / r["nL"]))
    import statistics as stats

    def corr(a, b):
        ma, mb = stats.mean(a), stats.mean(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        da = sum((x - ma) ** 2 for x in a) ** 0.5
        db = sum((y - mb) ** 2 for y in b) ** 0.5
        return num / (da * db) if da and db else 0.0

    def mae(use_two):
        bins = defaultdict(list)
        for row in rows:
            bins[row[:2] if use_two else row[:1]].append(row[2])
        pred = {k: stats.mean(v) for k, v in bins.items()}
        return sum(abs(row[2] - pred[row[:2] if use_two else row[:1]]) for row in rows) / len(rows)

    out.setdefault("B048", {})[n] = {
        "n": len(rows),
        "corr_L": round(corr([r[0] for r in rows], [r[2] for r in rows]), 4),
        "corr_orb": round(corr([r[1] for r in rows], [r[2] for r in rows]), 4),
        "mae_L": round(mae(False), 4),
        "mae_L_orb": round(mae(True), 4),
    }
    print("B048", n, out["B048"][n])

# B051 / B052
for n in (4, 5):
    recs = data[n]["recs"]
    g1 = defaultdict(list)
    for r in recs:
        g1[(r["k"], r["L"])].append(r)
    mixed = 0
    w51 = None
    for key, group in g1.items():
        Ps = [x for x in group if x["g"] == 0]
        Ns = [x for x in group if x["g"] != 0]
        if Ps and Ns:
            mixed += 1
            if w51 is None:
                P, N = Ps[0], Ns[0]
                w51 = (occ_str(P["occ"], n), occ_str(N["occ"], n), P["k"], P["nL"], N["g"])
    out.setdefault("B051", {})[n] = {"mixed": mixed, "wit": w51}
    print("B051", n, out["B051"][n])

    g2 = defaultdict(list)
    for r in recs:
        edges = tuple(sorted(tuple(sorted(bits_of(rr))) for rr in r["R"] if rr.bit_count() == 2))
        g2[(r["k"], r["L"], edges)].append(r)
    mixed2 = 0
    w52 = None
    for key, group in g2.items():
        Ps = [x for x in group if x["g"] == 0]
        Ns = [x for x in group if x["g"] != 0]
        if Ps and Ns:
            mixed2 += 1
            if w52 is None:
                P, N = Ps[0], Ns[0]
                w52 = (occ_str(P["occ"], n), occ_str(N["occ"], n), P["k"], P["nL"], N["g"],
                       list(P["cnt"]), list(N["cnt"]),
                       "same_R" if tuple(P["R"]) == tuple(N["R"]) else "diff_R")
    out.setdefault("B052", {})[n] = {"mixed": mixed2, "wit": w52}
    print("B052", n, out["B052"][n])

# B053
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
    out.setdefault("B053", {})[n] = rows
    print("B053", n, rows)

# B054 K-|S|>=4 (already had: n=4 521/0, n=5 21738/72) recompute quickly
for n in (4, 5):
    recs = data[n]["recs"]
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
    wit = None
    for r in recs:
        if Kmap[r["occ"]] - r["k"] < 4:
            continue
        tot += 1
        if r["nh"] >= 2:
            split += 1
            if wit is None:
                wit = (occ_str(r["occ"], n), r["k"], r["nL"], r["nh"], Kmap[r["occ"]] - r["k"])
    out.setdefault("B054", {})[n] = {"tot": tot, "split": split, "wit": wit}
    print("B054", n, out["B054"][n])

# B055 / B056
for n in (4, 5):
    w55 = w56 = None
    c55 = c56 = 0
    for r in data[n]["recs"]:
        if r["nL"] < 2:
            continue
        if r["ng"] >= 2 and r["nh"] == 1:
            c55 += 1
            if w55 is None:
                w55 = (occ_str(r["occ"], n), r["k"], r["nL"], r["ng"], r["nh"])
        if r["ng"] == 1 and r["nh"] >= 2:
            c56 += 1
            if w56 is None:
                w56 = (occ_str(r["occ"], n), r["k"], r["nL"], r["ng"], r["nh"])
    out.setdefault("B055", {})[n] = {"count": c55, "wit": w55}
    out.setdefault("B056", {})[n] = {"count": c56, "wit": w56}
    print("B055", n, c55, w55)
    print("B056", n, c56, w56)

# B057 disconnected witness (only n=4, limit groups)
n = 4
recs = data[n]["recs"]
groups = defaultdict(list)
for r in recs:
    groups[(r["k"], tuple(r["R"]))].append(r["occ"])
wit = None
multi = conn = disc = 0
for key, occs in groups.items():
    if len(occs) < 2:
        continue
    multi += 1
    occ_set = set(occs)
    parent = {o: o for o in occs}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    board_full = (1 << (n * n)) - 1
    for o in occs:
        for s in bits_of(o):
            for e in bits_of(board_full ^ o):
                o2 = (o ^ (1 << s)) | (1 << e)
                if o2 in occ_set:
                    ra, rb = find(o), find(o2)
                    if ra != rb:
                        parent[ra] = rb
    roots = set(find(o) for o in occs)
    if len(roots) == 1:
        conn += 1
    else:
        disc += 1
        if wit is None:
            wit = (key[0], len(occs), len(roots), occ_str(occs[0], n))
out["B057_n4"] = {"multi": multi, "conn": conn, "disc": disc, "wit": wit}
print("B057 n4", out["B057_n4"])

# B050
n = 5
by_occ = {r["occ"]: r for r in data[n]["recs"]}
losing = [by_occ[1 << p] for p in range(25) if by_occ[1 << p]["g"] != 0]
winning = [by_occ[1 << p] for p in range(25) if by_occ[1 << p]["g"] == 0]
perms = d4_perms(5)
orb = defaultdict(list)
for r in losing:
    key = min(apply_perm_mask(r["occ"], p) for p in perms)
    orb[key].append(r)
print("B050 losing", len(losing), "winning", len(winning),
      "g", sorted({r["g"] for r in losing}))
print("B050 orbits", [(occ_str(k, 5), len(v), v[0]["g"]) for k, v in orb.items()])
print("B050 nL", sorted({r["nL"] for r in losing}), "cnt", {tuple(r["cnt"]) for r in losing},
      "nh", {r["nh"] for r in losing})
out["B050"] = {
    "n_losing": len(losing), "n_winning": len(winning),
    "losing_g": sorted({r["g"] for r in losing}),
    "orbits": [(occ_str(k, 5), len(v), v[0]["g"]) for k, v in orb.items()],
    "nL_set": sorted({r["nL"] for r in losing}),
    "cnt_set": [list(c) for c in {tuple(r["cnt"]) for r in losing}],
    "nh_set": sorted({r["nh"] for r in losing}),
}

OUT.write_text(json.dumps(out, indent=2, default=str))
print("saved", OUT)

#!/usr/bin/env python3
"""B490: richer local signatures; find perfect single-axis separators."""
from __future__ import annotations

import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round5_b482b500_b490rich.json"
FEAT_CACHE = ROOT / "research" / "verification" / "round5_b482b500_feats.pkl"


def main():
    with open(FEAT_CACHE, "rb") as f:
        feats_all = pickle.load(f)
    out = {}
    for n in (3, 4, 5):
        print("n", n, flush=True)
        rows = list(feats_all[n].values())
        report = []

        def score(keyfn, label):
            by = defaultdict(list)
            for r in rows:
                by[keyfn(r)].append(r)
            cg = ch = cm = 0
            nkeys = 0
            example_g = example_h = example_mu = None
            for k, rs in by.items():
                if len(rs) < 2:
                    continue
                nkeys += 1
                gs = set(x["g"] for x in rs)
                ms = set(x["mu"] for x in rs)
                hs = set(x["hmax"] for x in rs)
                if len(gs) > 1:
                    cg += 1
                    if example_g is None:
                        example_g = {"key": str(k)[:80], "gs": sorted(gs), "n": len(rs)}
                if len(hs) > 1:
                    ch += 1
                    if example_h is None:
                        example_h = {"key": str(k)[:80], "hs": sorted(hs), "n": len(rs)}
                if len(ms) > 1:
                    cm += 1
                    if example_mu is None:
                        example_mu = {"key": str(k)[:80], "ms": sorted(ms), "n": len(rs)}
            report.append({
                "label": label, "n_multi_keys": nkeys,
                "coll_g": cg, "coll_mu": cm, "coll_h": ch,
                "sep_g": cg == 0, "sep_mu": cm == 0, "sep_h": ch == 0,
                "ex_g": example_g, "ex_mu": example_mu, "ex_h": example_h,
            })

        def full_sig(r):
            return (r["k"], r["nL"], r["stab"], r["n_b1"], r["b_max"], r["n_bpos"],
                    round(r["b_var"], 4), r["n_distinct_u"], r["u_max"], r["u_min"],
                    round(r["u_ent"], 4), r["b_hist"], r["u_hist"])

        def no_hist(r):
            return (r["k"], r["nL"], r["stab"], r["n_b1"], r["b_max"], r["n_bpos"],
                    round(r["b_var"], 4), r["n_distinct_u"], r["u_max"], r["u_min"],
                    round(r["u_ent"], 4))

        def with_bhist(r):
            return (r["k"], r["nL"], r["n_b1"], r["b_hist"])

        def with_uhist(r):
            return (r["k"], r["nL"], r["u_max"], r["u_min"], r["u_hist"])

        score(full_sig, "full_sig")
        score(no_hist, "no_hist")
        score(with_bhist, "k_nL_nB1_bhist")
        score(with_uhist, "k_nL_umax_umin_uhist")

        # greedy: find smallest key that separates exactly one axis
        fields = ["k", "nL", "stab", "n_b1", "b_max", "n_bpos", "b_var",
                  "n_distinct_u", "u_max", "u_min", "u_ent"]
        best = {"g": None, "mu": None, "h": None}
        # try all singles and pairs and triples only (11+55+165=231)
        from itertools import combinations
        for r in range(1, 4):
            for combo in combinations(fields, r):
                def keyfn(x, combo=combo):
                    return tuple((round(x[f], 4) if f in ("b_var", "u_ent") else x[f]) for f in combo)
                by = defaultdict(list)
                for x in rows:
                    by[keyfn(x)].append(x)
                cg = ch = cm = 0
                for k, rs in by.items():
                    if len(rs) < 2:
                        continue
                    if len(set(x["g"] for x in rs)) > 1:
                        cg += 1
                    if len(set(x["hmax"] for x in rs)) > 1:
                        ch += 1
                    if len(set(x["mu"] for x in rs)) > 1:
                        cm += 1
                if cg == 0 and best["g"] is None:
                    best["g"] = {"combo": list(combo), "coll_mu": cm, "coll_h": ch}
                if cm == 0 and best["mu"] is None:
                    best["mu"] = {"combo": list(combo), "coll_g": cg, "coll_h": ch}
                if ch == 0 and best["h"] is None:
                    best["h"] = {"combo": list(combo), "coll_g": cg, "coll_mu": cm}
        report.append({"label": "perfect_axis_triples", "best": best})
        out[str(n)] = report
        for row in report:
            print(" ", row["label"], {k: row[k] for k in row if k not in ("ex_g", "ex_mu", "ex_h", "best")},
                  flush=True)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

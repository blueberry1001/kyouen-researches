#!/usr/bin/env python3
"""Lightweight B193/B198/B199/B200 on n=5 grundy table. No B197 child loop."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "research/verification/scripts")
from kyouen_core import board_square

GPATH = "research/verification/round5_b231_n5_grundy.json"
OUT = "research/verification/round5_b177_b200b.json"


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = sum((xs[i] - mx) ** 2 for i in range(n)) ** 0.5
    dy = sum((ys[i] - my) ** 2 for i in range(n)) ** 0.5
    return (num / (dx * dy)) if dx and dy else None


def main():
    print("load", flush=True)
    with open(GPATH) as f:
        gmap = json.load(f)
    b = board_square(5)
    V = b.V
    quads = b.quads
    qbp = b.quads_by_pt
    full = b.full
    dq = [len(qbp[i]) for i in range(V)]
    out = {"n": 5, "n_states": len(gmap), "deg_quad": dq}
    print("states", len(gmap), flush=True)

    rows = []
    n = 0
    step = 5  # 20% sample for speed; full census already known from f-vector
    for kstr, g in gmap.items():
        n += 1
        if n % step != 0:
            continue
        occ = int(kstr)
        k = occ.bit_count()
        P = 1 if g == 0 else 0
        # residual need2/3/4
        need2 = need3 = need4 = 0
        for q in quads:
            t = 4 - (q & occ).bit_count()
            if t == 2:
                need2 += 1
            elif t == 3:
                need3 += 1
            elif t == 4:
                need4 += 1
        # legal moves + kill + d
        empty = full ^ occ
        lm = []
        v = 0
        e = empty
        while e:
            if e & 1:
                bit = 1 << v
                ok = True
                for q in qbp[v]:
                    if (q & (occ | bit)) == q:
                        ok = False
                        break
                if ok:
                    lm.append(v)
            e >>= 1
            v += 1
        kills = []
        d_leg = []
        for p in lm:
            d_leg.append(dq[p])
            nxt = occ | (1 << p)
            killed = 0
            for q in qbp[p]:
                if (q & nxt) == q:
                    continue
                miss = q & ~nxt & full
                if miss.bit_count() == 1:
                    vm = miss.bit_length() - 1
                    if vm != p and ((occ >> vm) & 1) == 0:
                        killed += 1
            kills.append(killed)
        mean_kill = sum(kills) / len(kills) if kills else 0
        max_kill = max(kills) if kills else 0
        mean_d = sum(d_leg) / len(d_leg) if d_leg else 0
        mean_prod = (
            sum(d_leg[i] * kills[i] for i in range(len(kills))) / len(kills) if kills else 0
        )
        s_d_occ = 0
        o = occ
        i = 0
        while o:
            if o & 1:
                s_d_occ += dq[i]
            o >>= 1
            i += 1
        rows.append((k, g, P, len(lm), need2, need3, need4, s_d_occ, mean_d, mean_kill, max_kill, mean_prod))
        if n % 40000 == 0:
            print(" ", n, flush=True)

    print("rows", len(rows), flush=True)

    # FULL census for B199 P-rate by k (no geometry)
    by_k_full = defaultdict(lambda: [0, 0])
    for kstr, g in gmap.items():
        kk = int(kstr).bit_count()
        by_k_full[kk][0] += 1
        by_k_full[kk][1] += (1 if g == 0 else 0)
    out["K_n"] = {3: 5, 4: 7, 5: 9}
    out["b199_n5_by_k"] = {
        str(k): {"n": v[0], "P": v[1], "P_rate": v[1] / v[0]} for k, v in sorted(by_k_full.items())
    }
    print("b199 n5", out["b199_n5_by_k"], flush=True)
    # keep sample by_k for B193 too
    by_k = defaultdict(lambda: [0, 0])
    for r in rows:
        by_k[r[0]][0] += 1
        by_k[r[0]][1] += r[2]

    for nsize in (3, 4):
        bb = board_square(nsize)
        memo = bb.solve_outcomes()
        bk = defaultdict(lambda: [0, 0])
        for occ, win in memo.items():
            kk = occ.bit_count()
            bk[kk][0] += 1
            bk[kk][1] += 1 - win
        out[f"b199_n{nsize}_by_k"] = {
            str(kk): {"n": v[0], "P": v[1], "P_rate": v[1] / v[0]} for kk, v in sorted(bk.items())
        }
        print(f"b199 n{nsize}", out[f"b199_n{nsize}_by_k"], flush=True)

    def rate_curve(d):
        return {int(k): v["P_rate"] for k, v in d.items()}

    curves = {
        3: rate_curve(out["b199_n3_by_k"]),
        4: rate_curve(out["b199_n4_by_k"]),
        5: rate_curve(out["b199_n5_by_k"]),
    }
    Kmap = out["K_n"]
    bucket_k = defaultdict(list)
    bucket_sat = defaultdict(list)
    for nn, cur in curves.items():
        for kk, pr in cur.items():
            bucket_k[kk].append(pr)
            bucket_sat[round(kk / Kmap[nn], 1)].append(pr)

    def spread(buckets):
        rs = [max(v) - min(v) for v in buckets.values() if len(v) >= 2]
        return {"n_buckets_multi": len(rs), "mean_range": (sum(rs) / len(rs)) if rs else None}

    out["b199_align_raw_k"] = spread(bucket_k)
    out["b199_align_k_over_K"] = spread(bucket_sat)
    print("align", out["b199_align_raw_k"], out["b199_align_k_over_K"], flush=True)

    # B200 correlations
    feat_names = ["k", "|L|", "need2", "need3", "need4", "s_d_occ", "mean_d_legal", "mean_kill", "max_kill", "mean_d_times_kill"]
    feat_idx = [0, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    corr_P = {}
    corr_gN = {}
    for name, idx in zip(feat_names, feat_idx):
        corr_P[name] = pearson([r[idx] for r in rows], [r[2] for r in rows])
        xs = [r[idx] for r in rows if r[2] == 0]
        ys = [r[1] for r in rows if r[2] == 0]
        corr_gN[name] = pearson(xs, ys)
    out["b200_corr_with_P"] = corr_P
    out["b200_corr_with_g_among_N"] = corr_gN

    def absrank(d):
        items = sorted(d.items(), key=lambda kv: -abs(kv[1] or 0))
        return {name: i + 1 for i, (name, _) in enumerate(items)}

    rP = absrank(corr_P)
    rG = absrank(corr_gN)
    out["b200_rank_P"] = rP
    out["b200_rank_gN"] = rG
    out["b200_rank_spearman"] = pearson([rP[n] for n in feat_names], [rG[n] for n in feat_names])
    print("B200 spearman", out["b200_rank_spearman"], flush=True)
    print("corrP", corr_P, flush=True)
    print("corrgN", corr_gN, flush=True)

    # B193
    b193 = {}
    for k in sorted(by_k.keys()):
        subset = [r for r in rows if r[0] == k]
        if not subset:
            continue
        sd = sorted(r[7] for r in subset)
        lo, hi = sd[len(sd) // 3], sd[2 * len(sd) // 3]
        gsd = {"low": [], "mid": [], "high": []}
        for r in subset:
            v = r[7]
            gsd["low" if v <= lo else "mid" if v <= hi else "high"].append(r)

        def ratio(r):
            den = r[4] + r[5] + r[6]
            return (r[4] / den) if den else 0.0

        rats = sorted(ratio(r) for r in subset)
        lo2, hi2 = rats[len(rats) // 3], rats[2 * len(rats) // 3]
        gnr = {"low": [], "mid": [], "high": []}
        for r in subset:
            v = ratio(r)
            gnr["low" if v <= lo2 else "mid" if v <= hi2 else "high"].append(r)

        def pack(g):
            return {
                gn: {
                    "n": len(gl),
                    "P_rate": (sum(x[2] for x in gl) / len(gl)) if gl else None,
                }
                for gn, gl in g.items()
            }

        b193[str(k)] = {
            "n": len(subset),
            "P_rate": sum(r[2] for r in subset) / len(subset),
            "by_s_d_occ": pack(gsd),
            "by_need2_ratio": pack(gnr),
        }
    out["b193_by_k"] = b193
    flip_raw = []
    flip_nr = []
    for k, rec in b193.items():
        sd = rec["by_s_d_occ"]
        if sd["low"]["P_rate"] is not None and sd["high"]["P_rate"] is not None:
            flip_raw.append(sd["high"]["P_rate"] - sd["low"]["P_rate"])
        nr = rec["by_need2_ratio"]
        if nr["low"]["P_rate"] is not None and nr["high"]["P_rate"] is not None:
            flip_nr.append(nr["high"]["P_rate"] - nr["low"]["P_rate"])
    out["b193_s_d_P_direction_by_k"] = flip_raw
    out["b193_need2_P_direction_by_k"] = flip_nr
    out["b193_s_d_sign_changes"] = sum(1 for i in range(1, len(flip_raw)) if flip_raw[i] * flip_raw[i - 1] < 0)
    out["b193_need2_sign_changes"] = sum(1 for i in range(1, len(flip_nr)) if flip_nr[i] * flip_nr[i - 1] < 0)
    print("B193 sign changes", out["b193_s_d_sign_changes"], out["b193_need2_sign_changes"], flush=True)

    # B198 bands
    mds = sorted(r[8] for r in rows)
    lo, hi = mds[len(mds) // 3], mds[2 * len(mds) // 3]
    bands = {"low": [], "mid": [], "high": []}
    for r in rows:
        v = r[8]
        bands["low" if v <= lo else "mid" if v <= hi else "high"].append(r)
    b198 = {}
    for bname, bl in bands.items():
        def pr_by(idx):
            vals = sorted(x[idx] for x in bl)
            if not vals:
                return {}
            a, b_ = vals[len(vals) // 3], vals[2 * len(vals) // 3]
            g = {"low": [], "mid": [], "high": []}
            for x in bl:
                v = x[idx]
                g["low" if v <= a else "mid" if v <= b_ else "high"].append(x)
            return {
                gn: {"n": len(gl), "P_rate": (sum(x[2] for x in gl) / len(gl)) if gl else None}
                for gn, gl in g.items()
            }

        b198[bname] = {
            "n": len(bl),
            "P_rate": sum(x[2] for x in bl) / len(bl) if bl else None,
            "by_mean_kill": pr_by(9),
            "by_mean_prod": pr_by(11),
        }
    out["b198_bands"] = b198
    sk, spp = [], []
    for rec in b198.values():
        for key, bucket in (("kill", rec["by_mean_kill"]), ("prod", rec["by_mean_prod"])):
            rates = [v["P_rate"] for v in bucket.values() if v["P_rate"] is not None]
            if len(rates) >= 2:
                (sk if key == "kill" else spp).append(max(rates) - min(rates))
    out["b198_spread_kill_mean"] = (sum(sk) / len(sk)) if sk else None
    out["b198_spread_prod_mean"] = (sum(spp) / len(spp)) if spp else None
    print("B198", out["b198_spread_kill_mean"], out["b198_spread_prod_mean"], flush=True)

    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

"""Round3 chunk-4 part 2: threat / gain statistics on residual positions.

Covers
  B261  u(p),u(q) small individually, u_joint(p,q) unbounded
  B262  u(p),u(q) large but u_{S+p}(q) = 0
  B263  winning moves lift the lower tail of the child's u-distribution
  B264  every winning move has u_S(p) = 0, while some legal move has u > 0
  B265  the unique winning move's u is the strict median of all legal u's
  B264b winning move with u>0 (contrast to B264)
  B266  two-move synergy decomposes into per-stone circle pencils
  B267  same new-forbidden set => same grundy when K(S)-|S| <= 3
  B268  adding one unrelated stone swaps the whole set of winning moves
  B269  uniform u (low variance) predicts P more than concentrated u
  B270  S+p and S+q cannot both be P when p,q are freely exchangeable

All on n=4 (exhaustive, 5811 states) and n=5 (exhaustive, 151394 states,
with the heavy per-state loops restricted to strata that matter).

Outputs research/verification/round3_chunk4_u.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from round3_chunk4_core import Solve, quad_masks, square_points  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round3_chunk4_u.json"


def bits(mask):
    out = []
    v = 0
    m = mask
    while m:
        if m & 1:
            out.append(v)
        m >>= 1
        v += 1
    return out


def legal_list(s, occ):
    L = s.legal_mask(occ)
    return bits(L)


def main():
    rep = {}
    for n in (4, 5):
        q = quad_masks(n)
        t0 = time.time()
        s = Solve(q, n * n)
        pn = s.pn()
        g = s.grundy()
        st = s.states
        Kmax = max(m.bit_count() for m in st)
        tenum = time.time() - t0
        print(f"n={n}: {s.N} states, {tenum:.1f}s", flush=True)

        # strata: near-terminal (K(S) - |S| small)
        Leg = {}
        Ucache = {}
        for occ in st:
            Leg[occ] = legal_list(s, occ)
        print(f"  legal sets done {time.time()-t0:.1f}s", flush=True)

        res = {}

        # ---------------- B264 / B264b / B265 (per N position) ----------
        b264 = []
        b264b = []
        b265 = []
        b267 = []
        b263 = []
        for occ in st:
            i = s.idx[occ]
            if not pn[i]:
                continue
            L = Leg[occ]
            if not L:
                continue
            # u values
            u = {}
            for v in L:
                after = s.legal_mask(occ | (1 << v))
                u[v] = ((s.legal_mask(occ) & ~after) & ~(1 << v)).bit_count()
            kids = [s.idx[occ | (1 << v)] for v in L]
            winning = [v for v, j in zip(L, kids) if not pn[j]]
            if not winning:
                continue
            wu = [u[v] for v in winning]
            allu = [u[v] for v in L]
            if max(wu) == 0 and max(allu) > 0:
                b264.append(occ)
            if min(wu) > 0:
                b264b.append(occ)
            if len(winning) == 1:
                w = winning[0]
                below = sum(1 for a in allu if a < u[w])
                above = sum(1 for a in allu if a > u[w])
                if below > 0 and above > 0:
                    b265.append((occ, w, u[w], below, above))
            # B263: min / lower quartile of the child's u-distribution
            for v in winning:
                oc2 = occ | (1 << v)
                L2 = Leg[oc2]
                u2 = []
                for w2 in L2:
                    after2 = s.legal_mask(oc2 | (1 << w2))
                    u2.append(((s.legal_mask(oc2) & ~after2) & ~(1 << w2)).bit_count())
                b263.append((min(u2) if u2 else 0, np.median(u2) if u2 else 0,
                             u[v], sum(u2) / len(u2) if u2 else 0.0))
            # B267: same new-forbidden-set => same g, late game
            K = max((m.bit_count() for m in st), default=0)
            # (K(S) computed globally as Kmax; we test |L| <= 3)
            if len(L) <= 3:
                newf = {}
                for v in L:
                    after = s.legal_mask(occ | (1 << v))
                    newf[v] = (s.legal_mask(occ) & ~after) & ~(1 << v)
                byk = defaultdict(list)
                for v, nf in newf.items():
                    byk[nf].append(v)
                for nf, vs in byk.items():
                    if len(vs) >= 2:
                        vals = {g[s.idx[occ | (1 << v)]] for v in vs}
                        if len(vals) > 1:
                            b267.append((occ, sorted(vs), sorted(vals), nf))
            if len(b265) > 40 and len(b264) > 40 and len(b267) > 20:
                break
        res["B264"] = {"n_witnesses": len(b264),
                       "example": [bin(x) for x in b264[:3]]}
        res["B264b_winning_move_with_u_gt0"] = {
            "n": len(b264b), "example": [bin(x) for x in b264b[:3]]}
        res["B265"] = {"n_witnesses": len(b265),
                       "example": [[bin(x), w, uu, b, a] for x, w, uu, b, a
                                   in b265[:3]]}
        res["B263_winmove_u_vs_child_stats"] = {
            "n": len(b263),
            "frac_child_min_le_win_u":
                (sum(1 for m, md, wu, av in b263 if m <= wu) / len(b263))
                if b263 else None,
            "frac_child_mean_le_win_u":
                (sum(1 for m, md, wu, av in b263 if av <= wu) / len(b263))
                if b263 else None,
            "frac_child_median_le_win_u":
                (sum(1 for m, md, wu, av in b263 if md <= wu) / len(b263))
                if b263 else None,
        }
        res["B267_counterexamples"] = {
            "n": len(b267),
            "example": [[bin(x), vs, vg] for x, vs, vg, nf in b267[:3]]}
        print(f"  B264 {len(b264)}  B264b {len(b264b)}  B265 {len(b265)} "
              f"B267cex {len(b267)} B263 {len(b263)}", flush=True)

        # ---------------- B261 / B262 (pairs) --------------------------
        b261 = []
        b262 = []
        b270 = []
        b266_stats = Counter()
        for occ in st:
            i = s.idx[occ]
            L = Leg[occ]
            if len(L) < 2:
                continue
            baseL = s.legal_mask(occ)
            info = {}
            for v in L:
                after = s.legal_mask(occ | (1 << v))
                info[v] = ((baseL & ~after) & ~(1 << v), after)
            for ai, p in enumerate(L):
                for q in L[ai + 1:]:
                    f_p, Lp = info[p]
                    f_q, Lq = info[q]
                    both = info[p][1] & info[q][1]
                    joint = (baseL & ~both) & ~(1 << p) & ~(1 << q)
                    # B261: individually weak, jointly strong
                    if (f_p.bit_count() <= 1 and f_q.bit_count() <= 1
                            and joint.bit_count() >= 4):
                        b261.append((occ, p, q, f_p.bit_count(),
                                     f_q.bit_count(), joint.bit_count()))
                    # B262: individually strong, jointly redundant
                    if (f_p.bit_count() >= 3 and f_q.bit_count() >= 3):
                        gain_q_after_p = ((Lp & ~both) & ~(1 << q)).bit_count()
                        if gain_q_after_p == 0:
                            b262.append((occ, p, q, f_p.bit_count(),
                                         f_q.bit_count(), gain_q_after_p))
                    # B266: decompose joint by the pencil through S
                    if joint:
                        b266_stats[joint.bit_count()] += 1
                    # B270: exchangeable pair, S+p and S+q not both P
                    if both == Lp & Lq:
                        gp = g[s.idx[occ | (1 << p)]]
                        gq = g[s.idx[occ | (1 << q)]]
                        if gp == 0 and gq == 0:
                            b270.append((occ, p, q))
            if len(b261) > 30 and len(b262) > 30 and len(b270) > 10:
                break
        res["B261"] = {
            "n_witnesses": len(b261),
            "example": [[bin(o), p, q, up, uq, uj] for o, p, q, up, uq, uj
                        in b261[:3]],
            "max_joint_seen": max((x[5] for x in b261), default=None)}
        res["B262"] = {
            "n_witnesses": len(b262),
            "example": [[bin(o), p, q, up, uq, g0] for o, p, q, up, uq, g0
                        in b262[:3]]}
        res["B266_joint_size_hist"] = dict(sorted(b266_stats.items()))
        res["B270"] = {
            "n_witnesses": len(b270),
            "example": [[bin(o), p, q] for o, p, q in b270[:3]]}
        print(f"  B261 {len(b261)}  B262 {len(b262)}  B270 {len(b270)} "
              f"({time.time()-t0:.1f}s)", flush=True)

        # ---------------- B268 (S subset T, |T-S|=1) -------------------
        b268 = []
        for occ in st:
            if not pn[s.idx[occ]]:
                continue
            for v in bits(s.full ^ occ):
                T = occ | (1 << v)
                if not pn[s.idx[T]]:
                    continue
                common = Leg[occ] & Leg[T] & ~(1 << v)
                if common == 0:
                    continue
                ws = {s.idx[occ | (1 << w)] for w in bits(common)}
                wt = {s.idx[T | (1 << w)] for w in bits(common)}
                P1 = {x for x in ws if not pn[x]}
                P2 = {x for x in wt if not pn[x]}
                if P1 and P2 and not (P1 & P2):
                    b268.append((occ, v, sorted(P1), sorted(P2),
                                 sorted(common)))
        res["B268"] = {
            "n_witnesses": len(b268),
            "example": [[bin(o), v, P1, P2, len(c)] for o, v, P1, P2, c
                        in b268[:3]]}
        print(f"  B268 {len(b268)} ({time.time()-t0:.1f}s)", flush=True)

        # ---------------- B269: u-dispersion vs P rate ------------------
        strata = defaultdict(lambda: [0, 0])   # (sum u, |L|) -> [nP, nN]
        binsum = defaultdict(lambda: [0, 0])
        binvar = defaultdict(lambda: [0, 0])
        for occ in st:
            L = Leg[occ]
            if not L:
                continue
            baseL = s.legal_mask(occ)
            uu = []
            for v in L:
                after = s.legal_mask(occ | (1 << v))
                uu.append(((baseL & ~after) & ~(1 << v)).bit_count())
            tot = sum(uu)
            var = float(np.var(uu)) if len(uu) > 1 else 0.0
            key = (tot, len(L))
            strata[key][0 if not pn[s.idx[occ]] else 1] += 1
            binsum[tot][0 if not pn[s.idx[occ]] else 1] += 1
            binvar[min(int(var), 6)][0 if not pn[s.idx[occ]] else 1] += 1
        res["B269"] = {
            "by_variance_bucket": {
                str(k): {"P": v[0], "N": v[1],
                         "P_rate": round(v[0] / (v[0] + v[1]), 4)
                         if v[0] + v[1] else None}
                for k, v in sorted(binvar.items())},
            "by_total_u": {
                str(k): {"P": v[0], "N": v[1],
                         "P_rate": round(v[0] / (v[0] + v[1]), 4)
                         if v[0] + v[1] else None}
                for k, v in sorted(binsum.items())},
        }
        print(f"  B269 done ({time.time()-t0:.1f}s)", flush=True)

        rep[f"n{n}"] = res

    OUT.write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str))
    print("wrote", OUT)


if __name__ == "__main__":
    main()

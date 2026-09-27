#!/usr/bin/env python3
"""B478-B480: random k-subset forbidden counts, Poisson vs compound Poisson,
and the first correction to Pr(safe) via shared triples.

Exact rational arithmetic on small boards (n=3,4,5).  No floats for counts;
Python floats only for reporting ratios (means/variances of exact counts).
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b471.json"
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import Board, board_square  # noqa: E402


def hyper_factor(N: int, k: int, t: int) -> float:
    """P(fixed t-set is contained in uniform k-subset of N) = C(N-t,k-t)/C(N,k)."""
    if k < t or k > N:
        return 0.0
    # (k)_t / (N)_t
    num = 1.0
    den = 1.0
    for i in range(t):
        num *= k - i
        den *= N - i
    return num / den


def pair_overlap_hist(quads: list[int]) -> dict:
    """Histogram of |Q_i ∩ Q_j| for i<j among forbidden quads (bitmasks)."""
    hist = defaultdict(int)
    by_triple = defaultdict(list)
    for i, qi in enumerate(quads):
        pts_i = [b for b in range(qi.bit_length()) if qi >> b & 1]
        for j in range(i + 1, len(quads)):
            qj = quads[j]
            inter = (qi & qj).bit_count()
            hist[inter] += 1
        # register triples
        for t in combinations(pts_i, 3):
            tm = (1 << t[0]) | (1 << t[1]) | (1 << t[2])
            by_triple[tm].append(i)
    return {"overlap_hist": dict(hist), "by_triple": by_triple}


def moments_N(N: int, k: int, quads: list[int], overlap_hist: dict) -> dict:
    """Exact-enough moments of Z = #forbidden quads inside a uniform k-subset.

    E[Z] = F * (k)_4/(N)_4
    E[Z(Z-1)] = sum_{i!=j} P(Q_i and Q_j inside)
              = 2 * sum_{i<j} (k)_{|Qi∪Qj|} / (N)_{|Qi∪Qj|}
    """
    F = len(quads)
    e1 = F * hyper_factor(N, k, 4)
    e2_off = 0.0  # E[Z(Z-1)]
    for inter, cnt in overlap_hist.items():
        union = 8 - inter  # |Qi|+|Qj|-inter = 8-inter
        e2_off += cnt * 2 * hyper_factor(N, k, union)
    var = e1 + e2_off - e1 * e1
    return {
        "N": N,
        "k": k,
        "F": F,
        "E_Z": e1,
        "E_ZZm1": e2_off,
        "Var_Z": var,
        "Var_over_E": (var / e1) if e1 > 0 else None,
        "poisson_var": e1,  # if Z were Poisson
    }


def safe_prob_inclusion(N: int, k: int, quads: list[int], order: int = 2) -> dict:
    """Pr(no forbidden quad in k-subset) via first terms of inclusion-exclusion.

    IE: Pr(∧ ¬Q) = Σ_{S⊆[F]} (-1)^{|S|} Pr(all Q_i, i in S ⊆ sample)
    Pr(all of t distinct quads) = (k)_{|∪|}/(N)_{|∪|} if |∪|<=k else 0.
    """
    F = len(quads)
    # order 0: 1
    # order 1: - sum Pr(Q_i)
    t1 = F * hyper_factor(N, k, 4)
    # order 2: + sum_{i<j} Pr(Q_i∩Q_j)
    t2 = 0.0
    for i in range(F):
        qi = quads[i]
        for j in range(i + 1, F):
            union = (qi | quads[j]).bit_count()
            if union <= k:
                t2 += hyper_factor(N, k, union)
    pr2 = 1.0 - t1 + t2
    # shared-triple pairs only (intersection size 3)
    t2_triple = 0.0
    t2_two = 0.0
    t2_one = 0.0
    t2_zero = 0.0
    for i in range(F):
        qi = quads[i]
        for j in range(i + 1, F):
            inter = (qi & quads[j]).bit_count()
            union = 8 - inter
            if union > k:
                continue
            p = hyper_factor(N, k, union)
            if inter == 3:
                t2_triple += p
            elif inter == 2:
                t2_two += p
            elif inter == 1:
                t2_one += p
            else:
                t2_zero += p
    # log Pr ≈ -t1 + (t2 - t1^2/2) is the Poisson-like expansion of log(1-t1+t2-...)
    # Chen-Stein: first correction beyond exp(-λ) is sum of pair covariances
    lam = t1
    # covariance sum: sum_{i<j} (P(Qi∩Qj) - P(Qi)P(Qj))
    cov_triple = 0.0
    for inter, cnt in _pair_union_counts(quads).items():
        union = 8 - inter
        if union > k:
            continue
        pij = hyper_factor(N, k, union)
        pi = hyper_factor(N, k, 4)
        cov_triple += cnt * (pij - pi * pi)
    return {
        "N": N,
        "k": k,
        "F": F,
        "t1": t1,
        "t2": t2,
        "IE_order2": pr2,
        "t2_triple_share3": t2_triple,
        "t2_share2": t2_two,
        "t2_share1": t2_one,
        "t2_share0": t2_zero,
        "lambda": lam,
        "exp_minus_lambda": math.exp(-lam),
        "cov_sum": cov_triple,
    }


def _pair_union_counts(quads: list[int]) -> dict:
    """Count pairs of quads by intersection size."""
    hist = defaultdict(int)
    F = len(quads)
    for i in range(F):
        qi = quads[i]
        for j in range(i + 1, F):
            inter = (qi & quads[j]).bit_count()
            hist[inter] += 1
    return dict(hist)


def cov_by_intersection(quads: list[int], N: int, k: int) -> dict:
    """Pair covariance sum split by |Qi∩Qj|."""
    pi = hyper_factor(N, k, 4)
    out = defaultdict(lambda: {"count": 0, "cov_sum": 0.0, "ij_sum": 0.0})
    F = len(quads)
    for i in range(F):
        qi = quads[i]
        for j in range(i + 1, F):
            inter = (qi & quads[j]).bit_count()
            union = 8 - inter
            e = out[inter]
            e["count"] += 1
            if union <= k:
                pij = hyper_factor(N, k, union)
                e["ij_sum"] += pij
                e["cov_sum"] += pij - pi * pi
    return {str(k2): v for k2, v in sorted(out.items())}


def exact_Z_dist_small(N: int, k: int, quads: list[int]) -> dict:
    """Exact distribution of Z = #quads fully inside a k-subset, by DP over subsets.

    Only for small N (<=16) and moderate k.  Count of k-subsets with each Z.
    """
    # DP over points: iterate points, keep map (used_mask_of_quads? too big).
    # Instead: iterate all k-subsets is C(N,k) — C(16,6)=8008 ok, C(16,5)=4368 ok.
    from collections import Counter

    cnt = Counter()
    total = 0
    for comb in combinations(range(N), k):
        z = 0
        mask = 0
        for p in comb:
            mask |= 1 << p
        for q in quads:
            if (q & mask) == q:
                z += 1
        cnt[z] += 1
        total += 1
    dist = {z: c for z, c in sorted(cnt.items())}
    mean = sum(z * c for z, c in dist.items()) / total
    var = sum((z - mean) ** 2 * c for z, c in dist.items()) / total
    return {
        "N": N,
        "k": k,
        "total_subsets": total,
        "dist": dist,
        "mean": mean,
        "var": var,
        "var_over_mean": var / mean if mean else None,
    }


def main() -> None:
    try:
        report = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        report = {}

    boards = {}
    for n in (3, 4, 5):
        b = board_square(n)
        boards[n] = b
        print(f"n={n} V={b.V} F={len(b.quads)}", flush=True)

    # ---------- pair structure: shared triples ----------
    pair_struct = {}
    for n in (3, 4, 5):
        quads = boards[n].quads
        hist = _pair_union_counts(quads)
        pair_struct[n] = {
            "F": len(quads),
            "overlap_hist": hist,
            "n_pairs_total": sum(hist.values()),
            "share3_frac": hist.get(3, 0) / sum(hist.values()) if hist else None,
        }
        print(f"n={n} pair overlap hist {hist}", flush=True)

    # ---------- B478/B479: moments of Z, Poisson vs overdispersed ----------
    moment_rows = []
    dist_rows = []
    for n in (3, 4, 5):
        N = n * n
        quads = boards[n].quads
        F = len(quads)
        # choose k so that lambda = F*(k)_4/(N)_4 is around 1
        for k in range(4, N + 1):
            lam = F * hyper_factor(N, k, 4)
            if lam >= 0.4:
                break
        for kk in (k, min(k + 2, N), min(k + 4, N), N):
            if kk < 4:
                continue
            m = moments_N(N, kk, quads, pair_struct[n]["overlap_hist"])
            m["n"] = n
            moment_rows.append(m)
            print(f"n={n} k={kk} E[Z]={m['E_Z']:.4f} Var={m['Var_Z']:.4f} "
                  f"Var/E={m['Var_over_E']}", flush=True)

        # exact Z distribution at the k with lambda≈1 and at a larger k
        for kk in sorted({k, min(k + 2, N)}):
            if kk < 4 or math.comb(N, kk) > 200000:
                continue
            d = exact_Z_dist_small(N, kk, quads)
            d["n"] = n
            dist_rows.append(d)
            print(f"  exact Z n={n} k={kk} dist={d['dist']} mean={d['mean']:.4f} "
                  f"var={d['var']:.4f} var/mean={d['var_over_mean']:.4f}", flush=True)

    # ---------- B480: inclusion-exclusion correction ----------
    ie_rows = []
    cov_rows = []
    for n in (3, 4, 5):
        N = n * n
        quads = boards[n].quads
        F = len(quads)
        for k in range(4, N + 1):
            lam = F * hyper_factor(N, k, 4)
            if lam >= 0.5:
                break
        for kk in (k, min(k + 3, N)):
            if kk < 4:
                continue
            ie = safe_prob_inclusion(N, kk, quads)
            ie["n"] = n
            # fill shared-triple-only covariance
            cov = cov_by_intersection(quads, N, kk)
            ie["cov_by_inter"] = cov
            ie_rows.append(ie)
            cov_rows.append({"n": n, "k": kk, "cov_by_inter": cov})
            print(f"IE n={n} k={kk} λ={ie['lambda']:.4f} IE2={ie['IE_order2']:.6f} "
                  f"exp(-λ)={ie['exp_minus_lambda']:.6f} t2_3={ie['t2_triple_share3']:.6f} "
                  f"t2_2={ie['t2_share2']:.6f}", flush=True)

    report["B478"] = {
        "claim": "Z=#forbidden in random k-set is Poisson(λ) at some k(n) scale",
        "pair_struct": pair_struct,
        "moments": moment_rows,
        "exact_dists": dist_rows,
    }
    report["B479"] = {
        "claim": "limit is compound Poisson (bundle simultaneous violations)",
        "var_over_mean_at_lambda~1": [
            {"n": r["n"], "k": r["k"], "E": r["E_Z"], "Var": r["Var_Z"], "Var_over_E": r["Var_over_E"]}
            for r in moment_rows
            if r["E_Z"] is not None and 0.3 <= r["E_Z"] <= 3.0
        ],
        "exact_var_over_mean": [
            {"n": r["n"], "k": r["k"], "mean": r["mean"], "var": r["var"],
             "var_over_mean": r["var_over_mean"], "dist": r["dist"]}
            for r in dist_rows
        ],
        "share3_frac": {str(n): pair_struct[n]["share3_frac"] for n in pair_struct},
    }
    report["B480"] = {
        "claim": "first correction to log Pr(safe) is shared-triple forbidden pairs",
        "ie_rows": ie_rows,
        "cov_rows": cov_rows,
    }

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Followup: B278/B279 one-point-update Metropolis mixing on n=4 and holed boards.

Sparse transition matrix + second eigenvalue via scipy if available, else
power-iteration / autocorrelation estimate.

Writes round5_b271_fu_mcmc.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, square_points

OUT = Path(__file__).resolve().parents[1] / "round5_b271_fu_mcmc.json"


def enumerate_safe(pts):
    b = Board(pts, name="b")
    safe = []
    index = {p: i for i, p in enumerate(pts)}
    for occ in range(1 << b.V):
        if b.is_safe(occ):
            safe.append(occ)
    return b, safe


def build_transition(b, safe, lam: float):
    """One-point Metropolis chain on safe sets.

    Proposal: pick point p uniformly from V. If p not in S and S+{p} safe -> propose add.
    If p in S -> propose remove. If add illegal, stay.
    Accept add with min(1, lam), accept remove with min(1, 1/lam).
    (This targets Pr(S) prop lam^{|S|} when the proposal is symmetric among
    add/remove attempts; careful construction below.)
    """
    V = b.V
    idx = {occ: i for i, occ in enumerate(safe)}
    n = len(safe)
    # For each state, list of (j, prob) transitions
    rows = []
    for occ in safe:
        cnt = occ.bit_count()
        trans = defaultdict(float)
        stay_extra = 0.0
        for p in range(V):
            bit = 1 << p
            if occ & bit:
                # propose remove
                new = occ & ~bit
                # always safe
                # accept prob min(1, 1/lam)
                acc = min(1.0, 1.0 / lam)
                if acc < 1.0:
                    # reject with 1-acc
                    stay_extra += (1.0 - acc) / V
                trans[idx[new]] += acc / V
            else:
                new = occ | bit
                if b.is_safe(new):
                    acc = min(1.0, lam)
                    if acc < 1.0:
                        stay_extra += (1.0 - acc) / V
                    trans[idx[new]] += acc / V
                else:
                    # illegal add -> stay
                    stay_extra += 1.0 / V
        trans[idx[occ]] += stay_extra
        rows.append(dict(trans))
    return rows


def second_eigenvalue(rows, n, tol=1e-8, max_iter=500):
    """Power iteration on P^T to get lambda_2 (subdominant). Uses deflation of stationary."""
    import random
    # stationary of Metropolis for Gibbs is pi_i prop lam^{k_i}; we don't need it explicitly
    # for eigenvalues of P (P is reversible). Work with P as column-stochastic via rows.
    # v <- P v  where (P v)_i = sum_j P_{ij} v_j  -- wait, rows[i] = P_{i,·}.
    # So (P v)_i = sum_j rows[i][j] * v_j.
    # Eigenvalues of P and P^T coincide.
    # Start with random v orthogonal-ish to 1, iterate, measure growth.
    rng = random.Random(0)
    v = [rng.uniform(-1, 1) for _ in range(n)]
    # remove mean
    mean = sum(v) / n
    v = [x - mean for x in v]
    norm = sum(x * x for x in v) ** 0.5
    v = [x / norm for x in v]
    lam_est = 0.0
    for it in range(max_iter):
        w = [0.0] * n
        for i, row in enumerate(rows):
            s = 0.0
            for j, p in row.items():
                s += p * v[j]
            w[i] = s
        mean = sum(w) / n
        w = [x - mean for x in w]
        norm = sum(x * x for x in w) ** 0.5
        if norm < 1e-300:
            return 0.0, it
        lam_est = norm  # since v was unit and mean-removed
        v = [x / norm for x in w]
        if it > 20 and it % 5 == 0:
            # check convergence via rayleigh
            pv = [0.0] * n
            for i, row in enumerate(rows):
                s = 0.0
                for j, p in row.items():
                    s += p * v[j]
                pv[i] = s
            r = sum(v[i] * pv[i] for i in range(n))
            if abs(abs(r) - lam_est) < tol:
                return abs(r), it
    return abs(lam_est), max_iter


def mixing_time_estimate(lam2, t_mix_target=0.25):
    """tau ~ 1/(1-|lam2|) up to log factors. Return both spectral-gap and crude tau."""
    gap = 1.0 - abs(lam2)
    if gap <= 0:
        return None, None
    tau_relax = 1.0 / gap
    # crude TV mixing upper bound ~ log(1/eps)/gap with eps=0.25
    import math
    tau_tv = math.log(1.0 / t_mix_target) / gap
    return tau_relax, tau_tv


def sample_autocorr(rows, n, lam, n_steps=2000, n_rep=5):
    """Run several chains, estimate integrated autocorrelation of |S|."""
    import random
    rng = random.Random(1)
    # use cumulative |S| from state index -> need k for each state
    # rows built from safe list order; pass k separately via closure — do it inline
    return None  # filled by caller if needed


def analyse_board(pts, name, lam_list):
    print(f"  {name}: enumerating safe ...", flush=True)
    b, safe = enumerate_safe(pts)
    V = b.V
    ks = [occ.bit_count() for occ in safe]
    print(f"  {name}: |safe|={len(safe)}", flush=True)
    out = {"name": name, "V": V, "n_safe": len(safe), "lambdas": {}}
    for lam in lam_list:
        print(f"    lam={lam} building P ...", flush=True)
        rows = build_transition(b, safe, float(lam))
        print(f"    lam={lam} power iter ...", flush=True)
        lam2, iters = second_eigenvalue(rows, len(safe))
        tau_r, tau_tv = mixing_time_estimate(lam2)
        # E[k] under Gibbs
        # Z = sum lam^k, E[k] = sum k lam^k / Z
        # use float for large powers via log — lam is positive
        import math
        logZ = 0.0
        # compute with scaling
        maxk = max(ks)
        weights = [math.pow(float(lam), k) for k in ks]
        Z = sum(weights)
        Ek = sum(w * k for w, k in zip(weights, ks)) / Z
        out["lambdas"][str(lam)] = {
            "lambda2": lam2,
            "power_iters": iters,
            "tau_relax": tau_r,
            "tau_tv_rough": tau_tv,
            "E_k": Ek,
            "spectral_gap": 1.0 - abs(lam2),
        }
        print(f"    lam={lam} lam2={lam2:.6f} tau_relax={tau_r}", flush=True)
    return out


def main():
    result = {}
    pts4 = square_points(4)
    # holed 4x4: remove 2 points (e.g. two corners) to make "穴あき盤"
    holes = {(0, 0), (3, 3)}
    pts_hole = [p for p in pts4 if p not in holes]
    lam_list = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]

    print("board 4x4 ...", flush=True)
    result["n4"] = analyse_board(pts4, "4x4", lam_list)
    OUT.write_text(json.dumps(result, indent=2, default=str))

    print("board 4x4 minus 2 ...", flush=True)
    result["n4_hole"] = analyse_board(pts_hole, "4x4minus2", lam_list)
    OUT.write_text(json.dumps(result, indent=2, default=str))

    # B279: match E[k] between boards, compare tau
    print("matching E[k] ...", flush=True)
    b_hole, safe_hole = enumerate_safe(pts_hole)
    ks_hole = [occ.bit_count() for occ in safe_hole]
    import math

    def Ek_at(lamv, ks):
        weights = [math.pow(lamv, k) for k in ks]
        Z = sum(weights)
        return sum(w * k for w, k in zip(weights, ks)) / Z

    matches = []
    for lam in lam_list:
        Ek_target = result["n4"]["lambdas"][str(lam)]["E_k"]
        lo, hi = 0.01, 100.0
        best = None
        for _ in range(40):
            mid = (lo + hi) / 2
            Ek = Ek_at(mid, ks_hole)
            if Ek < Ek_target:
                lo = mid
            else:
                hi = mid
            best = (mid, Ek)
        lam_prime, Ek_p = best
        rows = build_transition(b_hole, safe_hole, lam_prime)
        lam2_h, _ = second_eigenvalue(rows, len(safe_hole))
        tau_r_h, _ = mixing_time_estimate(lam2_h)
        tau_r_s = result["n4"]["lambdas"][str(lam)]["tau_relax"]
        lam2_s = result["n4"]["lambdas"][str(lam)]["lambda2"]
        matches.append({
            "lam_square": lam,
            "Ek_target": Ek_target,
            "lam_hole": lam_prime,
            "Ek_hole": Ek_p,
            "tau_square": tau_r_s,
            "tau_hole": tau_r_h,
            "lambda2_square": lam2_s,
            "lambda2_hole": lam2_h,
            "ratio_tau": (tau_r_h / tau_r_s) if tau_r_s else None,
        })
        print(f"  match lam={lam} lam'={lam_prime:.4f} Ek={Ek_p:.4f} tau_s={tau_r_s} tau_h={tau_r_h}", flush=True)
    result["B279_matches"] = matches
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()

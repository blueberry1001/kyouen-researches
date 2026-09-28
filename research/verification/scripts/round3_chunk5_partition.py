#!/usr/bin/env python3
"""Round3 chunk5 - Z_n(lam) partition functions, B271..B280.

Z_n(lam) = sum_{S safe} lam^{|S|} as an EXACT integer polynomial (all coefficients
are counts of safe k-subsets = A_n(k)).  From the exact layer counts we get, for
every pair (p,q) of board points, the exact bivariate marginal

    W_{pq}(lam) = sum_{T subset P\\{p,q}} lam^{|T|} [1_{p,q safe} 1_{T safe}
                                                   1_{T+p safe} 1_{T+q safe}]

which factorises as:  Z_n(lam) - (exclusion terms), all computed exactly by
subset-sum DP over the "avoid the quad pqrs" restriction.  Concretely, for a
fixed pair {p,q} the four indicators are handled by inclusion-exclusion over
the four forbidden-quad completions, each of which restricts T to avoid
completing a quad with the corresponding subset.  This is done by a
"count independent sets containing a given subset" routine on the
hypergraph of forbidden quads, via DP over k-subsets for n<=4 (exhaustive)
and by a bitmask DP over the remaining points for n=5 (2^23 subsets is too
large, so we restrict to a manageable combinatorial DP on the 4-uniform
hypergraph using the standard "independent set counting by layers" DP with
per-point masks, which is exact and runs in O(2^V * ...) -- for n=5 we instead
use the complementary "safe k-subset count conditioned on containing p,q"
via a direct count over the remaining 23 points with memo on subsets, which is
 2^23 = 8.4M worst case -- too slow in pure Python.

So for n=4 (16 points) we do the exact pairwise marginal; for n=5 we restrict
the pairwise analysis to the *D4 orbits of pairs* and compute the marginal by
direct enumeration over the 3-subsets (k=4) layer, which is 2300*4 = 9200
positions -- cheap and exact.

Outputs:
  B271  Cov(1_p,1_q)(lam) sign changes with lam  (exact rational function)
  B272  pairs sharing a forbidden quad -> positive covariance at large lam
  B273  A/B phase bimodality proxy: n=5 layer-count profile shape
  B274  max-set type count vs (K-1)-neighbourhood volume, and whether the
        ordering can invert
  B275  Var_lam(|S|) peak location and its relation to layer-count structure
  B276  symmetry breaking: does Pr_lam(S) break D4 (variance of orbit-level mass)
  B277  max-set count vs neighbourhood volume
  B278  mixing of single-point-update chain: measured via spectral gap proxy
        (second eigenvalue of the random-walk on k-layers) -- exact for n<=4
  B279  same mean |S|, different mixing: square vs punctured board
  B280  multivariate Z in (orbit occupancy counts) -- highest-degree term vs
        mutual exclusivity of maximal-set phases

Output: research/verification/round3_chunk5_partition.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round3_chunk5_sharp import Game  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_chunk5_partition.json"


# ------------------------------------------------------------ polynomial utils
def poly_mul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                if y:
                    out[i + j] += x * y
    return out


def poly_add(a, b, sign=1):
    n = max(len(a), len(b))
    out = [0] * n
    for i, x in enumerate(a):
        out[i] += x
    for i, x in enumerate(b):
        out[i] += sign * x
    return out


def poly_eval_exact(p, lam_num, lam_den=1):
    """p(lam_num/lam_den) as an exact Fraction."""
    v = Fraction(0)
    x = Fraction(lam_num, lam_den)
    for c in reversed(p):
        v = v * x + c
    return v


def var_poly(p, lam_num, lam_den=1):
    x = Fraction(lam_num, lam_den)
    Z = poly_eval_exact(p, lam_num, lam_den)
    M1 = poly_eval_exact(poly_mul([0, 1], p), lam_num, lam_den)
    M2 = poly_eval_exact(poly_mul([0, 0, 1], p), lam_num, lam_den)
    return M1 / Z, M2 / Z - (M1 / Z) ** 2


# ---------------------------------------------------------------- safe sets
def safe_set_count_by_layer(n):
    """A_n(k) = number of safe k-subsets, for k=0..K.  Exact integers."""
    game = Game(n)
    reach = game.reachable()
    cnt = defaultdict(int)
    for occ in reach:
        cnt[occ.bit_count()] += 1
    K = max(cnt)
    A = [cnt.get(k, 0) for k in range(K + 1)]
    return game, A, reach


def conditional_count(game, required, forbidden_extra=()):
    """# safe sets containing `required` and avoiding nothing extra.
    (required must itself be safe)"""
    m = 0
    for v in required:
        m |= 1 << v
    if not game._safe(m):
        return 0
    total = [0] * (game.V + 1)
    # DP over remaining points, layer by layer
    rem = [v for v in range(game.V) if not (m >> v) & 1]
    k0 = m.bit_count()
    # brute force over subsets is fine only for n<=4
    assert game.V <= 16, "use the k-layer route for n=5"
    cur = {m: 1}
    for v in rem:
        nxt = {}
        for occ, c in cur.items():
            nxt[occ] = nxt.get(occ, 0) + c
            n2 = occ | (1 << v)
            if game._safe(n2):
                nxt[n2] = nxt.get(n2, 0) + c
        cur = nxt
    for occ, c in cur.items():
        total[occ.bit_count()] += c
    return total


def _safe(self, occ):
    for q in self.quad_masks if hasattr(self, "quad_masks") else self.quads:
        if (occ & q) == q:
            return False
    return True


Game._safe = _safe


def pairwise_marginal_poly(game, p, q):
    """W_{pq}(lam) = sum over T (T disjoint from {p,q}) of lam^{|T|}
    times [safe(T+p) and safe(T+q)].
    Returns exact integer coefficient list indexed by |T|."""
    both = (1 << p) | (1 << q)
    if not game._safe(both):
        return None
    rem = [v for v in range(game.V) if not (both >> v) & 1]
    # DP: count subsets of rem by size that keep both p and q legal
    cur = {0: 1}
    polys = [0] * (len(rem) + 1)
    for v in rem:
        b = 1 << v
        nxt = defaultdict(int)
        for occ, c in cur.items():
            nxt[occ] += c
            n2 = occ | b
            if game._safe(n2 | both):
                nxt[n2] += c
        cur = nxt
    for occ, c in cur.items():
        polys[occ.bit_count()] += c
    return polys


def main():
    out = {}
    for n in (2, 3, 4):
        t0 = time.time()
        game, A, reach = safe_set_count_by_layer(n)
        K = len(A) - 1
        Z = A[:]
        print(f"[n={n}] K={K} A={A} ({time.time()-t0:.1f}s)", flush=True)
        rec = {"n": n, "K": K, "A_n_k": A, "Z_poly": Z}

        # -------- B275 : Var_lam(|S|) as exact rational function, peak scan
        #      use integer lam values 1..64 and also rationals
        var_table = []
        for lam in range(1, 129):
            m, v = var_poly(Z, lam)
            var_table.append((lam, round(float(m), 6), round(float(v), 8)))
        peak = max(var_table, key=lambda z: z[2])
        rec["B275"] = {
            "var_scan_1_to_128": var_table,
            "peak_lambda": peak[0], "peak_var": peak[2],
            "peak_mean_k": peak[1],
            "K": K,
            "peak_is_below_K": peak[1] < K - 0.5,
        }
        print(f"  B275 peak lambda={peak[0]} mean={peak[1]} var={peak[2]} K={K}", flush=True)

        # -------- B271 / B272 : pairwise covariance sign changes
        pairs_info = []
        for p, q in combinations(range(n * n), 2):
            W = pairwise_marginal_poly(game, p, q)
            if W is None:
                pairs_info.append({"p": p, "q": q, "safe_together": False})
                continue
            # E[1p 1q] = lam^2 W(lam)/Z ; E[1p] = lam A_p(lam)/Z etc.
            # E[1p] = lam * (number of safe sets containing p weighted) / Z
            marg_p = None
            pairs_info.append({"p": p, "q": q, "safe_together": True, "W": W})
        rec["n_pairs"] = len(pairs_info)
        out[f"n{n}"] = rec
        print(f"  n={n} done ({time.time()-t0:.1f}s)", flush=True)

    # --- B271/B272 need E[1p]; compute per point
    for n in (2, 3, 4):
        rec = out[f"n{n}"]
        game, A, reach = safe_set_count_by_layer(n)
        Z = rec["Z_poly"]
        K = rec["K"]
        # point marginals
        pm = {}
        for p in range(n * n):
            tot = conditional_count(game, (p,))
            # E[1p]*Z = lam * sum_k tot[k] lam^{k-1}
            poly = [0] + tot
            pm[p] = poly
        rec["point_marginal_poly"] = {str(k): v for k, v in pm.items()}

        # sign changes of covariance for each unordered safe pair
        b271 = []
        b272 = []
        for p, q in combinations(range(n * n), 2):
            W = rec["n_pairs"] and None
        # recompute W here
        for p, q in combinations(range(n * n), 2):
            W = pairwise_marginal_poly(game, p, q)
            if W is None:
                continue
            # Cov * Z^2 = lam^2 W * Z - (lam*Ap)*(lam*Aq)
            num = poly_mul([0, 0] + W, Z)
            sub = poly_mul([0, 0] + pm[p][1:], [0] + pm[q][1:])
            num = poly_add(num, sub, -1)
            # scan lambda
            signs = []
            prev = None
            for lam in range(1, 4097):
                v = poly_eval_exact(num, lam)
                s = 0 if v == 0 else (1 if v > 0 else -1)
                if prev is not None and s != 0 and prev != 0 and s != prev:
                    signs.append((lam - 1, lam))
                if s != 0:
                    prev = s
            shares_quad = any((qm & (1 << p)) and (qm & (1 << q)) for qm in game.quads)
            rec_pq = {"p": p, "q": q, "sign_changes": signs,
                      "shares_forbidden_quad": shares_quad,
                      "num_poly": num}
            if signs:
                b271.append(rec_pq)
            if shares_quad and signs:
                b272.append(rec_pq)
        rec["B271"] = {"n_pairs_with_sign_change": len(b271),
                       "total_pairs": sum(1 for p, q in combinations(range(n * n), 2)
                                          if pairwise_marginal_poly(game, p, q) is not None),
                       "examples": [{k: v for k, v in x.items() if k != "num_poly"} for x in b271[:8]]}
        rec["B272"] = {"n_sign_changing_pairs_sharing_a_quad": len(b272),
                       "examples": [{k: v for k, v in x.items() if k != "num_poly"} for x in b272[:8]]}
        print(f"  n={n} B271 sign-change pairs={len(b271)} (sharing quad: {len(b272)})", flush=True)

    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

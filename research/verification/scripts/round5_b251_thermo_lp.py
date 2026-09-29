#!/usr/bin/env python3
"""Round5 B275 (Var peak), B277 (neighborhood volume), B280 (Z top coeff),
B288/B289 (fractional capacity LP vs K_n).
"""
import json
from pathlib import Path
from fractions import Fraction

OUT = Path(__file__).resolve().parents[1] / "round5_b251_thermo_lp.json"

# level counts from round5_b251_solver.json (n=4,5)
LEVELS = {
    4: [1, 16, 120, 560, 1626, 2360, 1064, 64],
    5: [1, 25, 300, 2300, 11824, 37272, 59192, 35208, 5172, 100],
    # n=6 from prior round4 data (if available) — load from solver json if present
}

# Known K_n (max safe size) and maximal counts from PROTOCOL/HANDOVER
KNOWN_K = {4: 7, 5: 9, 6: 11, 7: 14}
# maximal counts: n=4:64, n=5:100, n=6:349132, n=7:16
KNOWN_MAX = {4: 64, 5: 100, 6: 349132, 7: 16}

def thermo(level):
    """Return variance profile of |S| under Pr_lambda for integer lambda."""
    # Z(lam) = sum A_k lam^k
    # E[k] = (sum k A_k lam^k) / Z
    # E[k^2] = (sum k^2 A_k lam^k) / Z
    # Var = E[k2] - E[k]^2
    res = {}
    for lam in [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 5000, 20000]:
        Z = 0
        s1 = 0
        s2 = 0
        pl = 1
        for k, a in enumerate(level):
            Z += a * pl
            s1 += k * a * pl
            s2 += k * k * a * pl
            pl *= lam
        if Z == 0:
            continue
        Ek = Fraction(s1, Z)
        Ek2 = Fraction(s2, Z)
        var = Ek2 - Ek * Ek
        res[lam] = {
            "E_k": float(Ek),
            "Var": float(var),
            "Z_digits": len(str(Z)),
        }
    return res

def neighborhood(level):
    """Ratios A_K / A_{K-1} etc."""
    if not level:
        return {}
    K = max(i for i, v in enumerate(level) if v > 0)
    out = {"K": K, "A_K": level[K]}
    if K >= 1 and level[K]:
        out["A_Kminus1"] = level[K - 1]
        out["ratio_K-1_over_K"] = level[K - 1] / level[K]
    if K >= 2 and level[K]:
        out["A_Kminus2"] = level[K - 2]
        out["ratio_K-2_over_K"] = level[K - 2] / level[K]
    return out

def fractional_capacity_lp(points, quads, K_n):
    """
    Fractional relaxation: max sum x_p s.t. for each quad q, sum_{p in q} x_p <= 3,
    0 <= x_p <= 1.
    This is an LP. Without an LP solver, use dual: min sum_{q} 3 y_q s.t.
    for each p, sum_{q ni p} y_q >= 1, y_q >= 0.
    A feasible dual gives an upper bound on the integer max (=K_n).
    Uniform y_q = 1/d_p max ... simple bound: assign y_q = 1/m where m = max degree.
    Better: greedy set-cover dual.
    """
    # Simple dual feasible: y_q = 1 / max_{p} deg(p) for all q gives
    # sum_{q ni p} y_q = deg(p)/maxdeg <= 1. Not feasible when deg(p) < maxdeg.
    # Instead use y_q = 1/3 for quads covering high-degree points... let's do
    # a simple iterative dual improvement.
    V = len(points)
    deg = [0] * V
    for q in quads:
        for p in q:
            deg[p] += 1
    # dual variables y_q
    y = [Fraction(1, 3)] * len(quads)  # start: each quad pays 1/3
    # check coverage
    cover = [Fraction(0)] * V
    for qi, q in enumerate(quads):
        for p in q:
            cover[p] += y[qi]
    # scale up if needed
    for p in range(V):
        if cover[p] > 0 and cover[p] < 1:
            # need to increase y on quads containing p
            pass
    # Simple valid dual: y_q = 1/3 for all q. cover[p] = deg(p)/3.
    # If deg(p) >= 3 for all p, then cover[p] >= 1, dual feasible.
    # dual objective = 3 * sum y_q = 3 * nquads / 3 = nquads.
    all_ge3 = all(deg[p] >= 3 for p in range(V))
    dual_uniform = Fraction(3 * len(quads), 3) if all_ge3 else None
    # Better dual: y_q = 1/max(3, maxdeg)? No.
    # Use y_q = 1/deg_max? cover[p]=deg(p)/deg_max.
    dmax = max(deg) if deg else 1
    dmin = min(deg) if deg else 1
    # dual feasible: y_q = 1/dmin  => cover[p] = deg(p)/dmin >= 1
    y2 = [Fraction(1, dmin)] * len(quads)
    dual_dmin = Fraction(3 * len(quads), dmin)

    # Even better dual via greedy covering: repeatedly pick quad covering
    # the most uncovered mass. Approximate set-cover dual.
    # Start y=0, residual[r]=1 for each point. Pick quad minimizing cost/cover.
    residual = [Fraction(1)] * V
    y_greedy = [Fraction(0)] * len(quads)
    for _ in range(50):
        if all(r <= 0 for r in residual):
            break
        best_qi = -1
        best_score = None
        for qi, q in enumerate(quads):
            cover_amt = sum(residual[p] for p in q if residual[p] > 0)
            if cover_amt <= 0:
                continue
            # cost per unit cover = 3 / cover_amt  (adding 1 to y_qi)
            # we add the minimal amount to zero out one point
            score = Fraction(3, 1) / cover_amt
            if best_score is None or score < best_score:
                best_score = score
                best_qi = qi
        if best_qi < 0:
            break
        q = quads[best_qi]
        # add enough y to reduce residual of the tightest point to 0
        add_amt = min(residual[p] for p in q if residual[p] > 0)
        y_greedy[best_qi] += add_amt
        for p in q:
            residual[p] -= add_amt
            if residual[p] < 0:
                residual[p] = Fraction(0)
    dual_greedy = 3 * sum(y_greedy)

    return {
        "V": V,
        "nquads": len(quads),
        "min_deg": dmin,
        "max_deg": dmax,
        "all_deg_ge_3": all_ge3,
        "dual_uniform_y_1_3": float(dual_uniform) if dual_uniform else None,
        "dual_y_1_dmin": float(dual_dmin),
        "dual_greedy": float(dual_greedy),
        "K_n": K_n,
    }

def main():
    result = {}

    # ---- B275: variance peak ----
    b275 = {}
    for n, level in LEVELS.items():
        th = thermo(level)
        # find lambda of max Var
        max_var_lam = max(th.keys(), key=lambda L: th[L]["Var"])
        b275[f"n{n}"] = {
            "levels": level,
            "var_max_lambda": max_var_lam,
            "var_max": th[max_var_lam]["Var"],
            "var_profile": {str(k): v for k, v in th.items()},
            "E_k_at_var_max": th[max_var_lam]["E_k"],
            "K": max(i for i, v in enumerate(level) if v > 0),
        }
    result["B275"] = b275

    # ---- B277: neighborhood volume ----
    b277 = {}
    for n, level in LEVELS.items():
        b277[f"n{n}"] = neighborhood(level)
    result["B277"] = b277

    # ---- B280: highest-degree coeff = maximal count ----
    b280 = {}
    for n, level in LEVELS.items():
        K = max(i for i, v in enumerate(level) if v > 0)
        top = level[K]  # coefficient of lambda^K
        b280[f"n{n}"] = {
            "K": K,
            "top_coeff": top,
            "known_maximal": KNOWN_MAX.get(n),
            "match": top == KNOWN_MAX.get(n),
        }
    result["B280"] = b280

    # ---- B288: fractional capacity ----
    # Need actual quads. Rebuild n=4,5 geometry in Python.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from kyouen_core import board_square, det4, is_forbidden_quad
    from itertools import combinations

    b288 = {}
    for n in [4, 5]:
        pts = [(x, y) for y in range(n) for x in range(n)]
        V = n * n
        quads = []
        for ids in combinations(range(V), 4):
            if is_forbidden_quad([pts[i] for i in ids]):
                quads.append(list(ids))
        lp = fractional_capacity_lp(pts, quads, KNOWN_K[n])
        b288[f"n{n}"] = lp
    result["B288"] = b288

    # ---- B289: gap between fractional and integer ----
    b289 = {}
    for n in [4, 5]:
        lp = b288[f"n{n}"]
        K = KNOWN_K[n]
        # best (smallest) dual upper bound we have
        candidates = [lp.get("dual_y_1_dmin"), lp.get("dual_greedy"), lp.get("dual_uniform_y_1_3")]
        candidates = [c for c in candidates if c is not None]
        frac_ub = min(candidates) if candidates else None
        b289[f"n{n}"] = {
            "K_n": K,
            "dual_y_1_dmin": lp.get("dual_y_1_dmin"),
            "dual_greedy": lp.get("dual_greedy"),
            "best_fractional_upper_bound": frac_ub,
            "gap_upper_minus_K": (frac_ub - K) if frac_ub else None,
        }
    result["B289"] = b289

    OUT.write_text(json.dumps(result, indent=2))
    print("WROTE", OUT)
    print("B275 n4 var_max_lambda", b275["n4"]["var_max_lambda"], "var", round(b275["n4"]["var_max"], 4), "E_k", round(b275["n4"]["E_k_at_var_max"], 4))
    print("B275 n5 var_max_lambda", b275["n5"]["var_max_lambda"], "var", round(b275["n5"]["var_max"], 4))
    print("B277 n4", b277["n4"])
    print("B277 n5", b277["n5"])
    print("B280", b280)
    print("B288 n4", b288["n4"])
    print("B288 n5", b288["n5"])
    print("B289", b289)

if __name__ == "__main__":
    main()

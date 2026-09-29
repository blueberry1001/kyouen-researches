"""B325/B327/B329/B330: ceiling stats + child-value required pairs on n=6 (and extra rects for B340).
Also WFT width on 4x5 / 4x6 if affordable.
"""
import sys, json, time
from collections import defaultdict
sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import board_square, board_rect

def ceiling_stats(B, g, name):
    """h(S) = max size of a safe extension of S (i.e. max |T| over safe T superset S).
    Actually from prior code: h is 'local ceiling' = K of the remaining board?
    From round2-batch: h(S) is such that g(S)=h(S) is 'ceiling-achieving'.
    Looking at B325 evidence: k=6, g=h=3, |L|=4. And K_global=9 for n=5.
    Likely h(S) = max_{legal extensions} final size = k + max_safe_extension(S),
    i.e. the maximum number of stones achievable from S (including S).
    = popcount of a maximum safe superset of S.
    We'll compute h(S) = max |U| over safe U ⊇ S, via DP on supersets.
    """
    # Build map occ -> list of stones? Better: for each safe occ, h = max size of safe superset.
    # DP: h[occ] = max(popcount(occ), max over legal moves v of h[occ|v]) but only if occ is safe.
    # All occ in g are safe. A legal move from occ gives a safe child.
    # So h[occ] = max(k, max h[child] over legal children, k if no children)
    # This equals the maximum terminal size reachable (not necessarily winner-preserving).
    # Wait, B325 says "h(S) は残り最大手数" related to mu = min remaining. Let's use:
    # h(S) = max achievable total stones from S  (>= |S|)
    Kmax = max(occ.bit_count() for occ in g) if g else 0
    by_k = defaultdict(list)
    for occ in g:
        by_k[occ.bit_count()].append(occ)
    h = {}
    for k in range(Kmax, -1, -1):
        for occ in by_k.get(k, []):
            ch = [occ | (1 << v) for v in B.legal_moves(occ)]
            best = k
            for c in ch:
                if c in h:
                    if h[c] > best:
                        best = h[c]
            h[occ] = best

    # mu(S) = min achievable total stones from S
    mu = {}
    for k in range(Kmax, -1, -1):
        for occ in by_k.get(k, []):
            ch = [occ | (1 << v) for v in B.legal_moves(occ)]
            if not ch:
                mu[occ] = k
            else:
                mu[occ] = min(mu[c] for c in ch)

    # B325: ceiling-achieving g==h, min(|L|-h)
    min_slack_by_h = {}
    slack_examples = {}
    n_ceiling = 0
    for occ, gv in g.items():
        hv = h[occ]
        if gv == hv:
            n_ceiling += 1
            L = len(B.legal_moves(occ))
            slack = L - hv
            if hv not in min_slack_by_h or slack < min_slack_by_h[hv]:
                min_slack_by_h[hv] = slack
                slack_examples[hv] = {"occ": occ, "k": occ.bit_count(), "g": gv, "h": hv, "L": L, "slack": slack}

    # B327: deficit h-g large, but some child has deficit 0
    max_deficit = 0
    b327_examples = []
    n_b327 = 0
    for occ, gv in g.items():
        hv = h[occ]
        deficit = hv - gv
        if deficit <= 0:
            continue
        ch = [occ | (1 << v) for v in B.legal_moves(occ)]
        has_zero = any((h[c] - g[c]) == 0 for c in ch if c in g)
        if has_zero:
            n_b327 += 1
            if deficit > max_deficit:
                max_deficit = deficit
                b327_examples = [{"occ": occ, "k": occ.bit_count(), "g": gv, "h": hv, "deficit": deficit}]
            elif deficit == max_deficit and len(b327_examples) < 3:
                b327_examples.append({"occ": occ, "k": occ.bit_count(), "g": gv, "h": hv, "deficit": deficit})

    # B330: same (h, mu) cell, max g spread
    cells = defaultdict(list)
    for occ, gv in g.items():
        cells[(h[occ], mu[occ])].append((gv, occ))
    max_spread = 0
    spread_cell = None
    spread_ex = None
    n_spread_ge3 = 0
    for key, lst in cells.items():
        gs = [x[0] for x in lst]
        spread = max(gs) - min(gs)
        if spread >= 3:
            n_spread_ge3 += 1
        if spread > max_spread:
            max_spread = spread
            lo = min(lst, key=lambda x: x[0])
            hi = max(lst, key=lambda x: x[0])
            spread_cell = key
            spread_ex = {"low_g": lo[0], "low_occ": lo[1], "high_g": hi[0], "high_occ": hi[1],
                         "low_k": lo[1].bit_count(), "high_k": hi[1].bit_count()}

    return {
        "name": name,
        "n_states": len(g),
        "K_global": Kmax,
        "max_g": max(g.values()) if g else 0,
        "n_ceiling_g_eq_h": n_ceiling,
        "B325_min_slack_by_h": {str(k): v for k, v in sorted(min_slack_by_h.items())},
        "B325_examples": slack_examples,
        "B327_max_deficit": max_deficit,
        "B327_count": n_b327,
        "B327_examples": b327_examples,
        "B330_max_spread": max_spread,
        "B330_cell": list(spread_cell) if spread_cell else None,
        "B330_examples": spread_ex,
        "B330_n_cells_spread_ge3": n_spread_ge3,
    }

def required_pairs(B, g, name, layer_k=None):
    """B329: at the saturation layer (layer_k), check that whenever children contain
    0..a-1 they also contain a (for a = each hole / each a).
    """
    if layer_k is None:
        # sigma layer = K_global - 2 as in prior data? For n=6 sigma=3, K=11.
        # From holes_by_n: layer_k equals sigma_computed. We'll use the k that maximizes
        # state count among k < K, or just compute for all k and pick holes.
        pass
    # First: which nimbers appear at each k
    by_k = defaultdict(lambda: defaultdict(int))
    for occ, gv in g.items():
        by_k[occ.bit_count()][gv] += 1
    layer_hist = {str(k): {str(gv): c for gv, c in sorted(d.items())} for k, d in sorted(by_k.items())}

    # Focus on a specific layer: the one just below saturation where holes appear.
    # Prior definition: sigma layer is the smallest k such that max nimber at that k equals K-? 
    # holes_by_n.6: layer_k=3, present=[0,1,2,3,5,6,7,8], missing=[4]
    # We'll scan all layers for holes and test required pairs at layers with holes.
    results = {}
    for k, hist in by_k.items():
        present = set(hist.keys())
        if not present:
            continue
        mx = max(present)
        missing = [a for a in range(0, mx + 1) if a not in present]
        if not missing:
            continue
        # test required pairs at this layer for each missing a
        a_results = {}
        for a in missing:
            # antecedent: some position at this layer has children containing 0..a-1
            ante = 0
            viol = 0
            viol_examples = []
            for occ, gv in g.items():
                if occ.bit_count() != k:
                    continue
                ch = [occ | (1 << v) for v in B.legal_moves(occ)]
                child_vals = {g[c] for c in ch if c in g}
                if all(x in child_vals for x in range(a)):
                    ante += 1
                    if a not in child_vals:
                        viol += 1
                        if len(viol_examples) < 3:
                            viol_examples.append({"occ": occ, "g": gv, "child_vals": sorted(child_vals)})
            a_results[str(a)] = {"antecedent_true": ante, "violations": viol, "examples": viol_examples}
        results[str(k)] = {"present": sorted(present), "missing": missing, "required_pairs": a_results,
                           "hist": {str(gv): c for gv, c in sorted(hist.items())}}
    return {"name": name, "layer_hist": layer_hist, "holes_and_required_pairs": results}

def main():
    out = {}
    # n=4,5 cross-check (fast-ish), n=6 heavy
    for n in (4, 5):
        t0 = time.time()
        B = board_square(n)
        g = B.solve_grundy()
        print(f"[n{n}] grundy {len(g)} {time.time()-t0:.1f}s", flush=True)
        out[f"n{n}_ceiling"] = ceiling_stats(B, g, f"n{n}")
        out[f"n{n}_B329"] = required_pairs(B, g, f"n{n}")
        print(f"[n{n}] ceiling+B329 done {time.time()-t0:.1f}s", flush=True)
        print("  B325", out[f"n{n}_ceiling"]["B325_min_slack_by_h"], flush=True)
        print("  B327", out[f"n{n}_ceiling"]["B327_max_deficit"], out[f"n{n}_ceiling"]["B327_count"], flush=True)
        print("  B330", out[f"n{n}_ceiling"]["B330_max_spread"], out[f"n{n}_ceiling"]["B330_cell"], flush=True)

    # n=6
    t0 = time.time()
    B = board_square(6)
    print("[n6] solving grundy...", flush=True)
    g = B.solve_grundy()
    print(f"[n6] grundy {len(g)} {time.time()-t0:.1f}s", flush=True)
    out["n6_ceiling"] = ceiling_stats(B, g, "n6")
    out["n6_B329"] = required_pairs(B, g, "n6")
    print(f"[n6] done {time.time()-t0:.1f}s", flush=True)
    print("  B325", out["n6_ceiling"]["B325_min_slack_by_h"], flush=True)
    print("  B327", out["n6_ceiling"]["B327_max_deficit"], out["n6_ceiling"]["B327_count"], flush=True)
    print("  B330", out["n6_ceiling"]["B330_max_spread"], out["n6_ceiling"]["B330_cell"], flush=True)
    print("  B329 holes", {k: v["missing"] for k, v in out["n6_B329"]["holes_and_required_pairs"].items()}, flush=True)

    path = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b325_ceiling.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("wrote", path, flush=True)

if __name__ == "__main__":
    main()

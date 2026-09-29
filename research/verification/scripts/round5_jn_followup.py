#!/usr/bin/env python3
"""Round5 J_n follow-up: B312 composite classifier, B318 one-stone theorem,
B320 three-stone rule, B321/B322 all-layer hole analysis (n<=5 complete).

Output: research/verification/round5_jn_followup.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square  # noqa: E402

VER = Path(__file__).resolve().parents[1]
CACHE = VER / "round5_b231_n5_grundy.json"
OUT = VER / "round5_jn_followup.json"


def load_grundy(n: int, cache: dict | None) -> dict[int, int]:
    if n == 5 and cache is not None:
        return {int(k): v for k, v in cache.items()}
    b = board_square(n)
    return b.solve_grundy()


def layer_hists(gr: dict[int, int]) -> dict[int, Counter]:
    h: dict[int, Counter] = defaultdict(Counter)
    for occ, g in gr.items():
        h[occ.bit_count()][g] += 1
    return {k: Counter(v) for k, v in h.items()}


def max_g_at(hists: dict[int, Counter], k: int) -> int:
    c = hists.get(k)
    return max(c) if c else -1


def compute_K_sigma(hists: dict[int, Counter], V: int) -> tuple[int, int]:
    """K = max game length bound observed as max g at layer 0? Use prior values.
    Prior: K_n = 3,5,7,9,11 and sigma = min{k: M(k) == K-k}.
    Infer K from empty: actually K is a known constant per n. We recompute sigma
    given K from the table, and also recompute K as the first k where M(k)==k0-k
    for some k0... Better: K is the max total moves bound = max_k (k + M(k)).
    """
    # K := max over layers of (k + M(k)); matches 3,5,7,9,11
    K = 0
    for k, c in hists.items():
        m = max(c) if c else 0
        K = max(K, k + m)
    # sigma = min k such that M(k) == K - k
    sigma = None
    for k in sorted(hists):
        m = max(hists[k])
        if m == K - k:
            sigma = k
            break
    return K, sigma if sigma is not None else -1


def holes_at(hists: dict[int, Counter], k: int, bound: int) -> dict:
    present = sorted(hists.get(k, Counter()).keys())
    missing = [j for j in range(bound) if j not in set(present)]
    # consecutive pairs among missing
    mset = set(missing)
    cons = [(j, j + 1) for j in range(bound - 1) if j in mset and (j + 1) in mset]
    pos_missing = [j for j in missing if j > 0]
    nonpow2 = [j for j in pos_missing if (j & (j - 1)) != 0]
    return {
        "bound": bound,
        "present": present,
        "missing": missing,
        "consecutive_pairs": cons,
        "positive_missing": pos_missing,
        "positive_missing_non_pow2": nonpow2,
    }


def is_pow2(x: int) -> bool:
    return x > 0 and (x & (x - 1)) == 0


def analyze_n(n: int, gr: dict[int, int]) -> dict:
    b = board_square(n)
    V = b.V
    hists = layer_hists(gr)
    K, sigma = compute_K_sigma(hists, V)
    # also use given K from round2 table
    given_K = {2: 3, 3: 5, 4: 7, 5: 9, 6: 11}.get(n)
    given_sigma = {2: 2, 3: 4, 4: 2, 5: 3, 6: 3}.get(n)
    sigma_layer = holes_at(hists, sigma, K - sigma) if sigma >= 0 else {}

    # all-layer hole analysis (B321/B322 generalized)
    all_layers = {}
    for k in sorted(hists):
        bound = max(0, K - k)
        # only meaningful while bound > 0 (saturation region starts at sigma)
        if k < 0:
            continue
        all_layers[str(k)] = holes_at(hists, k, bound)

    # one-stone / two-stone structure
    one = Counter()
    two = {}
    for occ, g in gr.items():
        c = occ.bit_count()
        if c == 1:
            one[g] += 1
        elif c == 2:
            two[occ] = g
    one_hist = dict(one)
    two_hist = dict(Counter(two.values()))
    uniform_one = len(one_hist) == 1
    h = next(iter(one_hist)) if uniform_one else None

    # THEOREM check: uniform one-stone h => no two-stone has g == h
    thm_violations = 0
    thm_j_empty_pred = None
    if uniform_one and h is not None:
        thm_violations = sum(1 for g in two.values() if g == h)
        thm_j_empty_pred = (h == 0)
    # J edges = two-stone with g==0
    p_pairs = [occ for occ, g in two.items() if g == 0]
    # isolated vertices in J
    deg = [0] * V
    for occ in p_pairs:
        bits = [i for i in range(V) if (occ >> i) & 1]
        deg[bits[0]] += 1
        deg[bits[1]] += 1
    n_iso = sum(1 for d in deg if d == 0)

    # B318: missing two-stone value vs one-stone uniform value
    two_present = sorted(set(two.values()))
    two_missing_in_range = [j for j in range(max(two_present) + 2 if two_present else 2) if j not in set(two_present)]

    return {
        "n": n,
        "V": V,
        "n_states": len(gr),
        "K": K,
        "K_given": given_K,
        "sigma": sigma,
        "sigma_given": given_sigma,
        "sigma_match": (given_K == K and given_sigma == sigma),
        "g_empty": gr.get(0, None),
        "layer_max_g": {str(k): max(c) for k, c in sorted(hists.items())},
        "layer_counts": {str(k): dict(sorted(c.items())) for k, c in sorted(hists.items())},
        "sigma_layer_holes": sigma_layer,
        "all_layer_holes": all_layers,
        "one_stone_hist": one_hist,
        "two_stone_hist": two_hist,
        "uniform_one": uniform_one,
        "uniform_one_h": h,
        "thm_uniform_h_absent_in_two": thm_violations == 0 if uniform_one else None,
        "thm_violations": thm_violations,
        "thm_j_empty_if_h0": thm_j_empty_pred,
        "n_P_pairs": len(p_pairs),
        "n_isolated_vertices_J": n_iso,
        "two_missing": two_missing_in_range,
    }


def b312_classifier(n: int = 4) -> dict:
    """Composite feature separation of TD vs non-TD P pairs on J_4."""
    b = board_square(n)
    V = b.V
    gr = b.solve_grundy()
    adj = [0] * V
    p_pairs = []
    for i, j in combinations(range(V), 2):
        occ = (1 << i) | (1 << j)
        if gr[occ] == 0:
            adj[i] |= 1 << j
            adj[j] |= 1 << i
            p_pairs.append((i, j))

    def is_td(a, bpt):
        for v in range(V):
            openN = adj[v]
            if ((openN >> a) & 1) == 0 and ((openN >> bpt) & 1) == 0:
                return False
        return True

    def feat(a, bpt):
        ax, ay = a % n, a // n
        bx, by = bpt % n, bpt // n
        dx, dy = ax - bx, ay - by
        d2 = dx * dx + dy * dy
        linf = max(abs(dx), abs(dy))
        manh = abs(dx) + abs(dy)
        def is_corner(p):
            x, y = p % n, p // n
            return (x == 0 or x == n - 1) and (y == 0 or y == n - 1)
        corners = int(is_corner(a)) + int(is_corner(bpt))
        da = bin(adj[a]).count("1")
        db = bin(adj[bpt]).count("1")
        Na = {v for v in range(V) if (adj[a] >> v) & 1}
        Nb = {v for v in range(V) if (adj[bpt] >> v) & 1}
        union = len(Na | Nb)
        inter = len(Na & Nb)
        # closed coverage: vertices with neighbor in {a,b} (open) = TD check
        # local: number of board points within chebyshev 1 of either
        def near(p, r):
            x, y = p % n, p // n
            s = set()
            for yy in range(max(0, y - r), min(n, y + r + 1)):
                for xx in range(max(0, x - r), min(n, x + r + 1)):
                    s.add(yy * n + xx)
            return s
        cov1 = len(near(a, 1) | near(bpt, 1))
        return {
            "d2": d2, "linf": linf, "manh": manh, "corners": corners,
            "deg_a": da, "deg_b": db, "deg_sum": da + db, "deg_min": min(da, db),
            "deg_max": max(da, db),
            "n_union": union, "n_inter": inter, "cov1": cov1,
            "is_P": True,
        }

    td_rows, nontd_rows = [], []
    for (a, bpt) in p_pairs:
        f = feat(a, bpt)
        f["pair"] = [a, bpt]
        f["d4"] = None
        (td_rows if is_td(a, bpt) else nontd_rows).append(f)

    # try single features and simple conjunctions for perfect separation
    keys = ["d2", "linf", "manh", "corners", "deg_a", "deg_b", "deg_sum",
            "deg_min", "deg_max", "n_union", "n_inter", "cov1"]

    def sep_single(k):
        tv = Counter(r[k] for r in td_rows)
        nv = Counter(r[k] for r in nontd_rows)
        td_only = [v for v in tv if v not in nv]
        non_only = [v for v in nv if v not in tv]
        mixed = [v for v in tv if v in nv]
        return {"td_only_values": sorted(td_only), "nontd_only_values": sorted(non_only),
                "mixed_values": sorted(mixed),
                "perfect": len(mixed) == 0}

    singles = {k: sep_single(k) for k in keys}

    # conjunctions of two features: value pair (k1=v1, k2=v2)
    def sep_pair(k1, k2):
        tset = set((r[k1], r[k2]) for r in td_rows)
        nset = set((r[k1], r[k2]) for r in nontd_rows)
        inter = tset & nset
        return {
            "td_only": sorted(tset - nset),
            "nontd_only": sorted(nset - tset),
            "mixed": sorted(inter),
            "perfect": len(inter) == 0,
        }

    pairs = {}
    for i, k1 in enumerate(keys):
        for k2 in keys[i + 1:]:
            r = sep_pair(k1, k2)
            if r["perfect"] or len(r["mixed"]) <= 2:
                pairs[f"{k1}+{k2}"] = r

    # three-feature conjunction on the residual mixed d2 values
    # first find best 2-feature that reduces mixed most
    best2 = None
    for i, k1 in enumerate(keys):
        for k2 in keys[i + 1:]:
            r = sep_pair(k1, k2)
            score = len(r["mixed"])
            if best2 is None or score < best2[0]:
                best2 = (score, k1, k2, r)

    return {
        "n": n,
        "n_P": len(p_pairs),
        "n_TD": len(td_rows),
        "n_nonTD": len(nontd_rows),
        "singles": singles,
        "pairs_notable": pairs,
        "best_pair": {"n_mixed": best2[0], "keys": [best2[1], best2[2]], **best2[3]} if best2 else None,
        "td_rows": td_rows,
        "nontd_rows": nontd_rows,
    }


def b320_three_stone(n: int = 5, gr: dict | None = None) -> dict:
    """For n=5 mixed-key pairs (same one-stone g + same distance, P vs non-P),
    compare three-stone child nimber histograms; look for a short rule."""
    if gr is None:
        gr = load_grundy(n, None)
    b = board_square(n)
    V = b.V
    # one-stone grundy
    one = {}
    for i in range(V):
        one[i] = gr[1 << i]
    # pairs
    pairs = []
    for i, j in combinations(range(V), 2):
        occ = (1 << i) | (1 << j)
        g2 = gr[occ]
        ax, ay = i % n, i // n
        bx, by = j % n, j // n
        d2 = (ax - bx) ** 2 + (ay - by) ** 2
        # three-stone children: legal third stones
        L = b.legal_moves(occ)
        child_g = [gr[occ | (1 << q)] for q in L]
        hist = Counter(child_g)
        pairs.append({
            "pair": [i, j],
            "g2": g2,
            "is_P": g2 == 0,
            "one": (one[i], one[j]),
            "one_key": tuple(sorted((one[i], one[j]))),
            "d2": d2,
            "n_child": len(L),
            "child_hist": dict(sorted(hist.items())),
            "child_set": sorted(set(child_g)),
            "child_mex": next((x for x in range(20) if x not in set(child_g)), None),
            "child_min": min(child_g) if child_g else None,
            "child_max": max(child_g) if child_g else None,
            "has0": 0 in set(child_g),
            "has1": 1 in set(child_g),
        })

    # group by (one_key, d2)
    groups = defaultdict(list)
    for p in pairs:
        groups[(p["one_key"], p["d2"])].append(p)
    mixed = {k: v for k, v in groups.items() if len(set(x["is_P"] for x in v)) > 1}

    # find a short predicate on child_hist features that separates within mixed groups
    # features available at pair level: has0, has1, child_set, child_mex, n_child
    def rule_stats(members):
        Ps = [m for m in members if m["is_P"]]
        Ns = [m for m in members if not m["is_P"]]
        out = {}
        for k in ["has0", "has1", "n_child", "child_mex", "child_min", "child_max"]:
            out[k] = {
                "P": dict(Counter(m[k] for m in Ps)),
                "nonP": dict(Counter(m[k] for m in Ns)),
            }
        # child_set as frozenset
        out["child_sets_P"] = sorted({tuple(m["child_set"]) for m in Ps})
        out["child_sets_nonP"] = sorted({tuple(m["child_set"]) for m in Ns})
        # 1-stone values of pair already in key
        # does "0 in child_hist" define P? (P => has a losing child = 0 in children)
        # actually g2=0 means mex of children = 0, i.e. 0 not in children.
        out["mex_eq_g2_check"] = all(
            (m["child_mex"] == m["g2"]) for m in members
        )
        # short rule candidates:
        # R1: 0 not in children <=> P  (this is DEFINITION of mex=0)
        out["R1_0_not_in_children_iff_P"] = all(
            ((not m["has0"]) == m["is_P"]) for m in members
        )
        return out

    mixed_detail = {}
    for k, v in mixed.items():
        mixed_detail[str(k)] = {
            "n": len(v),
            "n_P": sum(1 for x in v if x["is_P"]),
            "n_nonP": sum(1 for x in v if not x["is_P"]),
            "stats": rule_stats(v),
            "examples_P": [x for x in v if x["is_P"]][:3],
            "examples_nonP": [x for x in v if not x["is_P"]][:3],
        }

    # global: is there a short rule using one-stone + d2 + a single child feature?
    # Actually the DEFINING rule is mex; B320 asks for a *short* rule distinguishing
    # P vs non-P among same one-stone/distance keys via three-stone distribution.
    # Check: presence of particular nimber in children.
    short_rules = {}
    for name, pred in [
        ("0_not_in_children", lambda p: not p["has0"]),
        ("1_in_children", lambda p: p["has1"]),
        ("child_min_ge1", lambda p: p["child_min"] is not None and p["child_min"] >= 1),
        ("child_max_eq", lambda p: p["child_max"]),
    ]:
        ok_p = ok_n = 0
        tot_p = tot_n = 0
        for p in pairs:
            try:
                r = pred(p)
            except Exception:
                continue
            if p["is_P"]:
                tot_p += 1
                ok_p += int(bool(r) == p["is_P"]) if name != "0_not_in_children" else int(r)
            else:
                tot_n += 1
                if name == "0_not_in_children":
                    ok_n += int(r == p["is_P"])  # r True means predicts P
                else:
                    ok_n += int(bool(r) == p["is_P"])
        short_rules[name] = {"ok_P": ok_p, "tot_P": tot_p, "ok_nonP": ok_n, "tot_nonP": tot_n}

    # cleaner accuracy
    acc = {}
    for name, pred in [
        ("0_not_in_children", lambda p: not p["has0"]),
        ("1_in_children", lambda p: p["has1"]),
    ]:
        correct = 0
        for p in pairs:
            pred_P = pred(p)
            correct += int(pred_P == p["is_P"])
        acc[name] = {"correct": correct, "total": len(pairs),
                     "perfect": correct == len(pairs)}

    return {
        "n": n,
        "n_pairs": len(pairs),
        "n_P": sum(1 for p in pairs if p["is_P"]),
        "n_nonP": sum(1 for p in pairs if not p["is_P"]),
        "n_mixed_keys": len(mixed),
        "mixed_keys": {str(k): {"n": len(v), "nP": sum(1 for x in v if x["is_P"]),
                                "nN": sum(1 for x in v if not x["is_P"])}
                       for k, v in mixed.items()},
        "mixed_detail": mixed_detail,
        "accuracy": acc,
        "two_hist": dict(Counter(p["g2"] for p in pairs)),
    }


def main() -> None:
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else None
    result = {"n_analyses": {}, "b312": None, "b320": None}

    for n in (2, 3, 4, 5):
        print(f"analyzing n={n} ...", flush=True)
        gr = load_grundy(n, cache)
        result["n_analyses"][str(n)] = analyze_n(n, gr)

    print("b312 classifier ...", flush=True)
    result["b312"] = b312_classifier(4)

    print("b320 three-stone ...", flush=True)
    gr5 = load_grundy(5, cache)
    result["b320"] = b320_three_stone(5, gr5)

    # compact summary for the md
    result["summary"] = {
        "B321_all_n_sigma_layer_no_consecutive": all(
            not result["n_analyses"][str(n)]["sigma_layer_holes"].get("consecutive_pairs")
            for n in (2, 3, 4, 5)
        ),
        "B321_all_layers_no_consecutive": {
            str(n): {
                k: (len(v["consecutive_pairs"]) == 0)
                for k, v in result["n_analyses"][str(n)]["all_layer_holes"].items()
            }
            for n in (2, 3, 4, 5)
        },
        "B322_sigma_positive_missing_pow2_only": all(
            all(is_pow2(x) for x in result["n_analyses"][str(n)]["sigma_layer_holes"].get("positive_missing", []))
            for n in (2, 3, 4, 5)
        ),
        "B322_all_layers": {
            str(n): {
                k: all(is_pow2(x) for x in v.get("positive_missing", []))
                for k, v in result["n_analyses"][str(n)]["all_layer_holes"].items()
            }
            for n in (2, 3, 4, 5)
        },
        "B318_uniform_theorem_ok": {
            str(n): result["n_analyses"][str(n)]["thm_uniform_h_absent_in_two"]
            for n in (2, 3, 4, 5)
        },
    }

    OUT.write_text(json.dumps(result, indent=2, default=str))
    print("wrote", OUT)
    # brief stdout
    for n in (2, 3, 4, 5):
        a = result["n_analyses"][str(n)]
        print(f"n={n} K={a['K']} sigma={a['sigma']} g_empty={a['g_empty']} "
              f"one={a['one_stone_hist']} two={a['two_stone_hist']} "
              f"P={a['n_P_pairs']} iso={a['n_isolated_vertices_J']} "
              f"sigma_holes={a['sigma_layer_holes'].get('missing')} "
              f"thm={a['thm_uniform_h_absent_in_two']} viol={a['thm_violations']}")
    b = result["b312"]
    print("B312", b["n_TD"], "TD /", b["n_nonTD"], "nonTD /", b["n_P"], "P")
    print("best_pair", b["best_pair"]["keys"], "mixed", b["best_pair"]["n_mixed"])
    print("B320 mixed keys", result["b320"]["n_mixed_keys"], "acc", result["b320"]["accuracy"])


if __name__ == "__main__":
    main()

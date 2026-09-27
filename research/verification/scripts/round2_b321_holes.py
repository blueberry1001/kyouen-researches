#!/usr/bin/env python3
"""Round-2 B321-B323, B329: nimber holes at saturation-start layer.

Uses existing cycle5-grundy-n{2..6}.json histograms plus a fresh n=4 (and
n=5 sample) child-value must-pair check for B329.
Integer arithmetic only.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square

ROOT = Path(__file__).resolve().parents[3]
NIGHT = ROOT / "night-research"
OUT = ROOT / "research" / "verification" / "round2_b321.json"

K_N = {2: 3, 3: 5, 4: 7, 5: 9, 6: 11}
SIGMA = {2: 2, 3: 4, 4: 2, 5: 3, 6: 3}


def load_layers() -> dict:
    layers = {}
    for n in (2, 3, 4, 5, 6):
        fn = "cycle5-grundy-n6-cap14.json" if n == 6 else f"cycle5-grundy-n{n}.json"
        d = json.loads((NIGHT / fn).read_text(encoding="utf-8"))
        lp = d["layer_profiles"]
        hist = {}
        for k, v in lp.items():
            ki = int(k)
            hist[ki] = {int(g): int(c) for g, c in v["grundy_hist"].items()}
        layers[n] = hist
    return layers


def analyze_holes(layers: dict) -> dict:
    out = {}
    for n, hist in layers.items():
        kn = K_N[n]
        sig = SIGMA[n]
        # verify sigma definition against histograms
        computed_sigma = None
        for k in sorted(hist):
            if hist[k]:
                mx = max(hist[k])
                if mx == kn - k:
                    computed_sigma = k
                    break
        present = set(hist[sig])
        target = kn - sig
        missing = [j for j in range(target + 1) if j not in present]
        consecutive_pairs = []
        for j in missing:
            if (j + 1) in missing:
                consecutive_pairs.append((j, j + 1))
        pos_missing = [j for j in missing if j > 0]
        non_pow2 = [j for j in pos_missing if (j & (j - 1)) != 0]
        zero_missing = 0 in missing
        out[n] = {
            "K": kn,
            "sigma_given": sig,
            "sigma_computed": computed_sigma,
            "sigma_match": computed_sigma == sig,
            "layer_k": sig,
            "K_minus_sigma": target,
            "present": sorted(present),
            "missing": missing,
            "consecutive_missing_pairs": consecutive_pairs,
            "positive_missing": pos_missing,
            "positive_missing_non_pow2": non_pow2,
            "zero_missing": zero_missing,
            "layer_hist": {str(g): c for g, c in sorted(hist[sig].items())},
        }
    return out


def full_positions(n: int):
    """Yield (occ, g, legal_moves_list) for all reachable safe sets."""
    B = board_square(n)
    reachable = {0}
    stack = [0]
    while stack:
        occ = stack.pop()
        for u in B.legal_moves(occ):
            nxt = occ | (1 << u)
            if nxt not in reachable:
                reachable.add(nxt)
                stack.append(nxt)
    g = {}

    def ev(occ: int) -> int:
        hit = g.get(occ)
        if hit is not None:
            return hit
        mv = B.legal_moves(occ)
        if not mv:
            g[occ] = 0
            return 0
        seen = {ev(occ | (1 << u)) for u in mv}
        x = 0
        while x in seen:
            x += 1
        g[occ] = x
        return x

    ev(0)
    Lc = {occ: B.legal_moves(occ) for occ in reachable}
    return B, reachable, g, Lc


def b329_must_pair(n: int, missing_a: list[int]) -> dict:
    """For each missing a at the sigma layer: check
    'if children contain 0..a-1 then a also appears among children'.

    This is the geometric must-pair behind mex; the mex identity itself is
    trivial and is NOT counted. Here we test the concrete child-value sets
    of every position at the sigma layer.
    """
    B, reachable, g, Lc = full_positions(n)
    sig = SIGMA[n]
    by_k: dict[int, list[int]] = defaultdict(list)
    for occ in reachable:
        by_k[occ.bit_count()].append(occ)
    result = {}
    for a in missing_a:
        need = set(range(a))  # 0..a-1
        viol_parents = []
        checked = 0
        for occ in by_k[sig]:
            children = [occ | (1 << u) for u in Lc[occ]]
            if not children:
                continue
            cg = {g[ch] for ch in children}
            if need <= cg:
                checked += 1
                if a not in cg:
                    viol_parents.append(occ)
        result[str(a)] = {
            "antecedent_true_count": checked,
            "violations": len(viol_parents),
            "violation_masks": viol_parents[:5],
        }
    # also record child-value coverage patterns at sigma layer
    patterns = defaultdict(int)
    for occ in by_k[sig]:
        children = [occ | (1 << u) for u in Lc[occ]]
        cg = frozenset(g[ch] for ch in children) if children else frozenset()
        patterns[tuple(sorted(cg))] += 1
    result["child_value_patterns_at_sigma"] = {
        ",".join(map(str, k)): v for k, v in sorted(patterns.items())
    }
    return result


def main() -> None:
    layers = load_layers()
    holes = analyze_holes(layers)

    b329 = {}
    for n, miss in ((4, holes[4]["missing"]), (5, holes[5]["missing"])):
        print(f"[B329] computing n={n} missing={miss}", flush=True)
        b329[n] = b329_must_pair(n, miss)

    out = {
        "holes_by_n": holes,
        "B321": {
            "all_n_no_consecutive_missing": all(
                not holes[n]["consecutive_missing_pairs"] for n in holes
            ),
            "details": {
                str(n): holes[n]["consecutive_missing_pairs"] for n in holes
            },
        },
        "B322": {
            "all_missing_positive_are_pow2": all(
                not holes[n]["positive_missing_non_pow2"] for n in holes
            ),
            "positive_missing": {
                str(n): holes[n]["positive_missing"] for n in holes
            },
        },
        "B323": {
            "witness_n": [n for n in holes if holes[n]["zero_missing"]],
            "per_n_zero_missing": {
                str(n): holes[n]["zero_missing"] for n in holes
            },
        },
        "B329": b329,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT)
    print(json.dumps({k: out[k] for k in ("B321", "B322", "B323")}, indent=2))


if __name__ == "__main__":
    main()

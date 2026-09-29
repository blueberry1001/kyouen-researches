#!/usr/bin/env python3
"""B376: for each of the 408 maximal 8-stone sets on 8x8, compute the minimum
number of covering triples (circles/lines through 3 stones) needed to forbid all
56 empty points. Existence claim: some set has cover size <= 12.

Also B380-class stats and B370 sample (1-out 2-in shrink failure reasons).
"""
from __future__ import annotations

import json
import struct
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square, det4  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
BIN = ROOT / "research" / "verification" / "round4_b371.bin"
OUT = ROOT / "research" / "verification" / "round5_b301_b376.json"


def load_masks(path: Path):
    data = path.read_bytes()
    (count,) = struct.unpack_from("<Q", data, 0)
    return list(struct.unpack_from(f"<{count}Q", data, 8))


def cover_data(b: Board, S_bits: list[int]):
    empties = [i for i in range(b.V) if i not in S_bits]
    triples = []
    for tri in combinations(S_bits, 3):
        covers = 0
        for e in empties:
            ids = list(tri) + [e]
            rows = [b.rows[i] for i in ids]
            if det4(*rows) == 0:
                covers |= 1 << empties.index(e)
        if covers:
            triples.append(covers)
    return empties, triples


def greedy_size(empties, triples):
    n = len(empties)
    full = (1 << n) - 1
    covered = 0
    used = [False] * len(triples)
    size = 0
    while covered != full:
        best_i, best_gain = -1, 0
        for i, m in enumerate(triples):
            if used[i]:
                continue
            gain = bin(m & ~covered).count("1")
            if gain > best_gain:
                best_gain = gain
                best_i = i
        if best_i < 0 or best_gain == 0:
            return None  # cannot cover
        used[best_i] = True
        covered |= triples[best_i]
        size += 1
    return size


def exact_within(triples, n, budget):
    """Return True if a cover of size <= budget exists (complete DFS with pruning)."""
    full = (1 << n) - 1
    # sort triples by popcount desc for better pruning
    tmsk = sorted(triples, key=lambda m: -bin(m).count("1"))
    # precompute which triples cover each bit
    coverers = [[] for _ in range(n)]
    for i, m in enumerate(tmsk):
        for e in range(n):
            if (m >> e) & 1:
                coverers[e].append(i)
    nodes = [0]
    NODE_LIMIT = 2_000_000

    def dfs(covered, start, chosen):
        nodes[0] += 1
        if nodes[0] > NODE_LIMIT:
            return False
        if covered == full:
            return True
        if chosen >= budget:
            return False
        # choose uncovered element with fewest coverers that are not yet redundant
        best_e, best_cnt = -1, 10**9
        for e in range(n):
            if (covered >> e) & 1:
                continue
            cnt = 0
            for i in coverers[e]:
                if tmsk[i] & ~covered:
                    cnt += 1
            if cnt < best_cnt:
                best_cnt = cnt
                best_e = e
                if cnt == 0:
                    return False
        # try coverers of best_e
        for i in coverers[best_e]:
            nm = tmsk[i]
            if not (nm & ~covered):
                continue
            if dfs(covered | nm, i + 1, chosen + 1):
                return True
        return False

    return dfs(0, 0, 0)


def main():
    b = board_square(8)
    masks = load_masks(BIN)
    print(f"loaded {len(masks)} maximal 8-sets")

    greedy_hist = {}
    exact_le12 = []
    exact_found = []  # (idx, size) when we find one within budget
    min_greedy = 99
    max_greedy = 0
    collinear_hist = {}
    results = []

    for si, T in enumerate(masks):
        S_bits = [i for i in range(b.V) if (T >> i) & 1]
        empties, triples = cover_data(b, S_bits)
        assert len(empties) == 56
        # sanity: every empty must be covered by at least one triple (maximal)
        allc = 0
        for m in triples:
            allc |= m
        if allc != (1 << 56) - 1:
            print(f"WARNING set {si} not fully coverable? uncovered={bin(((1<<56)-1)&~allc).count('1')}")
        g = greedy_size(empties, triples)
        greedy_hist[g] = greedy_hist.get(g, 0) + 1
        if g is not None:
            min_greedy = min(min_greedy, g)
            max_greedy = max(max_greedy, g)
        # count collinear triples among the stones
        n_col = 0
        for tri in combinations(S_bits, 3):
            (x0, y0), (x1, y1), (x2, y2) = [b.points[i] for i in tri]
            if (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) == 0:
                n_col += 1
        collinear_hist[n_col] = collinear_hist.get(n_col, 0) + 1

        # exact within 12 (the claim threshold) — only on a sample to keep runtime sane
        found12 = None
        if si < 8:
            found12 = exact_within(triples, 56, 12)
            if found12:
                exact_le12.append(si)
        results.append({
            "idx": si,
            "T": S_bits,
            "greedy": g,
            "n_triples": len(triples),
            "n_collinear_triples": n_col,
            "exact_le12": found12,
        })
        if si % 40 == 0:
            print(f"  set {si}: greedy={g} triples={len(triples)} le12={found12}", flush=True)

    print("greedy hist:", greedy_hist)
    print("collinear triple count hist:", collinear_hist)
    print("min/max greedy:", min_greedy, max_greedy)
    print("n with exact cover <= 12:", len(exact_le12), "idx:", exact_le12[:10])

    res = {
        "B376": {
            "n_sets": len(masks),
            "greedy_hist": {str(k): v for k, v in sorted(greedy_hist.items())},
            "collinear_triple_hist": {str(k): v for k, v in sorted(collinear_hist.items())},
            "min_greedy": min_greedy,
            "max_greedy": max_greedy,
            "n_exact_le12": len(exact_le12),
            "exact_le12_idx": exact_le12,
            "results": results,
        }
    }

    # B370 sample: 1-out 2-in shrink failure classification
    print("=== B370 sample ===")
    fail_forbidden = fail_uncovered = success = total = 0
    for T in masks[:40]:
        bits = [i for i in range(b.V) if (T >> i) & 1]
        for out in bits:
            base = T & ~(1 << out)
            empties = [i for i in range(b.V) if not ((base >> i) & 1)]
            for a, c in combinations(empties, 2):
                cand = base | (1 << a) | (1 << c)
                total += 1
                if not b.is_safe(cand):
                    fail_forbidden += 1
                else:
                    L = b.legal_moves(cand)
                    if len(L) == 0:
                        success += 1
                    else:
                        fail_uncovered += 1
    res["B370"] = {
        "n_sets_sampled": 40,
        "n_candidates": total,
        "fail_forbidden_quad": fail_forbidden,
        "fail_uncovered_point": fail_uncovered,
        "success_size9_maximal": success,
    }
    print(json.dumps(res["B370"], indent=2))

    OUT.write_text(json.dumps(res, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""round5_b101a_defs — B129/B130（変形・勝敗境界）と B106/B107（識別点数）を n<=5 で深掘り。

- B129: 最小極大配置 vs 最大配置 の 1-swap 可動性比較
- B130: k 点安全集合の 1 点移動グラフ成分と P/N の保存
- B106/B107: 識別曲線 min_det の精密化
- 出力: research/verification/round5_b101a_defs.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, square_points  # noqa: E402

OUT = ROOT / "research" / "verification" / "round5_b101a_defs.json"


def load_masks(path: Path) -> list[int]:
    raw = path.read_bytes()
    import struct
    cnt = len(raw) // 8
    if cnt == 0:
        return []
    return list(struct.unpack(f"<{cnt}Q", raw))


def one_swap_neighbors(board: Board, mask: int) -> list[int]:
    """Remove one stone and add one empty stone, still safe. (deformation step)"""
    n_pts = board.V
    stones = [i for i in range(n_pts) if (mask >> i) & 1]
    empties = [i for i in range(n_pts) if not ((mask >> i) & 1)]
    out = []
    for r in stones:
        base = mask ^ (1 << r)
        for a in empties:
            if a == r:
                continue
            cand = base | (1 << a)
            if board.is_safe(cand):
                out.append(cand)
    return out


def b129(n: int) -> dict:
    board = Board(square_points(n))
    max_path = DATA / f"maximal_n{n}.bin"
    max_sets = load_masks(max_path)
    # need ALL maximal sets to find min-size ones. For n<=5, enumerate all maximal.
    # Use safe_n{n}.bin which has all safe sets; filter maximal.
    safe_path = DATA / f"safe_n{n}.bin"
    if not safe_path.exists():
        return {"error": f"missing {safe_path}"}
    safe_sets = load_masks(safe_path)
    # maximal = safe and no legal move
    maximal = []
    for m in safe_sets:
        if not board.legal_moves(m):
            maximal.append(m)
    sizes = [m.bit_count() for m in maximal]
    smin, smax = min(sizes), max(sizes)
    min_sets = [m for m in maximal if m.bit_count() == smin]
    max_sets_k = [m for m in maximal if m.bit_count() == smax]

    def swap_stats(sets):
        if not sets:
            return {"n": 0, "mean_swaps": 0.0, "mean_norm": 0.0, "zero_frac": 1.0}
        cnts = []
        for m in sets:
            nb = one_swap_neighbors(board, m)
            cnts.append(len(nb))
        mean = sum(cnts) / len(cnts)
        norm = mean / smin if sets is min_sets else mean / smax
        zero = sum(1 for c in cnts if c == 0) / len(cnts)
        return {
            "n": len(sets),
            "mean_swaps": mean,
            "mean_norm": (sum(c / (smin if sets is min_sets else smax) for c in cnts) / len(cnts)),
            "zero_frac": zero,
            "min_swaps": min(cnts),
            "max_swaps": max(cnts),
        }

    return {
        "n": n,
        "n_maximal": len(maximal),
        "smin": smin,
        "smax": smax,
        "n_min_sets": len(min_sets),
        "n_max_sets": len(max_sets_k),
        "min_side": swap_stats(min_sets),
        "max_side": swap_stats(max_sets_k),
        # B129 claims max is MORE frozen => max_side.mean_norm < min_side.mean_norm
        "b129_supports": (
            swap_stats(max_sets_k)["mean_norm"] < swap_stats(min_sets)["mean_norm"]
            if min_sets and max_sets_k
            else None
        ),
    }


def b130(n: int, k: int) -> dict:
    """k-point safe sets, 1-point-move graph components, P/N purity."""
    board = Board(square_points(n))
    safe_path = DATA / f"safe_n{n}.bin"
    if not safe_path.exists():
        return {"error": f"missing {safe_path}"}
    safe_sets = load_masks(safe_path)
    level = [m for m in safe_sets if m.bit_count() == k]
    # 1-point move: remove one, add one (same as 1-swap) — or just "deformation step"
    # Hypothesis says "1点移動グラフ" which likely means the 1-swap deformation graph.
    index = {m: i for i, m in enumerate(level)}
    parent = list(range(len(level)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for m in level:
        for nb in one_swap_neighbors(board, m):
            if nb in index:
                union(index[m], index[nb])

    comps = defaultdict(list)
    for m in level:
        comps[find(index[m])].append(m)

    # P/N: player to move wins if exists a move to a losing position.
    # A safe set is terminal if no legal move (place a stone). Outcome = Grundy via last-move-wins.
    # We need outcomes for all safe sets of size <= k (the game places stones).
    # Memoize outcomes for all safe subsets (could be large). For n<=5, |safe| is manageable.
    memo: dict[int, int] = {}

    def outcome(occ: int) -> int:
        """1 if player to move wins, 0 loses."""
        if occ in memo:
            return memo[occ]
        moves = board.legal_moves(occ)
        if not moves:
            memo[occ] = 0  # no move => loses (normal play last-move-wins? actually no-move loses)
            return 0
        # win if some move leads to opponent loss
        w = 0
        for v in moves:
            if outcome(occ | (1 << v)) == 0:
                w = 1
                break
        memo[occ] = w
        return w

    # only evaluate outcomes for sets on the level and below (game only places stones)
    # but outcome() recurses upward so it's fine
    n_mixed = 0
    n_pure = 0
    for root, members in comps.items():
        outs = {outcome(m) for m in members}
        if len(outs) == 1:
            n_pure += 1
        else:
            n_mixed += 1

    return {
        "n": n,
        "k": k,
        "n_level_sets": len(level),
        "n_components": len(comps),
        "n_pure_components": n_pure,
        "n_mixed_components": n_mixed,
        "largest_component": max((len(v) for v in comps.values()), default=0),
        "b130_supports": n_mixed == 0 and len(comps) > 1,
    }


def b106_ident(n: int) -> dict:
    """For each max set, find the min |C| such that C ⊆ S and no other max set contains C."""
    board = Board(square_points(n))
    max_sets = load_masks(DATA / f"maximal_n{n}.bin")
    # only keep max-size ones (K_n)
    sizes = [m.bit_count() for m in max_sets]
    K = max(sizes) if sizes else 0
    M = [m for m in max_sets if m.bit_count() == K]
    # For each S, for c=1..3 try all subsets of size c that uniquely identify S
    ident_needed = []
    for S in M:
        stones = [i for i in range(board.V) if (S >> i) & 1]
        found = None
        for c in range(1, min(5, len(stones)) + 1):
            from itertools import combinations
            ok = False
            for sub in combinations(stones, c):
                cmask = sum(1 << i for i in sub)
                # does any other max set contain all of sub?
                if all((T & cmask) == cmask for T in M if T != S):
                    continue
                ok = True
                break
            if ok:
                found = c
                break
        ident_needed.append(found if found is not None else -1)
    valid = [x for x in ident_needed if x > 0]
    return {
        "n": n,
        "K": K,
        "n_max": len(M),
        "min_det": min(valid) if valid else -1,
        "max_det": max(valid) if valid else -1,
        "mean_det": (sum(valid) / len(valid)) if valid else None,
        "ident_curve": {
            str(c): sum(1 for x in ident_needed if x > 0 and x <= c) for c in range(1, 6)
        },
        "n_unidentified": sum(1 for x in ident_needed if x < 0),
    }


def main():
    out = {}
    print("=== B129", flush=True)
    for n in (4, 5):
        print(f"n={n} ...", flush=True)
        r = b129(n)
        out[f"b129_n{n}"] = r
        print(" ", r, flush=True)

    print("=== B130", flush=True)
    for n, k in [(4, 3), (4, 4), (5, 3), (5, 4)]:
        print(f"n={n} k={k} ...", flush=True)
        r = b130(n, k)
        out[f"b130_n{n}k{k}"] = r
        print(" ", r, flush=True)

    print("=== B106 ident", flush=True)
    for n in (4, 5, 6):
        print(f"n={n} ...", flush=True)
        r = b106_ident(n)
        out[f"b106_n{n}"] = r
        print(" ", r, flush=True)

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()

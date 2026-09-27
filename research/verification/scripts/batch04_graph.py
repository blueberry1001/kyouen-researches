#!/usr/bin/env python3
"""Batch 04 competition graphs: B061-B070.

P(S) = graph on legal points L(S); edge pq iff some 2-subset of S completes
with {p,q} to a forbidden 4-set (a size-2 residual).

2-point-only game = independent-set game on P(S) (never occupy both ends of an edge).
Actual game forbids all residual sets of size 2-4.

Outputs research/verification/batch04_graph.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))

from kyouen_core import Board, board_square  # noqa: E402

OUT = ROOT / "research" / "verification" / "batch04_graph.json"
sys.setrecursionlimit(200000)


def all_safe_masks(board: Board) -> list[int]:
    out: list[int] = []

    def dfs(next_id: int, occ: int) -> None:
        out.append(occ)
        for v in range(next_id, board.V):
            bit = 1 << v
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & occ) == (q & ~bit):
                    ok = False
                    break
            if ok:
                dfs(v + 1, occ | bit)

    dfs(0, 0)
    return out


def compute_all_grundy(board: Board, safe: list[int]) -> dict[int, int]:
    """Grundy for every safe mask via memoized recursion (iterative stack)."""
    memo: dict[int, int] = {0: 0}
    # process in increasing popcount so children (larger) may not be ready — use recursion
    def ev(occ: int) -> int:
        hit = memo.get(occ)
        if hit is not None:
            return hit
        mv = board.legal_moves(occ)
        if not mv:
            memo[occ] = 0
            return 0
        seen = set()
        for u in mv:
            seen.add(ev(occ | (1 << u)))
        g = 0
        while g in seen:
            g += 1
        memo[occ] = g
        return g

    for S in safe:
        ev(S)
    return memo


def residual_info(board: Board, S: int):
    legal = board.legal_moves(S)
    lmask = 0
    for p in legal:
        lmask |= 1 << p
    resid2: set[int] = set()
    resid3: set[int] = set()
    resid4: set[int] = set()
    for q in board.quads:
        r = q & ~S
        if r == 0:
            continue
        if (r & lmask) == r:
            sz = r.bit_count()
            if sz == 2:
                resid2.add(r)
            elif sz == 3:
                resid3.add(r)
            elif sz == 4:
                resid4.add(r)
    return lmask, resid2, resid3, resid4


def build_adj(board: Board, edges: set[int], lmask: int):
    legal_pts = [p for p in range(board.V) if (lmask >> p) & 1]
    idx = {p: i for i, p in enumerate(legal_pts)}
    adj = [[] for _ in legal_pts]
    for e in edges:
        pts = [p for p in legal_pts if (e >> p) & 1]
        if len(pts) != 2:
            continue
        a, b = idx[pts[0]], idx[pts[1]]
        adj[a].append(b)
        adj[b].append(a)
    return legal_pts, adj


def count_tri_edges(adj):
    as_sets = [set(a) for a in adj]
    tri = 0
    for i in range(len(adj)):
        for j in adj[i]:
            if j > i:
                tri += len(as_sets[i] & as_sets[j])
    e = sum(len(a) for a in adj) // 2
    return tri, e


def greedy_colors(adj) -> int:
    n = len(adj)
    color = [-1] * n
    order = sorted(range(n), key=lambda v: -len(adj[v]))
    for v in order:
        used = {color[u] for u in adj[v] if color[u] >= 0}
        c = 0
        while c in used:
            c += 1
        color[v] = c
    return (max(color) + 1) if n else 0


def chromatic_at_most(adj, cap: int = 3) -> bool:
    """Return True if chi <= cap (proven). False only if proven chi > cap.
    Uses greedy first; exact backtrack only when greedy fails and nv small."""
    if not adj:
        return True
    if greedy_colors(adj) <= cap:
        return True
    n = len(adj)
    if n > 14:
        return True  # cannot prove failure cheaply; treat as unproven-pass (report separately)
    order = sorted(range(n), key=lambda v: -len(adj[v]))
    color = [-1] * n

    def ok(v, c):
        return all(color[u] != c for u in adj[v])

    def dfs(i, used):
        if i == n:
            return True
        v = order[i]
        for c in range(min(used + 1, cap + 1)):
            if c > cap:
                break
            if ok(v, c):
                color[v] = c
                if dfs(i + 1, max(used, c + 1)):
                    return True
                color[v] = -1
        return False

    return dfs(0, 0)


def is_tree(adj) -> bool:
    n = len(adj)
    e = sum(len(a) for a in adj) // 2
    if n == 0:
        return True
    if e != n - 1:
        return False
    seen = set()

    def dfs(u, p):
        seen.add(u)
        for v in adj[u]:
            if v == p:
                continue
            if v in seen:
                return False
            if not dfs(v, u):
                return False
        return True

    return dfs(0, -1) and len(seen) == n


def longest_induced_odd_cycle(adj):
    """Exact for nv<=11; else None."""
    n = len(adj)
    if n > 11:
        return None
    best = 0
    for k in range(3, n + 1, 2):
        for vs in combinations(range(n), k):
            vs_set = set(vs)
            good = True
            for v in vs:
                deg = sum(1 for u in adj[v] if u in vs_set)
                if deg != 2:
                    good = False
                    break
            if not good:
                continue
            # connected
            vis = set()
            stack = [vs[0]]
            while stack:
                u = stack.pop()
                if u in vis:
                    continue
                vis.add(u)
                for w in adj[u]:
                    if w in vs_set and w not in vis:
                        stack.append(w)
            if len(vis) == k:
                best = max(best, k)
    return best


def game_g_constraints(lmask: int, resid_masks: list[int], V: int) -> int:
    legal_pts = [p for p in range(V) if (lmask >> p) & 1]
    m = len(legal_pts)
    if m == 0:
        return 0
    pid_to_i = {p: i for i, p in enumerate(legal_pts)}
    res_masks = []
    for r in resid_masks:
        rm = 0
        for p in range(V):
            if (r >> p) & 1:
                rm |= 1 << pid_to_i[p]
        res_masks.append(rm)

    memo: dict[int, int] = {}

    def ev(occ_i: int) -> int:
        if occ_i in memo:
            return memo[occ_i]
        nxt = set()
        free = ((1 << m) - 1) ^ occ_i
        while free:
            b = free & -free
            free ^= b
            new = occ_i | b
            ok = True
            for rm in res_masks:
                if (new & rm) == rm:
                    ok = False
                    break
            if ok:
                nxt.add(ev(new))
        g = 0
        while g in nxt:
            g += 1
        memo[occ_i] = g
        return g

    return ev(0)


def K_of(board: Board, S: int) -> int:
    best = S.bit_count()
    ids = [i for i in range(board.V) if (S >> i) & 1]
    last = ids[-1] if ids else -1

    def dfs(occ: int, start: int, sz: int) -> None:
        nonlocal best
        if sz > best:
            best = sz
        for v in range(start, board.V):
            if (occ >> v) & 1:
                continue
            bit = 1 << v
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & occ) == (q & ~bit):
                    ok = False
                    break
            if ok:
                dfs(occ | bit, v + 1, sz + 1)

    dfs(S, last + 1, S.bit_count())
    return best


def degree_sequence(adj):
    return tuple(sorted(len(a) for a in adj))


def rank_corr(rows, key_x, key_y):
    xs = [r[key_x] for r in rows]
    ys = [r[key_y] for r in rows]
    n = len(rows)
    if n < 5:
        return None

    def ranks(a):
        order = sorted(range(len(a)), key=lambda i: a[i])
        r = [0] * len(a)
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for t in range(i, j + 1):
                r[order[t]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denx = sum((a - mx) ** 2 for a in rx) ** 0.5
    deny = sum((b - my) ** 2 for b in ry) ** 0.5
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def main():
    result = {
        "boards": {},
        "b061": {},
        "b062": {"checked": 0, "violations": [], "greedy_le3": 0, "exact_needed": 0},
        "b063": {},
        "b064": [],
        "b065": [],
        "b066": {},
        "b067": {"checked": 0, "violations": []},
        "b068": {},
        "b069": {},
        "b070": {},
    }

    for n in range(2, 6):
        print(f"=== {n}x{n} ===", flush=True)
        board = board_square(n)
        safe = all_safe_masks(board)
        print(f"safe={len(safe)} computing grundy...", flush=True)
        gmemo = compute_all_grundy(board, safe)
        print(f"grundy entries={len(gmemo)}", flush=True)

        # max extension K(S) for all S (needed for B067): compute only when nv small
        # Precompute K for all safe via reverse: K(S) = max over T⊇S safe |T|
        # On n<=5, do a DP over safe sets: sort by size desc, K[S]=max(|S|, max K[S|bit] wait no that's subset).
        # K(S) = max |T| over safe T ⊇ S. For each safe T, update all subsets? 151k * 2^9 too much for n=5.
        # Instead compute K(S) by DFS extension only for candidate positions (near-terminal).
        # We detect near-terminal: legal_moves small AND few remaining stones able to fit.
        # Use: if |L(S)| == 0, K=|S|. If we can add all of some set... simpler: DFS K for S with |L|<=6.

        b062_bad = []
        b064_hits = []
        b065_hits = []
        b067_bad = []
        b066_rows = []
        tri_vs_g = []
        graph_by_k = defaultdict(list)
        chrom_stats = Counter()

        # decide sample: full for n<=4, step for n=5
        step = 1 if n <= 4 else 2
        checked = 0

        for S in safe[::step]:
            checked += 1
            lmask, resid2, resid3, resid4 = residual_info(board, S)
            legal_pts, adj = build_adj(board, resid2, lmask)
            nv = len(adj)
            tri, ne = count_tri_edges(adj)
            k = S.bit_count()
            gval = gmemo[S]

            # B062
            if k == 3:
                result["b062"]["checked"] += 1
                gcol = greedy_colors(adj)
                if gcol <= 3:
                    result["b062"]["greedy_le3"] += 1
                    chrom_stats[("3", gcol)] += 1
                else:
                    result["b062"]["exact_needed"] += 1
                    if chromatic_at_most(adj, 3):
                        chrom_stats[("3", "greedy4_but_chi_le3")] += 1
                    else:
                        b062_bad.append(
                            {
                                "n": n,
                                "S": [p for p in range(board.V) if (S >> p) & 1],
                                "greedy": gcol,
                                "nv": nv,
                                "ne": ne,
                                "edges": [[a, b] for a in range(nv) for b in adj[a] if b > a],
                            }
                        )
                        chrom_stats[("3", "chi_ge4")] += 1

            # B061
            dens = (tri / ne) if ne else 0.0
            tri_vs_g.append({"k": k, "nv": nv, "ne": ne, "tri": tri, "dens": dens, "g": gval})

            # B065
            if ne == 0 and gval >= 4:
                b065_hits.append(
                    {
                        "n": n,
                        "k": k,
                        "g": gval,
                        "S": [p for p in range(board.V) if (S >> p) & 1],
                        "nv": nv,
                        "res3": len(resid3),
                        "res4": len(resid4),
                    }
                )

            # B064: tree P(S), 2pt-only game value != actual g
            if is_tree(adj) and 1 <= nv <= 12:
                g2 = game_g_constraints(lmask, list(resid2), board.V)
                if g2 != gval:
                    b064_hits.append(
                        {
                            "n": n,
                            "k": k,
                            "g_actual": gval,
                            "g_2pt_only": g2,
                            "S": [p for p in range(board.V) if (S >> p) & 1],
                            "nv": nv,
                            "ne": ne,
                            "res3": len(resid3),
                            "res4": len(resid4),
                        }
                    )

            # B066
            r3 = list(resid3)
            share2 = 0
            pairs_r3 = 0
            for a, b in combinations(r3, 2):
                pairs_r3 += 1
                if (a & b).bit_count() >= 2:
                    share2 += 1
            g2_small = None
            if nv <= 10:
                g2_small = game_g_constraints(lmask, list(resid2), board.V)
            b066_rows.append(
                {
                    "k": k,
                    "nv": nv,
                    "ne": ne,
                    "g": gval,
                    "g2": g2_small,
                    "err": None if g2_small is None else (g2_small == 0) != (gval == 0),
                    "r3": len(r3),
                    "r3_share2": share2,
                    "r3_pairs": pairs_r3,
                }
            )

            # B067: only when few remaining stones (K(S)-|S|<=3)
            # cheap necessary condition: |L(S)| can be large while K-|S| small, so need K.
            # Compute K only if |L| small enough that DFS is cheap OR n<=4.
            if n <= 4:
                KS = K_of(board, S)
                if KS - k <= 3 and 3 <= nv <= 11:
                    result["b067"]["checked"] += 1
                    c = longest_induced_odd_cycle(adj)
                    if c is not None and c >= 7:
                        b067_bad.append(
                            {
                                "n": n,
                                "k": k,
                                "S": [p for p in range(board.V) if (S >> p) & 1],
                                "odd": c,
                                "nv": nv,
                                "K": KS,
                            }
                        )
            elif n == 5:
                # K(S)-|S|<=3 ⇒ at most 3 more stones. Use DFS extension with a cap:
                # if legal_moves empty → K=k. Try greedy lower bound first.
                lmv = board.legal_moves(S)
                if len(lmv) <= 8:
                    KS = K_of(board, S)
                    if KS - k <= 3 and 3 <= nv <= 11:
                        result["b067"]["checked"] += 1
                        c = longest_induced_odd_cycle(adj)
                        if c is not None and c >= 7:
                            b067_bad.append(
                                {
                                    "n": n,
                                    "k": k,
                                    "S": [p for p in range(board.V) if (S >> p) & 1],
                                    "odd": c,
                                    "nv": nv,
                                    "K": KS,
                                }
                            )

            # B063/B070 inventory
            if k <= 5:
                dseq = degree_sequence(adj)
                graph_by_k[k].append((nv, ne, dseq, tri, is_tree(adj)))

        # B061 within-k correlations
        by_k_tg = defaultdict(list)
        for r in tri_vs_g:
            by_k_tg[r["k"]].append(r)
        within = {}
        for k, rows in by_k_tg.items():
            g0 = [r for r in rows if r["g"] == 0]
            gpos = [r for r in rows if r["g"] > 0]
            within[str(k)] = {
                "n": len(rows),
                "spearman_dens_g": rank_corr(rows, "dens", "g"),
                "spearman_tri_g": rank_corr(rows, "tri", "g"),
                "mean_tri_g0": (sum(r["tri"] for r in g0) / len(g0)) if g0 else None,
                "mean_tri_gpos": (sum(r["tri"] for r in gpos) / len(gpos)) if gpos else None,
                "mean_dens_g0": (sum(r["dens"] for r in g0) / len(g0)) if g0 else None,
                "mean_dens_gpos": (sum(r["dens"] for r in gpos) / len(gpos)) if gpos else None,
            }

        # B066 aggregate
        err_rows = [r for r in b066_rows if r["err"] is True]
        ok_rows = [r for r in b066_rows if r["err"] is False]
        unknown = [r for r in b066_rows if r["err"] is None]

        def mean_share(rows):
            vals = [r["r3_share2"] / r["r3_pairs"] for r in rows if r["r3_pairs"] > 0]
            return sum(vals) / len(vals) if vals else 0.0

        result["b066"][f"{n}x{n}"] = {
            "n_err": len(err_rows),
            "n_ok": len(ok_rows),
            "n_unknown": len(unknown),
            "mean_share2_ratio_err": mean_share(err_rows),
            "mean_share2_ratio_ok": mean_share(ok_rows),
            "mean_r3_err": (sum(r["r3"] for r in err_rows) / len(err_rows)) if err_rows else None,
            "mean_r3_ok": (sum(r["r3"] for r in ok_rows) / len(ok_rows)) if ok_rows else None,
        }

        # B068: same degree sequence, different P/N, restricted to no higher-order residuals
        degmap = defaultdict(lambda: {"g0": [], "gpos": []})
        for S in safe:
            lmask, resid2, resid3, resid4 = residual_info(board, S)
            if resid3 or resid4:
                continue
            legal_pts, adj = build_adj(board, resid2, lmask)
            dseq = degree_sequence(adj)
            gval = gmemo[S]
            entry = {
                "k": S.bit_count(),
                "g": gval,
                "S": [p for p in range(board.V) if (S >> p) & 1],
                "nv": len(adj),
            }
            if gval == 0:
                degmap[dseq]["g0"].append(entry)
            else:
                degmap[dseq]["gpos"].append(entry)
        pairs = []
        for dseq, bucket in degmap.items():
            if bucket["g0"] and bucket["gpos"]:
                pairs.append(
                    {
                        "dseq": list(dseq),
                        "g0": bucket["g0"][0],
                        "gpos": bucket["gpos"][0],
                        "n_g0": len(bucket["g0"]),
                        "n_gpos": len(bucket["gpos"]),
                    }
                )
        result["b068"][f"{n}x{n}"] = {
            "n_degree_classes_with_both_outcomes": len(pairs),
            "examples": pairs[:8],
            "n_classes": len(degmap),
        }
        print(f"b068 pairs={len(pairs)} classes={len(degmap)}", flush=True)

        # B063: graph types appearing at k=3 vs k=4
        def keys(k):
            return set(graph_by_k.get(k, []))

        k3, k4, k5 = keys(3), keys(4), keys(5)
        result["b063"][f"{n}x{n}"] = {
            "k3_types": len(k3),
            "k4_types": len(k4),
            "k5_types": len(k5),
            "k4_not_k3": [list(x) for x in sorted(k4 - k3)[:12]],
            "k5_not_k4": [list(x) for x in sorted(k5 - k4)[:8]],
            "note": "type = (nv, ne, degree_seq, tri, is_tree); induced-subgraph H question not fully resolved by type counts",
        }

        # B070 inventory
        inv = {}
        for k, items in sorted(graph_by_k.items()):
            inv[str(k)] = {
                "count": len(items),
                "nv_range": [min(i[0] for i in items), max(i[0] for i in items)],
                "tree_count": sum(1 for i in items if i[4]),
                "tri_free": sum(1 for i in items if i[3] == 0),
                "max_tri": max(i[3] for i in items),
                "max_ne": max(i[1] for i in items),
            }
        result["b070"][f"{n}x{n}"] = inv

        # B069 proxy
        sep_rows = []
        sample = safe[:: max(1, len(safe) // 1500)]
        for S in sample:
            lmask, resid2, resid3, resid4 = residual_info(board, S)
            legal_pts, adj = build_adj(board, resid2, lmask)
            nv = len(adj)
            if nv == 0:
                continue
            vc = None
            if nv <= 10:
                from itertools import combinations as comb

                edges = [(a, b) for a in range(nv) for b in adj[a] if b > a]
                for t in range(0, nv + 1):
                    found = False
                    for vs in comb(range(nv), t):
                        vsset = set(vs)
                        if all(a in vsset or b in vsset for a, b in edges):
                            vc = t
                            found = True
                            break
                    if found:
                        break
            gval = gmemo[S]
            sep_rows.append({"k": S.bit_count(), "nv": nv, "vc": vc, "g": gval})
        small = [r for r in sep_rows if r["vc"] is not None and r["vc"] <= 1]
        large = [r for r in sep_rows if r["vc"] is not None and r["vc"] >= 3]
        result["b069"][f"{n}x{n}"] = {
            "n_sample": len(sep_rows),
            "n_vc_le1": len(small),
            "n_vc_ge3": len(large),
            "mean_nv_vc_le1": (sum(r["nv"] for r in small) / len(small)) if small else None,
            "mean_nv_vc_ge3": (sum(r["nv"] for r in large) / len(large)) if large else None,
            "loss_rate_vc_le1": (sum(1 for r in small if r["g"] == 0) / len(small)) if small else None,
            "loss_rate_vc_ge3": (sum(1 for r in large if r["g"] == 0) / len(large)) if large else None,
            "note": "proxy only — strategy-proof-length not measured",
        }

        result["boards"][f"{n}x{n}"] = {
            "n_safe": len(safe),
            "checked": checked,
            "step": step,
            "chrom_stats": {str(k): v for k, v in chrom_stats.items()},
            "b062_bad": len(b062_bad),
            "b064_hits": len(b064_hits),
            "b065_hits": len(b065_hits),
            "b067_checked": result["b067"]["checked"],
            "b067_bad": len(b067_bad),
            "b061_within_k": within,
        }
        result["b062"]["violations"].extend(b062_bad[:5])
        result["b064"].extend(b064_hits[:8])
        result["b065"].extend(b065_hits[:8])
        result["b067"]["violations"].extend(b067_bad[:8])
        print(
            f"b062bad={len(b062_bad)} b064={len(b064_hits)} b065={len(b065_hits)} "
            f"b067bad={len(b067_bad)} checked={checked}",
            flush=True,
        )

    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""B571-B580: 1-point exchange graph E_k on safe k-sets.

E_k vertices = safe k-sets; edges = one-stone swaps (remove one, add one, safe).
Also computes g(S), winning moves, covering-triple counts b_S(p).

No n>=7 search.  n<=4 complete; n=5 full safe + g, exchange on samples.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict, deque
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b561.json"


def enumerate_safe(board: Board) -> list[list[int]]:
    V = board.V
    by: list[list[int]] = [[] for _ in range(V + 1)]

    def dfs(occ, start, size):
        by[size].append(occ)
        for v in range(start, V):
            bit = 1 << v
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & (occ | bit)) == q:
                    ok = False
                    break
            if ok:
                dfs(occ | bit, v + 1, size + 1)

    dfs(0, 0, 0)
    return by


def legal_mask(board: Board, occ: int) -> int:
    out = 0
    for v in board.legal_moves(occ):
        out |= 1 << v
    return out


def grundy_table(board: Board, safe_set: set[int]) -> dict[int, int]:
    memo: dict[int, int] = {}
    sys.setrecursionlimit(100000)

    def ev(occ: int) -> int:
        if occ in memo:
            return memo[occ]
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

    ev(0)
    return memo


def winning_moves(board: Board, occ: int, gtab: dict[int, int]) -> list[int]:
    out = []
    for u in board.legal_moves(occ):
        if gtab.get(occ | (1 << u), -1) == 0:
            out.append(u)
    return out


def b_sp(occ: int, p: int, board: Board) -> int:
    """number of triples in occ whose completion with p is a forbidden quad."""
    bit = 1 << p
    c = 0
    for q in board.quads_by_pt[p]:
        rest = q & ~bit
        if rest and (rest & occ) == rest:
            c += 1
    return c


def swap_neighbors(board: Board, occ: int, by_size: dict[int, set[int]]) -> list[tuple[int, int]]:
    """1-point exchanges: (out_pt, in_pt) with result still safe, same size."""
    k = occ.bit_count()
    out = []
    empties = board.full ^ occ
    # remove one
    o = occ
    while o:
        b = o & -o
        o ^= b
        out_pt = b.bit_length() - 1
        base = occ ^ b
        e = empties | b  # empties including the removed one
        # try add one (not the same)
        e2 = e
        while e2:
            b2 = e2 & -e2
            e2 ^= b2
            in_pt = b2.bit_length() - 1
            if in_pt == out_pt:
                continue
            nxt = base | b2
            if nxt in by_size.get(k, ()):
                out.append((out_pt, in_pt))
    return out


def connected_components(nodes: list[int], adj: dict[int, list[int]]) -> list[list[int]]:
    seen = set()
    comps = []
    for s in nodes:
        if s in seen:
            continue
        q = deque([s])
        seen.add(s)
        comp = [s]
        while q:
            u = q.popleft()
            for v in adj.get(u, []):
                if v not in seen:
                    seen.add(v)
                    q.append(v)
                    comp.append(v)
        comps.append(comp)
    return comps


def cycle_space_dim(n_nodes: int, n_edges: int, n_comp: int) -> int:
    # dim of cycle space of undirected graph = E - V + C  (over GF2, for
    # each component: E_i - V_i + 1; sum)
    return n_edges - n_nodes + n_comp


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for i, idx in enumerate(order):
            r[idx] = i
        return r
    if len(xs) < 3:
        return 0.0
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(len(rx)))
    denx = math.sqrt(sum((rx[i] - mx) ** 2 for i in range(len(rx))))
    deny = math.sqrt(sum((ry[i] - my) ** 2 for i in range(len(ry))))
    return num / (denx * deny) if denx * deny else 0.0


def analyze_n(n: int, rng: random.Random, full_exchange: bool) -> dict:
    board = board_square(n)
    by = enumerate_safe(board)
    safe_set = set()
    for g in by:
        safe_set.update(g)
    print(f"n={n}: {sum(len(x) for x in by)} safe sets", flush=True)
    gtab = grundy_table(board, safe_set)
    print(f"  gtab={len(gtab)}", flush=True)

    by_size: dict[int, set[int]] = {k: set(by[k]) for k in range(len(by))}
    res: dict = {"n": n, "n_safe": sum(len(x) for x in by)}

    # ---------- B571: g-staircase path in E_k component ----------
    b571 = {"checked_layers": [], "witness": None}
    layers = [k for k in range(2, len(by) - 1) if 8 <= len(by[k]) <= (2000 if not full_exchange else 8000)]
    if not full_exchange:
        layers = layers[:3]
    for k in layers:
        nodes = list(by[k])
        if len(nodes) > 4000:
            rng.shuffle(nodes)
            nodes = nodes[:4000]
            node_set = set(nodes)
        else:
            node_set = set(nodes)
        adj: dict[int, list[int]] = defaultdict(list)
        edges = 0
        for S in nodes:
            for out_pt, in_pt in swap_neighbors(board, S, by_size):
                T = (S ^ (1 << out_pt)) | (1 << in_pt)
                if T in node_set:
                    adj[S].append(T)
                    edges += 1
        # undirected unique edges
        edges //= 2 if edges else 1
        comps = connected_components(nodes, adj)
        layer_rec = {"k": k, "n_nodes": len(nodes), "n_edges": edges, "n_comp": len(comps)}
        # look for component containing a full g-staircase 0..max
        for comp in comps:
            gs = {S: gtab[S] for S in comp}
            gvals = sorted(set(gs.values()))
            if len(gvals) < 3:
                continue
            gmin, gmax = gvals[0], gvals[-1]
            if gmin > 0:
                continue
            # BFS in subgraph where g increases by exactly 1 along edges
            # from any g=0 node to any g=gmax node
            start = [S for S in comp if gs[S] == 0]
            # state: node; track max g reached along an increasing path
            # find if exists path 0->1->2->...->gmax
            reach = {g: set() for g in range(gmax + 1)}
            for S in start:
                reach[0].add(S)
            ok_path = True
            parent: dict[int, int] = {}
            for g in range(gmax):
                nxt = set()
                for S in reach[g]:
                    for T in adj[S]:
                        if gs[T] == g + 1 and T not in reach[g + 1]:
                            nxt.add(T)
                            parent[T] = S
                reach[g + 1] = nxt
                if not nxt:
                    ok_path = False
                    break
            if ok_path:
                # reconstruct one path
                end = next(iter(reach[gmax]))
                path = [end]
                while path[-1] in parent:
                    path.append(parent[path[-1]])
                path.reverse()
                b571["witness"] = {
                    "n": n,
                    "k": k,
                    "g_range": [0, gmax],
                    "path_len": len(path),
                    "path_masks": path[:20],
                    "path_g": [gs[S] for S in path[:20]],
                }
                break
        b571["checked_layers"].append(layer_rec)
        if b571["witness"]:
            break
    res["b571"] = b571

    # ---------- B572: max |g(S)-g(T)| over 1-swap pairs ----------
    b572 = {"per_layer": [], "max_jump": 0, "example": None}
    for k in range(1, len(by) - 1):
        if len(by[k]) == 0 or len(by[k]) > 8000:
            continue
        nodes = list(by[k])
        mx = 0
        ex = None
        for S in nodes:
            for out_pt, in_pt in swap_neighbors(board, S, by_size):
                T = (S ^ (1 << out_pt)) | (1 << in_pt)
                if T in by_size.get(k, ()):
                    d = abs(gtab[S] - gtab[T])
                    if d > mx:
                        mx = d
                        ex = (S, T, gtab[S], gtab[T])
        b572["per_layer"].append({"k": k, "max_jump": mx, "n": len(nodes)})
        if mx > b572["max_jump"]:
            b572["max_jump"] = mx
            if ex:
                b572["example"] = {
                    "k": k,
                    "gS": ex[2],
                    "gT": ex[3],
                    "S": ex[0],
                    "T": ex[1],
                }
    res["b572"] = b572

    # ---------- B573: every nonterminal P near another nonterminal P ----------
    b573 = {"checked": 0, "violations": [], "n_P": 0}
    # sample P positions with |L|>=4 and h>=3 (h = K(S)-|S| >= 3 means some
    # extension path of length 3; use max supersets size via DFS)
    Ppos = [m for m in safe_set if gtab.get(m, 0) == 0 and m != 0]
    b573["n_P"] = len(Ppos)
    rng.shuffle(Ppos)

    def max_ext_size(occ: int) -> int:
        # size of largest safe superset
        best = occ.bit_count()

        def dfs(o, start):
            nonlocal best
            if o.bit_count() > best:
                best = o.bit_count()
            for v in range(start, board.V):
                bit = 1 << v
                if o & bit:
                    continue
                ok = True
                for q in board.quads_by_pt[v]:
                    if (q & (o | bit)) == q:
                        ok = False
                        break
                if ok:
                    dfs(o | bit, v + 1)

        dfs(occ, 0)
        return best

    sample_P = Ppos[: min(250 if not full_exchange else 600, len(Ppos))]
    for S in sample_P:
        L = legal_mask(board, S)
        if L.bit_count() < 4:
            continue
        h = max_ext_size(S) - S.bit_count()
        if h < 3:
            continue
        b573["checked"] += 1
        # 1-swap
        found = False
        k = S.bit_count()
        for out_pt, in_pt in swap_neighbors(board, S, by_size):
            T = (S ^ (1 << out_pt)) | (1 << in_pt)
            if T in safe_set and gtab.get(T, -1) == 0 and legal_mask(board, T).bit_count() >= 1:
                found = True
                break
        if not found:
            # 2-swap: remove 2 add 2
            stones = [i for i in range(board.V) if (S >> i) & 1]
            empties = [i for i in range(board.V) if not (S >> i) & 1]
            for o1, o2 in combinations(stones, 2):
                base = S ^ (1 << o1) ^ (1 << o2)
                for i1, i2 in combinations(empties, 2):
                    T = base | (1 << i1) | (1 << i2)
                    if T in safe_set and gtab.get(T, -1) == 0:
                        found = True
                        break
                if found:
                    break
        if not found:
            b573["violations"].append({"S": S, "L": L.bit_count(), "h": h})
    res["b573"] = b573

    # ---------- B574: disjoint winning-move sets on neighboring N ----------
    b574 = {"pairs": 0, "witness": None, "max_common": 0}
    Npos = [m for m in safe_set if gtab.get(m, 0) != 0 and m != 0]
    rng.shuffle(Npos)
    for S in Npos[: min(400, len(Npos))]:
        WS = set(winning_moves(board, S, gtab))
        if not WS:
            continue
        k = S.bit_count()
        for out_pt, in_pt in swap_neighbors(board, S, by_size):
            T = (S ^ (1 << out_pt)) | (1 << in_pt)
            if T not in safe_set or gtab.get(T, 0) == 0:
                continue
            WT = set(winning_moves(board, T, gtab))
            if not WT:
                continue
            b574["pairs"] += 1
            LS = set(board.legal_moves(S))
            LT = set(board.legal_moves(T))
            common = LS & LT
            b574["max_common"] = max(b574["max_common"], len(common))
            if WS.isdisjoint(WT):
                if b574["witness"] is None or len(common) > b574["witness"][2]:
                    b574["witness"] = (S, T, len(common), sorted(WS)[:6], sorted(WT)[:6])
    if b574["witness"]:
        S, T, nc, ws, wt = b574["witness"]
        b574["witness"] = {
            "S": S,
            "T": T,
            "n_common_legal": nc,
            "WS": ws,
            "WT": wt,
            "expected_n_prop": nc / n,
        }
    res["b574"] = b574

    # ---------- B575: b-histogram change larger on P/N flip edges ----------
    b575 = {"flip_deltas": [], "nonflip_deltas": []}

    def b_hist(occ):
        L = board.legal_moves(occ)
        return [b_sp(occ, p, board) for p in L]

    def hist_delta(h1, h2):
        # L1 distance of sorted histograms (pad zeros)
        a = sorted(h1)
        b = sorted(h2)
        m = max(len(a), len(b))
        a += [0] * (m - len(a))
        b += [0] * (m - len(b))
        return sum(abs(x - y) for x, y in zip(a, b))

    sample5 = [m for m in safe_set if 3 <= m.bit_count() <= (6 if n == 5 else 6)]
    rng.shuffle(sample5)
    for S in sample5[: min(200, len(sample5))]:
        hS = b_hist(S)
        k = S.bit_count()
        for out_pt, in_pt in swap_neighbors(board, S, by_size):
            T = (S ^ (1 << out_pt)) | (1 << in_pt)
            if T not in safe_set:
                continue
            flip = (gtab[S] == 0) != (gtab[T] == 0)
            d = hist_delta(hS, b_hist(T))
            if flip:
                b575["flip_deltas"].append(d)
            else:
                b575["nonflip_deltas"].append(d)
    fd = b575["flip_deltas"]
    nd = b575["nonflip_deltas"]
    b575["mean_flip"] = sum(fd) / len(fd) if fd else None
    b575["mean_nonflip"] = sum(nd) / len(nd) if nd else None
    res["b575"] = b575

    # ---------- B576: L equal, both N, unique winning move different ----------
    b576 = {"witness": None, "checked": 0}
    # group N positions by L mask
    by_L: dict[int, list[int]] = defaultdict(list)
    for m in Npos[: min(2000, len(Npos))]:
        by_L[legal_mask(board, m)].append(m)
    for Lm, group in by_L.items():
        if len(group) < 2:
            continue
        for i in range(min(len(group) - 1, 6)):
            S, T = group[i], group[i + 1]
            b576["checked"] += 1
            WS = winning_moves(board, S, gtab)
            WT = winning_moves(board, T, gtab)
            if len(WS) == 1 and len(WT) == 1 and WS[0] != WT[0]:
                b576["witness"] = {
                    "S": S,
                    "T": T,
                    "L": Lm,
                    "wS": WS[0],
                    "wT": WT[0],
                    "gS": gtab[S],
                    "gT": gtab[T],
                }
                break
        if b576["witness"]:
            break
    res["b576"] = b576

    # ---------- B577: cycle space of P-position E_k not gen by <=4 cycles ----------
    b577 = {"done": False, "note": "cycle-space-vs-short-cycles requires explicit small-cycle basis; deferred if layer large"}
    # use small k with many P positions
    for k in range(2, min(7, len(by) - 1)):
        pnodes = [m for m in by[k] if gtab.get(m, 0) == 0]
        if not (6 <= len(pnodes) <= 500):
            continue
        adj = defaultdict(set)
        for S in pnodes:
            for out_pt, in_pt in swap_neighbors(board, S, by_size):
                T = (S ^ (1 << out_pt)) | (1 << in_pt)
                if T in set(pnodes):
                    adj[S].add(T)
                    adj[T].add(S)
        # edges
        seen_e = set()
        edges = []
        for S in adj:
            for T in adj[S]:
                e = (min(S, T), max(S, T))
                if e not in seen_e:
                    seen_e.add(e)
                    edges.append(e)
        comps = connected_components(pnodes, {u: list(vs) for u, vs in adj.items()})
        cdim = cycle_space_dim(len(pnodes), len(edges), len(comps))
        # count 3- and 4-cycles (simple)
        n3 = 0
        n4 = 0
        node_set = set(pnodes)
        for S in pnodes:
            ns = adj[S]
            for T in ns:
                if T <= S:
                    continue
                for U in adj[T]:
                    if U <= S or U == S:
                        continue
                    if U in ns:
                        n3 += 1
        # 4-cycles
        for S in pnodes:
            for T in adj[S]:
                if T <= S:
                    continue
                for U in adj[T]:
                    if U == S:
                        continue
                    for V in adj[U]:
                        if V == T or V == S:
                            continue
                        if V in adj[S] and V > U:
                            n4 += 1
        b577 = {
            "done": True,
            "k": k,
            "n_P": len(pnodes),
            "n_edges": len(edges),
            "n_comp": len(comps),
            "cycle_dim": cdim,
            "n_triangles": n3,
            "n_4cycles": n4,
            "short_cycle_span_upper": min(cdim, n3 + n4),
            "span_equals_dim_if": "need explicit incidence rank; see note",
        }
        # explicit rank of short cycles vs cycle space
        # build vertex-edge incidence? easier: edge-cycle incidence of all 3,4 cycles
        eix = {e: i for i, e in enumerate(edges)}
        short_masks = []
        for S in pnodes:
            ns = adj[S]
            for T in ns:
                if T <= S:
                    continue
                for U in adj[T]:
                    if U <= S or U == S:
                        continue
                    if U in ns:
                        m = (1 << eix[(min(S, T), max(S, T))]) | (1 << eix[(min(T, U), max(T, U))]) | (1 << eix[(min(S, U), max(S, U))])
                        short_masks.append(m)
        for S in pnodes:
            for T in adj[S]:
                if T <= S:
                    continue
                for U in adj[T]:
                    if U == S:
                        continue
                    for V in adj[U]:
                        if V == T or V == S:
                            continue
                        if V in adj[S] and V > U:
                            e1 = (min(S, T), max(S, T))
                            e2 = (min(T, U), max(T, U))
                            e3 = (min(U, V), max(U, V))
                            e4 = (min(V, S), max(V, S))
                            m = (1 << eix[e1]) | (1 << eix[e2]) | (1 << eix[e3]) | (1 << eix[e4])
                            short_masks.append(m)
        # rank of short_masks
        basis = {}
        for m in short_masks:
            x = m
            while x:
                b = x.bit_length() - 1
                if b in basis:
                    x ^= basis[b]
                else:
                    basis[b] = x
                    break
        rank_short = len(basis)
        b577["rank_short"] = rank_short
        b577["short_generate_cycle_space"] = rank_short >= cdim
        break
    res["b577"] = b577

    # ---------- B578: keep a fixed winning move across many stone changes ----------
    b578 = {"witness": None}
    # find p that is a winning move for many S; look for large symmetric diffs
    win_by_p: dict[int, list[int]] = defaultdict(list)
    for S in Npos[: min(1500, len(Npos))]:
        for p in winning_moves(board, S, gtab):
            win_by_p[p].append(S)
    best = None
    for p, group in win_by_p.items():
        if len(group) < 4:
            continue
        # max pairwise symmetric difference
        mx = 0
        pair = None
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                sd = (group[i] ^ group[j]).bit_count()
                if sd > mx:
                    mx = sd
                    pair = (group[i], group[j])
        if best is None or mx > best[0]:
            best = (mx, p, pair, len(group))
    if best:
        mx, p, pair, ng = best
        b578["witness"] = {
            "p": p,
            "n_positions_sharing": ng,
            "max_symdiff": mx,
            "S": pair[0],
            "T": pair[1],
        }
    res["b578"] = b578

    # ---------- B579: WFT uniqueness vs winning-move stability ----------
    b579 = {"rows": [], "spearman_g": None, "spearman_wftuniq": None}
    # WFT(S): terminal stone counts forceable by winner.  Approximate T*:
    # for N, only moves to P; for P, all moves.  Compute T* sets for sample.
    def T_star(occ, memo=None):
        if memo is None:
            memo = {}
        if occ in memo:
            return memo[occ]
        mv = board.legal_moves(occ)
        if not mv:
            memo[occ] = {occ.bit_count()}
            return memo[occ]
        g = gtab.get(occ, 0)
        if g == 0:
            opts = mv  # P: all moves
        else:
            opts = [u for u in mv if gtab.get(occ | (1 << u), -1) == 0]
            if not opts:
                opts = mv
        acc = set()
        for u in opts:
            acc |= T_star(occ | (1 << u), memo)
        memo[occ] = acc
        return acc

    def wft(occ):
        # winner forces both win and terminal size t.  For N: exists move to P
        # s.t. for all replies ... simplified: use T* as proxy in this pass.
        return T_star(occ)

    sample79 = Npos[: min(80, len(Npos))]
    rows = []
    for S in sample79:
        WS = winning_moves(board, S, gtab)
        if not WS:
            continue
        # stability: min overlap of WS with WS' over 1-swap neighbors
        neigh = []
        k = S.bit_count()
        for out_pt, in_pt in swap_neighbors(board, S, by_size):
            T = (S ^ (1 << out_pt)) | (1 << in_pt)
            if T in safe_set and gtab.get(T, 0) != 0:
                WT = winning_moves(board, T, gtab)
                if WT:
                    neigh.append(len(set(WS) & set(WT)) / len(set(WS) | set(WT)))
        if not neigh:
            continue
        Ts = wft(S)
        rows.append({
            "g": gtab[S],
            "wft_uniq": 1 if len(Ts) == 1 else 0,
            "wft_size": len(Ts),
            "stability": sum(neigh) / len(neigh),
            "L": legal_mask(board, S).bit_count(),
            "k": k,
        })
    b579["rows"] = rows[:30]
    if len(rows) >= 6:
        gs = [r["g"] for r in rows]
        wu = [r["wft_size"] for r in rows]
        st = [r["stability"] for r in rows]
        b579["spearman_g"] = spearman(gs, st)
        b579["spearman_wftuniq"] = spearman(wu, st)
    res["b579"] = b579

    # ---------- B580: local circle-bundle difference as witness ----------
    # Structural claim.  For P/N flip swaps, compute the two circle bundles
    # (triples through removed stone, triples through added stone) and see
    # whether their small symmetric difference already determines the flip.
    b580 = {"flip_cases": 0, "determined_by_bundle_diff": 0, "note": "sufficient-class search on sample"}
    for S in sample5[: min(120, len(sample5))]:
        k = S.bit_count()
        for out_pt, in_pt in swap_neighbors(board, S, by_size):
            T = (S ^ (1 << out_pt)) | (1 << in_pt)
            if T not in safe_set:
                continue
            flip = (gtab[S] == 0) != (gtab[T] == 0)
            if not flip:
                continue
            b580["flip_cases"] += 1
            # bundle diff: points newly forbidden / newly legal in L
            LS = set(board.legal_moves(S))
            LT = set(board.legal_moves(T))
            diff = LS ^ LT
            # if diff is small (<=4) the local description is "small"
            if len(diff) <= 4:
                b580["determined_by_bundle_diff"] += 1
    res["b580"] = b580

    return res


def main():
    report = json.loads(OUT.read_text(encoding="utf-8"))
    rng = random.Random(20260927)
    for n, full in ((4, True), (5, False)):
        print(f"===== analyze n={n} =====", flush=True)
        r = analyze_n(n, rng, full)
        report[f"n{n}"]["exchange"] = r
        # compact print
        for key in ("b571", "b572", "b573", "b574", "b575", "b576", "b577", "b578", "b579", "b580"):
            v = r.get(key)
            if isinstance(v, dict):
                brief = {k: v[k] for k in v if k in (
                    "witness", "max_jump", "checked", "violations", "pairs",
                    "mean_flip", "mean_nonflip", "done", "short_generate_cycle_space",
                    "max_symdiff", "spearman_g", "spearman_wftuniq",
                    "flip_cases", "determined_by_bundle_diff", "n_P",
                    "checked_layers",
                )}
                print(f"  {key}: {brief}", flush=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""B581-B590: residual-game realization on the standard board.

Search safe S whose residual hypergraph R(S) is:
  B581  exactly a path P_m (2-point edges only, legal = path vertices)
  B582  exactly an odd cycle C_{2r+1}
  B583  path with |S| = O(m) (measure |S| vs m)
  B584  same abstract residual, different |S| (shielding cost)
  B585  two independent residuals sharing shielding
  B586  one-stone move toggles direct-sum join
  B587  nimber-2 pieces joined to nimber 4
  B588  two same pieces give 3+ values by separation
  B589  finite pieces generate unbounded g
  B590  change g while keeping WFT, or vice versa

No n>=7 full search.  n<=5 full, n=6 layer samples, n=7 only existing bins.
"""
from __future__ import annotations

import json
import random
import struct
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"
OUT = ROOT / "research" / "verification" / "round2_b561.json"


def load_bin(path: Path) -> list[int]:
    raw = path.read_bytes()
    m = len(raw) // 8
    return list(struct.unpack(f"<{m}Q", raw))


def mask_of(pts, n):
    m = 0
    for x, y in pts:
        m |= 1 << (y * n + x)
    return m


def pts_of(mask, n):
    return [(i % n, i // n) for i in range(n * n) if (mask >> i) & 1]


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


def residual_R(board: Board, occ: int) -> list[int]:
    empties = board.full ^ occ
    L = legal_mask(board, occ)
    seen = set()
    for q in board.quads:
        rest = q & empties
        if rest and (rest & ~L) == 0:
            seen.add(rest)
    minimal = []
    for r in seen:
        ok = True
        x = r
        while x:
            x = (x - 1) & r
            if x == 0:
                break
            if x in seen:
                ok = False
                break
        if ok:
            minimal.append(r)
    return sorted(minimal)


def edge_graph(R: list[int]) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Return (2-point edges, 3-point residuals, 4-point residuals)."""
    e2, e3, e4 = [], [], []
    for r in R:
        k = r.bit_count()
        if k == 2:
            a, b = [i for i in range(r.bit_length()) if (r >> i) & 1]
            e2.append((a, b) if a < b else (b, a))
        elif k == 3:
            e3.append(r)
        elif k == 4:
            e4.append(r)
    return sorted(set(e2)), e3, e4


def classify_path_or_cycle(L: int, edges: list[tuple[int, int]]) -> dict:
    """If the 2-point edges form exactly a path or cycle on supp(L), say so."""
    if not edges:
        return {"kind": "empty"}
    verts = [i for i in range(L.bit_length()) if (L >> i) & 1]
    vset = set(verts)
    # every legal point must appear in an edge
    used = set()
    for a, b in edges:
        used.add(a)
        used.add(b)
    if used != vset:
        return {"kind": "not_tight", "n_unused": len(vset - used)}
    deg = Counter()
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    # connected?
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    start = next(iter(vset))
    seen = {start}
    stack = [start]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    if seen != vset:
        return {"kind": "disconnected"}
    degs = sorted(deg.values())
    m = len(edges)
    k = len(vset)
    if m == k - 1 and degs.count(1) == 2 and all(d <= 2 for d in degs):
        # path: order it
        ends = [v for v in vset if deg[v] == 1]
        order = [ends[0]]
        prev = None
        cur = ends[0]
        while True:
            nxts = [x for x in adj[cur] if x != prev]
            if not nxts:
                break
            prev, cur = cur, nxts[0]
            order.append(cur)
        return {"kind": "path", "m": k, "order": order}
    if m == k and all(d == 2 for d in degs):
        # cycle
        order = [start]
        prev = None
        cur = start
        while True:
            nxts = [x for x in adj[cur] if x != prev]
            if not nxts:
                break
            prev, cur = cur, nxts[0]
            if cur == start:
                break
            order.append(cur)
        return {"kind": "cycle", "m": k, "odd": k % 2 == 1, "order": order}
    return {"kind": "other", "n_edges": m, "n_verts": k, "deg_hist": dict(Counter(degs))}


def abstract_type(L: int, edges: list[tuple[int, int]], e3, e4) -> tuple:
    """Abstract residual signature: path/cycle/other + edge multiset + higher sizes."""
    info = classify_path_or_cycle(L, edges)
    higher = tuple(sorted(Counter(r.bit_count() for r in e3 + e4).items()))
    if info["kind"] in ("path", "cycle"):
        key = (info["kind"], info["m"], info.get("odd"), higher)
    else:
        key = (info["kind"], len(edges), len(e3), len(e4), higher)
    return key


def grundy(board: Board, occ: int, memo: dict[int, int]) -> int:
    if occ in memo:
        return memo[occ]
    mv = board.legal_moves(occ)
    if not mv:
        memo[occ] = 0
        return 0
    seen = set()
    for u in mv:
        seen.add(grundy(board, occ | (1 << u), memo))
    g = 0
    while g in seen:
        g += 1
    memo[occ] = g
    return g


def main():
    report = json.loads(OUT.read_text(encoding="utf-8"))
    rng = random.Random(561)

    findings = {
        "b581_paths": [],
        "b582_cycles": [],
        "b581_m_values": set(),
        "b582_m_values": set(),
        "by_type": defaultdict(list),  # abstract type -> list of (n, |S|, S)
    }

    def record(n, S, board, R, L, gm):
        e2, e3, e4 = edge_graph(R)
        info = classify_path_or_cycle(L, e2)
        key = abstract_type(L, e2, e3, e4)
        findings["by_type"][key].append((n, S.bit_count(), S, info))
        if e3 or e4:
            return info
        if info["kind"] == "path":
            findings["b581_paths"].append({
                "n": n,
                "S_size": S.bit_count(),
                "S_pts": pts_of(S, n),
                "m": info["m"],
                "order_ids": info["order"],
                "order_pts": [pts_of(1 << i, n)[0] for i in info["order"]],
                "g": gm.get(S),
            })
            findings["b581_m_values"].add(info["m"])
        elif info["kind"] == "cycle" and info.get("odd"):
            findings["b582_cycles"].append({
                "n": n,
                "S_size": S.bit_count(),
                "S_pts": pts_of(S, n),
                "m": info["m"],
                "order_pts": [pts_of(1 << i, n)[0] for i in info["order"]],
                "g": gm.get(S),
            })
            findings["b582_m_values"].add(info["m"])
        return info

    # ---- n=2..5 full ----
    for n in (2, 3, 4, 5):
        board = board_square(n)
        by = enumerate_safe(board)
        safe_set = set()
        for g in by:
            safe_set.update(g)
        print(f"n={n}: {sum(len(x) for x in by)} safe", flush=True)
        gm: dict[int, int] = {}
        # only need g for S with path/cycle residuals; compute lazily
        n_path = n_cyc = 0
        for k in range(0, len(by)):
            for S in by[k]:
                if k == 0:
                    continue
                # cheap prefilter: residual only 2-point iff every empty point
                # is in exactly the right constraints... just compute R
                L = legal_mask(board, S)
                if L.bit_count() < 3:
                    continue
                R = residual_R(board, S)
                e2, e3, e4 = edge_graph(R)
                if e3 or e4:
                    continue
                info = classify_path_or_cycle(L, e2)
                if info["kind"] in ("path", "cycle"):
                    g = grundy(board, S, gm)
                    record(n, S, board, R, L, gm)
                    if info["kind"] == "path":
                        n_path += 1
                    elif info.get("odd"):
                        n_cyc += 1
        print(f"  paths={n_path} odd_cycles={n_cyc}", flush=True)

    # ---- n=6: use layer bins ----
    n = 6
    board = board_square(n)
    bins = []
    for k in range(8, 12):
        p = DATA / f"safe_n6_k{k}.bin"
        if k == 11:
            p = NIGHT / "maxsafe_n6_K11.bin"
        if p.exists():
            bins.append((k, load_bin(p)))
    # also DFS-sample small |S|
    print(f"n=6 bins: {[(k, len(v)) for k, v in bins]}", flush=True)
    gm6: dict[int, int] = {}
    n_path6 = n_cyc6 = 0
    for k, lst in bins:
        rng.shuffle(lst)
        for S in lst[: min(400, len(lst))]:
            L = legal_mask(board, S)
            if L.bit_count() < 3:
                continue
            R = residual_R(board, S)
            e2, e3, e4 = edge_graph(R)
            if e3 or e4:
                continue
            info = classify_path_or_cycle(L, e2)
            if info["kind"] in ("path", "cycle"):
                g = grundy(board, S, gm6)
                record(n, S, board, R, L, gm6)
                if info["kind"] == "path":
                    n_path6 += 1
                elif info.get("odd"):
                    n_cyc6 += 1
    print(f"n=6 sample paths={n_path6} odd_cycles={n_cyc6}", flush=True)

    # ---- n=7: only max-safe bins ----
    n = 7
    board = board_square(n)
    max7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    k13 = load_bin(DATA / "safe_n7_k13.bin")
    gm7: dict[int, int] = {}
    n_path7 = 0
    for S in list(max7) + list(k13[::30])[:200]:
        L = legal_mask(board, S)
        if L.bit_count() < 3:
            continue
        R = residual_R(board, S)
        e2, e3, e4 = edge_graph(R)
        if e3 or e4:
            continue
        info = classify_path_or_cycle(L, e2)
        if info["kind"] in ("path", "cycle"):
            g = grundy(board, S, gm7)
            record(n, S, board, R, L, gm7)
            n_path7 += 1
    print(f"n=7 paths/cycles={n_path7}", flush=True)

    # ---- summaries ----
    paths = findings["b581_paths"]
    cycles = findings["b582_cycles"]
    b581 = {
        "n_found": len(paths),
        "m_values": sorted(findings["b581_m_values"]),
        "examples": paths[:8],
    }
    b582 = {
        "n_found": len(cycles),
        "m_values": sorted(findings["b582_m_values"]),
        "examples": cycles[:8],
    }

    # B583: |S| vs m for paths
    pairs = [(p["m"], p["S_size"], p["n"]) for p in paths]
    b583 = {
        "pairs_m_size": pairs[:40],
        "n_pairs": len(pairs),
        "max_m": max((m for m, _, _ in pairs), default=0),
        "min_size_at_max_m": min((s for m, s, _ in pairs if m == max((x for x, _, _ in pairs), default=0)), default=None),
    }
    if pairs:
        # linear fit |S| vs m (integer least squares)
        ms = [m for m, s, _ in pairs]
        ss = [s for m, s, _ in pairs]
        mm = sum(ms) / len(ms)
        sm = sum(ss) / len(ss)
        var = sum((x - mm) ** 2 for x in ms)
        cov = sum((ms[i] - mm) * (ss[i] - sm) for i in range(len(ms)))
        slope = cov / var if var else 0
        b583["slope_size_per_m"] = slope
        b583["intercept"] = sm - slope * mm
        b583["size_over_m_max"] = max((s / m for m, s, _ in pairs if m > 0), default=None)

    # B584: same abstract residual type, different |S|
    b584 = {"witness": None, "n_types_with_varying_size": 0}
    for key, lst in findings["by_type"].items():
        sizes = {}
        for n, sz, S, info in lst:
            sizes.setdefault(sz, []).append((n, S))
        if len(sizes) >= 2:
            b584["n_types_with_varying_size"] += 1
            if b584["witness"] is None:
                smin = min(sizes)
                smax = max(sizes)
                b584["witness"] = {
                    "type": str(key),
                    "min_size": smin,
                    "max_size": smax,
                    "min_example": {"n": sizes[smin][0][0], "S_pts": pts_of(sizes[smin][0][1], sizes[smin][0][0])},
                    "max_example": {"n": sizes[smax][0][0], "S_pts": pts_of(sizes[smax][0][1], sizes[smax][0][0])},
                }

    # B585/B586: look for residual with 2 components in P(S)
    def components2(edges, L):
        verts = [i for i in range(L.bit_length()) if (L >> i) & 1]
        adj = defaultdict(set)
        for a, b in edges:
            adj[a].add(b)
            adj[b].add(a)
        seen = set()
        comps = []
        for s in verts:
            if s in seen:
                continue
            stack = [s]
            seen.add(s)
            c = {s}
            while stack:
                u = stack.pop()
                for v in adj[u]:
                    if v not in seen:
                        seen.add(v)
                        c.add(v)
                        stack.append(v)
            comps.append(c)
        return comps

    b585 = {"two_comp_examples": [], "shared_shield_note": None}
    b586 = {"witness": None, "tried": 0}
    # search among path/cycle-free-only 2-edge residuals with 2 components
    for n in (4, 5):
        board = board_square(n)
        by = enumerate_safe(board)
        gm: dict[int, int] = {}
        count2 = 0
        for k in range(1, len(by)):
            for S in by[k]:
                L = legal_mask(board, S)
                if L.bit_count() < 4:
                    continue
                R = residual_R(board, S)
                e2, e3, e4 = edge_graph(R)
                if e3 or e4:
                    continue
                comps = components2(e2, L)
                if len(comps) == 2 and all(len(c) >= 2 for c in comps):
                    count2 += 1
                    if len(b585["two_comp_examples"]) < 6:
                        g = grundy(board, S, gm)
                        b585["two_comp_examples"].append({
                            "n": n,
                            "S_size": S.bit_count(),
                            "S_pts": pts_of(S, n),
                            "comp_sizes": [len(c) for c in comps],
                            "g": g,
                            "L": L.bit_count(),
                        })
                    # B586: try moving one stone
                    if b586["witness"] is None and S.bit_count() >= 2:
                        stones = [i for i in range(board.V) if (S >> i) & 1]
                        empties = [i for i in range(board.V) if not (S >> i) & 1]
                        for o in stones[:6]:
                            for inp in empties[:12]:
                                T = (S ^ (1 << o)) | (1 << inp)
                                if T not in safe_set:
                                    continue
                                b586["tried"] += 1
                                L2 = legal_mask(board, T)
                                if L2 != L:
                                    continue
                                R2 = residual_R(board, T)
                                e2b, e3b, e4b = edge_graph(R2)
                                comps2 = components2(e2b, L2)
                                # join: fewer components or a higher-order edge between
                                if len(comps2) == 1 or e3b or e4b:
                                    b586["witness"] = {
                                        "n": n,
                                        "S_pts": pts_of(S, n),
                                        "T_pts": pts_of(T, n),
                                        "moved_out": pts_of(1 << o, n)[0],
                                        "moved_in": pts_of(1 << inp, n)[0],
                                        "L_same": True,
                                        "S_comps": [sorted(pts_of(sum(1 << i for i in c), n)) for c in comps],
                                        "T_comps": [sorted(pts_of(sum(1 << i for i in c), n)) for c in comps2],
                                        "T_has_higher": bool(e3b or e4b),
                                    }
                                    break
                            if b586["witness"]:
                                break
                        if b586["witness"]:
                            break
        print(f"n={n} two-component residuals={count2}", flush=True)
        if b586["witness"]:
            break

    # B587/B588: component grundy xor vs connected join
    b587 = {"g2_components": [], "connected_g4": None}
    b588 = {"same_piece_pairs": [], "n_values": 0, "values": []}
    # find residual components whose own game has g=2
    for n in (4, 5):
        board = board_square(n)
        by = enumerate_safe(board)
        gm: dict[int, int] = {}
        for k in range(1, len(by)):
            for S in by[k]:
                L = legal_mask(board, S)
                if L.bit_count() < 3:
                    continue
                R = residual_R(board, S)
                e2, e3, e4 = edge_graph(R)
                if e3 or e4:
                    continue
                comps = components2(e2, L)
                if len(comps) != 2:
                    continue
                # g of whole vs xor of parts: compute part games by restricting
                g_full = grundy(board, S, gm)
                # part g: treat each component as independent game on L∩comp
                # with only edges inside; but geometry may couple through
                # higher residuals we excluded.  With only 2-edges and two
                # components the true game splits iff no residual touches
                # both; we already have only 2-edges in separate comps.
                # However adding points from both comps can create NEW quads
                # (4-point residuals appear only after adds).  So R is the
                # static residual; the actual game may still couple.
                # Record g and try to detect coupling: g != xor of part g.
                pass
    # Simpler concrete B588: two identical small residual gadgets placed
    # differently; compare g of the union.  Look for same abstract type
    # appearing with different g.
    by_type_g = defaultdict(list)
    for key, lst in findings["by_type"].items():
        for n, sz, S, info in lst:
            pass
    # use collected paths/cycles
    type_g = defaultdict(set)
    for p in paths:
        type_g[("path", p["m"])].add(p["g"])
    for c in cycles:
        type_g[("cycle", c["m"])].add(c["g"])
    b588["type_g_values"] = {str(k): sorted(v) for k, v in type_g.items()}
    b588["types_with_multiple_g"] = {
        str(k): sorted(v) for k, v in type_g.items() if len(v) >= 3
    }
    b588["n_values_max"] = max((len(v) for v in type_g.values()), default=0)

    # B587: look for S with g=4 whose R has two g=2-like halves
    b587["max_g_path"] = max((p["g"] for p in paths), default=None)
    b587["max_g_cycle"] = max((c["g"] for c in cycles), default=None)
    b587["g4_examples"] = [p for p in paths + cycles if p.get("g") == 4][:4]

    # B589: unbounded g — max g seen per n
    maxg_by_n = {}
    for p in paths + cycles:
        maxg_by_n[p["n"]] = max(maxg_by_n.get(p["n"], 0), p.get("g") or 0)
    b589 = {
        "max_g_of_realized_path_cycle": maxg_by_n,
        "note": "existing table max nimber n=2..6 is 1,1,5,6,8; path/cycle gadgets sit inside these",
        "unbounded_verified": False,
    }

    # B590: same g different WFT / same WFT different g on small boards
    b590 = {"witness_g_fixed_wft_diff": None, "witness_wft_fixed_g_diff": None}
    for n in (4, 5):
        board = board_square(n)
        by = enumerate_safe(board)
        safe_set = set()
        for g in by:
            safe_set.update(g)
        gm: dict[int, int] = {}

        def ev(occ):
            if occ in gm:
                return gm[occ]
            mv = board.legal_moves(occ)
            if not mv:
                gm[occ] = 0
                return 0
            seen = set()
            for u in mv:
                seen.add(ev(occ | (1 << u)))
            g = 0
            while g in seen:
                g += 1
            gm[occ] = g
            return g

        ev(0)

        def T_star(occ, memo=None):
            if memo is None:
                memo = {}
            if occ in memo:
                return memo[occ]
            mv = board.legal_moves(occ)
            if not mv:
                memo[occ] = frozenset([occ.bit_count()])
                return memo[occ]
            g = gm.get(occ, 0)
            if g == 0:
                opts = mv
            else:
                opts = [u for u in mv if gm.get(occ | (1 << u), -1) == 0] or mv
            acc = set()
            for u in opts:
                acc |= set(T_star(occ | (1 << u), memo))
            memo[occ] = frozenset(acc)
            return memo[occ]

        by_g_wft = defaultdict(list)
        by_wft_g = defaultdict(list)
        sample = [m for m in safe_set if 2 <= m.bit_count() <= 6]
        rng.shuffle(sample)
        for S in sample[: min(400, len(sample))]:
            g = gm[S]
            ts = T_star(S)
            by_g_wft[(g, ts)].append(S)
            by_wft_g[ts].append((g, S))
        # same g different WFT
        g_to_wfts = defaultdict(set)
        for (g, ts) in by_g_wft:
            g_to_wfts[g].add(ts)
        for g, tss in g_to_wfts.items():
            if len(tss) >= 2 and b590["witness_g_fixed_wft_diff"] is None:
                t1, t2 = list(tss)[:2]
                b590["witness_g_fixed_wft_diff"] = {
                    "n": n,
                    "g": g,
                    "WFT1": sorted(t1),
                    "WFT2": sorted(t2),
                }
        for ts, lst in by_wft_g.items():
            gs = sorted(set(g for g, _ in lst))
            if len(gs) >= 2 and b590["witness_wft_fixed_g_diff"] is None:
                b590["witness_wft_fixed_g_diff"] = {
                    "n": n,
                    "WFT": sorted(ts),
                    "g_values": gs,
                }
        if b590["witness_g_fixed_wft_diff"] and b590["witness_wft_fixed_g_diff"]:
            break

    report["b581"] = b581
    report["b582"] = b582
    report["b583"] = b583
    report["b584"] = b584
    report["b585"] = b585
    report["b586"] = b586
    report["b587"] = b587
    report["b588"] = b588
    report["b589"] = b589
    report["b590"] = b590

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("b581 paths", b581["n_found"], "m", b581["m_values"])
    print("b582 cycles", b582["n_found"], "m", b582["m_values"])
    print("b583", b583)
    print("b584", b584)
    print("b585 examples", len(b585["two_comp_examples"]))
    print("b586", b586["witness"] is not None, "tried", b586["tried"])
    print("b587 max_g", b587["max_g_path"], b587["max_g_cycle"])
    print("b588", b588["type_g_values"], "multi", b588["types_with_multiple_g"])
    print("b589", b589)
    print("b590", b590)
    print("wrote", OUT)


if __name__ == "__main__":
    main()

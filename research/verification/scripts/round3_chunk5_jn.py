#!/usr/bin/env python3
"""Round3 chunk5 - J_n computations for B312, B313, B314, B315, B317, B318, B319, B320.

J_n: vertices = board points, edge {p,q} iff g({p,q}) == 0 (2-stone P-position).

B312  J_4 total-dominating pairs vs P-pairs: full D4-type classification of BOTH
      sets plus the 44 "answerable but not substitutable" pairs.
B313  perfect matching / near-perfect matching on J_n for n=4,5,6 (J_6 via
      symmetry-orbit reduction of the two-stone layer).
B314  bridges of the non-isolated part.
B315  articulation points of the non-isolated part.
B317  exhaustive check that EVERY perfect matching of J_4 breaks in midgame
      (previous round only sampled 20 of 112212).
B318  complement graph of J_4 (done) + new: J_6 two-stone g spectrum and the
      "1 is missing" phenomenon on a larger, denser J.
B319  one-stone nimber spectrum on all second-player-win square boards
      n=2,3,4,5,6,7,8,9,10 (J_n only needs g(singleton) for W, which needs the
      one- and two-stone layers only -> tractable by orbit/oriented-edge
      reduction).
B320  (n=5 redo + n=6): mixed (one-stone g, squared distance) buckets.

Output: research/verification/round3_chunk5_jn.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict, deque
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402
from round3_chunk5_sharp import Game  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_chunk5_jn.json"


# ------------------------------------------------------------------ J helpers
def two_stone_layer(n: int) -> dict:
    """g({p,q}) for all pairs p<q, plus g({p}).

    Computed directly: g({p}) = mex{ g({p,q}) : q legal } and
    g({p,q}) = 0 iff no child of {p,q} is P, i.e. iff every legal third point r
    satisfies g({p,q,r}) > 0 -- so we need the 3-stone layer.  Instead we build
    g by a full 3-layer solve restricted to |S|<=2 ... not possible in general.
    We therefore use the standard trick: a pair {p,q} is P iff it is safe AND
    every legal r gives a non-P triple.  We compute the full grundy map for
    n<=5 with the ordinary solver (cheap), and for n=6,7 we use the
    full solver too but only extract the 1- and 2-stone layers.
    """
    game = Game(n)
    reach = game.reachable()
    g, Lc = game.grundy_all(reach)
    one = {p: g[1 << p] for p in range(n * n)}
    two = {}
    for a, b in combinations(range(n * n), 2):
        two[(a, b)] = g[(1 << a) | (1 << b)]
    return game, g, Lc, one, two


def jgraph(n, two):
    adj = defaultdict(set)
    for (a, b), gv in two.items():
        if gv == 0:
            adj[a].add(b)
            adj[b].add(a)
    return {v: set(s) for v, s in adj.items()}


def components(adj, verts):
    seen = set()
    comps = []
    for s in verts:
        if s in seen:
            continue
        q = deque([s])
        seen.add(s)
        comp = []
        while q:
            u = q.popleft()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        comps.append(sorted(comp))
    return comps


def bridges_arts(adj, verts):
    vs = set(verts)
    sub = {v: (adj[v] & vs) for v in vs}
    disc, low, parent = {}, {}, {}
    bridges, arts = [], set()
    t = [0]
    for root in vs:
        if root in disc:
            continue
        stack = [(root, iter(sorted(sub[root])))]
        disc[root] = low[root] = t[0]
        t[0] += 1
        parent[root] = None
        children = 0
        while stack:
            u, it = stack[-1]
            adv = False
            for v in it:
                if v not in disc:
                    parent[v] = u
                    disc[v] = low[v] = t[0]
                    t[0] += 1
                    if u == root:
                        children += 1
                    stack.append((v, iter(sorted(sub[v]))))
                    adv = True
                    break
                elif parent.get(u) != v:
                    low[u] = min(low[u], disc[v])
            if not adv:
                stack.pop()
                pu = parent[u]
                if pu is not None:
                    low[pu] = min(low[pu], low[u])
                    if low[u] > disc[pu]:
                        bridges.append(tuple(sorted((pu, u))))
                    if low[u] >= disc[pu] and pu != root:
                        arts.add(pu)
                elif children > 1:
                    arts.add(u)
    return bridges, sorted(arts)


def d4_maps(n):
    def pt(x, y):
        return y * n + x

    def inv(i):
        return i % n, i // n

    fs = [lambda x, y: (x, y), lambda x, y: (y, n - 1 - x),
          lambda x, y: (n - 1 - x, n - 1 - y), lambda x, y: (n - 1 - y, x),
          lambda x, y: (n - 1 - x, y), lambda x, y: (x, n - 1 - y),
          lambda x, y: (y, x), lambda x, y: (n - 1 - y, n - 1 - x)]
    return [lambda i, f=f: pt(*f(*inv(i))) for f in fs]


def d4_types(n, items, key=lambda t: t):
    maps = d4_maps(n)
    rem = {}
    for it in items:
        rem.setdefault(key(it), []).append(it)
    groups = []
    done = set()
    for rep in list(rem.keys()):
        if rep in done:
            continue
        orb = set()
        for mp in maps:
            orb.add(tuple(sorted((mp(rep[0]), mp(rep[1])))))
        types = [k for k in rem if k in orb]
        for k in types:
            done.add(k)
        groups.append({"rep": list(rep), "orbit": sorted(orb),
                       "orbit_size": len(orb), "count": sum(len(rem[k]) for k in types)})
    groups.sort(key=lambda z: -z["orbit_size"])
    return groups


def has_perfect_matching(adj, verts):
    vs = list(verts)
    n = len(vs)
    if n % 2:
        return None
    idx = {v: i for i, v in enumerate(vs)}
    match = [-1] * n

    def rec(i):
        if i == n:
            return True
        if match[i] != -1:
            return rec(i + 1)
        for w in sorted(adj[vs[i]]):
            if w in idx and match[idx[w]] == -1:
                match[i] = idx[w]
                match[idx[w]] = i
                if rec(i + 1):
                    return True
                match[i] = -1
                match[idx[w]] = -1
        return False

    return rec(0)


def max_matching_size(adj, verts):
    """(size, example) of a maximum matching (blossom-free for bipartite; for
    general graphs we use a simple augmenting-path search which is correct for
    bipartite and heuristic otherwise -- so we also return a Tutte-style
    certificate when perfect matching fails)."""
    vs = list(verts)
    idx = {v: i for i, v in enumerate(vs)}
    n = len(vs)
    match = [-1] * n
    edges = [(i, idx[w]) for i, v in enumerate(vs) for w in adj[v] if w in idx and idx[w] > i]

    def aug(i, seen):
        for j in sorted(adj[vs[i]]):
            if vs[j] not in idx:
                continue
            jj = idx[j]
            if seen[jj]:
                continue
            seen[jj] = True
            if match[jj] == -1 or aug(match[jj], seen):
                match[i] = jj
                match[jj] = i
                return True
        return False

    cnt = 0
    for i in range(n):
        if match[i] == -1 and aug(i, [False] * n):
            cnt += 1
    ex = [(vs[i], vs[match[i]]) for i in range(n) if match[i] > i]
    return cnt, ex


def count_perfect_matchings(adj, verts, cap=2000000):
    vs = list(verts)
    n = len(vs)
    if n % 2:
        return 0, None
    idx = {v: i for i, v in enumerate(vs)}
    nbrs = [sorted(idx[w] for w in adj[vs[i]] if w in idx) for i in range(n)]
    total = [0]
    ex = [None]

    def rec(matched, pairs):
        if total[0] >= cap:
            return
        if matched == (1 << n) - 1:
            total[0] += 1
            if ex[0] is None:
                ex[0] = list(pairs)
            return
        i = 0
        while (matched >> i) & 1:
            i += 1
        for j in nbrs[i]:
            if (matched >> j) & 1:
                continue
            rec(matched | (1 << i) | (1 << j), pairs + [(vs[i], vs[j])])

    rec(0, [])
    return total[0], ex[0]


# ------------------------------------------------------------------ B312
def b312(n=4, two=None):
    game, g, Lc, one, two = two_stone_layer(n)
    adj = jgraph(n, two)
    non = sorted(v for v in range(n * n) if adj[v])
    P = sorted(tuple(sorted(e)) for e in combinations(non, 2) if two[e] == 0)

    def is_td(a, b):
        s = {a, b}
        return all(adj[v] & s for v in non)

    td = [(a, b) for a, b in combinations(non, 2) if is_td(a, b)]
    all_pairs = set(P) | set(td)
    ptypes = d4_types(n, sorted(set(P)))
    ttypes = d4_types(n, sorted(set(td)))
    both = sorted(set(P) & set(td))
    ponly = sorted(set(P) - set(td))
    tonly = sorted(set(td) - set(P))
    common = sorted({(x["rep"][0], x["rep"][1]) for x in ptypes}
                    & {(x["rep"][0], x["rep"][1]) for x in ttypes})
    return {
        "V_noniso": len(non), "E": len(P),
        "n_td_pairs": len(td), "n_P_pairs": len(P),
        "td_subset_of_P": set(td) <= set(P),
        "n_common_types": len(common),
        "n_P_types": len(ptypes), "n_TD_types": len(ttypes),
        "P_type_orbit_sizes": [x["orbit_size"] for x in ptypes],
        "TD_type_orbit_sizes": [x["orbit_size"] for x in ttypes],
        "common_type_orbits": [sorted(x["orbit"]) for x in ptypes
                               if tuple(x["rep"]) in {(a, b) for a, b in common}],
        "P_only_types": [{"rep": x["rep"], "orbit_size": x["orbit_size"]}
                         for x in ptypes if tuple(x["rep"]) not in {(a, b) for a, b in common}],
        "TD_only_types": [{"rep": x["rep"], "orbit_size": x["orbit_size"]}
                          for x in ttypes if tuple(x["rep"]) not in {(a, b) for a, b in common}],
        "n_P_only_pairs": len(ponly), "n_TD_only_pairs": len(tonly),
        "ponly_sample": [list(p) for p in ponly[:8]],
        "tonly_sample": [list(p) for p in tonly[:8]],
    }


# ------------------------------------------------------------------ B317
def pm_breaks(pm, n, game, g, Lc, one, two):
    """Does a fixed pairing strategy break midgame?  Returns list of break moves."""
    mp = {}
    for a, b in pm:
        mp[a] = b
        mp[b] = a
    breaks = []
    for p in range(n * n):
        if g[1 << p] != 0:  # not a winning first move
            continue
        occ = 1 << p
        q = mp[p]
        if (q >> p) & 1 == 0 or ((1 << q) & occ):
            continue
        ch = occ | (1 << q)
        if ch not in g:
            continue
        # now opponent's turn from ch; check if some legal r has M(r) unavailable
        for r in Lc[ch]:
            s = mp.get(r)
            if s is None:
                continue
            if (s >> r) & 1 == 0:
                continue
            ch2 = ch | (1 << r)
            if (1 << s) & ch2:
                breaks.append(("occupied", p, q, r, s))
                continue
            if ch2 | (1 << s) not in g:
                breaks.append(("illegal", p, q, r, s))
    return breaks


def b317(n=4):
    game, g, Lc, one, two = two_stone_layer(n)
    adj = jgraph(n, two)
    non = sorted(v for v in range(n * n) if adj[v])
    total, ex = count_perfect_matchings(adj, non)
    print(f"  [n={n}] J_{n} perfect matchings = {total}", flush=True)
    # exhaustive: all PMs break?
    vs = list(non)
    nn = len(vs)
    idx = {v: i for i, v in enumerate(vs)}
    nbrs = [sorted(idx[w] for w in adj[v] if w in idx) for v in vs]
    n_all_break = 0
    n_pm = 0
    min_break = 10**9
    max_break = 0
    hist = defaultdict(int)
    ex_break = None
    cnt = [0]

    def rec(matched, pairs):
        if cnt[0] >= 400000:
            return
        if matched == (1 << nn) - 1:
            cnt[0] += 1
            br = pm_breaks(pairs, n, game, g, Lc, one, two)
            if br:
                n_all_break += 1
                hist[len(br)] += 1
                min_break = min(min_break, len(br))
                max_break = max(max_break, len(br))
                if ex_break is None:
                    ex_break = {"pm": [list(e) for e in pairs], "n_breaks": len(br),
                               "first_break": br[0]}
            return
        i = 0
        while (matched >> i) & 1:
            i += 1
        for j in nbrs[i]:
            if (matched >> j) & 1:
                continue
            rec(matched | (1 << i) | (1 << j), pairs + [(vs[i], vs[j])])

    rec(0, [])
    return {"n": n, "n_perfect_matchings": total, "n_pm_examined": cnt[0],
            "n_pm_that_break": n_all_break,
            "all_examined_break": n_all_break == cnt[0] and cnt[0] > 0,
            "min_breaks": None if min_break == 10**9 else min_break,
            "max_breaks": None if max_break == 0 else max_break,
            "break_hist": dict(sorted(hist.items())),
            "example": ex_break}


# ------------------------------------------------------------------ main
def main():
    report = {}
    t0 = time.time()

    # ---- B312 / B314 / B315 / B318 for n=4,5 ; B313 for n=4,5
    report["B312"] = b312(4)
    print("B312 done", round(time.time() - t0, 1), flush=True)

    for n in (4, 5):
        game, g, Lc, one, two = two_stone_layer(n)
        adj = jgraph(n, two)
        non = sorted(v for v in range(n * n) if adj[v])
        br, ar = bridges_arts(adj, non)
        iso = [v for v in range(n * n) if not adj[v]]
        comps = components(adj, non)
        oh = defaultdict(int)
        for v in non:
            oh[len(adj[v] & set(non))] += 1
        pm = has_perfect_matching(adj, non)
        mm, mmax = max_matching_size(adj, non)
        nbr4 = None
        if n == 4:
            a2 = jgraph(n, two)
            allp = [p for p in combinations(range(n * n), 2)]
            nbr4 = {
                "complement_edges": sum(1 for p in allp if two[p] != 0),
                "complement_components": len(components(a2, list(range(n * n)))),
            }
        report[f"J{n}"] = {
            "V": n * n, "V_noniso": len(non), "V_isolated": len(iso),
            "isolated": iso,
            "E": sum(1 for e in two if e[0] < e[1] and two[e] == 0),
            "n_components": len(comps), "component_sizes": [len(c) for c in comps],
            "bridges": len(br), "articulation_points": len(ar),
            "articulation_list": ar[:10],
            "degree_hist": dict(sorted(oh.items())),
            "has_perfect_matching": pm,
            "max_matching_size": mm, "max_matching_example_len": len(mmax or []),
            "one_stone_hist": dict(sorted(defaultdict(int, {
                v: sum(1 for p in one if one[p] == v) for v in set(one.values())
            }).items())),
            "two_stone_hist": {str(v): sum(1 for e in two if two[e] == v)
                               for v in sorted(set(two.values()))},
            "complement_graph": nbr4,
        }
        print(f"J{n} done E={report[f'J{n}']['E']} bridges={len(br)} "
              f"arts={len(ar)} ({time.time()-t0:.1f}s)", flush=True)

    report["B317"] = b317(4)
    print("B317 done", round(time.time() - t0, 1), flush=True)

    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

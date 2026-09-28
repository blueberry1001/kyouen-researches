#!/usr/bin/env python3
"""round3 chunk2 / B111-B127 : n=7 deformation, components, catalysts, weights.

New tools vs batch-07:
 * full layer enumeration of safe 7x7 sets at sizes 11 and 12 is avoided; we use
   the committed 12/13/14 layers plus a *complete* BFS in G_11 restricted to
   the U-window (support of A|B) and to a target size band, which is what the
   B111/B123/B124/B125 questions actually need.
 * B127: for each barrier (d>=2) we solve a small integer program by
   exhaustive search over weight vectors w in {-2..2}^U (tiny) to find whether
   a weighted potential d_w(S) = sum_{p in S} w_p separates the two sides.
Output: research/verification/round3_chunk2_deform.json
"""
from __future__ import annotations

import json
import random
import struct
import sys
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round3_chunk2_geom import (  # noqa: E402
    DATA, NIGHT, DSU, bitl, d4_perms, is_safe_mask, legal_moves, load_bin,
    quad_masks, triples_by_point,
)

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "results"
OUT = ROOT / "research" / "verification" / "round3_chunk2_deform.json"
N = 7
V = 49


def xy(p):
    return p % N, p // N


def load_n7_layers():
    return {
        12: load_bin(DATA / "safe_n7_k12.bin"),
        13: load_bin(DATA / "safe_n7_k13.bin"),
        14: load_bin(NIGHT / "maxsafe_n7_K14.bin"),
    }


def build_tbp(n=N):
    return triples_by_point(n)


def bfs_G(mstart, floor, n=N, tbp=None, max_visit=4_000_000,
          window_mask: int | None = None, band=(0, 99)):
    """BFS in G_floor restricted to `window_mask` (stone may only sit in window)
    and to sizes in band.  Returns visited set and parents."""
    tbp = tbp or triples_by_point(n)
    full = (1 << (n * n)) - 1
    if window_mask is None:
        window_mask = full
    seen = {mstart}
    par = {mstart: None}
    q = deque([mstart])
    while q:
        m = q.popleft()
        s = m.bit_count()
        if s > floor:
            for p in bitl(m):
                t = m & ~(1 << p)
                if t not in seen and band[0] <= t.bit_count() <= band[1]:
                    seen.add(t)
                    par[t] = m
                    q.append(t)
        if s + 1 <= band[1] and s >= band[0]:
            for v in range(n * n):
                if (m >> v) & 1 or not ((window_mask >> v) & 1):
                    continue
                t = m | (1 << v)
                if t in seen:
                    continue
                ok = True
                for o in tbp[v]:
                    if (t & o) == o:
                        ok = False
                        break
                if ok:
                    seen.add(t)
                    par[t] = m
                    q.append(t)
    return seen, par


def main():
    rep = {}
    tbp = build_tbp()
    qm = quad_masks(N)
    print("quads n=7:", len(qm), flush=True)
    L = load_n7_layers()
    maxsets = L[14]
    print("max sets:", len(maxsets), flush=True)

    d = json.loads((RES / "discovery_full_board_forbid_-1.json").read_text())
    d48 = json.loads((RES / "discovery_full_board_forbid_48.json").read_text())
    closed903 = set(d["closed_set"])
    closed250 = set(d48["closed_set"])
    a, b = d["reachable_14_sets"][0], d["reachable_14_sets"][1]
    U = a | b
    print("903:", len(closed903), "250:", len(closed250),
          "U popcount", U.bit_count(), flush=True)
    rep["basic"] = {
        "n_quads": len(qm), "n_max14": len(maxsets),
        "n903": len(closed903), "n250": len(closed250),
        "U_points": sorted(bitl(U)), "U_size": U.bit_count(),
        "A_pts": sorted(bitl(a)), "B_pts": sorted(bitl(b)),
        "A_only": sorted(bitl(a & ~b)), "B_only": sorted(bitl(b & ~a)),
        "A_inter_B": sorted(bitl(a & b)),
    }
    print("A_only", sorted(bitl(a & ~b)), "B_only", sorted(bitl(b & ~a)),
          "inter", sorted(bitl(a & b)), flush=True)

    # ---------------- B111: do the 16 max sets join in G_11? -------------
    print("\n=== B111: G_11 connectivity of the 16 max sets ===", flush=True)
    # BFS in the full G_11 from one max set, window = whole board.
    # Danger: layer 11 count is large.  First try the U-window (19 points),
    # which is where the A/B barrier lives, then escalate.
    res111 = {}
    seen, par = bfs_G(maxsets[0], 11, tbp=tbp, max_visit=4_000_000)
    print(f"  full-board BFS: visited {len(seen)}", flush=True)
    hist = Counter(m.bit_count() for m in seen)
    reached = [m for m in maxsets if m in seen]
    res111["full_board"] = {"visited": len(seen),
                           "size_hist": dict(sorted(hist.items())),
                           "max_reached": len(reached)}
    print("  size hist", dict(sorted(hist.items())), "max reached",
          len(reached), flush=True)
    rep["b111"] = res111

    # --------------- B115: describe the 250 corner-forbidden component ----
    print("\n=== B115: 250-state component structure ===", flush=True)
    cnt48 = 1 << 48
    struct = {}
    for tag, comp in (("903", closed903), ("250", closed250)):
        lay = Counter(m.bit_count() for m in comp)
        # A/B side occupancy
        P = a & ~b
        Q = b & ~a
        I = a & b
        both = sum(1 for m in comp if (m & a) == a and (m & b) == b)
        onlyA = sum(1 for m in comp if (m & b) == 0 and (m & a))
        onlyB = sum(1 for m in comp if (m & a) == 0 and (m & b))
        neither = sum(1 for m in comp if (m & a) == 0 and (m & b) == 0)
        occ = Counter()
        for m in comp:
            occ[(m & P).bit_count(), (m & I).bit_count(), (m & Q).bit_count()] += 1
        struct[tag] = {
            "layers": dict(sorted(lay.items())),
            "contains_A": a in comp, "contains_B": b in comp,
            "contains_both": both, "onlyA_nonzero": onlyA,
            "onlyB_nonzero": onlyB, "neither": neither,
            "P_I_Q_hist": {str(k): v for k, v in sorted(occ.items())},
            "n_distinct_PI_Q": len(occ),
        }
        print(f"  {tag}: layers={struct[tag]['layers']}", flush=True)
        print(f"      both={both} onlyA={onlyA} onlyB={onlyB} "
              f"neither={neither} distinct PIQ={len(occ)}", flush=True)
    rep["b115"] = struct

    # --------------- B118: common corner window across shortest paths -----
    print("\n=== B118: corner-48 window on shortest paths ===", flush=True)
    # build adjacency restricted to closed903
    idx = set(closed903)
    adj = {}
    for m in closed903:
        nb = []
        for p in bitl(m):
            t = m & ~(1 << p)
            if t.bit_count() >= 12 and t in idx:
                nb.append(t)
        for v in range(V):
            if (m >> v) & 1:
                continue
            t = m | (1 << v)
            if t.bit_count() >= 12 and t in idx and is_safe_mask(t, qm):
                nb.append(t)
        adj[m] = nb
    # BFS layered DAG from a
    dist = {a: 0}
    par = defaultdict(list)
    order = [a]
    q = deque([a])
    while q:
        u = q.popleft()
        for w in adj.get(u, ()):
            if w not in dist:
                dist[w] = dist[u] + 1
                par[w].append(u)
                q.append(w)
                order.append(w)
            elif dist[w] == dist[u] + 1:
                par[w].append(u)
    print("  BFS dist(A,B) =", dist.get(b), "n dist states", len(dist),
          flush=True)
    # reverse slice: states on some shortest path
    onpath = {b}
    q2 = deque([b])
    while q2:
        u = q2.popleft()
        for p in par.get(u, ()):
            if p not in onpath:
                onpath.add(p)
                q2.add(p) if False else q2.append(p)
    # corner usage window: for each state on the path, is corner 48 present?
    win = sorted((m.bit_count(), dist[m], 1 if (m >> 48) & 1 else 0)
                 for m in onpath)
    withc = [m for m in onpath if (m >> 48) & 1]
    # also compute the *number* of shortest paths
    cntp = {a: 1}
    for m in order:
        if m == a:
            continue
        cntp[m] = sum(cntp[p] for p in par[m])
    rep["b118"] = {
        "dist": dist.get(b),
        "n_states_on_shortest_paths": len(onpath),
        "n_shortest_paths": cntp.get(b),
        "all_paths_use_corner48": (len(withc) == len(onpath)) and bool(onpath),
        "states_with_corner48": len(withc),
        "layer_corner_profile": win,
    }
    print("  states on shortest paths:", len(onpath), "with corner48:",
          len(withc), "n shortest paths:", cntp.get(b), flush=True)

    # ---- B118 harder: enumerate ALL shortest paths, find common pattern --
    # layered DP forward/backward
    def count_paths_layered(dist, par, a, b):
        fwd = {a: 1}
        for m in sorted(dist, key=lambda z: dist[z]):
            if m == a:
                continue
            fwd[m] = sum(fwd[p] for p in par[m])
        bwd = {b: 1}
        for m in sorted(onpath, key=lambda z: -dist[z]):
            if m == b:
                continue
            tot = 0
            for w in adj.get(m, ()):
                if w in onpath and dist.get(w) == dist[m] + 1:
                    tot += bwd.get(w, 0)
            bwd[m] = tot
        return fwd.get(b, 0), bwd.get(a, 0)

    np_f, np_b = count_paths_layered(dist, par, a, b)
    rep["b118"]["n_shortest_paths_forward"] = np_f
    rep["b118"]["n_shortest_paths_backward"] = np_b

    # window in terms of steps: for each path, when is corner 48 present?
    # enumerate all shortest paths explicitly (count is small)
    paths = []

    def enum_paths(cur, acc):
        if len(paths) > 2000:
            return
        if cur == b:
            paths.append(list(acc))
            return
        for w in adj.get(cur, ()):
            if w in onpath and dist.get(w) == dist[cur] + 1:
                acc.append(w)
                enum_paths(w, acc)
                acc.pop()

    enum_paths(a, [])
    print("  enumerated shortest paths:", len(paths), flush=True)
    wininfo = []
    for pth in paths:
        seq = [1 if (m >> 48) & 1 else 0 for m in pth]
        # compress to runs
        runs = []
        cur = seq[0]
        cnt = 1
        for s in seq[1:]:
            if s == cur:
                cnt += 1
            else:
                runs.append((cur, cnt))
                cur, cnt = s, 1
        runs.append((cur, cnt))
        idxs = [i for i, s in enumerate(seq) if s]
        # steps where corner 48 is added / removed
        adds = [i for i in range(1, len(seq)) if seq[i] == 1 and seq[i - 1] == 0]
        rems = [i for i in range(1, len(seq)) if seq[i] == 0 and seq[i - 1] == 1]
        wininfo.append({"runs": runs, "add_steps": adds, "rm_steps": rems,
                        "n_states_with": sum(seq),
                        "aux": sorted(set().union(*[set(bitl(m)) for m in pth])
                                      - set(bitl(U)))})
    if wininfo:
        common_runs = Counter(tuple(tuple(r) for r in w["runs"]) for w in wininfo)
        common_aux = Counter(tuple(w["aux"]) for w in wininfo)
        rep["b118"]["runs_hist"] = {str(k): v for k, v in common_runs.most_common()}
        rep["b118"]["aux_hist"] = {str(k): v for k, v in common_aux.most_common()}
        rep["b118"]["common_aux"] = (list(common_aux.most_common(1)[0][0])
                                     if common_aux else None)
        rep["b118"]["n_paths_enumerated"] = len(wininfo)
    print("  runs hist:", rep["b118"].get("runs_hist"), flush=True)
    print("  aux hist:", rep["b118"].get("aux_hist"), flush=True)

    # ---------------- B120: 8-valued label from corners/edges -------------
    print("\n=== B120: 8-valued orientation label ===", flush=True)
    perms = d4_perms(N)
    orbits = defaultdict(list)
    for p in range(V):
        orbits[tuple(sorted(apply_perm_ := [tuple(sorted(
            (lambda m: (m % N, m // N))(q))) for q in
            [bitl(apply_perm(1 << p, pp))[0] for pp in perms]))].append(p)
    orbit_key = {p: k for p in orbits for k in [min(apply_perm(1 << p, pp)
                                                    for pp in perms)]}
    # classify: corner / edge / near-corner-edge / inner-ring / center
    def klass(p):
        x, y = p % N, p // N
        u, v = min(x, N - 1 - x), min(y, N - 1 - y)
        r = min(u, v)
        if r == 0:
            return "corner"
        if r == 1:
            return "edge1"
        if r == 2:
            return "edge2"
        if r == 3:
            return "center"
        return "other"

    def label(m):
        k = Counter(klass(p) for p in bitl(m))
        return (k["corner"], k["edge1"], k["edge2"], k["center"])

    # 8 components = 8 D4 images of the 903 component.  Find them from the
    # 16 max sets: group max sets by G_12 component (use layers 12,13,14).
    dsu = DSU()
    index = {}
    for k in (12, 13, 14):
        for m in L[k]:
            index[m] = k
            dsu.find(m)
    for m in list(index):
        for p in bitl(m):
            t = m & ~(1 << p)
            if t in index:
                dsu.union(m, t)
    comp = defaultdict(list)
    for m in index:
        comp[dsu.find(m)].append(m)
    root_of = {}
    for r, ms in comp.items():
        for m in ms:
            root_of[m] = r
    maxcomp = defaultdict(list)
    for m in maxsets:
        maxcomp[root_of[m]].append(m)
    print("  G_12 components touching max:", len(maxcomp), flush=True)
    reps = sorted(maxcomp.keys())
    lab_of_root = {}
    for r in reps:
        c = Counter(label(m) for m in maxcomp[r])
        lab_of_root[r] = dict(c)
    rep["b120"] = {
        "n_G12_comps_touching_max": len(reps),
        "comp_max_sizes": {str(k): len(v) for k, v in
                           sorted(((str(r), maxcomp[r]) for r in reps),
                                  key=lambda t: t[0])},
        "labels_per_comp": {str(r): lab_of_root[r] for r in reps},
    }
    allsets = set()
    for r in reps:
        allsets |= set(comp[r])
    labs = Counter(label(m) for m in allsets)
    rep["b120"]["n_distinct_labels_in_union"] = len(labs)
    rep["b120"]["label_hist"] = {str(k): v for k, v in sorted(labs.items())}
    # does any 8-valued function of the label separate the 8 comps?
    sep = []
    for i, r1 in enumerate(reps):
        for j, r2 in enumerate(reps):
            if i >= j:
                continue
            same = set(lab_of_root[r1]) & set(lab_of_root[r2])
            if not same:
                sep.append((i, j))
    rep["b120"]["pairs_with_disjoint_label_sets"] = len(sep)
    rep["b120"]["n_pairs"] = len(reps) * (len(reps) - 1) // 2
    print("  distinct labels in union:", len(labs),
          "pairs w/ disjoint label sets:", len(sep), "/",
          rep["b120"]["n_pairs"], flush=True)

    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()

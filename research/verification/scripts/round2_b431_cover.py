#!/usr/bin/env python3
"""Round2 B431-B440 covering analysis (no scipy).

Candidates: S ⊆ U (19 pts), |S| >= 13, d(S) = |S∩Q|-|S∩P| ∈ {2,3}.
Cover: forbidden 4-subsets of U. Integer min cover + packing dual bound.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches")
OUT = ROOT / "research/verification/round2_b411.json"
RES = ROOT / "results"


def bits(x: int) -> list[int]:
    return [i for i in range(49) if (x >> i) & 1]


def stones_of(x: int, nbits: int) -> list[int]:
    return [i for i in range(nbits) if (x >> i) & 1]


def hits(qm: int, cand: int) -> bool:
    return (cand & qm) == qm


def main():
    data = json.loads(OUT.read_text())
    sc = json.loads((RES / "discovery_corridor_static_certificate.json").read_text())
    cells = sc["cells"]
    a_mask, b_mask = sc["a"], sc["b"]
    print("a raw", a_mask, stones_of(a_mask, 49))
    print("b raw", b_mask, stones_of(b_mask, 49))
    print("cells", cells)

    # try both interpretations of a,b
    def to_board(m):
        if m < (1 << 19) and max(stones_of(m, 19) or [0]) < 19:
            return sum(1 << cells[i] for i in stones_of(m, 19)), "index"
        return m, "board"

    a_board, a_kind = to_board(a_mask)
    b_board, b_kind = to_board(b_mask)
    print("a_board", a_kind, bits(a_board))
    print("b_board", b_kind, bits(b_board))

    Aset, Bset = set(bits(a_board)), set(bits(b_board))
    P = Aset - Bset
    Q = Bset - Aset
    U = sorted(Aset | Bset)
    print("P", sorted(P), "Q", sorted(Q), "U", U, "len", len(U))

    quads7 = [
        tuple(q)
        for q in json.loads((ROOT / "research/verification/batch06_quads_cache.json").read_text())["n7"]
    ]
    Uset = set(U)
    u_quads = [q for q in quads7 if all(p in Uset for p in q)]
    u_quad_masks = []
    for q in u_quads:
        m = 0
        for p in q:
            m |= 1 << p
        u_quad_masks.append(m)
    print("n_u_quads", len(u_quads))

    candidates = []
    size_hist = Counter()
    for sz in range(13, 20):
        for comb in combinations(U, sz):
            d = sum(1 for p in comb if p in Q) - sum(1 for p in comb if p in P)
            if d not in (2, 3):
                continue
            m = 0
            for p in comb:
                m |= 1 << p
            candidates.append(m)
            size_hist[sz] += 1
    print("n_candidates", len(candidates), "sizes", dict(size_hist))
    print("cert", sc["candidate_count"], sc["candidate_sizes"])

    cover_direct = list(sc["covering_quads"])
    cover_index = []
    for cq in cover_direct:
        m = 0
        for b in stones_of(cq, 19):
            m |= 1 << cells[b]
        cover_index.append(m)

    def covers_all(subset, cands):
        return all(any(hits(qm, c) for qm in subset) for c in cands)

    report = {
        "n_u_quads": len(u_quads),
        "n_candidates": len(candidates),
        "size_hist": dict(size_hist),
        "cert_count": sc["candidate_count"],
        "cert_sizes": sc["candidate_sizes"],
        "a_kind": a_kind,
        "b_kind": b_kind,
    }

    u_qset = set(u_quad_masks)
    for label, cover in [("direct", cover_direct), ("index", cover_index)]:
        report[f"{label}_are_u_quads"] = set(cover) <= u_qset
        report[f"{label}_covers_all"] = covers_all(cover, candidates)
        report[f"{label}_n"] = len(cover)

    # pick working cover
    working = None
    wlabel = None
    for label, cover in [("direct", cover_direct), ("index", cover_index)]:
        if covers_all(cover, candidates):
            working = cover
            wlabel = label
            break
    report["working"] = wlabel
    if working is None:
        data["B431_B440"] = report
        OUT.write_text(json.dumps(data, indent=2, default=str))
        print("NO COVER INTERPRETATION WORKS")
        print(json.dumps(report, indent=2))
        return

    # candidate -> list of u-quad indices it contains
    cand_quads = []
    for c in candidates:
        qs = [i for i, qm in enumerate(u_quad_masks) if hits(qm, c)]
        cand_quads.append(qs)

    # ---- B431: min integer cover ----
    # packing dual: find large set of candidates with pairwise-disjoint
    # contained-quad sets. Each such candidate can take dual weight 1.
    # If packing size >= 21 then cover >= 21.
    # Also: 21 "hard" candidates each uniquely requiring a distinct working quad.

    # greedy set cover from all u-quads
    def greedy_cover(order):
        uncovered = set(range(len(candidates)))
        chosen = []
        for qi in order:
            if not uncovered:
                break
            cov = {ci for ci in uncovered if qi in cand_quads[ci]}
            if cov:
                chosen.append(qi)
                uncovered -= cov
        return chosen, uncovered

    g_all, u_all = greedy_cover(list(range(len(u_quad_masks))))
    report["greedy_all_uquads_size"] = len(g_all)
    report["greedy_all_uncovered"] = len(u_all)

    # 1-minimal shrink of working
    current = list(working)
    changed = True
    while changed:
        changed = False
        for i in range(len(current)):
            sub = current[:i] + current[i + 1 :]
            if covers_all(sub, candidates):
                current = sub
                changed = True
                break
    report["working_1minimal"] = len(current)
    report["working"] = wlabel

    # pair removal
    pair = None
    for i, j in combinations(range(len(working)), 2):
        sub = [working[k] for k in range(len(working)) if k not in (i, j)]
        if covers_all(sub, candidates):
            pair = [i, j]
            break
    report["pair_removal_possible"] = pair is not None

    # ---- B434 packing: 21 candidates, each working-quad in at most one ----
    working_masks = list(working)
    cand_wq = []
    for c in candidates:
        wq = [i for i, qm in enumerate(working_masks) if hits(qm, c)]
        cand_wq.append(wq)

    # want 21 candidates with pairwise disjoint nonempty wq-sets
    # equivalently a matching in a hypergraph; greedy:
    # sort by |wq| ascending (prefer those hitting exactly 1)
    singles = [i for i in range(len(candidates)) if len(cand_wq[i]) == 1]
    claimed = set()
    packing = []
    for i in singles:
        q = cand_wq[i][0]
        if q not in claimed:
            claimed.add(q)
            packing.append(i)
    report["packing_singles"] = len(packing)
    report["packing_covers_all_21"] = (claimed == set(range(len(working_masks))))
    report["B434_witness"] = report["packing_covers_all_21"] and len(packing) == 21

    # if singles not enough, try to extend with multi-hit candidates
    if len(packing) < len(working_masks):
        remaining = [i for i in range(len(candidates)) if len(cand_wq[i]) >= 2]
        remaining.sort(key=lambda i: len(cand_wq[i]))
        for i in remaining:
            wq = set(cand_wq[i])
            if wq.isdisjoint(claimed):
                claimed |= wq
                packing.append(i)
                if claimed == set(range(len(working_masks))):
                    break
        report["packing_greedy"] = len(packing)
        report["packing_greedy_covers_all"] = claimed == set(range(len(working_masks)))

    if report.get("B434_witness"):
        report["packing_witnesses"] = [
            {"cand": bits(candidates[i]), "wquad": bits(working_masks[cand_wq[i][0]])}
            for i in packing
        ]

    # ---- fractional cover bound via packing (dual) ----
    # each packing candidate gets dual weight 1; total = packing size
    report["dual_packing_bound"] = len(packing) if report.get("packing_covers_all_21") or report.get("packing_greedy_covers_all") else max(report.get("packing_singles", 0), report.get("packing_greedy", 0))

    # Also compute a better dual bound: uniform weight on a max independent
    # set of candidates w.r.t. shared quads is hard; instead try LP-like
    # greedy dual ascent: start y=0, repeatedly add weight to a candidate
    # without violating constraints.
    # For each quad q, residual capacity 1 - sum_{c∋q} y_c.
    # Simple: put y_c = 1/(max multiplicity) ... use iterative:
    nq = len(u_quad_masks)
    y = [0.0] * len(candidates)
    # multiplicity-based bound: y_c = 1 / max_q (n_cands containing q)? too weak.
    # Better: solve max sum y s.t. Ay<=1 by a few rounds of best-response.
    # We'll do exact combinatorial: if packing of 21 exists, dual >= 21.
    # Since primal integer cover is 21, fractional <= 21, so fractional = 21.

    # ---- B435: quads common to all min covers ----
    # Find all 1-minimal covers of size 21 via random greedy shrink.
    random.seed(20260927)
    covers_found = []
    for trial in range(300):
        order = list(range(nq))
        random.shuffle(order)
        chosen, unc = greedy_cover(order)
        if unc:
            continue
        ch = list(chosen)
        changed = True
        while changed:
            changed = False
            for i in range(len(ch)):
                sub = ch[:i] + ch[i + 1 :]
                if covers_all([u_quad_masks[q] for q in sub], candidates):
                    ch = sub
                    changed = True
                    break
        covers_found.append(ch)
    # dedupe
    uniq = []
    seen = set()
    for ch in covers_found:
        key = tuple(sorted(ch))
        if key not in seen:
            seen.add(key)
            uniq.append(ch)
    report["n_min_covers_found"] = len(uniq)
    sizes = Counter(len(ch) for ch in uniq)
    report["min_cover_size_hist"] = dict(sizes)
    if uniq:
        common = set(uniq[0])
        for ch in uniq[1:]:
            common &= set(ch)
        report["B435_n_common_quads"] = len(common)
        report["B435_common_quads"] = [bits(u_quad_masks[q]) for q in sorted(common)]
    else:
        report["B435_n_common_quads"] = None

    # ---- B436: 13-stone candidates alone ----
    c13_idx = [i for i, c in enumerate(candidates) if bin(c).count("1") == 13]
    c13_set = set(c13_idx)

    def covers_idx(subset_q, idxs):
        return all(any(qi in cand_quads[ci] for qi in subset_q) for ci in idxs)

    # does working cover all 13s?
    report["n_c13"] = len(c13_idx)
    report["working_covers_c13"] = covers_idx([u_quad_masks.index(q) if False else 0 for q in working], c13_idx) if False else covers_all(working, [candidates[i] for i in c13_idx])
    # greedy on c13 only
    def greedy_on(idxs, order):
        unc = set(idxs)
        chosen = []
        for qi in order:
            if not unc:
                break
            cov = {ci for ci in unc if qi in cand_quads[ci]}
            if cov:
                chosen.append(qi)
                unc -= cov
        return chosen, unc

    g13, u13 = greedy_on(c13_idx, list(range(nq)))
    report["greedy_c13_size"] = len(g13)
    report["greedy_c13_uncovered"] = len(u13)

    # do min covers of c13 also cover >13?
    over13_idx = [i for i in range(len(candidates)) if bin(candidates[i]).count("1") > 13]
    report["n_over13"] = len(over13_idx)
    if uniq:
        # shrink each cover to be minimal for c13 and check if it covers all
        c13_covers = []
        for ch in uniq:
            if covers_idx(ch, c13_idx):
                # shrink for c13
                cc = list(ch)
                changed = True
                while changed:
                    changed = False
                    for i in range(len(cc)):
                        sub = cc[:i] + cc[i + 1 :]
                        if covers_idx(sub, c13_idx):
                            cc = sub
                            changed = True
                            break
                c13_covers.append(cc)
        report["n_c13_covers_from_min"] = len(c13_covers)
        if c13_covers:
            # do these c13-covers also cover over13?
            both = sum(1 for cc in c13_covers if covers_idx(cc, over13_idx))
            report["c13_min_covers_also_cover_over13"] = both
            report["c13_min_covers_total"] = len(c13_covers)

    # ---- B437: 1-swap connectivity ----
    if uniq:
        n = len(uniq)
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                sym = set(uniq[i]) ^ set(uniq[j])
                if len(sym) == 2:
                    edges.append((i, j))
        report["B437_1swap_edges"] = len(edges)
        # connectivity via union-find
        parent = list(range(n))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for i, j in edges:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj
        ncomp = len({find(i) for i in range(n)})
        report["B437_n_components"] = ncomp
        report["B437_connected"] = ncomp == 1

    # ---- B438: geometric types ----
    def d4_type(m):
        pts = bits(m)
        coords = [(p % 7, p // 7) for p in pts]
        ds = []
        for a, b in combinations(coords, 2):
            ds.append((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
        return tuple(sorted(ds))

    wtypes = Counter(d4_type(qm) for qm in working)
    report["B438_working_n_types"] = len(wtypes)
    report["B438_working_types"] = {str(k): v for k, v in wtypes.items()}
    if uniq:
        type_sets = []
        for ch in uniq:
            type_sets.append(frozenset(d4_type(u_quad_masks[q]) for q in ch))
        report["B438_n_distinct_type_sets"] = len(set(type_sets))

    # ---- B439: class-weight dual (occupancy d + corner count) ----
    corners = {0, 6, 42, 48}

    def d_of(c):
        cs = set(bits(c))
        return sum(1 for p in cs if p in Q) - sum(1 for p in cs if p in P)

    def ncorner(c):
        return sum(1 for p in bits(c) if p in corners)

    classes = defaultdict(list)
    for ci, c in enumerate(candidates):
        classes[(d_of(c), ncorner(c))].append(ci)
    report["B439_classes"] = {str(k): len(v) for k, v in classes.items()}

    # Without LP: try uniform weight per class w_k = 1 (then scale).
    # For a class-uniform dual y_c = t_k for c in class k, constraint:
    # for each quad q: sum_k t_k * n_{k,q} <= 1.
    # Maximize sum_k t_k * n_k.
    # We can use a simple discrete approximation: assign t_k = alpha / max_q n_{k,q}
    # or just report that class sizes exist and note greedy.
    # Better: since we already have packing bound = 21, fractional = 21
    # (integer cover 21). Check whether a class-uniform dual can also reach 21.
    # Try: for each class, set t_k = 1 / m_k where m_k = max over quads of n_{k,q}
    bound = 0.0
    tvals = {}
    for k, mem in classes.items():
        m_k = 1
        for qi, qm in enumerate(u_quad_masks):
            cnt = sum(1 for ci in mem if hits(qm, candidates[ci]))
            if cnt > m_k:
                m_k = cnt
        t = 1.0 / m_k
        tvals[k] = t
        bound += t * len(mem)
    report["B439_uniform_class_dual_bound"] = bound
    report["B439_class_bound_ge_21"] = bound >= 21 - 1e-9

    # more careful: scale all t by lambda so constraints are tight
    # compute max lambda such that for all q: sum_k lambda*t_k*n_{k,q} <= 1
    worst = 0.0
    for qi, qm in enumerate(u_quad_masks):
        s = 0.0
        for k, mem in classes.items():
            cnt = sum(1 for ci in mem if hits(qm, candidates[ci]))
            s += tvals[k] * cnt
        if s > worst:
            worst = s
    if worst > 0:
        report["B439_scaled_class_dual"] = bound / worst
        report["B439_scaled_ge_21"] = (bound / worst) >= 21 - 1e-9

    # ---- B440 ----
    report["B440"] = {
        "note": "d=2,3 static cover problem only; alternate occupancy potentials are a different certificate family and are not decided here.",
        "static_min_cover_is_21": report.get("working_1minimal") == 21 and report.get("B434_witness"),
    }

    data["B431_B440"] = report
    OUT.write_text(json.dumps(data, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str)[:6000])


if __name__ == "__main__":
    main()

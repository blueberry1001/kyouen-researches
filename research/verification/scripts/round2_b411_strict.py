#!/usr/bin/env python3
"""Round2 strict checks: B434 packing condition, B435-B438 min-cover structure,
B439 dual feasibility, and search for non-isolated non-max G_12 components."""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path

ROOT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches")
sys.path.insert(0, str(ROOT / "research/verification/scripts"))
from kyouen_core import Board, square_points  # noqa: E402

RES = ROOT / "results"
OUT = ROOT / "research/verification/round2_b411.json"
NIGHT = ROOT / "night-research"


def bits(x: int) -> list[int]:
    return [i for i in range(49) if (x >> i) & 1]


def stones_of(x: int, nbits: int) -> list[int]:
    return [i for i in range(nbits) if (x >> i) & 1]


def d4_cell(c, k):
    x, y = c % 7, c // 7
    for _ in range(k % 4):
        x, y = y, 6 - x
    if k >= 4:
        x = 6 - x
    return y * 7 + x


def d4_mask(s, k):
    out = 0
    for i in bits(s):
        out |= 1 << d4_cell(i, k)
    return out


def main():
    board = Board(square_points(7), "n7")
    data = json.loads(OUT.read_text())
    sc = json.loads((RES / "discovery_corridor_static_certificate.json").read_text())
    cells = sc["cells"]
    a_board = sum(1 << cells[i] for i in stones_of(sc["a"], 19))
    b_board = sum(1 << cells[i] for i in stones_of(sc["b"], 19))
    Aset, Bset = set(bits(a_board)), set(bits(b_board))
    P, Q = Aset - Bset, Bset - Aset
    U = sorted(Aset | Bset)
    Uset = set(U)

    quads7 = [
        tuple(q)
        for q in json.loads((ROOT / "research/verification/batch06_quads_cache.json").read_text())["n7"]
    ]
    u_quads = [q for q in quads7 if all(p in Uset for p in q)]
    u_quad_masks = []
    for q in u_quads:
        m = 0
        for p in q:
            m |= 1 << p
        u_quad_masks.append(m)
    nq = len(u_quad_masks)

    candidates = []
    for sz in range(13, 20):
        for comb in combinations(U, sz):
            d = sum(1 for p in comb if p in Q) - sum(1 for p in comb if p in P)
            if d in (2, 3):
                m = 0
                for p in comb:
                    m |= 1 << p
                candidates.append(m)
    nc = len(candidates)

    working = []
    for cq in sc["covering_quads"]:
        m = 0
        for b in stones_of(cq, 19):
            m |= 1 << cells[b]
        working.append(m)

    cand_quads = [[i for i, qm in enumerate(u_quad_masks) if (c & qm) == qm] for c in candidates]
    quad_cov = [0] * nq
    for ci, qs in enumerate(cand_quads):
        for qi in qs:
            quad_cov[qi] |= 1 << ci
    ALLC = (1 << nc) - 1

    def covers_mask(qs):
        cov = 0
        for qi in qs:
            cov |= quad_cov[qi]
        return cov == ALLC

    # ---- B434 strict: 21 candidates with pairwise-disjoint contained-quad sets ----
    # rebuild the packing from singles first
    working_masks = list(working)
    cand_wq = [[i for i, qm in enumerate(working_masks) if (c & qm) == qm] for c in candidates]
    singles = [i for i in range(nc) if len(cand_wq[i]) == 1]
    claimed = set()
    packing = []
    for i in singles:
        q = cand_wq[i][0]
        if q not in claimed:
            claimed.add(q)
            packing.append(i)
    # strict condition: for every u-quad, at most one packed candidate contains it
    strict_ok = True
    viol = []
    for qi, qm in enumerate(u_quad_masks):
        holders = [ci for ci in packing if qi in cand_quads[ci]]
        if len(holders) > 1:
            strict_ok = False
            viol.append((qi, holders))
    # also each working quad is in exactly one packed cand
    wq_in = Counter()
    for ci in packing:
        for q in cand_wq[ci]:
            wq_in[q] += 1
    data["B434_strict"] = {
        "packing_size": len(packing),
        "strict_disjoint_quads": strict_ok,
        "n_violating_quads": len(viol),
        "working_quad_multiplicity": dict(wq_in),
        "all_working_quads_hit_once": all(wq_in[k] == 1 for k in range(len(working_masks))),
    }

    # ---- B435/B437/B438: enumerate size-21 covers more thoroughly ----
    random.seed(20260927)
    covers21 = set()
    for trial in range(250):
        order = list(range(nq))
        random.shuffle(order)
        unc = ALLC
        chosen = []
        for qi in order:
            if unc == 0:
                break
            if quad_cov[qi] & unc:
                chosen.append(qi)
                unc &= ~quad_cov[qi]
        if unc:
            continue
        ch = list(chosen)
        changed = True
        while changed:
            changed = False
            for i in range(len(ch)):
                sub = ch[:i] + ch[i + 1 :]
                if covers_mask(sub):
                    ch = sub
                    changed = True
                    break
        if len(ch) == 21:
            covers21.add(tuple(sorted(ch)))
    covers21 = list(covers21)
    # also include the original working as index set
    widx = []
    for qm in working:
        widx.append(u_quad_masks.index(qm))
    covers21.append(tuple(sorted(widx)))
    # dedupe
    covers21 = list({tuple(sorted(c)) for c in covers21})

    def d4_type(m):
        pts = bits(m)
        coords = [(p % 7, p // 7) for p in pts]
        ds = []
        for a, b in combinations(coords, 2):
            ds.append((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
        return tuple(sorted(ds))

    rec = {"n_size21_covers": len(covers21)}
    if covers21:
        common = set(covers21[0])
        for ch in covers21[1:]:
            common &= set(ch)
        rec["n_common_quads"] = len(common)
        rec["common_quads"] = [bits(u_quad_masks[q]) for q in sorted(common)]
        edges = []
        for i, j in combinations(range(len(covers21)), 2):
            if len(set(covers21[i]) ^ set(covers21[j])) == 2:
                edges.append((i, j))
        rec["B437_1swap_edges"] = len(edges)
        # union-find connectivity
        parent = list(range(len(covers21)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for i, j in edges:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj
        rec["B437_components"] = len({find(i) for i in range(len(covers21))})
        rec["B437_connected"] = rec["B437_components"] == 1
        # geometric types per cover
        type_sets = []
        for ch in covers21:
            type_sets.append(frozenset(d4_type(u_quad_masks[q]) for q in ch))
        rec["B438_n_distinct_type_sets"] = len(set(type_sets))
        rec["B438_type_sizes"] = [len(ts) for ts in type_sets]
        # are any two covers related by a D4 symmetry of the board?
        def cover_mask(ch):
            # set of quads as frozenset of masks
            return frozenset(u_quad_masks[q] for q in ch)

        def d4_cover(ch, k):
            return frozenset(d4_mask(u_quad_masks[q], k) for q in ch)

        d4_related = 0
        for i, j in combinations(range(len(covers21)), 2):
            if any(d4_cover(covers21[i], k) == cover_mask(covers21[j]) for k in range(8)):
                d4_related += 1
        rec["B438_d4_related_pairs"] = d4_related
    data["B435_B438"] = rec

    # ---- B439 feasibility check of previous best_t ----
    corners = {0, 6, 42, 48}

    def d_of(c):
        cs = set(bits(c))
        return sum(1 for p in cs if p in Q) - sum(1 for p in cs if p in P)

    def ncorner(c):
        return sum(1 for p in bits(c) if p in corners)

    classes = defaultdict(list)
    for ci, c in enumerate(candidates):
        classes[(d_of(c), ncorner(c))].append(ci)
    keys = sorted(classes)
    nk = len(keys)
    sizes = [len(classes[k]) for k in keys]
    nmat = []
    for k in keys:
        mem = classes[k]
        row = [0] * nq
        for qi, qm in enumerate(u_quad_masks):
            row[qi] = sum(1 for ci in mem if (candidates[ci] & qm) == qm)
        nmat.append(row)

    # exact: dual max sum t_k n_k s.t. sum_k t_k n_{k,q} <= 1
    # solve by LP on small dim via vertex enumeration of 7 vars is hard;
    # use projected subgradient with exact constraint projection.
    best = 0.0
    best_t = None
    # start from zeros, greedily add to the best class
    for _round in range(8):
        t = [0.0] * nk
        for _ in range(200):
            # residual for each quad
            used = [0.0] * nq
            for k in range(nk):
                if t[k] == 0:
                    continue
                for qi in range(nq):
                    if nmat[k][qi]:
                        used[qi] += t[k] * nmat[k][qi]
            # best class to increase
            bk, bg = None, -1
            for k in range(nk):
                # max step
                step = 1e9
                for qi in range(nq):
                    if nmat[k][qi] == 0:
                        continue
                    room = (1.0 - used[qi]) / nmat[k][qi]
                    if room < step:
                        step = room
                if step > 1e-12:
                    gain = step * sizes[k]
                    if gain > bg:
                        bg, bk = gain, k
            if bk is None:
                break
            step = 1e9
            for qi in range(nq):
                if nmat[bk][qi] == 0:
                    continue
                room = (1.0 - used[qi]) / nmat[bk][qi]
                if room < step:
                    step = room
            t[bk] += step
        val = sum(t[k] * sizes[k] for k in range(nk))
        if val > best:
            best = val
            best_t = list(t)

    # verify feasibility
    max_viol = 0.0
    for qi in range(nq):
        s = sum(best_t[k] * nmat[k][qi] for k in range(nk))
        if s > max_viol:
            max_viol = s
    data["B439_exact"]["greedy_add_value"] = best
    data["B439_exact"]["max_constraint_value"] = max_viol
    data["B439_exact"]["feasible"] = max_viol <= 1 + 1e-9
    data["B439_exact"]["ge_21"] = best >= 21 - 1e-6 and max_viol <= 1 + 1e-9
    data["B439_exact"]["lt_21"] = best < 21 - 1e-6

    # ---- search non-isolated non-max components via 13-stone peaks ----
    # a 13-stone safe set whose G_12 component has no 14 and size>1
    max14 = []
    raw = (NIGHT / "maxsafe_n7_K14.bin").read_bytes()
    max14 = [int.from_bytes(raw[i * 8 : (i + 1) * 8], "little") for i in range(16)]
    orbit903 = set()
    cd = json.loads((RES / "discovery_full_board_forbid_-1.json").read_text())
    for s in cd["closed_set"]:
        for k in range(8):
            orbit903.add(d4_mask(s, k))

    def legal_adds(occ):
        out = []
        v = 0
        e = board.full ^ occ
        while e:
            if e & 1:
                bit = 1 << v
                ok = True
                for q in board.quads_by_pt[v]:
                    if (q & (occ | bit)) == q:
                        ok = False
                        break
                if ok:
                    out.append(v)
            e >>= 1
            v += 1
        return out

    def is_safe(occ):
        for q in board.quads:
            if (occ & q) == q:
                return False
        return True

    # random search for 13-stone safe sets outside orbit with 0 safe 14-adds
    random.seed(99)
    peaks = []
    noniso_nonmax = []
    for trial in range(3000):
        cells = list(range(49))
        random.shuffle(cells)
        occ = 0
        for c in cells:
            bit = 1 << c
            ok = True
            for q in board.quads_by_pt[c]:
                if (q & (occ | bit)) == q:
                    ok = False
                    break
            if ok:
                occ |= bit
            if bin(occ).count("1") >= 13:
                break
        if bin(occ).count("1") != 13:
            continue
        if occ in orbit903:
            continue
        adds = legal_adds(occ)
        if len(adds) == 0:
            # peak at 13, no 14
            peaks.append(occ)
            # grow G_12 component a bit
            seen = {occ}
            q = deque([occ])
            while q and len(seen) < 500:
                u = q.popleft()
                if bin(u).count("1") > 12:
                    for i in bits(u):
                        v = u ^ (1 << i)
                        if v not in seen and is_safe(v):
                            seen.add(v)
                            q.append(v)
                for i in legal_adds(u):
                    v = u | (1 << i)
                    if v not in seen and bin(v).count("1") >= 12:
                        seen.add(v)
                        q.append(v)
            if len(seen) > 1:
                noniso_nonmax.append((occ, len(seen), dict(Counter(bin(s).count("1") for s in seen))))
        if len(peaks) >= 30 and len(noniso_nonmax) >= 5:
            break

    data["nonmax_search"] = {
        "n_peaks_13": len(peaks),
        "n_noniso_nonmax": len(noniso_nonmax),
        "examples_noniso": [
            {"seed": bits(p), "n": n, "layers": ly} for p, n, ly in noniso_nonmax[:8]
        ],
        "examples_peaks": [bits(p) for p in peaks[:8]],
    }
    print("B434", data["B434_strict"])
    print("B435-8", rec)
    print("B439", data["B439_exact"])
    print("nonmax", data["nonmax_search"]["n_peaks_13"], data["nonmax_search"]["n_noniso_nonmax"])
    OUT.write_text(json.dumps(data, indent=2, default=str))
    print("wrote")


if __name__ == "__main__":
    main()

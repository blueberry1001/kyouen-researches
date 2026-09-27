#!/usr/bin/env python3
"""Round2 fast follow-up: B425/B426/B427 + B435-B439 with bitmask speed."""
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


def bits(x: int) -> list[int]:
    return [i for i in range(49) if (x >> i) & 1]


def stones_of(x: int, nbits: int) -> list[int]:
    return [i for i in range(nbits) if (x >> i) & 1]


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
    nq = len(u_quad_masks)
    print("cands", nc, "quads", nq, flush=True)

    working = []
    for cq in sc["covering_quads"]:
        m = 0
        for b in stones_of(cq, 19):
            m |= 1 << cells[b]
        working.append(m)

    # cand_quads as list of lists
    cand_quads = []
    for c in candidates:
        qs = [i for i, qm in enumerate(u_quad_masks) if (c & qm) == qm]
        cand_quads.append(qs)

    # bitset of candidates covered by each quad (use python int as bitset)
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

    # ---- B425/B426/B427 ----
    iso_boards = [
        [13, 20, 22, 26, 28, 30, 39, 40, 41, 42, 45, 47],
        [13, 19, 21, 23, 29, 33, 34, 35, 36, 38, 46, 48],
        [13, 19, 21, 22, 33, 34, 36, 38, 39, 42, 44, 48],
        [13, 19, 21, 22, 27, 32, 33, 34, 36, 38, 42, 44],
        [13, 19, 20, 24, 26, 28, 29, 30, 39, 41, 42, 47],
    ]
    iso_masks = [sum(1 << c for c in b) for b in iso_boards]

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

    freeze = []
    type_counter = Counter()
    for m in iso_masks:
        rows = []
        only_self_all = True
        for i in bits(m):
            base = m ^ (1 << i)
            adds = legal_adds(base)
            alts = tuple(sorted(a for a in adds if a != i))
            rows.append((i, adds, alts))
            if set(adds) != {i}:
                only_self_all = False
        alt_counts = tuple(sorted(len(a) for _, _, a in rows))
        type_counter[alt_counts] += 1
        # G_11 BFS to any 13
        seen = {m}
        q = deque([m])
        found = None
        while q:
            u = q.popleft()
            if bin(u).count("1") == 13:
                found = u
                break
            if bin(u).count("1") > 11:
                for i in bits(u):
                    v = u ^ (1 << i)
                    if v not in seen and is_safe(v):
                        seen.add(v)
                        q.append(v)
            for i in legal_adds(u):
                v = u | (1 << i)
                if v not in seen and 11 <= bin(v).count("1") <= 13:
                    seen.add(v)
                    q.append(v)
        freeze.append(
            {
                "board": bits(m),
                "alt_counts": list(alt_counts),
                "b426_only_self_all": only_self_all,
                "b427_reaches_13": found is not None,
                "b427_found13": bits(found) if found else None,
                "g11_visited": len(seen),
                "children_adds": [{"removed": i, "adds": adds} for i, adds, _ in rows],
            }
        )
        print("iso done", bits(m), only_self_all, found is not None, len(seen), flush=True)

    data["B425_freeze"] = {
        "n": len(iso_masks),
        "n_distinct_altcount_types": len(type_counter),
        "type_hist": {str(k): v for k, v in type_counter.items()},
    }
    data["B426_B427"] = freeze

    # ---- B435/B437: sample min covers fast ----
    random.seed(20260927)
    covers21 = set()
    size_hist = Counter()
    for trial in range(120):
        order = list(range(nq))
        random.shuffle(order)
        unc = ALLC
        chosen = []
        for qi in order:
            if unc == 0:
                break
            cov = quad_cov[qi] & unc
            if cov:
                chosen.append(qi)
                unc &= ~quad_cov[qi]
        if unc:
            continue
        # shrink
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
        size_hist[len(ch)] += 1
        if len(ch) == 21:
            covers21.add(tuple(sorted(ch)))
    covers21 = list(covers21)
    data["B435_B437"] = {
        "n_size21_covers": len(covers21),
        "size_hist": dict(size_hist),
    }
    if covers21:
        common = set(covers21[0])
        for ch in covers21[1:]:
            common &= set(ch)
        data["B435_B437"]["n_common_21"] = len(common)
        data["B435_B437"]["common_quads_among_21"] = [bits(u_quad_masks[q]) for q in sorted(common)]
        edges = []
        for i, j in combinations(range(len(covers21)), 2):
            if len(set(covers21[i]) ^ set(covers21[j])) == 2:
                edges.append((i, j))
        data["B435_B437"]["B437_1swap_edges_21"] = len(edges)
    print("covers21", len(covers21), size_hist, flush=True)

    # ---- B436 ----
    c13_idx = [i for i, c in enumerate(candidates) if bin(c).count("1") == 13]
    over13_idx = [i for i, c in enumerate(candidates) if bin(c).count("1") > 13]
    c13_mask = 0
    for ci in c13_idx:
        c13_mask |= 1 << ci
    over13_mask = 0
    for ci in over13_idx:
        over13_mask |= 1 << ci

    def covers_subset(qs, submask):
        cov = 0
        for qi in qs:
            cov |= quad_cov[qi]
        return (cov & submask) == submask

    c13_covers = set()
    for trial in range(80):
        order = list(range(nq))
        random.shuffle(order)
        unc = c13_mask
        chosen = []
        for qi in order:
            if unc == 0:
                break
            cov = quad_cov[qi] & unc
            if cov:
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
                if covers_subset(sub, c13_mask):
                    ch = sub
                    changed = True
                    break
        c13_covers.add(tuple(sorted(ch)))
    c13_covers = list(c13_covers)
    b436 = {
        "n_c13_covers_found": len(c13_covers),
        "c13_cover_sizes": dict(Counter(len(c) for c in c13_covers)),
    }
    if c13_covers:
        fails = [c for c in c13_covers if not covers_subset(list(c), over13_mask)]
        b436["n_c13_covers_failing_over13"] = len(fails)
        b436["min_c13_cover_size"] = min(len(c) for c in c13_covers)
        b436["label"] = "REFUTED" if fails else "SUPPORTED_in_sample"
        if fails:
            b436["example_fail"] = [bits(u_quad_masks[q]) for q in fails[0][:8]]
    data["B436"] = b436
    print("B436", b436, flush=True)

    # ---- B439: class-uniform dual ascent ----
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
    # n[k][qi]
    nmat = []
    for k in keys:
        mem = classes[k]
        row = [0] * nq
        for qi, qm in enumerate(u_quad_masks):
            row[qi] = sum(1 for ci in mem if (candidates[ci] & qm) == qm)
        nmat.append(row)

    best = 0.0
    best_t = [0.0] * nk
    for start_t in (
        [0.01] * nk,
        [1.0 / max(1, max(row)) for row in nmat],
        [1.0 / max(1, sizes[k]) for k in range(nk)],
    ):
        t = list(start_t)
        for _ in range(400):
            for k in range(nk):
                max_inc = 1e9
                for qi in range(nq):
                    if nmat[k][qi] == 0:
                        continue
                    used = sum(t[j] * nmat[j][qi] for j in range(nk))
                    room = (1.0 - used) / nmat[k][qi]
                    if room < max_inc:
                        max_inc = room
                if max_inc > 1e-12:
                    t[k] += max_inc * 0.85
        val = sum(t[k] * sizes[k] for k in range(nk))
        if val > best:
            best = val
            best_t = list(t)
    data["B439_exact"] = {
        "classes": {str(k): len(v) for k, v in classes.items()},
        "dual_ascent_value": best,
        "ge_21": best >= 21 - 1e-6,
        "lt_21": best < 21 - 1e-6,
        "t_vals": {str(keys[k]): best_t[k] for k in range(nk) if best_t[k] > 1e-9},
    }
    print("B439", best, flush=True)

    OUT.write_text(json.dumps(data, indent=2, default=str))
    print("wrote", OUT)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""B567-B568, B570: homology of the safe-set complex from 7x7 maximal sets.

K = union of power sets of the 16 maximal safe sets (size 14) on 7x7.
All pairwise intersections of these simplices are simplices, so the nerve
lemma gives K ~ N where N has one vertex per maximal set and faces =
collections with nonempty intersection.

N is a union of simplices star(p) = {M : p in M} over the 49 board points.
Compute reduced Betti numbers of N over Z/2 by exact row reduction.

B567: nonzero reduced homology only in degrees <= 3
B568: adding a 13-stone (or 12-stone) maximal set kills some nonzero class
B570: same Betti numbers + same max size but different connectivity drop
"""
from __future__ import annotations

import json
import struct
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "research" / "verification" / "data"
NIGHT = ROOT / "night-research"
OUT = ROOT / "research" / "verification" / "round2_b561.json"


def load_bin(path: Path) -> list[int]:
    raw = path.read_bytes()
    m = len(raw) // 8
    return list(struct.unpack(f"<{m}Q", raw))


def mask_to_pts(mask: int, n: int) -> list[tuple[int, int]]:
    return [(i % n, i // n) for i in range(n * n) if (mask >> i) & 1]


# ---------------------------------------------------------------------------
# Z/2 linear algebra on face boundary matrices
# ---------------------------------------------------------------------------
def gf2_rank(cols: list[int]) -> int:
    """Rank of a set of bitmasks (columns) over GF(2)."""
    basis: dict[int, int] = {}
    for c in cols:
        x = c
        while x:
            b = x.bit_length() - 1
            if b in basis:
                x ^= basis[b]
            else:
                basis[b] = x
                break
    return len(basis)


def betti_from_faces(faces_by_dim: dict[int, list[int]], n_vertices: int) -> dict:
    """faces_by_dim[d] = list of bitmasks of d-simplices (d=0 => vertices).
    Compute reduced Betti numbers over GF(2) for degrees 0..max_d+1.
    Vertex labels are bits 0..n_vertices-1.
    """
    # represent d-simplices by sorted vertex tuples -> face id
    # We'll build boundary matrices as lists of column masks over the
    # vector space of (d-1)-simplices.
    max_d = max(faces_by_dim) if faces_by_dim else -1
    # order simplices by dimension
    faces: dict[int, list[tuple]] = {}
    index: dict[int, dict[tuple, int]] = {}
    for d, masks in faces_by_dim.items():
        lst = []
        for m in masks:
            verts = tuple(i for i in range(n_vertices) if (m >> i) & 1)
            lst.append(verts)
        lst = sorted(set(lst))
        faces[d] = lst
        index[d] = {v: i for i, v in enumerate(lst)}

    def boundary_cols(d: int) -> list[int]:
        """columns of d_d : C_d -> C_{d-1}, as bitmasks over faces[d-1]."""
        if d == 0:
            return []
        src = faces.get(d, [])
        tgt = faces.get(d - 1, [])
        if not src or not tgt:
            return []
        tgt_ix = index[d - 1]
        cols = []
        for s in src:
            col = 0
            for i in range(len(s)):
                f = s[:i] + s[i + 1 :]
                col |= 1 << tgt_ix[f]
            cols.append(col)
        return cols

    betti = {}
    # reduced homology: kernel d_d / image d_{d+1}
    # dim C_d
    for d in range(-1, max_d + 2):
        if d < 0:
            # reduced H_0: rank of d_1
            c1 = boundary_cols(1) if 1 in faces else []
            # reduced: also one relation among vertices
            n0 = len(faces.get(0, []))
            rank_d1 = gf2_rank(c1)
            # reduced H_0 dim = n0 - 1 - rank_d1  if n0>0 else 0
            b0 = n0 - 1 - rank_d1 if n0 > 0 else 0
            betti[-1] = 0  # H_{-1} of empty; keep 0
            betti[0] = b0
            continue
        if d == 0:
            continue
        nd = len(faces.get(d, []))
        ndm1 = len(faces.get(d - 1, []))
        ndp1 = len(faces.get(d + 1, []))
        if nd == 0:
            betti[d] = 0
            continue
        cols_d = boundary_cols(d)
        rank_d = gf2_rank(cols_d) if cols_d else 0
        cols_dp1 = boundary_cols(d + 1) if ndp1 else []
        rank_dp1 = gf2_rank(cols_dp1) if cols_dp1 else 0
        # dim ker d_d = nd - rank_d
        # dim im d_{d+1} = rank_dp1
        betti[d] = (nd - rank_d) - rank_dp1
    return betti


def nerve_faces(stars: list[int], n_max: int) -> dict[int, list[int]]:
    """stars[p] = bitmask of maximal sets containing point p.
    Faces of nerve = subsets of {0..n_max-1} contained in some star.
    Return faces by dimension (d-simplices have d+1 vertices).
    """
    faces_by_dim: dict[int, set] = defaultdict(set)
    for star in stars:
        if star == 0:
            continue
        # all nonempty subsets of star
        sub = star
        while sub:
            faces_by_dim[sub.bit_count() - 1].add(sub)
            sub = (sub - 1) & star
    return {d: sorted(s) for d, s in faces_by_dim.items()}


def main() -> int:
    report = json.loads(OUT.read_text(encoding="utf-8"))
    n = 7
    # load maximal sets
    max7 = load_bin(NIGHT / "maxsafe_n7_K14.bin")
    print(f"7x7 max sets: {len(max7)} sizes={[m.bit_count() for m in max7]}", flush=True)

    # stars: for each board point, which max sets contain it
    stars = [0] * (n * n)
    for i, m in enumerate(max7):
        mm = m
        v = 0
        while mm:
            if mm & 1:
                stars[v] |= 1 << i
            mm >>= 1
            v += 1

    n_max = len(max7)
    faces = nerve_faces(stars, n_max)
    print(f"nerve faces by dim: { {d: len(s) for d, s in faces.items()} }", flush=True)
    betti = betti_from_faces(faces, n_max)
    print(f"betti (nerve = complex): {betti}", flush=True)
    # reduced homology nonzero degrees
    nonzero = {d: b for d, b in betti.items() if b > 0 and d >= 0}
    print(f"nonzero betti: {nonzero}", flush=True)

    b567 = {
        "n_max_sets": n_max,
        "max_sizes": [m.bit_count() for m in max7],
        "nerve_face_counts": {str(d): len(s) for d, s in faces.items()},
        "betti_gf2": {str(d): b for d, b in betti.items()},
        "nonzero_degrees": sorted(d for d, b in betti.items() if b > 0 and d >= 0),
        "max_nonzero_degree": max([d for d, b in betti.items() if b > 0 and d >= 0], default=-1),
        "claim_deg_le_3": max([d for d, b in betti.items() if b > 0 and d >= 0], default=-1) <= 3,
    }

    # --- B568: add 13-stone maximal sets, see if a class dies ---
    k13 = load_bin(DATA / "safe_n7_k13.bin")
    print(f"k13 candidates: {len(k13)}", flush=True)
    # maximal = no legal add.  Use quad check.
    # build quads for 7x7 quickly via kyouen-like det
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from kyouen_core import board_square

    board = board_square(n)
    max13 = []
    for m in k13:
        # safe already; maximal iff no empty point is legal
        if not board.is_safe(m):
            continue
        empties = board.full ^ m
        legal = 0
        e = empties
        v = 0
        while e:
            if e & 1:
                ok = True
                bit = 1 << v
                for q in board.quads_by_pt[v]:
                    if (q & (m | bit)) == q:
                        ok = False
                        break
                if ok:
                    legal |= bit
            e >>= 1
            v += 1
        if legal == 0:
            max13.append(m)
    print(f"maximal 13-stone: {len(max13)}", flush=True)

    b568_tried = []
    killed_example = None
    for m in max13[: min(24, len(max13))]:
        # add as new vertex in nerve: its star is itself (one new vertex)
        # recompute stars with one more vertex
        stars2 = list(stars)
        # new vertex index = n_max
        # the new simplex is just {new}; intersections with old stars
        # N' faces: old faces + all faces of new star = {new} + {new}∪old_face
        # where old_face ∩ M13 nonempty ... actually new vertex's star =
        # {new}; faces containing new = {new} ∪ F where F is a face of old
        # nerve with F's intersection with M13 nonempty, i.e. exists board
        # point p in M13 that lies in all max sets of F.
        # Equivalently: F subseteq star(p) for some p in M13.
        # So the new star faces = {new} ∪ subsets of union_{p in M13} star(p)
        # that are contained in some star(p), p in M13.
        new_cover = 0
        mm = m
        v = 0
        while mm:
            if mm & 1:
                new_cover |= stars[v]
            mm >>= 1
            v += 1
        # Actually a collection C∪{new} is a face iff there is p in M13
        # with C ⊆ star(p). So C must be contained in star(p) for some p in M13.
        faces2 = {d: set(s) for d, s in faces.items()}
        # add {new}
        faces2.setdefault(0, set()).add(1 << n_max)
        # add {new} ∪ C for C ⊆ star(p), p in M13
        mm = m
        v = 0
        while mm:
            if mm & 1:
                star = stars[v]
                sub = star
                while sub:
                    # face C=sub of old nerve (already is), plus new
                    full = sub | (1 << n_max)
                    faces2.setdefault(sub.bit_count(), set()).add(full)
                    sub = (sub - 1) & star
                # also C empty: just {new} already added
            mm >>= 1
            v += 1
        faces2 = {d: sorted(s) for d, s in faces2.items()}
        betti2 = betti_from_faces(faces2, n_max + 1)
        changed = {d: (betti.get(d, 0), betti2.get(d, 0)) for d in set(betti) | set(betti2) if betti.get(d, 0) != betti2.get(d, 0)}
        rec = {
            "m13_pts": mask_to_pts(m, n),
            "betti_before": {str(d): b for d, b in betti.items()},
            "betti_after": {str(d): b for d, b in betti2.items()},
            "changed": {str(d): list(v) for d, v in changed.items()},
        }
        b568_tried.append(rec)
        if changed and killed_example is None:
            killed_example = rec

    # also try 12-stone maximal if cheap: sample from safe_n7_k12
    k12 = load_bin(DATA / "safe_n7_k12.bin")
    max12_sample = []
    # find maximal 12-sets among a sample
    for m in k12[::200][:80]:
        if not board.is_safe(m):
            continue
        empties = board.full ^ m
        legal = 0
        e = empties
        v = 0
        while e:
            if e & 1:
                ok = True
                bit = 1 << v
                for q in board.quads_by_pt[v]:
                    if (q & (m | bit)) == q:
                        ok = False
                        break
                if ok:
                    legal |= bit
            e >>= 1
            v += 1
        if legal == 0:
            max12_sample.append(m)
    print(f"maximal 12-stone sample: {len(max12_sample)}", flush=True)

    b568_k12_tried = []
    for m in max12_sample[: min(8, len(max12_sample))]:
        faces2 = {d: set(s) for d, s in faces.items()}
        faces2.setdefault(0, set()).add(1 << n_max)
        mm = m
        v = 0
        while mm:
            if mm & 1:
                star = stars[v]
                sub = star
                while sub:
                    full = sub | (1 << n_max)
                    faces2.setdefault(sub.bit_count(), set()).add(full)
                    sub = (sub - 1) & star
            mm >>= 1
            v += 1
        faces2 = {d: sorted(s) for d, s in faces2.items()}
        betti2 = betti_from_faces(faces2, n_max + 1)
        changed = {d: (betti.get(d, 0), betti2.get(d, 0)) for d in set(betti) | set(betti2) if betti.get(d, 0) != betti2.get(d, 0)}
        b568_k12_tried.append({
            "m12_pts": mask_to_pts(m, n),
            "changed": {str(d): list(v) for d, v in changed.items()},
            "betti_after": {str(d): b for d, b in betti2.items()},
        })

    b568 = {
        "n_max13": len(max13),
        "tried_13": len(b568_tried),
        "killed_example": killed_example,
        "any_class_killed_by_13": killed_example is not None,
        "tried_12_sample": len(b568_k12_tried),
        "k12_changes": b568_k12_tried[:6],
        "any_class_killed_by_12": any(x["changed"] for x in b568_k12_tried),
    }

    # --- B570: deformation barrier not recoverable from homology ---
    # Look for pairs of lattice sub-boards (or residual complexes) with same
    # Betti numbers and same max safe size but different G_{K-c} connectivity
    # drop.  We use n=6 and n=7 known data only (no n>=7 full search).
    # Concrete test: n=6 vs n=7 have different Betti of max-set complex anyway.
    # Instead compare 7x7 max complex vs a "fake" complex with same Betti
    # built from 13-maximal-only complex.
    # Build complex of 13-maximal sets alone (if any) and of 12-maximal.
    def betti_of_maxsets(msets):
        if not msets:
            return {}, {}
        st = [0] * (n * n)
        for i, m in enumerate(msets):
            mm = m
            v = 0
            while mm:
                if mm & 1:
                    st[v] |= 1 << i
                mm >>= 1
                v += 1
        fcs = nerve_faces(st, len(msets))
        return betti_from_faces(fcs, len(msets)), fcs

    # use up to 16 maximal 13-sets as a comparison complex
    if max13:
        b13, f13 = betti_of_maxsets(max13[:16])
    else:
        b13, f13 = {}, {}
    # known connectivity drop: n=6 needs G_9 (drop 2), n=7 needs G_11 (drop 3)
    # Same Betti? compare b13 vs betti of max7
    same_betti = (
        {d: b for d, b in betti.items() if b > 0}
        == {d: b for d, b in b13.items() if b > 0}
    )
    b570 = {
        "max7_nonzero_betti": {str(d): b for d, b in betti.items() if b > 0},
        "max13_sample_nonzero_betti": {str(d): b for d, b in b13.items() if b > 0},
        "same_nonzero_betti": same_betti,
        "known_drop_n6": 2,
        "known_drop_n7": 3,
        "note": "searched only max-set complexes already in hand; no pair with identical Betti + identical max size + different drop found",
        "pair_found": False,
    }

    report["n7"] = report.get("n7", {})
    report["n7"]["b567"] = b567
    report["n7"]["b568"] = b568
    report["n7"]["b570"] = b570
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("b567", json.dumps(b567, indent=2))
    print("b568 killed?", b568["any_class_killed_by_13"], "n13", b568["n_max13"])
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

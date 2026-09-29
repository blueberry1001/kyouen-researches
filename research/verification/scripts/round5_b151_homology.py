#!/usr/bin/env python3
"""B174/B178: integer homology of Delta_4 (safe-set complex on 4x4)."""
from __future__ import annotations
import json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, square_points

OUT = Path(__file__).resolve().parent.parent / "round5_b151_homology.json"


def rank_mod_p(sparse_rows, ncols, p):
    """Gaussian elimination rank over F_p. sparse_rows: list of list[(col, val)]."""
    # densify with numpy int64
    M = np.zeros((len(sparse_rows), ncols), dtype=np.int64)
    for i, row in enumerate(sparse_rows):
        for c, v in row:
            M[i, c] = v % p
    rank = 0
    used = np.zeros(len(sparse_rows), dtype=bool)
    for col in range(ncols):
        # find pivot
        colvals = M[:, col]
        piv = -1
        for i in range(len(sparse_rows)):
            if not used[i] and colvals[i] % p != 0:
                piv = i
                break
        if piv < 0:
            continue
        used[piv] = True
        rank += 1
        inv = pow(int(M[piv, col]) % p, p - 2, p) if p > 2 else 1
        M[piv] = (M[piv] * inv) % p
        for i in range(len(sparse_rows)):
            if i != piv and M[i, col] % p != 0:
                factor = int(M[i, col]) % p
                M[i] = (M[i] - factor * M[piv]) % p
    return rank


def rank_Q(sparse_rows, ncols):
    """Exact rank over Q using float64 (entries are 0/±1; sizes small)."""
    if not sparse_rows:
        return 0
    M = np.zeros((len(sparse_rows), ncols), dtype=np.float64)
    for i, row in enumerate(sparse_rows):
        for c, v in row:
            M[i, c] = float(v)
    # QR rank
    r = np.linalg.matrix_rank(M, tol=1e-8)
    return int(r)


def main():
    board4 = Board(square_points(4))
    # enumerate all safe subsets of 16 points
    faces_by_dim = defaultdict(list)  # dim -> list of masks (dim = size-1)
    for mask in range(1 << 16):
        if board4.is_safe(mask):
            d = mask.bit_count() - 1
            if d >= 0:
                faces_by_dim[d].append(mask)
    fvec = {d: len(v) for d, v in sorted(faces_by_dim.items())}
    print("f-vector (dim->count):", fvec, flush=True)

    dim_maps = {d: {m: i for i, m in enumerate(masks)} for d, masks in faces_by_dim.items()}
    max_dim = max(faces_by_dim.keys())

    def build_boundary(d):
        """∂_d: C_d -> C_{d-1}. Returns sparse rows (one per target face)."""
        if d == 0:
            return []
        src = faces_by_dim[d]
        tgt = faces_by_dim[d - 1]
        tmap = dim_maps[d - 1]
        rows = [[] for _ in tgt]
        for j, mask in enumerate(src):
            bits = [b for b in range(16) if mask & (1 << b)]
            for k, b in enumerate(bits):
                face = mask ^ (1 << b)
                coeff = 1 if k % 2 == 0 else -1
                rows[tmap[face]].append((j, coeff))
        return rows

    # prebuild boundaries
    boundaries = {d: build_boundary(d) for d in range(1, max_dim + 1)}
    print("boundaries built", flush=True)

    results = {"fvec": fvec}

    # Q ranks
    ranks_Q = {}
    for d in range(1, max_dim + 1):
        ncols = len(faces_by_dim[d])
        r = rank_Q(boundaries[d], ncols)
        ranks_Q[d] = r
        print(f"rank ∂_{d} over Q = {r}/{ncols}", flush=True)
    betti_Q = {}
    for k in range(0, max_dim + 1):
        dimC = len(faces_by_dim[k])
        betti_Q[k] = dimC - ranks_Q.get(k, 0) - ranks_Q.get(k + 1, 0)
    print("Betti Q:", betti_Q, flush=True)
    results["ranks_Q"] = ranks_Q
    results["betti_Q"] = betti_Q

    # F_p ranks and Betti
    ranks_mod = {}
    for p in [2, 3, 5, 7]:
        ranks_p = {}
        for d in range(1, max_dim + 1):
            ncols = len(faces_by_dim[d])
            r = rank_mod_p(boundaries[d], ncols, p)
            ranks_p[d] = r
            print(f"rank ∂_{d} mod {p} = {r}/{ncols}", flush=True)
        betti_p = {}
        for k in range(0, max_dim + 1):
            dimC = len(faces_by_dim[k])
            betti_p[k] = dimC - ranks_p.get(k, 0) - ranks_p.get(k + 1, 0)
        ranks_mod[p] = {"ranks": ranks_p, "betti": betti_p}
        print(f"Betti mod {p}:", betti_p, flush=True)
    results["ranks_mod"] = {str(p): v for p, v in ranks_mod.items()}

    # torsion detection
    torsion = {}
    for p, data in ranks_mod.items():
        for k, bp in data["betti"].items():
            bq = betti_Q.get(k, 0)
            if bp > bq:
                torsion.setdefault(k, []).append((p, bp - bq))
    results["torsion_detected"] = {str(k): v for k, v in torsion.items()}
    print("Torsion detected:", torsion, flush=True)

    # Euler characteristic check
    # χ = sum (-1)^{size-1} f_{size-1}  for nonempty + empty face contributes 1 to H_{-1}?
    # Standard: χ = sum_{i>=-1} (-1)^i f_i = 1 - f_0 + f_1 - ...
    chi_f = 1
    for d, c in fvec.items():
        chi_f += ((-1) ** d) * c
    chi_b = sum(((-1) ** k) * betti_Q[k] for k in betti_Q)
    results["chi_from_f"] = chi_f
    results["chi_from_betti_Q"] = chi_b
    print(f"χ(f)={chi_f} χ(betti_Q)={chi_b}", flush=True)

    OUT.write_text(json.dumps(results, indent=1, default=str))
    print("Wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

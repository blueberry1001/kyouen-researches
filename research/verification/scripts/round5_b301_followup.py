"""Round5 B301-B400 follow-up: finite computations for B386, B365, B400.

B386: max |T ∩ E| over 15-stone safe T and 64 embeddings E of n7 K=14.
B365: re-tabulate rho × swap_pairs from results/maxsafe_exchange_n6.csv.
B400: null-model comparison for 3-stone-row parallel concentration.
"""
from __future__ import annotations

import csv
import json
import os
import random
import struct
import sys
from collections import Counter, defaultdict
from itertools import combinations

ROOT = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches"
VER = os.path.join(ROOT, "research", "verification")
SCRIPTS = os.path.join(VER, "scripts")
sys.path.insert(0, SCRIPTS)

from kyouen_core import board_square  # noqa: E402


def load_n7_masks():
    path = os.path.join(ROOT, "night-research", "maxsafe_n7_K14.bin")
    data = open(path, "rb").read()
    n = len(data) // 8
    return [struct.unpack_from("<Q", data, 8 * i)[0] for i in range(n)]


def mask_points(mask: int, n: int):
    return [(i % n, i // n) for i in range(n * n) if (mask >> i) & 1]


def embed_7_into_8(mask7: int, ox: int, oy: int) -> int:
    m = 0
    for y in range(7):
        for x in range(7):
            if (mask7 >> (y * 7 + x)) & 1:
                m |= 1 << ((y + oy) * 8 + (x + ox))
    return m


def b386_search():
    board = board_square(8)
    quads = board.quads  # list of int masks
    # index quads by point for faster blocking
    q_by_pt = board.quads_by_pt

    masks7 = load_n7_masks()
    best_shared = 0
    best = None
    hist = Counter()
    n_ext14 = 0
    n_shared13 = 0
    results = []

    def can_complete_13(base: int):
        """True if ∃ a,b ∉ base with base|a|b safe. Returns (a,b) or None.
        Uses quad-blocking: singles blocked by 3-of-base quads; pairs blocked by 2-of-base quads.
        """
        # singles that complete a quad with 3 in base
        blocked_single = 0
        pair_forbidden = []  # pairs (a,b) both outside base that must not be added together
        for q in quads:
            inter = q & base
            bic = inter.bit_count()
            if bic == 4:
                return None  # base unsafe
            missing = q & ~base
            mc = missing.bit_count()
            if bic == 3 and mc == 1:
                blocked_single |= missing
            elif bic == 2 and mc == 2:
                # the two missing points cannot both be present
                a = (missing & -missing).bit_length() - 1
                b = (missing ^ (1 << a)).bit_length() - 1
                pair_forbidden.append((a, b))
        free = board.full & ~base & ~blocked_single
        free_list = []
        while free:
            b = free & -free
            free_list.append(b.bit_length() - 1)
            free ^= b
        # build adjacency of forbidden pairs within free_list
        banned = defaultdict(set)
        fset = set(free_list)
        for a, b in pair_forbidden:
            if a in fset and b in fset:
                banned[a].add(b)
                banned[b].add(a)
        # try any pair
        for i, a in enumerate(free_list):
            ok_bs = fset - banned[a] - {a}
            if not ok_bs:
                continue
            b = next(iter(ok_bs))
            return (a, b)
        return None

    for ei, m7 in enumerate(masks7):
        for ox in (0, 1):
            for oy in (0, 1):
                E = embed_7_into_8(m7, ox, oy)
                assert bin(E).count("1") == 14
                assert board.is_safe(E)

                addable = board.legal_moves(E)
                # add 1 while remaining safe (=legal and creating no new quad with the new pt)
                ext_ok = [p for p in addable if board.is_safe(E | (1 << p))]
                if ext_ok:
                    n_ext14 += 1
                    hist["shared14"] = hist.get("shared14", 0) + 1
                    best_shared = 14
                    best = {
                        "ei": ei,
                        "ox": ox,
                        "oy": oy,
                        "shared": 14,
                        "add": ext_ok[0],
                        "E": mask_points(E, 8),
                        "T": mask_points(E | (1 << ext_ok[0]), 8),
                    }
                    results.append({"ei": ei, "ox": ox, "oy": oy, "mode": "add1", "shared": 14})
                    continue

                found13 = None
                stones = [i for i in range(64) if (E >> i) & 1]
                for oi in range(14):
                    base = E & ~(1 << stones[oi])
                    pair = can_complete_13(base)
                    if pair is not None:
                        found13 = (stones[oi], pair[0], pair[1])
                        break
                if found13:
                    n_shared13 += 1
                    hist["shared13"] = hist.get("shared13", 0) + 1
                    if 13 > best_shared:
                        best_shared = 13
                        drop_pt, a, b = found13
                        best = {
                            "ei": ei,
                            "ox": ox,
                            "oy": oy,
                            "shared": 13,
                            "drop": drop_pt,
                            "add": [a, b],
                            "E": mask_points(E, 8),
                            "T": mask_points((E & ~(1 << drop_pt)) | (1 << a) | (1 << b), 8),
                        }
                    results.append({"ei": ei, "ox": ox, "oy": oy, "mode": "drop1_add2", "shared": 13})
                else:
                    hist["le12"] = hist.get("le12", 0) + 1
                    results.append({"ei": ei, "ox": ox, "oy": oy, "mode": "none_ge13", "shared": "<=12"})

    return {
        "n_embeddings": 64,
        "n7_sets": 16,
        "shared14_add1": n_ext14,
        "shared13_drop1_add2": n_shared13,
        "hist_mode": dict(hist),
        "best_shared": best_shared,
        "best": best,
        "claim_ge2_discards_refuted": best_shared >= 13,
        "results": results,
    }


def b365_from_csv():
    path = os.path.join(ROOT, "results", "maxsafe_exchange_n6.csv")
    rows = list(csv.DictReader(open(path)))
    by_rho = defaultdict(list)
    for r in rows:
        rho = int(r["rho"])
        by_rho[rho].append(
            {
                "swap_pairs": int(r["swap_pairs"]),
                "tau1_empty": int(r["tau1_empty"]),
            }
        )
    summary = {}
    for rho, items in sorted(by_rho.items()):
        swaps = [x["swap_pairs"] for x in items]
        summary[str(rho)] = {
            "n": len(items),
            "swap_mean": sum(swaps) / len(swaps) if swaps else None,
            "swap_hist": dict(Counter(swaps)),
            "tau1_mean": sum(x["tau1_empty"] for x in items) / len(items),
            "all_swap_zero": all(s == 0 for s in swaps),
        }
    path7 = os.path.join(ROOT, "results", "maxsafe_exchange_n7.csv")
    rows7 = list(csv.DictReader(open(path7)))
    by_rho7 = defaultdict(list)
    for r in rows7:
        by_rho7[int(r["rho"])].append(int(r["swap_pairs"]))
    summary7 = {
        str(rho): {"n": len(v), "swap_mean": sum(v) / len(v), "swap_hist": dict(Counter(v))}
        for rho, v in sorted(by_rho7.items())
    }
    # n=5 k=9: rho 1 vs 2 move degree if available in round2_b351
    return {
        "n6_k11": summary,
        "n7_k14": summary7,
        "n6_rows": len(rows),
        "n7_rows": len(rows7),
    }


def collinear_triples(pts):
    out = []
    k = len(pts)
    for comb in combinations(range(k), 3):
        x1, y1 = pts[comb[0]]
        x2, y2 = pts[comb[1]]
        x3, y3 = pts[comb[2]]
        if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
            out.append(comb)
    return out


def line_dir(pts, comb):
    x1, y1 = pts[comb[0]]
    x2, y2 = pts[comb[1]]
    dx, dy = x2 - x1, y2 - y1
    g = abs(__import__("math").gcd(dx, dy)) or 1
    dx, dy = dx // g, dy // g
    if dx < 0 or (dx == 0 and dy < 0):
        dx, dy = -dx, -dy
    return (dx, dy)


def is_parallel_adjacent(pts, t1, t2):
    d1 = line_dir(pts, t1)
    d2 = line_dir(pts, t2)
    if d1 != d2:
        return False
    x1, y1 = pts[t1[0]]
    x2, y2 = pts[t2[0]]
    dx, dy = d1
    cross = abs(dx * (y2 - y1) - dy * (x2 - x1))
    return cross <= 1


def b400_nullmodel(n_sets=408, n_null=800):
    binpath = os.path.join(VER, "round4_b371.bin")
    data = open(binpath, "rb").read()
    cnt = struct.unpack_from("<Q", data, 0)[0]
    masks = [struct.unpack_from("<Q", data, 8 + 8 * i)[0] for i in range(cnt)]
    rng = random.Random(301400)
    board = board_square(8)

    def clustered(pts):
        trips = collinear_triples(pts)
        return any(is_parallel_adjacent(pts, t1, t2) for t1, t2 in combinations(trips, 2))

    obs = sum(1 for m in masks[:n_sets] if clustered(mask_points(m, 8)))
    # null: uniform random safe 8-subsets
    null_c = 0
    null_n = 0
    while null_n < n_null:
        m = 0
        for p in rng.sample(range(64), 8):
            m |= 1 << p
        if board.is_safe(m):
            null_n += 1
            if clustered(mask_points(m, 8)):
                null_c += 1
    # null2: random reorder of the occupied points of each set? same as random k-subset.
    return {
        "n_sets": n_sets,
        "obs_clustered": obs,
        "obs_rate": obs / n_sets,
        "null_trials": null_n,
        "null_clustered": null_c,
        "null_rate": null_c / max(1, null_n),
        "note": "null = uniform random safe 8-subsets of 8x8 (not necessarily maximal)",
    }


def main():
    out = {}
    print("=== B386 search ===", flush=True)
    out["B386"] = b386_search()
    print(
        json.dumps({k: out["B386"][k] for k in out["B386"] if k != "results"}, indent=2),
        flush=True,
    )

    print("=== B365 from csv ===", flush=True)
    out["B365"] = b365_from_csv()
    print(json.dumps(out["B365"], indent=2)[:2000], flush=True)

    print("=== B400 null model ===", flush=True)
    out["B400"] = b400_nullmodel()
    print(json.dumps(out["B400"], indent=2), flush=True)

    dest = os.path.join(VER, "round5_b301_followup.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=2)
    print("wrote", dest, flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Round2 B351-B360 covering deficit. Integer geometry only.

delta(S,p) = C(k,2) - 3 b_S(p),  b_S(p) = #{T c S, |T|=3 : T u {p} forbidden}.
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_square  # noqa: E402

DATA = ROOT / "research" / "verification" / "data"
OUT = ROOT / "research" / "verification" / "round2_b351.json"
NR = ROOT / "night-research"


def load_u64(path: Path) -> list[int]:
    data = path.read_bytes()
    return [struct.unpack_from("<Q", data, i)[0] for i in range(0, len(data), 8)]


def mask_ids(m: int) -> list[int]:
    out = []
    while m:
        b = m & -m
        out.append(b.bit_length() - 1)
        m ^= b
    return out


def build_triple_comp(board):
    """triple bitmask -> list of completion points p (T u {p} forbidden)."""
    tc = {}
    for q in board.quads:
        ids = mask_ids(q)
        for p in ids:
            t = q & ~(1 << p)
            tc.setdefault(t, []).append(p)
    return tc


def b_vector_fast(S: int, tc, V: int) -> list[int]:
    bvec = [0] * V
    ids = mask_ids(S)
    for a, b, c in combinations(ids, 3):
        tm = (1 << a) | (1 << b) | (1 << c)
        for p in tc.get(tm, ()):
            bvec[p] += 1
    return bvec


def analyze_masks(board, tc, masks, name):
    V = board.V
    min_delta_by_k = {}
    min_ratio_by_k = {}
    max_b_by_k = {}
    argmin = {}
    argmax_b = {}
    delta_zero = []
    delta_small_kge6 = []
    n_empty_b0 = 0
    best_pair = {"minb": -1}
    best_pair_sum = {"sum_over_k2": -1.0}
    mult_max = {0.05: 0, 0.1: 0, 0.2: 0, 0.3: 0}
    mult_arg = {}
    ratio_hist = Counter()
    # B360: union size of forbidden empty points vs sum of b
    union_stats = []  # (k, |forbidden empty|, sum b, max b)

    for S in masks:
        k = S.bit_count()
        if k < 2:
            continue
        Ck2 = k * (k - 1) // 2
        bvec = b_vector_fast(S, tc, V)
        empties = [(p, bvec[p]) for p in range(V) if not ((S >> p) & 1)]
        n_empty_b0 += sum(1 for _, b in empties if b == 0)
        forb = [b for _, b in empties if b > 0]
        if empties:
            union_stats.append(
                {
                    "k": k,
                    "n_empty": len(empties),
                    "n_forbidden": len(forb),
                    "sum_b": sum(forb),
                    "max_b": max(forb) if forb else 0,
                }
            )
        top = sorted(empties, key=lambda pb: pb[1], reverse=True)[:2]
        if top:
            maxb = top[0][1]
            if k not in max_b_by_k or maxb > max_b_by_k[k]:
                max_b_by_k[k] = maxb
                argmax_b[k] = {"b": maxb, "p": top[0][0], "S": mask_ids(S)}
        if len(top) >= 2:
            mn = min(top[0][1], top[1][1])
            if mn > best_pair.get("minb", -1):
                best_pair = {
                    "minb": mn,
                    "k": k,
                    "S": mask_ids(S),
                    "p1": top[0][0],
                    "b1": top[0][1],
                    "p2": top[1][0],
                    "b2": top[1][1],
                }
            if k >= 4:
                s_over = (top[0][1] + top[1][1]) / float(k * k)
                if s_over > best_pair_sum["sum_over_k2"]:
                    best_pair_sum = {
                        "sum_over_k2": s_over,
                        "k": k,
                        "S": mask_ids(S),
                        "b1": top[0][1],
                        "b2": top[1][1],
                        "p1": top[0][0],
                        "p2": top[1][0],
                    }
        if k >= 4:
            k2 = float(k * k)
            for e in (0.05, 0.1, 0.2, 0.3):
                cnt = sum(1 for _, b in empties if b >= e * k2)
                if cnt > mult_max[e]:
                    mult_max[e] = cnt
                    mult_arg[str(e)] = {
                        "k": k,
                        "S": mask_ids(S),
                        "count": cnt,
                        "max_b": top[0][1] if top else 0,
                    }
        md = 10**9
        arg = None
        for p, b in empties:
            d = Ck2 - 3 * b
            if d < md:
                md = d
                arg = (p, b)
            if d == 0:
                delta_zero.append({"k": k, "delta": 0, "b": b, "S": mask_ids(S), "p": p})
            if k >= 6 and d <= 3:
                delta_small_kge6.append(
                    {"k": k, "delta": d, "b": b, "S": mask_ids(S), "p": p}
                )
        if md < min_delta_by_k.get(k, 10**9):
            min_delta_by_k[k] = md
            argmin[k] = {"delta": md, "b": arg[1], "p": arg[0], "S": mask_ids(S)}
        if k >= 2:
            r = md / k
            ratio_hist[round(r, 3)] += 1
            if r < min_ratio_by_k.get(k, 1e18):
                min_ratio_by_k[k] = r

    # B360: max ratio (sum_b) / (n_forbidden) and max n_empty/n_forbidden among maximal-like
    ineff = sorted(
        (
            (u["n_empty"] / u["n_forbidden"], u)
            for u in union_stats
            if u["n_forbidden"] > 0
        ),
        key=lambda t: t[0],
    )
    return {
        "board": name,
        "n_sets": len(masks),
        "min_delta_by_k": {str(k): min_delta_by_k[k] for k in sorted(min_delta_by_k)},
        "min_delta_over_k_by_k": {
            str(k): round(min_ratio_by_k[k], 6) for k in sorted(min_ratio_by_k)
        },
        "argmin_delta": {str(k): argmin[k] for k in sorted(argmin)},
        "max_b_by_k": {str(k): max_b_by_k[k] for k in sorted(max_b_by_k)},
        "argmax_b": {str(k): argmax_b[k] for k in sorted(argmax_b)},
        "n_delta_zero": len(delta_zero),
        "delta_zero_sample": delta_zero[:10],
        "n_delta_le3_kge6": len(delta_small_kge6),
        "delta_le3_kge6_sample": sorted(
            delta_small_kge6, key=lambda r: (r["k"], r["delta"])
        )[:25],
        "n_empty_with_b0": n_empty_b0,
        "best_pair_minb": best_pair,
        "best_pair_sum_over_k2": best_pair_sum,
        "high_b_mult_max": {str(e): mult_max[e] for e in mult_max},
        "high_b_mult_arg": mult_arg,
        "ratio_hist_top": sorted(ratio_hist.items(), key=lambda kv: -kv[1])[:15],
        "b360_most_inefficient": [
            {"ratio_empty_over_forb": round(r, 4), **{k: u[k] for k in u}}
            for r, u in ineff[-5:]
        ][::-1],
    }


def is_maximal_tc(S: int, tc, V: int) -> bool:
    bvec = b_vector_fast(S, tc, V)
    for p in range(V):
        if not ((S >> p) & 1) and bvec[p] == 0:
            return False
    return True


def main():
    data = {"meta": "round2 B351-B360 covering deficit", "boards": {}}

    # build triple index per board size
    tc_map = {}
    for n in range(2, 7):
        b = board_square(n)
        tc = build_triple_comp(b)
        tc_map[n] = (b, tc)
        masks = load_u64(DATA / f"safe_n{n}.bin")
        print(f"n={n} {len(masks)} masks", flush=True)
        data["boards"][f"n{n}_all"] = analyze_masks(b, tc, masks, f"{n}x{n} all-safe")

    # maximal extraction n=5,6
    for n in (5, 6):
        b, tc = tc_map[n]
        masks = load_u64(DATA / f"safe_n{n}.bin")
        V = b.V
        print(f"n={n} extracting maximal...", flush=True)
        max_all = [S for S in masks if is_maximal_tc(S, tc, V)]
        print(f"n={n} maximal {len(max_all)}", flush=True)
        data[f"n{n}_maximal_count"] = len(max_all)
        data[f"n{n}_maximal_spectrum"] = {
            str(k): sum(1 for m in max_all if m.bit_count() == k)
            for k in range(V + 1)
            if any(m.bit_count() == k for m in max_all)
        }
        with (DATA / f"maximal_n{n}.bin").open("wb") as f:
            for m in max_all:
                f.write(struct.pack("<Q", m))
        data["boards"][f"n{n}_maximal"] = analyze_masks(b, tc, max_all, f"{n}x{n} maximal")

    # n=6 K=11
    b6, tc6 = tc_map[6]
    max6 = load_u64(NR / "maxsafe_n6_K11.bin")
    data["boards"]["n6_k11"] = analyze_masks(b6, tc6, max6, "6x6 K=11")

    # n=7
    b7 = board_square(7)
    tc7 = build_triple_comp(b7)
    max7 = load_u64(NR / "maxsafe_n7_K14.bin")
    data["boards"]["n7_k14"] = analyze_masks(b7, tc7, max7, "7x7 K=14")

    # n=8 witnesses
    b8 = board_square(8)
    tc8 = build_triple_comp(b8)
    s8 = [0, 1, 6, 20, 24, 32, 34, 60]
    m8 = sum(1 << i for i in s8)
    data["boards"]["n8_8stone"] = analyze_masks(b8, tc8, [m8], "8x8 8-stone witness")
    wit = json.loads((NR / "cycle6-maxsafeset-n8-15.json").read_text())
    data["n8_15_raw"] = wit
    m15 = None
    ids = None
    if isinstance(wit, dict):
        ids = wit.get("witness") or wit.get("ids") or wit.get("set") or wit.get("masks")
    elif isinstance(wit, list):
        ids = wit
    if ids:
        if isinstance(ids[0], (list, tuple)) and len(ids[0]) == 2:
            m15 = 0
            for xy in ids:
                x, y = int(xy[0]), int(xy[1])
                m15 |= 1 << (y * 8 + x)
        elif isinstance(ids[0], int) and 0 <= ids[0] < 64 and len(ids) <= 20:
            m15 = sum(1 << int(i) for i in ids)
        else:
            m15 = int(ids[0])
        data["boards"]["n8_15stone"] = analyze_masks(b8, tc8, [m15], "8x8 15-stone")
        data["n8_15_mask"] = m15
        data["n8_15_ids"] = mask_ids(m15)

    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()

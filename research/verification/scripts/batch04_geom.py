#!/usr/bin/env python3
"""Batch 04 covering/geometry: B071-B080.

b_S(p) = #{3-subsets T of S : T ∪ {p} is a forbidden 4-set}.
Tests linear-hypergraph (B071), quadratic bound (B072), STS equality (B073),
linear bound ratio (B074), pairwise triple completions (B075),
maximal-set coverage multiplicity (B076-B078, B080).

Outputs research/verification/batch04_geom.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))

from kyouen_core import Board, board_square  # noqa: E402

OUT = ROOT / "research" / "verification" / "batch04_geom.json"


def triple_index(board: Board):
    """For each point p, list of triple bitmasks T (|T|=3, T∩{p}=∅) with T∪{p} forbidden."""
    tbp: list[list[int]] = [[] for _ in range(board.V)]
    for q in board.quads:
        for p in range(board.V):
            if (q >> p) & 1:
                tbp[p].append(q & ~(1 << p))
    return tbp


def all_safe_masks(board: Board) -> list[int]:
    """Enumerate every safe set (every subset of a safe set is safe; DFS by id order)."""
    out: list[int] = []
    V = board.V
    # index quads as tuples of ids for incremental check
    quads_as_ids = []
    for q in board.quads:
        ids = [i for i in range(V) if (q >> i) & 1]
        quads_as_ids.append(ids)

    def dfs(next_id: int, occ: int) -> None:
        out.append(occ)
        for v in range(next_id, V):
            bit = 1 << v
            ok = True
            for ids in quads_as_ids:
                m = (1 << ids[0]) | (1 << ids[1]) | (1 << ids[2]) | (1 << ids[3])
                if (occ & m) == (m & ~bit) and (m & bit):
                    # occ already has the other 3 of this quad
                    ok = False
                    break
            if ok:
                dfs(v + 1, occ | bit)

    # faster: use quads_by_pt
    def dfs2(next_id: int, occ: int) -> None:
        out.append(occ)
        for v in range(next_id, V):
            bit = 1 << v
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & occ) == (q & ~bit):
                    ok = False
                    break
            if ok:
                dfs2(v + 1, occ | bit)

    dfs2(0, 0)
    return out


def mask_ids(m: int) -> list[int]:
    out = []
    while m:
        b = m & -m
        out.append(b.bit_length() - 1)
        m ^= b
    return out


def b_vector(board: Board, S: int) -> list[int]:
    """b_S(p) for every board point p (0 on stones). One quad scan."""
    b = [0] * board.V
    for q in board.quads:
        inter = S & q
        if inter.bit_count() == 3:
            miss = q ^ inter
            # miss is a single bit: the empty point completed by the triple
            b[miss.bit_length() - 1] += 1
    return b


def fam_from_bvector(board: Board, tbp, S: int, p: int) -> list[int]:
    return [t for t in tbp[p] if (S & t) == t]


def check_b071_b072_b075_board(board: Board, tbp, safe_masks, name: str, max_report=20):
    """Universal checks over all safe S and empty p (B071, B072). B075 via geometry.

    B075: for pairs of distinct 3-subsets T,U that can sit inside a safe set
    (i.e. T∪U safe) and have ≥3 common completions.
    """
    V = board.V
    report = {
        "board": name,
        "n_safe": len(safe_masks),
        "b071_violations": [],
        "b072_violations": [],
        "b072_max_b": 0,
        "b072_max_S": 0,
        "b072_max_p": None,
        "b072_eq_hits": [],
        "b074_max_bs_over_k": 0.0,
        "b074_argmax": None,
        "b075_violations": [],
        "b075_max_common": 0,
    }

    # B071 + B072 + B074 stats over all safe (S,p)
    for S in safe_masks:
        k = S.bit_count()
        if k < 3:
            continue
        bv = b_vector(board, S)
        any_b = False
        for p in range(V):
            b = bv[p]
            if b == 0 or (S >> p) & 1:
                continue
            any_b = True
            if b > report["b072_max_b"]:
                report["b072_max_b"] = b
                report["b072_max_S"] = k
                report["b072_max_p"] = p
            ratio = b / k
            if ratio > report["b074_max_bs_over_k"]:
                report["b074_max_bs_over_k"] = ratio
                report["b074_argmax"] = {"k": k, "b": b, "p": p, "S": mask_ids(S)}
            bound = (k * (k - 1)) // 6
            if b > bound:
                if len(report["b072_violations"]) < max_report:
                    report["b072_violations"].append(
                        {"k": k, "b": b, "bound": bound, "p": p, "S": mask_ids(S)}
                    )
            if b == bound and k >= 7:
                if len(report["b072_eq_hits"]) < max_report:
                    report["b072_eq_hits"].append({"k": k, "b": b, "p": p, "S": mask_ids(S)})
            if b >= 2:
                fam = fam_from_bvector(board, tbp, S, p)
                for t1, t2 in combinations(fam, 2):
                    if (t1 & t2).bit_count() >= 2:
                        if len(report["b071_violations"]) < max_report:
                            report["b071_violations"].append(
                                {
                                    "k": k,
                                    "p": p,
                                    "t1": mask_ids(t1),
                                    "t2": mask_ids(t2),
                                    "S": mask_ids(S),
                                }
                            )
                        break

    # B075: geometry over all 3-subsets with nonempty completions
    # completion set of T = {p : T∪{p} forbidden} = union over quads containing T
    triples = set()
    triple_compl: dict[int, int] = {}  # triple mask -> completion mask
    for q in board.quads:
        for p in range(V):
            if (q >> p) & 1:
                t = q & ~(1 << p)
                triples.add(t)
    for t in triples:
        cm = 0
        for p in range(V):
            if (t >> p) & 1:
                continue
            for tt in tbp[p]:
                if tt == t:
                    cm |= 1 << p
                    break
        triple_compl[t] = cm

    tlist = sorted(triples)
    for i, t1 in enumerate(tlist):
        c1 = triple_compl[t1]
        for t2 in tlist[i + 1 :]:
            c2 = triple_compl[t2]
            common = (c1 & c2).bit_count()
            if common > report["b075_max_common"]:
                report["b075_max_common"] = common
            if common >= 3:
                # B075 as stated only constrains T,U both inside a SAFE S.
                # T∪U must itself be safe for any safe S to contain both.
                if board.is_safe(t1 | t2):
                    if len(report["b075_violations"]) < max_report:
                        report["b075_violations"].append(
                            {
                                "t1": mask_ids(t1),
                                "t2": mask_ids(t2),
                                "common": mask_ids(c1 & c2),
                            }
                        )
    return report


def maximal_stats(board: Board, tbp, safe_masks, name: str):
    """B076/B077/B078/B080 over maximal safe sets. Returns list of dicts."""
    V = board.V
    rows = []
    for S in safe_masks:
        bv = b_vector(board, S)
        empty = board.full ^ S
        if any(empty >> p & 1 and bv[p] == 0 for p in range(V)):
            continue  # not maximal: some empty point still legal
        vals = [bv[p] for p in range(V) if (empty >> p) & 1]
        avg = sum(vals) / len(vals) if vals else 0.0
        mn = min(vals) if vals else 0
        mx = max(vals) if vals else 0
        rows.append(
            {
                "n": name,
                "k": S.bit_count(),
                "S": mask_ids(S),
                "avg_b": avg,
                "min_b": mn,
                "max_b": mx,
                "all_once": all(v == 1 for v in vals),
                "min_ge2": all(v >= 2 for v in vals),
                "bs": {p: bv[p] for p in range(V) if (empty >> p) & 1},
            }
        )
    return rows


def sts_search(board: Board, tbp, safe_masks, min_k=7):
    """Look for safe S, empty p with b_S(p) = C(k,2)/3 (Steiner triple equality)."""
    V = board.V
    hits = []
    for S in safe_masks:
        k = S.bit_count()
        if k < min_k:
            continue
        if (k * (k - 1)) % 6 != 0:
            continue  # STS requires k ≡ 1 or 3 (mod 6)
        bound = (k * (k - 1)) // 6
        bv = b_vector(board, S)
        empty = board.full ^ S
        for p in range(V):
            if not (empty >> p) & 1:
                continue
            if bv[p] == bound and bound > 0:
                fam = fam_from_bvector(board, tbp, S, p)
                hits.append({"k": k, "p": p, "b": bv[p], "S": mask_ids(S), "fam": [mask_ids(t) for t in fam]})
    return hits


def load_n6_maxsafe():
    data = (ROOT / "night-research" / "maxsafe_n6_K11.bin").read_bytes()
    import struct

    return [struct.unpack_from("<Q", data, i)[0] for i in range(0, len(data), 8)]


def b076_correlation(maximal_rows):
    """Compare mean avg_b across sizes within each board (smaller k → smaller avg_b?)."""
    by_board = defaultdict(lambda: defaultdict(list))
    for r in maximal_rows:
        by_board[r["n"]][r["k"]].append(r["avg_b"])
    out = {}
    for n, byk in by_board.items():
        sizes = sorted(byk)
        means = {k: sum(v) / len(v) for k, v in byk.items()}
        # Spearman-like: is mean avg_b nonincreasing as k decreases?
        pairs = []
        monotone = True
        for k1, k2 in zip(sizes, sizes[1:]):
            pairs.append((k1, k2, means[k1], means[k2], means[k1] <= means[k2] + 1e-12))
            if means[k1] > means[k2] + 1e-12:
                monotone = False
        out[n] = {
            "sizes": sizes,
            "mean_avg_b": {str(k): means[k] for k in sizes},
            "nonincreasing_in_k": monotone,
            "pairs": pairs,
            "counts": {str(k): len(byk[k]) for k in sizes},
        }
    return out


def main():
    result = {"boards": {}, "b071": [], "b072": [], "b075": [], "b073_hits": [], "b074": [], "b077": [], "b078": [], "b080": [], "b076": {}, "n6_maxsafe": {}}

    # --- n=2..5 full safe enumeration ---
    for n in range(2, 6):
        print(f"board {n}x{n}: building...", flush=True)
        board = board_square(n)
        tbp = triple_index(board)
        print(f"  quads={len(board.quads)} enumerating safe...", flush=True)
        safe = all_safe_masks(board)
        print(f"  safe={len(safe)} checking B071/72/75...", flush=True)
        rep = check_b071_b072_b075_board(board, tbp, safe, f"{n}x{n}")
        rep["K"] = max(s.bit_count() for s in safe) if safe else 0
        result["boards"][f"{n}x{n}"] = {
            "n_safe": rep["n_safe"],
            "K": rep["K"],
            "b071_violations": rep["b071_violations"],
            "b072_violations": rep["b072_violations"],
            "b072_max_b": rep["b072_max_b"],
            "b072_max_S": rep["b072_max_S"],
            "b072_eq_hits_kge7": rep["b072_eq_hits"],
            "b074_max_bs_over_k": rep["b074_max_bs_over_k"],
            "b074_argmax": rep["b074_argmax"],
            "b075_violations": rep["b075_violations"],
            "b075_max_common": rep["b075_max_common"],
        }
        result["b071"].extend([{**v, "n": n} for v in rep["b071_violations"]])
        result["b072"].extend([{**v, "n": n} for v in rep["b072_violations"]])
        result["b075"].extend([{**v, "n": n} for v in rep["b075_violations"]])
        result["b074"].append({"n": n, "max_ratio": rep["b074_max_bs_over_k"], "argmax": rep["b074_argmax"]})
        print(f"  B071 viol={len(rep['b071_violations'])} B072 viol={len(rep['b072_violations'])} "
              f"B075 viol={len(rep['b075_violations'])} maxb={rep['b072_max_b']} "
              f"maxratio={rep['b074_max_bs_over_k']:.3f}", flush=True)

        print(f"  STS search (k>=7)...", flush=True)
        hits = sts_search(board, tbp, safe, min_k=7)
        result["b073_hits"].extend([{**h, "n": n} for h in hits])
        print(f"  STS hits={len(hits)}", flush=True)

        print(f"  maximal coverage stats...", flush=True)
        mrows = maximal_stats(board, tbp, safe, f"{n}x{n}")
        for r in mrows:
            if r["min_ge2"]:
                result["b077"].append(r)
            if r["all_once"] and r["k"] >= 1:
                result["b080"].append(r)
        # B078: among minimal-k maximal sets, is there always a point with b=1?
        if mrows:
            s_n = min(r["k"] for r in mrows)
            minrows = [r for r in mrows if r["k"] == s_n]
            any_single = any(r["min_b"] == 1 for r in minrows)
            all_have_single = all(r["min_b"] == 1 for r in minrows)
            result["b078"].append(
                {
                    "n": n,
                    "s_n": s_n,
                    "n_minimal_maximal": len(minrows),
                    "exists_b_eq_1": any_single,
                    "all_have_b_eq_1": all_have_single,
                    "min_b_values": Counter(r["min_b"] for r in minrows),
                    "counterexamples_without_single": [
                        {"S": r["S"], "min_b": r["min_b"], "bs": r["bs"]}
                        for r in minrows
                        if r["min_b"] != 1
                    ][:5],
                }
            )
        result["b076"][f"{n}x{n}"] = {
            "by_size": {str(r["k"]): None for r in mrows},
            "rows": [
                {"k": r["k"], "avg_b": r["avg_b"], "min_b": r["min_b"], "max_b": r["max_b"]}
                for r in mrows
            ],
        }
        print(f"  maximal count={len(mrows)} s_n={min(r['k'] for r in mrows) if mrows else None}", flush=True)

    # --- n=6 maximal K=11 sets only (464) ---
    print("n=6 maximal K=11 from bin...", flush=True)
    board6 = board_square(6)
    tbp6 = triple_index(board6)
    max6 = load_n6_maxsafe()
    print(f"  loaded {len(max6)} sets", flush=True)
    b071_v = b072_v = 0
    max_b = 0
    max_ratio = 0.0
    argmax = None
    eq_hits = []
    b077_hits = []
    b080_hits = []
    for S in max6:
        k = S.bit_count()
        bv = b_vector(board6, S)
        empty = board6.full ^ S
        for p in range(board6.V):
            if not (empty >> p) & 1:
                continue
            b = bv[p]
            if b == 0:
                continue
            if b > max_b:
                max_b = b
            if b / k > max_ratio:
                max_ratio = b / k
                argmax = {"k": k, "b": b, "p": p, "S": mask_ids(S)}
            bound = (k * (k - 1)) // 6
            if b > bound:
                b072_v += 1
            if b == bound and k >= 7:
                eq_hits.append({"k": k, "p": p, "b": b, "S": mask_ids(S)})
            if b >= 2:
                fam = fam_from_bvector(board6, tbp6, S, p)
                for t1, t2 in combinations(fam, 2):
                    if (t1 & t2).bit_count() >= 2:
                        b071_v += 1
                        break
        vals = [bv[p] for p in range(board6.V) if (empty >> p) & 1]
        if vals and min(vals) >= 2:
            b077_hits.append({"k": k, "S": mask_ids(S), "min_b": min(vals), "avg_b": sum(vals) / len(vals)})
        if vals and all(v == 1 for v in vals):
            b080_hits.append({"k": k, "S": mask_ids(S), "bs": {p: bv[p] for p in range(board6.V) if (empty >> p) & 1}})

    result["n6_maxsafe"] = {
        "n_sets": len(max6),
        "b071_violations": b071_v,
        "b072_violations": b072_v,
        "b075_note": "B075 is board-geometry; already checked via n<=5 geometry plus proof sketch",
        "max_b": max_b,
        "max_ratio": max_ratio,
        "argmax": argmax,
        "sts_eq_hits": eq_hits[:20],
        "b077_hits": b077_hits[:10],
        "b080_hits": b080_hits[:10],
    }
    result["b077"].extend(b077_hits)
    result["b080"].extend(b080_hits)
    print(f"  n6 B071v={b071_v} B072v={b072_v} maxb={max_b} maxratio={max_ratio:.3f} "
          f"STS={len(eq_hits)} b077={len(b077_hits)} b080={len(b080_hits)}", flush=True)

    rows = []
    for n, blk in result["b076"].items():
        for r in blk["rows"]:
            rows.append({"n": n, **r})
    result["b076_summary"] = b076_correlation(rows)

    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""B575 fix + B579 targeted: b-histogram change on flip vs nonflip swaps.

B575: fix zero-pad bug.  Multiset L1 distance of b-values (Counter),
stratified by |L Δ L'| (the exchange's legal-set symmetric difference).
Claim: flip edges have larger b-change than nonflip at fixed (n,k,|LΔ|).

B579: at fixed (n,k,g,|L|), singleton-WFT positions share winning moves
with 1-swap neighbours more often.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square  # noqa: E402
from round2_b561_exchange import (  # noqa: E402
    b_sp,
    enumerate_safe,
    grundy_table,
    legal_mask,
    swap_neighbors,
    winning_moves,
)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b561.json"


def counter_l1(c1: Counter, c2: Counter) -> int:
    keys = set(c1) | set(c2)
    return sum(abs(c1[k] - c2[k]) for k in keys)


def b_hist(occ, board):
    L = board.legal_moves(occ)
    return Counter(b_sp(occ, p, board) for p in L)


def main():
    report = json.loads(OUT.read_text(encoding="utf-8"))
    rng = random.Random(7)

    out575 = {}
    out579 = {}
    for n in (4, 5):
        board = board_square(n)
        by = enumerate_safe(board)
        safe_set = set()
        for g in by:
            safe_set.update(g)
        gtab = grundy_table(board, safe_set)
        by_size = {k: set(by[k]) for k in range(len(by))}

        # ---------- B575 ----------
        flip_by = defaultdict(list)
        nonflip_by = defaultdict(list)
        sample = [m for m in safe_set if 3 <= m.bit_count() <= 7]
        rng.shuffle(sample)
        for S in sample[: min(350, len(sample))]:
            hS = b_hist(S, board)
            LS = set(board.legal_moves(S))
            for out_pt, in_pt in swap_neighbors(board, S, by_size):
                T = (S ^ (1 << out_pt)) | (1 << in_pt)
                if T not in safe_set:
                    continue
                LT = set(board.legal_moves(T))
                sym = len(LS ^ LT)
                d = counter_l1(hS, b_hist(T, board))
                flip = (gtab[S] == 0) != (gtab[T] == 0)
                if flip:
                    flip_by[sym].append(d)
                else:
                    nonflip_by[sym].append(d)
        summary = []
        for sym in sorted(set(flip_by) | set(nonflip_by)):
            fd = flip_by.get(sym, [])
            nd = nonflip_by.get(sym, [])
            summary.append({
                "symdiff_L": sym,
                "n_flip": len(fd),
                "mean_flip": sum(fd) / len(fd) if fd else None,
                "n_nonflip": len(nd),
                "mean_nonflip": sum(nd) / len(nd) if nd else None,
            })
        all_f = [d for lst in flip_by.values() for d in lst]
        all_n = [d for lst in nonflip_by.values() for d in lst]
        out575[f"n{n}"] = {
            "n_flip": len(all_f),
            "n_nonflip": len(all_n),
            "mean_flip": sum(all_f) / len(all_f) if all_f else None,
            "mean_nonflip": sum(all_n) / len(all_n) if all_n else None,
            "by_symdiff": summary[:12],
        }

        # ---------- B579 ----------
        # sample N positions; for each, 1-swap N-neighbours; measure Jaccard
        # of winning-move sets.  Group by (k, g, |L|, wft_singleton).
        Npos = [m for m in safe_set if gtab.get(m, 0) != 0]
        rng.shuffle(Npos)

        def T_star(occ, memo=None):
            if memo is None:
                memo = {}
            if occ in memo:
                return memo[occ]
            mv = board.legal_moves(occ)
            if not mv:
                memo[occ] = {occ.bit_count()}
                return memo[occ]
            g = gtab.get(occ, 0)
            if g == 0:
                opts = mv
            else:
                opts = [u for u in mv if gtab.get(occ | (1 << u), -1) == 0]
                if not opts:
                    opts = mv
            acc = set()
            for u in opts:
                acc |= T_star(occ | (1 << u), memo)
            memo[occ] = acc
            return acc

        rows = []
        for S in Npos[: min(120, len(Npos))]:
            WS = set(winning_moves(board, S, gtab))
            if not WS:
                continue
            jacs = []
            k = S.bit_count()
            for out_pt, in_pt in swap_neighbors(board, S, by_size):
                T = (S ^ (1 << out_pt)) | (1 << in_pt)
                if T not in safe_set or gtab.get(T, 0) == 0:
                    continue
                WT = set(winning_moves(board, T, gtab))
                if not WT:
                    continue
                jacs.append(len(WS & WT) / len(WS | WT))
            if not jacs:
                continue
            ts = T_star(S)
            rows.append({
                "k": k,
                "g": gtab[S],
                "L": legal_mask(board, S).bit_count(),
                "wft_singleton": 1 if len(ts) == 1 else 0,
                "stability": sum(jacs) / len(jacs),
            })
        # within (k,g,L) compare singleton vs multi
        bins = defaultdict(lambda: [[], []])  # [singleton, multi] stability lists
        for r in rows:
            bins[(r["k"], r["g"], r["L"])][r["wft_singleton"]].append(r["stability"])
        pair_diffs = []
        for key, (sing, multi) in bins.items():
            if sing and multi:
                pair_diffs.append(sum(sing) / len(sing) - sum(multi) / len(multi))
        # also unconditional singleton vs multi
        st_s = [r["stability"] for r in rows if r["wft_singleton"]]
        st_m = [r["stability"] for r in rows if not r["wft_singleton"]]
        out579[f"n{n}"] = {
            "n_rows": len(rows),
            "n_singleton": len(st_s),
            "n_multi": len(st_m),
            "mean_stability_singleton": sum(st_s) / len(st_s) if st_s else None,
            "mean_stability_multi": sum(st_m) / len(st_m) if st_m else None,
            "n_matched_bins": len(pair_diffs),
            "mean_paired_diff_sing_minus_multi": (
                sum(pair_diffs) / len(pair_diffs) if pair_diffs else None
            ),
            "n_bins_singleton_higher": sum(1 for d in pair_diffs if d > 0),
        }
        print(f"n={n} B575 flip={out575[f'n{n}']['mean_flip']} non={out575[f'n{n}']['mean_nonflip']}")
        print(f"n={n} B579 {out579[f'n{n}']}")

    report["b575_fixed"] = out575
    report["b579_targeted"] = out579
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

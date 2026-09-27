#!/usr/bin/env python3
"""Follow-ups for B542, B545 detail, B546 (unrestricted shift intervals), B547 classification."""
from __future__ import annotations

import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round2_b541_pairsum import pairsum_game, sigma2  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round2_b531.json"


def shift_interval_stats(A, B, window=20):
    """Allowed integer shifts t of A (on an infinite column) such that
    Sigma2(A+t) cap Sigma2(B) = empty. Report #forbidden integer t and
    connected components of allowed t within [-window, window].
    """
    sA, sB = sigma2(A), sigma2(B)
    forbidden = set()
    for sa in sA:
        for sb in sB:
            diff = sb - sa
            if diff % 2 == 0:
                forbidden.add(diff // 2)
    allowed = [t for t in range(-window, window + 1) if t not in forbidden]
    comps = 0
    prev = None
    for t in allowed:
        if prev is None or t != prev + 1:
            comps += 1
        prev = t
    return {
        "n_forbidden_t": len(forbidden),
        "forbidden_t_sample": sorted(forbidden)[:12],
        "n_comps_in_window": comps,
        "allowed_sample": allowed[:20],
    }


def main():
    out = {}

    # ---- B545 detail: the 3v3 safe configs on m=5 ----
    m = 5
    cfgs = []
    for A in combinations(range(m), 3):
        sA = sigma2(A)
        for B in combinations(range(m), 3):
            if sigma2(B) & sA:
                continue
            sB = sigma2(B)
            sep = max(sA) < min(sB) or max(sB) < min(sA)
            cfgs.append(
                {
                    "A": list(A),
                    "B": list(B),
                    "sA": sorted(sA),
                    "sB": sorted(sB),
                    "separated": sep,
                    "which_low": "A" if max(sA) < min(sB) else ("B" if max(sB) < min(sA) else None),
                }
            )
    out["b545_detail"] = {
        "n": len(cfgs),
        "configs": cfgs,
    }

    # ---- B546 unrestricted shift intervals, m=5,6,7,8 ----
    b546u = {}
    for mm in (5, 6, 7, 8):
        rows = []
        for A in combinations(range(mm), 3):
            sA = sigma2(A)
            for B in combinations(range(mm), 3):
                if sigma2(B) & sA:
                    continue
                st = shift_interval_stats(A, B)
                rows.append(st["n_comps_in_window"])
        hist = Counter(rows)
        b46 = {
            "n_3v3": len(rows),
            "comps_hist": dict(hist),
            "n_ge3": sum(1 for c in rows if c >= 3),
        }
        # sample one config with max comps
        best = None
        best_c = -1
        for A in combinations(range(mm), 3):
            sA = sigma2(A)
            for B in combinations(range(mm), 3):
                if sigma2(B) & sA:
                    continue
                st = shift_interval_stats(A, B)
                if st["n_comps_in_window"] > best_c:
                    best_c = st["n_comps_in_window"]
                    best = {"A": list(A), "B": list(B), **st}
        b46["example_max"] = best
        b546u[f"m{mm}"] = b46
        print(f"b546u m={mm}", b46["comps_hist"], "ge3", b46["n_ge3"], flush=True)
    out["b546_unrestricted"] = b546u

    # ---- B542: canonical opposite-row replies ----
    # Test two order-type rules at m=6..10:
    #   R1: reply at same column (x, 1-r)
    #   R2: reply at the opposite-row column with the same rank among free cells
    #   R3: reply at x' = m-1-x (reflection)
    # Count how often the rule yields a winning (g=0) reply.
    b542 = {}
    for mm in (6, 7, 8, 9, 10):
        memo, lc = pairsum_game(mm)
        stats = {"R1_same_col": 0, "R3_reflect": 0, "R4_leftmost_win": 0, "n_first": 0, "fail_R1": [], "fail_R3": []}
        for r in (0, 1):
            for x in range(mm):
                A0, B0 = ((x,), ()) if r == 0 else ((), (x,))
                stats["n_first"] += 1
                # R1
                if r == 0:
                    st1 = ((x,), (x,))
                    if st1 in memo and memo[st1] == 0:
                        stats["R1_same_col"] += 1
                    else:
                        stats["fail_R1"].append((r, x))
                else:
                    st1 = ((x,), (x,))
                    if st1 in memo and memo[st1] == 0:
                        stats["R1_same_col"] += 1
                    else:
                        stats["fail_R1"].append((r, x))
                # R3 reflect
                xr = mm - 1 - x
                if r == 0:
                    st3 = ((x,), (xr,))
                else:
                    st3 = ((xr,), (x,))
                if st3 in memo and memo[st3] == 0:
                    stats["R3_reflect"] += 1
                else:
                    stats["fail_R3"].append((r, x))
                # R4: leftmost opposite-row winning reply (order-type greedy)
                wins = []
                for nA, nB in lc(A0, B0):
                    if memo[(nA, nB)] != 0:
                        continue
                    if r == 0:
                        played = [b for b in nB if b not in B0]
                    else:
                        played = [a for a in nA if a not in A0]
                    if played:
                        wins.append(played[0])
                if wins and min(wins) == wins[0]:
                    stats["R4_leftmost_win"] += 1
        b542[f"m{mm}"] = stats
        print(
            f"b542 m={mm} R1={stats['R1_same_col']}/{stats['n_first']} "
            f"R3={stats['R3_reflect']} R4={stats['R4_leftmost_win']}",
            flush=True,
        )
    out["b542_canonical"] = b542

    # ---- B547: classify 5-stone maximals by cover ----
    b547c = {}
    for mm in (5, 6, 7, 8):
        memo, lc = pairsum_game(mm)
        max5 = []
        for A, B in list(memo.keys()):
            if len(A) + len(B) == 5 and not lc(A, B):
                max5.append((A, B))
        # cover analysis: forbidden x for the 2-side
        rows = []
        for A, B in max5:
            if len(A) == 3 and len(B) == 2:
                sA = sigma2(A)
                forb = set()
                for b in B:
                    for s in sA:
                        forb.add(s - b)
                cover = forb | set(B)
                rows.append(
                    {
                        "A": list(A),
                        "B": list(B),
                        "n_forb_reflect": len(forb & set(range(mm))),
                        "covers_board": set(range(mm)) <= cover,
                        "cover_size": len(cover & set(range(mm))),
                    }
                )
            elif len(B) == 3 and len(A) == 2:
                sB = sigma2(B)
                forb = set()
                for a in A:
                    for s in sB:
                        forb.add(s - a)
                cover = forb | set(A)
                rows.append(
                    {
                        "A": list(A),
                        "B": list(B),
                        "n_forb_reflect": len(forb & set(range(mm))),
                        "covers_board": set(range(mm)) <= cover,
                        "cover_size": len(cover & set(range(mm))),
                    }
                )
        b547c[f"m{mm}"] = {
            "n_5stone_maximal": len(max5),
            "n_analyzed": len(rows),
            "all_cover": all(r["covers_board"] for r in rows),
            "cover_size_hist": dict(Counter(r["cover_size"] for r in rows)),
            "examples": rows[:6],
        }
        print(f"b547c m={mm}", b547c[f"m{mm}"]["n_5stone_maximal"], "all_cover", b547c[f"m{mm}"]["all_cover"], flush=True)
    out["b547_classification"] = b547c

    # ---- B548 threshold proof data: max cover size for (3,2) ----
    # For any (3,2), |reflect forbs| <= 6, |B| = 2 => cover <= 8.
    # Hence maximal (3,2) requires m <= 8. Record max cover observed.
    out["b548_cover_bound"] = {
        "max_cover_3_2": 8,
        "argument": "|Sigma2(A)|=3, |B|=2 => |forb|<=6; +|B|=2 => cover<=8. So m>=9 has no (3,2) maximal.",
    }

    path = OUT
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.setdefault("b541_followup", {}).update(out)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()

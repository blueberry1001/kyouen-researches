#!/usr/bin/env python3
"""Quick follow-ups: B133 circle hierarchy, B169 two-stone residues,
B181/B184 terminal-size stats, B189 last-point bias (n=4 exact)."""
from __future__ import annotations

import json
import math
import struct
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent.parent / "round5_b101_followup_q.json"


def load_u64(path: Path) -> list[int]:
    raw = path.read_bytes()
    return list(struct.unpack(f"<{len(raw)//8}Q", raw))


# ---- B133: circle types by center denominator ----
def circle_center(p1, p2, p3):
    """Circumcenter of 3 points as rational (num/den). Return None if collinear."""
    (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if d == 0:
        return None
    # a=x²+y²
    a1, a2, a3 = x1 * x1 + y1 * y1, x2 * x2 + y2 * y2, x3 * x3 + y3 * y3
    ux = (a1 * (y2 - y3) + a2 * (y3 - y1) + a3 * (y1 - y2)) / d
    uy = (a1 * (x3 - x2) + a2 * (x1 - x3) + a3 * (x2 - x1)) / d
    return (ux, uy)


def center_q(cx, cy):
    """Denominator of (cx,cy) as rationals. We compute via fractions."""
    from fractions import Fraction
    fx, fy = Fraction(cx).limit_denominator(10000), Fraction(cy).limit_denominator(10000)
    return max(fx.denominator, fy.denominator), (fx, fy)


def job_b133() -> dict:
    out = {}
    for n in (4, 5, 6):
        pts = square_points(n)
        # all circles through >=3 points: group by center+radius
        circ = defaultdict(list)
        for a, b, c in combinations(pts, 3):
            ctr = circle_center(a, b, c)
            if ctr is None:
                continue
            cx, cy = ctr
            # radius^2
            r2 = (a[0] - cx) ** 2 + (a[1] - cy) ** 2
            key = (round(cx, 9), round(cy, 9), round(r2, 9))
            circ[key].append((a, b, c))
        # unique circles: set of points on each
        circles = {}
        for key, _ in circ.items():
            cx, cy, r2 = key
            on = []
            for p in pts:
                if abs((p[0] - cx) ** 2 + (p[1] - cy) ** 2 - r2) < 1e-6:
                    on.append(p)
            if len(on) >= 3:
                circles[key] = on
        # classify by q
        by_q_max = {}
        by_q_count = Counter()
        for key, on in circles.items():
            cx, cy, _ = key
            # approximate q from rounded center
            from fractions import Fraction
            fx = Fraction(cx).limit_denominator(10000)
            fy = Fraction(cy).limit_denominator(10000)
            q = max(fx.denominator, fy.denominator)
            by_q_count[q] += 1
            by_q_max[q] = max(by_q_max.get(q, 0), len(on))
        # max points overall
        max_pts = max(len(on) for on in circles.values())
        # first q achieving max
        qs_at_max = sorted(q for q, mp in by_q_max.items() if mp == max_pts)
        out[f"n{n}"] = {
            "n_circles_ge3": len(circles),
            "max_pts": max_pts,
            "by_q_count": dict(by_q_count),
            "by_q_max": by_q_max,
            "qs_achieving_max_pts": qs_at_max,
            "q2_is_max": 2 in qs_at_max,
        }
        print(f"B133 n={n}: circles={len(circles)} max={max_pts} qs_at_max={qs_at_max}")
    return out


# ---- B169 two-stone residue mixing ----
def job_b169_2stone() -> dict:
    n = 5
    board = Board(square_points(n))
    cache_p = DATA / "round5_outcomes_cache.json"
    if cache_p.exists():
        cache = json.loads(cache_p.read_text(encoding="utf-8"))
        memo = {int(k): v for k, v in cache[f"n{n}"].items()}
    else:
        memo = board.solve_outcomes()
    out = {}
    for m_mod in (2, 3, 4, 5):
        groups = defaultdict(list)
        for i, j in combinations(range(n * n), 2):
            m = (1 << i) | (1 << j)
            if not board.is_safe(m):
                continue
            xi, yi = i % n, i // n
            xj, yj = j % n, j // n
            key = tuple(sorted([(xi % m_mod, yi % m_mod), (xj % m_mod, yj % m_mod)]))
            g = memo.get(m, -1)
            groups[key].append(g)
        mixed = sum(1 for gs in groups.values() if len(set(gs)) > 1)
        out[f"m{m_mod}"] = {
            "n_classes": len(groups),
            "n_mixed": mixed,
            "has_witness": mixed > 0,
            "example_mixed": [
                {"class": [list(c) for c in k], "outcomes": sorted(set(gs))}
                for k, gs in groups.items() if len(set(gs)) > 1
            ][:3],
        }
        print(f"B169-2s m={m_mod}: mixed={mixed}/{len(groups)}")
    return out


# ---- B181/B184/B189: terminal size distribution n=4 exact ----
def job_b181_184_189() -> dict:
    out = {}
    for n in (4,):
        board = Board(square_points(n))
        dist = board.exact_terminal_dist()
        # E[X], Var, skew, kurtosis
        xs = sorted(dist)
        EX = sum(t * p for t, p in dist.items())
        EX2 = sum(t * t * p for t, p in dist.items())
        var = EX2 - EX * EX
        sd = math.sqrt(var) if var > 0 else 0.0
        EX3 = sum(t ** 3 * p for t, p in dist.items())
        EX4 = sum(t ** 4 * p for t, p in dist.items())
        mu3 = EX3 - 3 * EX * EX2 + 2 * EX ** 3
        mu4 = EX4 - 4 * EX * EX3 + 6 * EX * EX2 - 3 * EX ** 4
        skew = mu3 / (sd ** 3) if sd > 0 else 0.0
        kurt = mu4 / (var * var) if var > 0 else 0.0
        # K_n
        maximal = load_u64(DATA / f"maximal_n{n}.bin")
        K = max(m.bit_count() for m in maximal)
        out[f"n{n}_term"] = {
            "dist": {str(k): v for k, v in dist.items()},
            "E_X": EX,
            "Var": var,
            "skewness": skew,
            "kurtosis": kurt,
            "K": K,
            "E_over_K": EX / K,
        }
        print(f"B181 n={n}: E={EX:.3f} K={K} E/K={EX/K:.3f} skew={skew:.3f} kurt={kurt:.3f}")

        # B189: last legal point under random greedy — exact via DP
        # P(last point = p) for each p. State: occupied mask. Absorb when no moves.
        # We want the unique last *legal* point at the terminal maximal set.
        # At terminal, L(S)=empty so "last legal point" means the last move made.
        # Compute P(last move placed at p).
        from functools import lru_cache
        sys.setrecursionlimit(100000)

        @lru_cache(maxsize=None)
        def last_dist(occ: int) -> tuple:
            """Return tuple of probabilities that the last placed point is p,
            for p=0..V-1, under uniform random legal moves."""
            V = n * n
            mv = board.legal_moves(occ)
            if not mv:
                return tuple(1.0 if (occ.bit_count() == 1 and (occ & (1 << p)) and False) else 0.0
                             for p in range(V))
            # actually: among moves, pick uniformly; recurse
            acc = [0.0] * V
            w = 1.0 / len(mv)
            for u in mv:
                sub = last_dist(occ | (1 << u))
                # the last move overall is either u (if terminal after) or from sub
                # We need: if occ|u is terminal, last is u; else last is from sub.
                nxt = occ | (1 << u)
                if not board.legal_moves(nxt):
                    acc[u] += w
                else:
                    for p in range(V):
                        acc[p] += sub[p] * w
            return tuple(acc)

        # Fix the terminal case: at a terminal occ, the last point is the most
        # recently added. We need a different DP that tracks the last point.
        # Recompute properly:
        @lru_cache(maxsize=None)
        def last_dist2(occ: int, last: int) -> float:
            """P(process ends with 'last' being the final placed point | state)."""
            return 0.0  # placeholder

        # Better: P(final move at p) = sum over paths that end by playing p.
        # DP: F(occ) = distribution over final-move point, given we are AT occ
        # and it is the opponent's turn (occ already includes the last move).
        # Actually define G(occ) = dist of the LAST point of the game starting
        # from empty, conditional on reaching occ as a nonterminal prefix with
        # the last placed point known... Easier: just simulate the DP where
        # we track (occ) and when we play u into a terminal, u is the answer.

        def last_point_dist() -> list[float]:
            V = n * n
            memo_d = {}

            def go(occ: int) -> list[float]:
                """Starting from occ (player to move), distribution of the
                point that will be the final move of the game."""
                if occ in memo_d:
                    return memo_d[occ]
                mv = board.legal_moves(occ)
                if not mv:
                    # game already over; the final move was made earlier.
                    # This branch shouldn't be used as a start; return zeros.
                    res = [0.0] * V
                    memo_d[occ] = res
                    return res
                acc = [0.0] * V
                w = 1.0 / len(mv)
                for u in mv:
                    nxt = occ | (1 << u)
                    if not board.legal_moves(nxt):
                        acc[u] += w
                    else:
                        sub = go(nxt)
                        for p in range(V):
                            acc[p] += sub[p] * w
                memo_d[occ] = acc
                return acc

            return go(0)

        lp = last_point_dist()
        deg = [0] * (n * n)
        for q in board.quads:
            for i in range(n * n):
                if q >> i & 1:
                    deg[i] += 1
        # correlation: P(last=p) vs deg(p)
        # also: fraction of last-point mass on the lowest-degree points
        order = sorted(range(n * n), key=lambda i: deg[i])
        low = order[: n * n // 4]
        high = order[-(n * n // 4):]
        mass_low = sum(lp[i] for i in low)
        mass_high = sum(lp[i] for i in high)
        out[f"n{n}_last"] = {
            "last_dist": {str(i % n) + "," + str(i // n): lp[i] for i in range(n * n)},
            "deg": {str(i % n) + "," + str(i // n): deg[i] for i in range(n * n)},
            "mass_on_lowest_quarter_deg": mass_low,
            "mass_on_highest_quarter_deg": mass_high,
            "pearson_r": None,
        }
        # pearson
        mean_p = sum(lp) / (n * n)
        mean_d = sum(deg) / (n * n)
        num = sum((lp[i] - mean_p) * (deg[i] - mean_d) for i in range(n * n))
        den = math.sqrt(sum((lp[i] - mean_p) ** 2 for i in range(n * n)) *
                       sum((deg[i] - mean_d) ** 2 for i in range(n * n)))
        out[f"n{n}_last"]["pearson_r"] = num / den if den else None
        print(f"B189 n={n}: mass_low={mass_low:.3f} mass_high={mass_high:.3f} r={out[f'n{n}_last']['pearson_r']}")
    return out


def main():
    out = {}
    if OUT.exists():
        try:
            out = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            out = {}
    for name, fn in [("b133", job_b133), ("b169_2stone", job_b169_2stone),
                     ("b181_184_189", job_b181_184_189)]:
        print(f"=== {name} ===")
        out[name] = fn()
        OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("DONE")


if __name__ == "__main__":
    main()

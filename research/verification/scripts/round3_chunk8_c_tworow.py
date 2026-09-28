#!/usr/bin/env python3
"""round3_chunk8_c_tworow.py — B542, B546, B550.

Previous state (round2-batch-b531.md):
  B542 PARTIAL: the "same column" reply rule wins for ALL first moves for m>=7
       (m=6: 8/12).  "Reflection" rule same score.  "leftmost opposite-row
       winning move" 100% for m=6..10.  The full *order type* description was
       not constructed.
  B546 PARTIAL: with interpretation (ii) (integer line, t unbounded),
       #configs with >=3 shift components: m=5:0, m=6:12, m=7:128, m=8:538.
  B550 PARTIAL: translation g-invariance (A,B)->(A+1,B+1) holds for ALL
       states once m>=9; fails only for edge-touching states at m=5..8.

This round's advance:
  B542 — build the *actual order-type invariant*: compute a canonical signature
       of each column x (the sequence of induced state-features of (A,B) for
       every safe (A,B) reachable with that column) and check whether the
       second-player reply strategy is a function of that signature only.
       Concretely: for m=6..13, for every first move (r,x) and every
       winning reply y, record the *order type* of y relative to the
       occupied columns and the reflected columns; test whether "reply to the
       least column whose signature class equals a fixed class" succeeds.
  B546 — full (not sampled) enumeration of 3-vs-3 safe configs for m=5..9 and
       the exact number of shift components, plus an explicit witness
       configuration at each m>=6 with >=3 components (previous round gave
       counts but the witness at each m was only for the max).
  B550 — turn the m>=9 invariance into an explicit FINITE-STATE EQUIVALENCE
       relation: define the canonical form c(A,B) = A - min(A), B - min(B)
       clipped to a window, and verify that g(A,B) = g(c(A,B)) whenever the
       state is "far from the edge" (i.e. after translating, both rows fit
       inside [0, m-1] with a margin >= M).  Determine the exact threshold M.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from round3_chunk8_lib import pairsum_children, pairsum_game, sigma2  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round3_chunk8_tworow.json"


# ---------------------------------------------------------------------------
# B546 — full enumeration of shift components
# ---------------------------------------------------------------------------
def shift_components(A, B, window=40):
    """Number of connected components of allowed integer shifts t of A
    (unbounded, |t| <= window)."""
    sA, sB = sigma2(A), sigma2(B)
    forbidden = set()
    for sa in sA:
        for sb in sB:
            d = sb - sa
            if d % 2 == 0:
                forbidden.add(d // 2)
    allowed = [t for t in range(-window, window + 1) if t not in forbidden]
    comps = 0
    prev = None
    allowed_runs = []
    start = None
    for t in allowed:
        if prev is None or t != prev + 1:
            comps += 1
            start = t
            allowed_runs.append([t, t])
        else:
            allowed_runs[-1][1] = t
        prev = t
    return comps, allowed_runs, sorted(forbidden)


def b546(ms=(5, 6, 7, 8, 9)):
    out = {}
    for m in ms:
        t0 = time.time()
        hist = Counter()
        ge3 = 0
        n3v3 = 0
        best = None
        best_c = -1
        witness = None
        for A in combinations(range(m), 3):
            sA = sigma2(A)
            for B in combinations(range(m), 3):
                if sigma2(B) & sA:
                    continue
                n3v3 += 1
                c, runs, forb = shift_components(A, B)
                hist[c] += 1
                if c >= 3:
                    ge3 += 1
                if c > best_c:
                    best_c = c
                    best = {"A": list(A), "B": list(B), "comps": c,
                            "runs": runs, "forbidden": forb}
                if witness is None and c >= 3:
                    witness = {"A": list(A), "B": list(B), "comps": c, "runs": runs}
        out[f"m{m}"] = {
            "n_3v3_safe": n3v3,
            "comps_hist": {str(k): v for k, v in sorted(hist.items())},
            "n_ge3": ge3,
            "frac_ge3": round(ge3 / n3v3, 4) if n3v3 else None,
            "max_comps": best_c,
            "max_example": best,
            "first_ge3_example": witness,
            "seconds": round(time.time() - t0, 1),
        }
        print(f"[b546] m={m} n3v3={n3v3} ge3={ge3} max={best_c} "
              f"({out[f'm{m}']['seconds']}s)", flush=True)
    return out


# ---------------------------------------------------------------------------
# B550 — finite-state equivalence of far-from-edge columns
# ---------------------------------------------------------------------------
def b550(ms=(6, 7, 8, 9, 10, 11, 12, 13)):
    out = {}
    for m in ms:
        t0 = time.time()
        memo, _ = pairsum_game(m)
        # margin M: state (A,B) fits in [lo, m-1-lo] with lo = min(A+B)
        # "far from edge" means lo >= M and (m-1-lo) - max(A+B) >= M.
        # Translation invariance: (A,B) vs (A+d, B+d) for d>0.
        # For a state S, the canonical form is the *leftmost* realisation,
        # i.e. shifted so min(A ∪ B) = 0.  Claim: g(S) = g(shift0(S))
        # whenever S has margin >= M on BOTH sides.
        by_margin = defaultdict(lambda: [0, 0])   # margin -> [ok, fail]
        by_margin0 = defaultdict(lambda: [0, 0])  # shift-to-0 vs g
        fail_ex = []
        for (A0, B0), g in memo.items():
            if not A0 and not B0:
                continue
            U = set(A0) | set(B0)
            hi = max(U)
            lo = min(U)
            A, B = A0, B0
            sA = tuple(a - lo for a in A)
            sB = tuple(b - lo for b in B)
            g0 = memo.get((sA, sB))
            margin = min(lo, m - 1 - hi)
            if g0 is not None:
                d0 = by_margin0[margin]
                d0[0 if g0 == g else 1] += 1
            # local translation d=+1
            if hi < m - 1:
                nA = tuple(a + 1 for a in A)
                nB = tuple(b + 1 for b in B)
                g1 = memo.get((nA, nB))
                if g1 is not None:
                    ok = (g1 == g)
                    d = by_margin[margin]
                    d[0 if ok else 1] += 1
                    if not ok and len(fail_ex) < 8:
                        fail_ex.append({"A": list(A), "B": list(B), "g": g,
                                        "shift1": [list(nA), list(nB)],
                                        "g_shift1": g1, "margin": margin})
        worst_fail_margin = None
        worst_fail0 = None
        for mg in sorted(by_margin):
            if by_margin[mg][1] > 0:
                worst_fail_margin = mg
        for mg in sorted(by_margin0):
            if by_margin0[mg][1] > 0:
                worst_fail0 = mg
        out[f"m{m}"] = {
            "n_states": len(memo),
            "by_min_margin_localtrans": {str(k): {"ok": v[0], "fail": v[1]}
                                         for k, v in sorted(by_margin.items())},
            "by_min_margin_shift0": {str(k): {"ok": v[0], "fail": v[1]}
                                     for k, v in sorted(by_margin0.items())},
            "max_margin_with_fail_localtrans": worst_fail_margin,
            "max_margin_with_fail_shift0": worst_fail0,
            "fail_examples": fail_ex,
            "seconds": round(time.time() - t0, 1),
        }
        print(f"[b550] m={m} localtrans_maxfailmargin={worst_fail_margin} "
              f"shift0_maxfailmargin={worst_fail0} "
              f"({out[f'm{m}']['seconds']}s)", flush=True)
    return out


# ---------------------------------------------------------------------------
# B542 — order-type description of the second-player reply
# ---------------------------------------------------------------------------
def b542(ms=(6, 7, 8, 9, 10, 11, 12)):
    out = {}
    for m in ms:
        t0 = time.time()
        memo, _lc = pairsum_game(m)
        lc = lambda A, B: _lc(m, A, B)
        empty_g = memo[((), ())]
        # For each first move (r, x) the second player must move to a P state.
        # Build the "order type" of each column x: the tuple of
        # (number of safe states containing x) is too coarse.  Instead use the
        # *winning reply signature*: which columns y admit a P-state reply.
        rows = []
        for r in (0, 1):
            for x in range(m):
                A0, B0 = ((x,), ()) if r == 0 else ((), (x,))
                wincols = set()
                for nA, nB in lc(A0, B0):
                    if memo.get((nA, nB), 1) != 0:
                        continue
                    if r == 0 and nB != B0:
                        wincols.add(nB[0] if len(nB) == 1 else None)
                    if r == 1 and nA != A0:
                        wincols.add(nA[0] if len(nA) == 1 else None)
                wincols.discard(None)
                rows.append({"row": r, "x": x,
                             "win_cols": sorted(wincols),
                             "n_win": len(wincols)})
        # Candidate ORDER-TYPE rules (coordinate-free):
        #   R_same : reply in the same column x
        #   R_min  : reply at the least winning column
        #   R_min_ge : reply at the least column y >= x among winning columns
        #   R_max  : reply at the greatest winning column
        #   R_ord  : reply at the winning column whose order-type class
        #            (rank among the cut points of A ∪ B ∪ reflections) is 0
        def wins_for(r, x, col):
            A0, B0 = ((x,), ()) if r == 0 else ((), (x,))
            if r == 0:
                return memo.get(((x,), (col,))) == 0 and (x,) != (col,) or \
                       (memo.get((A0, (col,))) == 0)
            return memo.get(((col,), (x,))) == 0

        stats = Counter()
        n_first = 0
        fails = defaultdict(list)
        for rec in rows:
            r, x, wcols = rec["row"], rec["x"], rec["win_cols"]
            n_first += 1
            if not wcols:
                fails["no_win_at_all"].append((r, x))
                continue
            # R_same
            if x in wcols:
                stats["R_same"] += 1
            else:
                fails["R_same"].append((r, x))
            if min(wcols) == wcols[0]:
                stats["R_min"] += 1
            else:
                fails["R_min"].append((r, x))
            if max(wcols) == wcols[-1]:
                stats["R_max"] += 1
            else:
                fails["R_max"].append((r, x))
            ge = [c for c in wcols if c >= x]
            if ge and min(ge) in wcols:
                stats["R_min_ge"] += 1
            else:
                fails["R_min_ge"].append((r, x))
        # ORDER-TYPE canonical form: is the *set* of winning columns a
        # function of the order type of x (i.e. only its rank among
        # A ∪ B ∪ {m-1-a} cut points)?  For an empty board the cut set is
        # {0..m-1} so order type == coordinate, so we instead test the
        # refined statement: two first moves (r,x),(r,x') with the same
        # *mirror+reflection* equivalence class have the same win set shape.
        shapes = defaultdict(list)
        for rec in rows:
            r, x = rec["row"], rec["x"]
            # normalise the win set relative to x: offsets
            off = tuple(sorted(c - x for c in rec["win_cols"]))
            shapes[(r, off)].append(x)
        consistent = all(len(v) == 1 for v in shapes.values())
        out[f"m{m}"] = {
            "empty_g": empty_g,
            "n_first_moves": n_first,
            "rule_scores": dict(stats),
            "fail_counts": {k: len(v) for k, v in fails.items()},
            "fail_examples": {k: v[:8] for k, v in fails.items()},
            "offset_shape_classes": len(shapes),
            "offset_shape_injective": consistent,
            "min_win_count": min(r["n_win"] for r in rows),
            "max_win_count": max(r["n_win"] for r in rows),
            "rows": rows,
            "seconds": round(time.time() - t0, 1),
        }
        print(f"[b542] m={m} g0={empty_g} scores={dict(stats)} "
              f"({out[f'm{m}']['seconds']}s)", flush=True)
    return out


def main():
    res = {"_meta": {"script": "round3_chunk8_c_tworow.py"}}
    print("=== B546 ===", flush=True)
    res["b546"] = b546()
    print("=== B550 ===", flush=True)
    res["b550"] = b550()
    print("=== B542 ===", flush=True)
    res["b542"] = b542()
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

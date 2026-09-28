#!/usr/bin/env python3
"""round3_chunk8_d_3row.py — B555, B556, B560 (3-row board {0..m-1} x {0,1,2}).

Previous state (round2-batch-b531.md):
  B555 INCONCLUSIVE: W-density for m=3..10 is 1.0,0.5,0,0.667,0.524,0,0.370,
       0.867.  No convergence to 1/3.  m=5,8 have g0=0 (W empty) which is
       "partially winning" (後手勝ち) -- the density was NOT separated out.
  B556 PARTIAL: W geometry is aperiodic, but the premise "period continues"
       is false (B551: g breaks period at m=9).
  B560 PARTIAL: m=6 -> 2+2 alone W=0, 2+1+1 alone W=0, both W=10.
       m=7 -> 2+2 alone W=15, 2+1+1 alone W=0, both W=1.

This round's advance:
  B555 — extend to m=11,12,13 (new data beyond the round-2 range) AND
       separate the three regimes properly:
         (a) full-board density |W|/(3m)
         (b) density restricted to the m = 3t+1 subfamily (B554's family)
         (c) density among boards with g0 != 0 (i.e. genuinely "partial win")
       and compute the *exception density*: the density of columns x that are
       NOT in the interior band.
  B556 — quantify the aperiodicity claim properly: count how many distinct
       "interior band" patterns appear among the m's with the SAME g value,
       and measure a growth rate for the number of exception columns.
  B560 — complete the 2+2 / 2+1+1 split for m=6,7,8,9,10 and add the
       crucial missing comparison: the *first-move phase* difference
       (B560 is about the FIRST-MOVE phase), so for each variant we record
       W and check whether the standard W's internal band survives.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from round3_chunk8_lib import Quads, all_forbidden, grid_board, is_collinear  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round3_chunk8_3row.json"


def solve(q):
    g = q.grundy()
    W = [v for v in range(q.V) if g.get(1 << v) == 0]
    return g, W


def run_3row(ms):
    out = {}
    for m in ms:
        t0 = time.time()
        try:
            q = grid_board(m, 3)
            g, W = solve(q)
        except Exception as e:  # pragma: no cover
            out[f"m{m}"] = {"error": str(e)}
            continue
        Wxy = [q.pts[v] for v in W]
        cols = sorted({x for x, y in Wxy})
        inner = sorted({x for x, y in Wxy if 0 < x < m - 1})
        out[f"m{m}"] = {
            "V": q.V, "F": len(q.quads), "g0": g[0],
            "n_W": len(W), "W_xy": [list(p) for p in Wxy],
            "density": round(len(W) / q.V, 4),
            "winning_columns": cols,
            "inner_columns": inner,
            "n_inner_cols": len(inner),
            "row_hist": dict(Counter(y for x, y in Wxy)),
            "seconds": round(time.time() - t0, 1),
        }
        print(f"[3row] m={m} g0={g[0]} |W|={len(W)}/{q.V} cols={cols} "
              f"({out[f'm{m}']['seconds']}s)", flush=True)
    return out


# ---------------------------------------------------------------------------
# B555 — densities, separated by regime
# ---------------------------------------------------------------------------
def b555(three):
    rows = {}
    for key, rec in three.items():
        if "error" in rec:
            continue
        m = int(key[1:])
        rec2 = {
            "g0": rec["g0"],
            "n_W": rec["n_W"],
            "V": rec["V"],
            "density_all": rec["density"],
            "is_partial_win": rec["g0"] != 0,
        }
        if rec["g0"] != 0:
            rec2["density_partial_only"] = rec["density"]
        else:
            rec2["density_partial_only"] = None
        if m % 3 == 1:
            t = (m - 1) // 3
            # B554 band: middle row + cols t, 2t
            band = set()
            for x in range(m):
                band.add((x, 1))
            for y in range(3):
                band.add((t, y))
                band.add((2 * t, y))
            Wset = set(tuple(p) for p in rec["W_xy"])
            rec2["b554_band"] = {
                "t": t, "n_band": len(band), "n_W": len(Wset),
                "match": Wset == band,
                "missing": [list(p) for p in sorted(band - Wset)],
                "extra": [list(p) for p in sorted(Wset - band)],
                "jaccard": round(len(band & Wset) / len(band | Wset), 4) if (band | Wset) else None,
            }
        rows[key] = rec2
    return rows


# ---------------------------------------------------------------------------
# B556 — aperiodicity quantification
# ---------------------------------------------------------------------------
def b556(three):
    by_g = defaultdict(list)
    for key, rec in three.items():
        if "error" in rec:
            continue
        m = int(key[1:])
        by_g[rec["g0"]].append((m, rec))
    rows = {}
    for g, lst in by_g.items():
        lst.sort()
        patterns = []
        for m, rec in lst:
            Wset = set(tuple(p) for p in rec["W_xy"])
            # canonical shape: for each column, the set of rows that win
            colpat = tuple(tuple(y for x, y in sorted(Wset) if x == xx)
                           for xx in range(m))
            patterns.append((m, colpat))
        # count distinct patterns per g
        distinct = len({p for _, p in patterns})
        # growth of the number of "exception columns" = columns whose
        # row-pattern differs from the modal pattern
        exc = []
        for m, colpat in patterns:
            cnt = Counter(colpat)
            modal, mc = cnt.most_common(1)[0]
            n_exc = sum(v for k, v in cnt.items() if k != modal)
            exc.append((m, n_exc, mc, len(cnt)))
        rows[str(g)] = {
            "ms": [m for m, _ in lst],
            "n_distinct_W_patterns": distinct,
            "patterns_distinct_fraction": round(distinct / len(lst), 4),
            "exception_columns": exc,
        }
        print(f"[b556] g={g} ms={[m for m,_ in lst]} distinct={distinct}", flush=True)
    return rows


# ---------------------------------------------------------------------------
# B560 — 2+2 vs 2+1+1 circle types
# ---------------------------------------------------------------------------
def circle_types(m):
    from round3_chunk8_lib import rect
    pts = rect(m, 3)
    quads = all_forbidden(pts)
    by_type = defaultdict(list)
    for ids in quads:
        if is_collinear(pts, ids):
            continue
        occ = Counter(pts[i][1] for i in ids)
        key = tuple(sorted(occ.values(), reverse=True))
        by_type[key].append(ids)
    return pts, by_type


def b560(ms=(6, 7, 8, 9, 10)):
    out = {}
    for m in ms:
        t0 = time.time()
        pts, by_type = circle_types(m)
        variants = {}
        specs = {
            "t22_only": [(2, 2)],
            "t211_only": [(2, 1, 1)],
            "both": [(2, 2), (2, 1, 1)],
            "all_circles": list(by_type.keys()),
        }
        for name, types in specs.items():
            qs = []
            for t in types:
                qs.extend(by_type.get(t, []))
            q = Quads(pts, qs, name=name, n=m)
            try:
                g, W = solve(q)
            except Exception as e:
                variants[name] = {"error": str(e)}
                continue
            Wxy = [pts[v] for v in W]
            inner = sorted({x for x, y in Wxy if 0 < x < m - 1})
            variants[name] = {
                "n_quads": len(qs), "g0": g[0], "n_W": len(W),
                "W_xy": [list(p) for p in Wxy],
                "inner_columns": inner,
                "n_inner": len(inner),
            }
        # standard
        qstd = grid_board(m, 3)
        gstd, Wstd = solve(qstd)
        std_inner = sorted({qstd.pts[v][0] for v in Wstd if 0 < qstd.pts[v][0] < m - 1})
        out[f"m{m}"] = {
            "type_counts": {str(k): len(v) for k, v in sorted(by_type.items())},
            "standard": {"g0": gstd[0], "n_W": len(Wstd), "inner": std_inner},
            "variants": variants,
            "seconds": round(time.time() - t0, 1),
        }
        print(f"[b560] m={m} types={out[f'm{m}']['type_counts']} "
              + " ".join(f"{k}={v.get('n_W')}" for k, v in variants.items())
              + f" ({out[f'm{m}']['seconds']}s)", flush=True)
    return out


def main():
    res = {"_meta": {"script": "round3_chunk8_d_3row.py"}}
    ms = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    print("=== 3-row solves ===", flush=True)
    res["three_row"] = run_3row(ms)
    res["b555"] = b555(res["three_row"])
    res["b556"] = b556(res["three_row"])
    print("=== B560 ===", flush=True)
    res["b560"] = b560((6, 7, 8, 9, 10))
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Round5 B201-B230 follow-up jobs.

Jobs (argv[1]):
  del1rect  w h     - all 1-point deletions on w x h: K, g0, W (B201/B202/B203)
  misere_rect w h   - misere vs normal winner on w x h empty (B226)
  maxcov_rect w h   - maximal safe sets: points never covered (B205)
  pairK_rect  w h   - all 2-point deletions on w x h (B207/B209/B210)
  tol_sym    n thr  - max-config symmetry distribution vs threshold (B229)
  subfam3    n      - 3-quad subfamily reproducing W (B224)
  wchange_rect w h  - |W| change under 1-pt deletion (B206 helper)
  period_chk        - B213: compare g0 series vs period-3 / period-k fits
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import (  # noqa: E402
    Board,
    board_rect,
    board_square,
    board_square_minus,
    det4,
    is_forbidden_quad,
)

OUTDIR = Path(__file__).resolve().parents[1]


def save(name: str, obj) -> None:
    p = OUTDIR / f"round5_b201fu_{name}.json"
    p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {p}", flush=True)


def winner_from_g(g0: int) -> str:
    return "First" if g0 != 0 else "Second"


def winning_first_moves(b: Board, g) -> list[int]:
    w = []
    for u in b.legal_moves(0):
        if g.get(1 << u, 0) == 0:
            w.append(u)
    return w


def pts_rect(w: int, h: int):
    return [(x, y) for y in range(h) for x in range(w)]


# ---------------------------------------------------------------- jobs


def job_del1rect(w: int, h: int) -> None:
    """One-point deletion on rectangle: does K stay and winner flip?"""
    pts = pts_rect(w, h)
    base = Board(pts, name=f"{w}x{h}")
    g_base = base.solve_grundy()
    K_base = max(occ.bit_count() for occ in g_base)
    W_base = winning_first_moves(base, g_base)
    rows = []
    for i, (x, y) in enumerate(pts):
        sub = [p for j, p in enumerate(pts) if j != i]
        b = Board(sub, name=f"{w}x{h}-({x},{y})")
        g = b.solve_grundy()
        K = max(occ.bit_count() for occ in g)
        W = winning_first_moves(b, g)
        rows.append(
            {
                "p": [x, y],
                "g0": g[0],
                "K": K,
                "Wsize": len(W),
                "winner_changed": winner_from_g(g[0]) != winner_from_g(g_base[0]),
                "K_changed": K != K_base,
                "same_K_flip": (K == K_base)
                and (winner_from_g(g[0]) != winner_from_g(g_base[0])),
                "K_down_same_win": (K < K_base)
                and (winner_from_g(g[0]) == winner_from_g(g_base[0])),
                "n_pos": len(g),
            }
        )
        print(
            f"  -({x},{y}) g0={g[0]} K={K} W={len(W)} "
            f"flip={rows[-1]['winner_changed']} Kch={rows[-1]['K_changed']}",
            flush=True,
        )
    save(
        f"del1rect_{w}x{h}",
        {
            "w": w,
            "h": h,
            "base_g0": g_base[0],
            "base_K": K_base,
            "base_Wsize": len(W_base),
            "base_n_pos": len(g_base),
            "rows": rows,
            "n_flip": sum(1 for r in rows if r["winner_changed"]),
            "n_Kchange": sum(1 for r in rows if r["K_changed"]),
            "n_sameK_flip": sum(1 for r in rows if r["same_K_flip"]),
            "n_Kdown_same": sum(1 for r in rows if r["K_down_same_win"]),
        },
    )


def job_misere_rect(w: int, h: int) -> None:
    """Misere vs normal empty winner on rectangle (B226)."""
    b = board_rect(w, h)
    g = b.solve_grundy()

    from functools import lru_cache

    @lru_cache(maxsize=None)
    def win(occ: int) -> int:
        moves = b.legal_moves(occ)
        if not moves:
            return 1
        for u in moves:
            if win(occ | (1 << u)) == 0:
                return 1
        return 0

    empty = win(0)
    rec = {
        "w": w,
        "h": h,
        "normal_g0": g[0],
        "normal_winner": winner_from_g(g[0]),
        "misere_empty": empty,
        "misere_winner": winner_from_g(empty),
        "agree": winner_from_g(empty) == winner_from_g(g[0]),
        "n_pos": len(g),
        "K": max(occ.bit_count() for occ in g),
    }
    # also a few 1-pt deletions if V small
    if w * h <= 15:
        dels = []
        pts = pts_rect(w, h)
        for i, (x, y) in enumerate(pts):
            sub = [p for j, p in enumerate(pts) if j != i]
            bb = Board(sub, name=f"{w}x{h}-({x},{y})")
            gb = bb.solve_grundy()

            @lru_cache(maxsize=None)
            def winb(occ: int) -> int:
                moves = bb.legal_moves(occ)
                if not moves:
                    return 1
                for u in moves:
                    if winb(occ | (1 << u)) == 0:
                        return 1
                return 0

            mb = winb(0)
            dels.append(
                {
                    "p": [x, y],
                    "normal": winner_from_g(gb[0]),
                    "misere": winner_from_g(mb),
                    "agree": winner_from_g(mb) == winner_from_g(gb[0]),
                }
            )
        rec["deletions"] = dels
        rec["n_del_agree"] = sum(1 for d in dels if d["agree"])
    save(f"misererect_{w}x{h}", rec)
    print(f"  {w}x{h} normal={rec['normal_winner']} misere={rec['misere_winner']} agree={rec['agree']}", flush=True)


def job_maxcov_rect(w: int, h: int) -> None:
    """Which points never appear in a maximal safe set? (B205)"""
    b = board_rect(w, h)
    K = b.max_safe_size()
    maxes: list[int] = []
    sys.setrecursionlimit(100000)

    def dfs(occ: int, cand: int, size: int) -> None:
        if size == K:
            maxes.append(occ)
            return
        if size + cand.bit_count() < K:
            return
        while cand:
            bit = cand & -cand
            v = bit.bit_length() - 1
            cand ^= bit
            nxt = occ | bit
            if not b.is_safe(nxt):
                continue
            remain = cand
            bad = 0
            for q in b.quads_by_pt[v]:
                if (q & nxt) == q:
                    pass
                elif (q & ~nxt & b.full).bit_count() == 1:
                    bad |= q & ~nxt
            dfs(nxt, remain & ~bad, size + 1)

    dfs(0, b.full, 0)
    counts = [0] * b.V
    for m in maxes:
        mm = m
        while mm:
            bit = mm & -mm
            counts[bit.bit_length() - 1] += 1
            mm ^= bit
    never = [i for i in range(b.V) if counts[i] == 0]
    save(
        f"maxcovrect_{w}x{h}",
        {
            "w": w,
            "h": h,
            "K": K,
            "n_maximal": len(maxes),
            "points_never_in_max": never,
            "never_coords": [(i % w, i // w) for i in never],
            "contain_counts": counts,
            "min_count": min(counts) if counts else 0,
            "max_count": max(counts) if counts else 0,
        },
    )
    print(f"  {w}x{h} K={K} nmax={len(maxes)} never={never} minc={min(counts)}", flush=True)


def job_pairK_rect(w: int, h: int) -> None:
    """Two-point deletions on rectangle (B207/B209/B210)."""
    pts = pts_rect(w, h)
    base = Board(pts, name=f"{w}x{h}")
    g_base = base.solve_grundy()
    K_base = max(occ.bit_count() for occ in g_base)
    rows = []
    t0 = time.time()
    for i, j in combinations(range(len(pts)), 2):
        di, dj = pts[i], pts[j]
        sub = [p for k, p in enumerate(pts) if k not in (i, j)]
        b = Board(sub, name="d2")
        g = b.solve_grundy()
        K = max(occ.bit_count() for occ in g)
        g0 = g[0]
        # one-point versions
        bi = Board([p for k, p in enumerate(pts) if k != i], name="d1i")
        bj = Board([p for k, p in enumerate(pts) if k != j], name="d1j")
        gi = bi.solve_grundy()[0]
        gj = bj.solve_grundy()[0]
        # symmetry class of the pair under D4 of the rectangle
        rows.append(
            {
                "pair": [list(di), list(dj)],
                "K": K,
                "g0": g0,
                "g_one": [gi, gj],
                "kloss": K < K_base,
                "flip": winner_from_g(g0) != winner_from_g(g_base[0]),
                "combo": (g0 != g_base[0])
                and (gi == g_base[0])
                and (gj == g_base[0]),
            }
        )
        if len(rows) % 20 == 0:
            print(f"  pair {len(rows)} t={time.time()-t0:.1f}s", flush=True)
    save(
        f"pairKrect_{w}x{h}",
        {
            "w": w,
            "h": h,
            "K_base": K_base,
            "g_base": g_base[0],
            "n_pairs": len(rows),
            "n_kloss": sum(1 for r in rows if r["kloss"]),
            "n_flip": sum(1 for r in rows if r["flip"]),
            "n_combo": sum(1 for r in rows if r["combo"]),
            "rows": rows,
        },
    )


def _d4_orbit(w: int, h: int, occ: int, pts) -> frozenset:
    """D4 orbit of a bitmask on w x h (swap w/h if not square)."""
    V = len(pts)
    idx = {p: i for i, p in enumerate(pts)}

    def apply(fn):
        m = 0
        for i, p in enumerate(pts):
            if occ & (1 << i):
                q = fn(p)
                if q not in idx:
                    return None
                m |= 1 << idx[q]
        return m

    transforms = [
        lambda p: (p[0], p[1]),
        lambda p: (w - 1 - p[0], p[1]),
        lambda p: (p[0], h - 1 - p[1]),
        lambda p: (w - 1 - p[0], h - 1 - p[1]),
        lambda p: (p[1], p[0]),
        lambda p: (h - 1 - p[1], p[0]),
        lambda p: (p[1], w - 1 - p[0]),
        lambda p: (h - 1 - p[1], w - 1 - p[0]),
    ]
    orb = set()
    for fn in transforms:
        m = apply(fn)
        if m is not None:
            orb.add(m)
    return frozenset(orb)


def job_tol_sym(n: int, thr: int) -> None:
    """B229: as threshold rises, do high-symmetry max configs die first?"""
    pts = [(x, y) for y in range(n) for x in range(n)]
    V = n * n
    dets = []
    for ids in combinations(range(V), 4):
        p4 = [pts[i] for i in ids]
        d = det4(
            (p4[0][0] ** 2 + p4[0][1] ** 2, p4[0][0], p4[0][1], 1),
            (p4[1][0] ** 2 + p4[1][1] ** 2, p4[1][0], p4[1][1], 1),
            (p4[2][0] ** 2 + p4[2][1] ** 2, p4[2][0], p4[2][1], 1),
            (p4[3][0] ** 2 + p4[3][1] ** 2, p4[3][0], p4[3][1], 1),
        )
        dets.append((abs(d), ids))
    dets.sort()
    levels = {}
    for t in range(0, thr + 1):
        extra = [ids for ad, ids in dets if 0 < ad <= t]
        exact = [ids for ad, ids in dets if ad == 0]
        fam = exact + extra
        quads = []
        qbp = [[] for _ in range(V)]
        for ids in fam:
            m = 0
            for i in ids:
                m |= 1 << i
            quads.append(m)
            for i in ids:
                qbp[i].append(m)
        full = (1 << V) - 1

        def is_safe(occ: int) -> bool:
            for q in quads:
                if (occ & q) == q:
                    return False
            return True

        best = 0
        maxes: list[int] = []

        def dfs(occ, cand, size):
            nonlocal best, maxes
            if size > best:
                best = size
                maxes = [occ]
            elif size == best and not cand:
                maxes.append(occ)
            if not cand:
                return
            if size + cand.bit_count() < best:
                return
            while cand:
                bit = cand & -cand
                v = bit.bit_length() - 1
                cand ^= bit
                nxt = occ | bit
                ok = True
                for q in qbp[v]:
                    if (q & nxt) == q:
                        ok = False
                        break
                if not ok:
                    continue
                remain = cand
                bad = 0
                for q in qbp[v]:
                    if (q & nxt) != q and (q & ~nxt & full).bit_count() == 1:
                        bad |= q & ~nxt
                dfs(nxt, remain & ~bad, size + 1)

        dfs(0, full, 0)
        # symmetry of max configs: orbit size under D4
        orbits = []
        seen = set()
        for m in maxes:
            if m in seen:
                continue
            orb = _d4_orbit(n, n, m, pts)
            seen |= orb
            orbits.append(len(orb))
        # fixed points under some non-identity symmetry = higher symmetry
        # approximate: orbit size 1 or 2 is highly symmetric
        n_high = sum(1 for o in orbits if o <= 2)
        levels[str(t)] = {
            "n_extra_quads": len(extra),
            "n_quads": len(fam),
            "K": best,
            "n_max": len(maxes),
            "n_orbits": len(orbits),
            "orbit_sizes_hist": {
                str(k): orbits.count(k) for k in sorted(set(orbits))
            },
            "n_high_sym_orbits": n_high,
            "frac_high_sym_orbits": (n_high / len(orbits)) if orbits else None,
        }
        print(
            f"  thr={t} extra={len(extra)} K={best} nmax={len(maxes)} "
            f"orbits={len(orbits)} high={n_high}",
            flush=True,
        )
    save(
        f"tolsym_n{n}_thr{thr}",
        {"n": n, "levels": levels, "det_min_nonzero": dets[0][0] if dets else None},
    )


def job_subfam3(n: int) -> None:
    """B224: search 3-quad subfamilies reproducing standard W and g0."""
    from batch10_core import Game, first_move_labels, forbidden_quads, grundy_map

    quads = forbidden_quads(n)
    g = grundy_map(Game(n, quads), 0)
    W_std = sorted(
        p for p, lab in first_move_labels(Game(n, quads), g).items() if lab == "Win"
    )
    g0 = g[0]
    t0 = time.time()
    best = None
    # heuristic: only try quads that individually reduce |W| toward target
    # or contain losing-first-move points. Full C(57,3)=29260 is fine.
    nq = len(quads)
    tried = 0
    for i, j, k in combinations(range(nq), 3):
        fam = [quads[i], quads[j], quads[k]]
        gq = grundy_map(Game(n, fam), 0)
        Wq = sorted(
            p for p, lab in first_move_labels(Game(n, fam), gq).items() if lab == "Win"
        )
        tried += 1
        if Wq == W_std and gq[0] == g0:
            best = {
                "size": 3,
                "quads": [list(quads[i]), list(quads[j]), list(quads[k])],
                "W": Wq,
                "g0": gq[0],
                "index_tried_at": tried,
            }
            break
        if tried % 2000 == 0:
            print(f"  tried {tried} t={time.time()-t0:.1f}s", flush=True)
    save(
        f"subfam3_n{n}",
        {
            "n": n,
            "n_quads": nq,
            "W_std": W_std,
            "g0_std": g0,
            "tried": tried,
            "best": best,
            "seconds": round(time.time() - t0, 2),
        },
    )


def job_wchange_rect(w: int, h: int) -> None:
    """B206 helper: |W| change under 1-pt deletion on rectangle."""
    pts = pts_rect(w, h)
    base = Board(pts)
    g = base.solve_grundy()
    W0 = winning_first_moves(base, g)
    deg = [len(base.quads_by_pt[i]) for i in range(base.V)]
    rows = []
    for i, (x, y) in enumerate(pts):
        sub = [p for j, p in enumerate(pts) if j != i]
        b = Board(sub)
        gb = b.solve_grundy()
        W = winning_first_moves(b, gb)
        K = max(occ.bit_count() for occ in gb)
        rows.append(
            {
                "p": [x, y],
                "deg": deg[i],
                "g0": gb[0],
                "K": K,
                "Wsize": len(W),
                "W_delta": len(set(W) ^ set(W0)),
                "winner_changed": winner_from_g(gb[0]) != winner_from_g(g[0]),
            }
        )
    save(
        f"wchangerect_{w}x{h}",
        {
            "w": w,
            "h": h,
            "base_g0": g[0],
            "base_Wsize": len(W0),
            "base_K": max(occ.bit_count() for occ in g),
            "deg": deg,
            "rows": rows,
        },
    )
    # print corr deg vs W_delta
    import math

    def pearson(a, c):
        ma = sum(a) / len(a)
        mc = sum(c) / len(c)
        num = sum((x - ma) * (y - mc) for x, y in zip(a, c))
        da = sum((x - ma) ** 2 for x in a) ** 0.5
        dc = sum((y - mc) ** 2 for y in c) ** 0.5
        return num / (da * dc) if da and dc else 0.0

    print(
        f"  {w}x{h} corr(deg,W_delta)={pearson(deg, [r['W_delta'] for r in rows]):.3f}",
        flush=True,
    )


def job_period_chk() -> None:
    """B213: read rect3 data and fit period-k for g0 series."""
    p = OUTDIR / "round5_b201_rect3.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    boards = data["boards"]
    series = [(b["m"], b["g0"], b["winner"], b["K"], len(b["W"])) for b in boards]
    # test period k=2..6 for g0 from m=4
    fits = {}
    g0map = {m: g for m, g, *_ in series}
    ms = sorted(g0map)
    for k in range(2, 7):
        # check consistency of g0[m] == g0[m-k] for all m where both exist and m-k >= 4
        viol = []
        for m in ms:
            if m - k in g0map and m - k >= 4:
                if g0map[m] != g0map[m - k]:
                    viol.append([m, g0map[m], g0map[m - k]])
        fits[str(k)] = {"n_violations": len(viol), "violations": viol[:10]}
    save(
        "period_chk",
        {"series": series, "period_fits": fits, "source": "round5_b201_rect3.json"},
    )
    print(json.dumps(fits, indent=2), flush=True)


def main() -> None:
    job = sys.argv[1]
    if job == "del1rect":
        job_del1rect(int(sys.argv[2]), int(sys.argv[3]))
    elif job == "misere_rect":
        job_misere_rect(int(sys.argv[2]), int(sys.argv[3]))
    elif job == "maxcov_rect":
        job_maxcov_rect(int(sys.argv[2]), int(sys.argv[3]))
    elif job == "pairK_rect":
        job_pairK_rect(int(sys.argv[2]), int(sys.argv[3]))
    elif job == "tol_sym":
        job_tol_sym(int(sys.argv[2]), int(sys.argv[3]))
    elif job == "subfam3":
        job_subfam3(int(sys.argv[2]))
    elif job == "wchange_rect":
        job_wchange_rect(int(sys.argv[2]), int(sys.argv[3]))
    elif job == "period_chk":
        job_period_chk()
    else:
        print("unknown job", job)
        sys.exit(1)


if __name__ == "__main__":
    main()

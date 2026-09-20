#!/usr/bin/env python3
"""V2 LOSS proof-cost analysis: which LOSS child is cheap to prove?

Existing-data-only dissect of the 10x10 parent-benchmark failure
(median work ratio 1.84, improved 2/12). Replicates the solver's native
root ordering (legal_move_count, canonical key) in Python, verifies the
replication against observed root_first diagnostics, then answers:

  core Q: can we predict, pre-exact, which LOSS child is cheapest to prove?

Inputs (all frozen, no new solves):
  results/10x10/clean-holdout-v2/exact_task_list.csv
  results/10x10/clean-holdout-v2/exact_outcomes.csv
  results/10x10/clean-holdout-v2/independent_probe_10000.csv
  results/10x10/parent-benchmark/probe_rows.csv        (fresh B-order probes)
  results/10x10/parent-benchmark/root_orders/order_*.txt (B treatment order)
  results/10x10/parent-benchmark/parent_benchmark_raw.csv
  results/10x10/parent-benchmark/parent_benchmark_results.csv

Outputs:
  results/10x10/parent-benchmark/loss_proof_cost_dataset.csv  (P1)
  results/10x10/parent-benchmark/loss_proof_cost_summary.json  (P2-P9)
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from itertools import combinations
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
V2 = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
BENCH = REPO_ROOT / "results" / "10x10" / "parent-benchmark"

N = 10
V = N * N
MASK64 = (1 << 64) - 1

# Solver transform table (kyouen_solver_10_kyoenc4_resume_2.inc :: maps):
# nx[k], ny[k] for k = 0..7.
NX = [[0] * V for _ in range(8)]
NY = [[0] * V for _ in range(8)]
for _p in range(V):
    _x, _y = _p % N, _p // N
    _nxs = [_x, N - 1 - _x, _x, N - 1 - _x, _y, N - 1 - _y, _y, N - 1 - _y]
    _nys = [_y, _y, N - 1 - _y, N - 1 - _y, _x, _x, N - 1 - _x, N - 1 - _x]
    for _k in range(8):
        NX[_k][_p] = _nxs[_k]
        NY[_k][_p] = _nys[_k]


def cells(state: str) -> tuple[int, ...]:
    return tuple(sorted(int(x) for x in state.replace(",", "-").split("-") if x != ""))


def canonical_key(pts: tuple[int, ...]) -> tuple[int, int]:
    """(hi, lo) canonical key; tuple order matches Bits operator< (hi first)."""
    best: tuple[int, int] | None = None
    for k in range(8):
        lo = hi = 0
        for p in pts:
            q = NY[k][p] * N + NX[k][p]
            if q < 64:
                lo |= 1 << q
            else:
                hi |= 1 << (q - 64)
        key = (hi, lo)
        if best is None or key < best:
            best = key
    assert best is not None
    return best


XY = np.array([[p % N, p // N] for p in range(V)], dtype=np.int64)


def det4_for_triple(a: int, b: int, c: int) -> np.ndarray:
    """det(a,b,c,d) for all d in 0..99 (integer-exact via float64 + round)."""
    t = np.array([XY[a], XY[b], XY[c]], dtype=np.float64)  # 3x2
    f = np.concatenate([(t ** 2).sum(axis=1, keepdims=True), t,
                        np.ones((3, 1))], axis=1)  # 3x4 rows for a,b,c
    dxy = XY.astype(np.float64)  # 100x2
    g = np.concatenate([(dxy ** 2).sum(axis=1, keepdims=True), dxy,
                        np.ones((100, 1))], axis=1)  # 100x4 row for d
    m = np.empty((100, 4, 4))
    m[:, 1, :] = f[0]
    m[:, 2, :] = f[1]
    m[:, 3, :] = f[2]
    m[:, 0, :] = g
    # Laplace along row 0 (matches solver sign convention; only ==0 matters).
    dets = np.zeros(100)
    for col in range(4):
        keep = [j for j in range(4) if j != col]
        minor = m[:, 1:, :][:, :, keep]  # 100x3x3
        md = (minor[:, 0, 0] * (minor[:, 1, 1] * minor[:, 2, 2] - minor[:, 1, 2] * minor[:, 2, 1])
              - minor[:, 0, 1] * (minor[:, 1, 0] * minor[:, 2, 2] - minor[:, 1, 2] * minor[:, 2, 0])
              + minor[:, 0, 2] * (minor[:, 1, 0] * minor[:, 2, 1] - minor[:, 1, 1] * minor[:, 2, 0]))
        dets += ((-1) ** col) * m[:, 0, col] * md
    return np.rint(dets).astype(np.int64)


_COMP_CACHE: dict[tuple[int, int, int], frozenset[int]] = {}


def completion(a: int, b: int, c: int) -> frozenset[int]:
    """{d : {a,b,c,d} concyclic or collinear} (== solver completion_[idx])."""
    t = tuple(sorted((a, b, c)))
    hit = _COMP_CACHE.get(t)
    if hit is None:
        ds = np.nonzero(det4_for_triple(*t) == 0)[0]
        hit = frozenset(int(d) for d in ds) - set(t)
        _COMP_CACHE[t] = hit
    return hit


def banned_of(state: tuple[int, ...]) -> set[int]:
    out: set[int] = set()
    for a, b, c in combinations(sorted(state), 3):
        out |= set(completion(a, b, c))
    return out


def ranks_avg(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    if n < 2:
        return None
    ra, rb = ranks_avg(a), ranks_avg(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra)
    vb = sum((y - mb) ** 2 for y in rb)
    if va == 0 or vb == 0:
        return None
    return cov / math.sqrt(va * vb)


def kendall(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    if n < 2:
        return None
    con = dis = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = (a[i] - a[j]) * (b[i] - b[j])
            if s > 0:
                con += 1
            elif s < 0:
                dis += 1
    if con + dis == 0:
        return None
    return (con - dis) / (con + dis)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def key_str(hi: int, lo: int) -> str:
    return f"{hi:09x}{lo:016x}"


def main() -> None:
    tasks = load_csv(V2 / "exact_task_list.csv")
    exact = {(r["parent"].strip(), "-".join(map(str, cells(r["state"])))): r
             for r in load_csv(V2 / "exact_outcomes.csv")}
    probe10k = {(r["parent"].strip(), "-".join(map(str, cells(r["state"])))): r
                for r in load_csv(V2 / "independent_probe_10000.csv")}
    fresh = {(r["parent"].strip(), "-".join(map(str, cells(r["state"])))): r
             for r in load_csv(BENCH / "probe_rows.csv")}
    assert len(tasks) == 1136 == len(exact) == len(probe10k), \
        (len(tasks), len(exact), len(probe10k))
    assert len(fresh) == 1136, len(fresh)

    raw = {(r["parent"], r["strategy"]): r
           for r in load_csv(BENCH / "parent_benchmark_raw.csv")}
    bench = {r["parent"]: r for r in load_csv(BENCH / "parent_benchmark_results.csv")}
    parents = sorted({t["parent"].strip() for t in tasks})
    assert len(parents) == 12

    file_order: dict[str, list[str]] = {}
    for t in tasks:
        p = t["parent"].strip()
        file_order.setdefault(p, []).append("-".join(map(str, cells(t["state"]))))

    # ---- replicate native expansion per parent ----
    rep = {}  # parent -> {canon_key: info}
    verify_lines = []
    for p in parents:
        ppts = cells(p)
        assert len(ppts) == 3
        bpar = banned_of(ppts)
        kids: dict[tuple[int, int], dict] = {}
        for s in file_order[p]:
            cpts = cells(s)
            extra = set(cpts) - set(ppts)
            assert len(extra) == 1 and set(ppts) < set(cpts), (p, s)
            v = next(iter(extra))
            ck = canonical_key(cpts)
            # canonical representative for count computation
            e = kids.get(ck)
            if e is None:
                # recover canonical point set: min transform preimage
                best_pts: tuple[int, ...] | None = None
                best_k: tuple[int, int] | None = None
                for k in range(8):
                    lo = hi = 0
                    for q in cpts:
                        qq = NY[k][q] * N + NX[k][q]
                        if qq < 64:
                            lo |= 1 << qq
                        else:
                            hi |= 1 << (qq - 64)
                    cand = (hi, lo)
                    if best_k is None or cand < best_k:
                        best_k = cand
                        best_pts = tuple(sorted(NY[k][q] * N + NX[k][q] for q in cpts))
                assert best_pts is not None and best_k == ck
                bc = banned_of(best_pts)
                legal = (set(range(V)) - set(best_pts)) - bc
                kids[ck] = {
                    "count": len(legal),
                    "banned_child": len(bc),
                    "newly_banned": len(bc - bpar),
                    "canon_pts": best_pts,
                    "states": [],
                }
            kids[ck]["states"].append((s, v))
        # native unique order: (count, key)
        natorder = sorted(kids, key=lambda k: (kids[k]["count"], k))
        rep[p] = {"kids": kids, "natorder": natorder, "bpar": bpar}

        # verify vs A root_first
        a = raw[(p, "A")]
        first_nat = natorder[0]
        morate = (int(a["root_first_hi"]), int(a["root_first_lo"]))
        # canonical_key returns (hi, lo); raw stores lo/hi separately
        ok_a = (first_nat[0] == int(a["root_first_hi"])
                and first_nat[1] == int(a["root_first_lo"]))
        # verify vs B: order file first line canonical == B root_first
        of = BENCH / "root_orders" / f"order_{p.replace(',', '_')}.txt"
        lines = [ln.strip() for ln in of.read_text().splitlines() if ln.strip()]
        b = raw[(p, "B")]
        ck0 = canonical_key(cells(lines[0]))
        ok_b = (ck0[0] == int(b["root_first_hi"]) and ck0[1] == int(b["root_first_lo"]))
        # order-file unique-key order must be memo-asc/move-asc dedup
        seen: list[tuple[int, int]] = []
        for ln in lines:
            ck = canonical_key(cells(ln))
            if ck not in seen:
                seen.append(ck)
        ukeys = [canonical_key(cells(s)) for s in file_order[p]]
        assert len(lines) == len(file_order[p]), (p, len(lines))
        assert set(seen) == set(ukeys), p
        verify_lines.append({
            "parent": p, "native_first_ok": ok_a,
            "border_first_ok": ok_b, "n_unique": len(seen),
            "n_lines": len(lines),
            "a_entered": int(a["root_entered"]), "b_entered": int(b["root_entered"]),
        })
        rep[p]["border"] = seen  # B unique order (treatment)
        rep[p]["blines"] = lines

    n_verify_a = sum(1 for v in verify_lines if v["native_first_ok"])
    n_verify_b = sum(1 for v in verify_lines if v["border_first_ok"])
    print(f"replication check: native-first match {n_verify_a}/12, "
          f"B-order-first match {n_verify_b}/12")
    assert n_verify_a == 12 and n_verify_b == 12, verify_lines

    # ---- P1: LOSS conditional dataset ----
    ds_rows = []
    loss_by_parent: dict[str, list[tuple[int, int]]] = {}
    for p in parents:
        kids = rep[p]["kids"]
        natorder = rep[p]["natorder"]
        nat_rank = {k: i + 1 for i, k in enumerate(natorder)}
        border = rep[p]["border"]
        b_rank = {k: i + 1 for i, k in enumerate(border)}
        # canonical-key rank (key ascending)
        c_rank = {k: i + 1 for i, k in enumerate(sorted(kids))}
        # 10k memo per key: min over duplicate file states (frozen independent probe)
        for ck, info in kids.items():
            sts = info["states"]
            outs = {exact[(p, s)]["outcome"].strip().upper() for s, _ in sts}
            assert len(outs) == 1, (p, ck, outs)
            out = next(iter(outs))
            if out != "LOSS":
                continue
            ex_rows = [exact[(p, s)] for s, _ in sts]
            vis = min(int(r["visited"]) for r in ex_rows)
            pr_rows = [probe10k[(p, s)] for s, _ in sts]
            memo = min(int(r["memo"]) for r in pr_rows)
            mxd = max(int(r["maxdepth"]) for r in pr_rows)
            psec = max(float(r["seconds"]) for r in pr_rows)
            moves = sorted(v for _, v in sts)
            # cheap geometry features on canonical point set
            cp = info["canon_pts"]
            assert cp is not None
            cxy = [(q % N, q // N) for q in cp]
            dists = [math.dist(cxy[i], cxy[j])
                     for i in range(len(cxy)) for j in range(i + 1, len(cxy))]
            xs = [q[0] for q in cxy]
            ys = [q[1] for q in cxy]
            # response-set features: parent pairs x move (use first move id)
            v0 = moves[0]
            ab_sets = []
            for aa, bb in combinations(sorted(cells(p)), 2):
                ab_sets.append(set(completion(aa, bb, v0)))
            union = set().union(*ab_sets) if ab_sets else set()
            bpar = rep[p]["bpar"]
            raw_pair = sum(len(s) for s in ab_sets)
            ds_rows.append({
                "parent": p, "key": key_str(*ck),
                "n_dup": len(sts), "moves": ";".join(map(str, moves)),
                "move_id": v0,
                "exact_visited": vis,
                "exact_seconds": max(float(r["seconds"]) for r in ex_rows),
                "exact_memo": max(int(r["memo"]) for r in ex_rows),
                "exact_maxdepth": max(int(r["maxdepth"]) for r in ex_rows),
                "probe10k_memo": memo, "probe10k_maxdepth": mxd,
                "probe10k_seconds": psec,
                "legal_move_count": info["count"],
                "banned_child": info["banned_child"],
                "newly_banned": info["newly_banned"],
                "raw_pair_sum": raw_pair,
                "T_union_new": len(union - bpar),
                "E_union_old": len(union & bpar),
                "O_overlap": raw_pair - len(union),
                "move_cdist": round(abs((v0 % N) - 4.5) + abs((v0 // N) - 4.5), 3),
                "pairdist_mean": round(statistics.mean(dists), 4),
                "pairdist_min": round(min(dists), 4),
                "bbox_area": (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1),
                "n_rows": len(set(xs)), "n_cols": len(set(ys)),
                "native_rank": nat_rank[ck],
                "memo10k_rank": b_rank[ck],
                "canon_rank": c_rank[ck],
            })
            loss_by_parent.setdefault(p, []).append(ck)

    # within-parent normalized cost / percentile
    for p, cks in loss_by_parent.items():
        vs = sorted(ds_rows[i]["exact_visited"]
                    for i, r in enumerate(ds_rows) if r["parent"] == p)
        # map visited -> percentile rank within parent LOSS set
        for r in ds_rows:
            if r["parent"] != p:
                continue
            vv = r["exact_visited"]
            lo = sum(1 for x in vs if x < vv)
            eq = sum(1 for x in vs if x == vv)
            r["loss_cost_rank"] = lo + 1
            r["loss_cost_pct"] = round((lo + 0.5 * eq) / len(vs), 4)
            r["loss_cost_norm"] = round(vv / min(vs), 4)
            r["n_loss_in_parent"] = len(vs)

    with (BENCH / "loss_proof_cost_dataset.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ds_rows[0].keys()))
        w.writeheader()
        w.writerows(ds_rows)
    print(f"LOSS children: {len(ds_rows)} "
          f"(parents: {len(loss_by_parent)})")

    bykey = {(r["parent"], r["key"]): r for r in ds_rows}
    key_cost = {}  # (parent, key) -> (outcome, min independent-exact visited)
    for p in parents:
        for ck, info in rep[p]["kids"].items():
            outs = {exact[(p, s)]["outcome"].strip().upper()
                    for s, _ in info["states"]}
            assert len(outs) == 1, (p, ck, outs)
            vis = min(int(exact[(p, s)]["visited"]) for s, _ in info["states"])
            key_cost[(p, key_str(*ck))] = (next(iter(outs)), vis)

    # ---- P2: selected-LOSS cost comparison ----
    p2 = []
    for p in parents:
        cks = loss_by_parent.get(p, [])
        assert cks, p
        kids = rep[p]["kids"]
        # first LOSS in native unique order
        nat_loss = next(k for k in rep[p]["natorder"]
                        if (p, key_str(*k)) in bykey)
        b_loss = next(k for k in rep[p]["border"]
                      if (p, key_str(*k)) in bykey)
        rn, rb = bykey[(p, key_str(*nat_loss))], bykey[(p, key_str(*b_loss))]
        minv = min(bykey[(p, key_str(*k))]["exact_visited"] for k in cks)
        p2.append({
            "parent": p,
            "work_ratio": float(bench[p]["work_ratio"]),
            "exact_only_ratio": float(bench[p]["exact_only_visited_ratio"]),
            "a_entered": int(raw[(p, "A")]["root_entered"]),
            "b_entered": int(raw[(p, "B")]["root_entered"]),
            "n_loss": len(cks),
            "native_loss_visited": rn["exact_visited"],
            "native_loss_rank": rn["loss_cost_rank"],
            "native_loss_pct": rn["loss_cost_pct"],
            "native_over_min": round(rn["exact_visited"] / minv, 3),
            "memo10k_loss_visited": rb["exact_visited"],
            "memo10k_loss_rank": rb["loss_cost_rank"],
            "memo10k_loss_pct": rb["loss_cost_pct"],
            "memo10k_over_min": round(rb["exact_visited"] / minv, 3),
            "sel_loss_ratio_b_over_a": round(
                rb["exact_visited"] / rn["exact_visited"], 3),
            "oracle_visited": minv,
        })
    # ---- P6b: entered-prefix decomposition (WIN-prefix waste vs sel LOSS) ----
    # Independent-exact visited is a proxy (parent solves share memo), used
    # only to split each strategy's cost into WIN-prefix waste + selected LOSS.
    for r in p2:
        p = r["parent"]
        for strat, order in (("a", rep[p]["natorder"]), ("b", rep[p]["border"])):
            ent = r[f"{strat}_entered"]
            prefix = order[:ent]
            outs = [key_cost[(p, key_str(*k))] for k in prefix]
            pos = next(i + 1 for i, k in enumerate(order)
                       if key_cost[(p, key_str(*k))][0] == "LOSS")
            r[f"{strat}_first_loss_pos"] = pos
            r[f"{strat}_entered_ok"] = (pos == ent)
            r[f"{strat}_win_waste_proxy"] = sum(v for o, v in outs if o == "WIN")
            r[f"{strat}_sel_proxy"] = next(v for o, v in outs if o == "LOSS")
        a_tot = r["a_win_waste_proxy"] + r["a_sel_proxy"]
        b_tot = r["b_win_waste_proxy"] + r["b_sel_proxy"]
        r["proxy_ratio_b_over_a"] = round(b_tot / a_tot, 3) if a_tot else None

    # ---- P3/P5: correlations on LOSS set ----
    feats = ["legal_move_count", "probe10k_memo", "probe10k_maxdepth",
             "probe10k_seconds", "move_id", "canon_rank", "banned_child",
             "newly_banned", "raw_pair_sum", "T_union_new", "E_union_old",
             "O_overlap", "move_cdist", "pairdist_mean", "pairdist_min",
             "bbox_area", "n_rows", "n_cols"]
    cor_overall, cor_pooled, cor_medparent = {}, {}, {}
    for feat in feats:
        xa = [float(r[feat]) for r in ds_rows]
        ya = [float(r["exact_visited"]) for r in ds_rows]
        cor_overall[feat] = {"spearman": spearman(xa, ya),
                             "kendall": kendall(xa, ya)}
        # pooled within-parent ranks
        xr, yr = [], []
        per_parent = []
        for p in parents:
            pr = [r for r in ds_rows if r["parent"] == p]
            if len(pr) < 3:
                continue
            xf = [float(r[feat]) for r in pr]
            yf = [float(r["exact_visited"]) for r in pr]
            per_parent.append(spearman(xf, yf))
            # Demean within parent: undemeaned per-parent mean ranks differ
            # by parent size, reintroducing parent scale into the pool.
            rx, ry = ranks_avg(xf), ranks_avg(yf)
            mx, my = statistics.mean(rx), statistics.mean(ry)
            xr += [v - mx for v in rx]
            yr += [v - my for v in ry]
        per_parent = [v for v in per_parent if v is not None]
        cor_medparent[feat] = (statistics.median(per_parent)
                               if per_parent else None)
        cor_pooled[feat] = {"spearman": spearman(xr, yr),
                            "kendall": kendall(xr, yr)}

    # ---- P4: legal_move_count as proof-cost predictor ----
    p4 = []
    for p in parents:
        pr = sorted([r for r in ds_rows if r["parent"] == p],
                    key=lambda r: r["exact_visited"])
        cheapest = pr[0]
        bycount = sorted(pr, key=lambda r: (r["legal_move_count"], r["canon_rank"]))
        top1 = bycount[0]
        cov = {"parent": p,
               "cheapest_count": cheapest["legal_move_count"],
               "top1_iscoupled": top1["key"] == cheapest["key"],
               "top1_over_min": round(top1["exact_visited"] / cheapest["exact_visited"], 3)}
        for k in (3, 5):
            cov[f"top{k}_hits_min"] = any(
                r["key"] == cheapest["key"] for r in bycount[:k])
        p4.append(cov)
    # tie-break experiment on LOSS-only ordering:
    # (count,key) vs (count,memo10k,key): first-selected cost per parent
    tb = []
    for p in parents:
        pr = [r for r in ds_rows if r["parent"] == p]
        base = min(pr, key=lambda r: (r["legal_move_count"], r["canon_rank"]))
        plus = min(pr, key=lambda r: (r["legal_move_count"], r["probe10k_memo"],
                                      r["canon_rank"]))
        cheap = min(r["exact_visited"] for r in pr)
        tb.append({"parent": p, "base_sel": base["exact_visited"],
                   "plus_sel": plus["exact_visited"], "oracle": cheap,
                   "base_over": round(base["exact_visited"] / cheap, 3),
                   "plus_over": round(plus["exact_visited"] / cheap, 3)})

    # ---- P7: S1/S2 split ----
    s1 = [r for r in p2 if r["a_entered"] == 1 and r["b_entered"] == 1]
    s2 = [r for r in p2 if not (r["a_entered"] == 1 and r["b_entered"] == 1)]

    def gmean(xs: list[float]) -> float:
        return math.exp(statistics.mean(math.log(x) for x in xs))

    def grp(rs: list[dict]) -> dict:
        er = [r["exact_only_ratio"] for r in rs]
        return {"n": len(rs),
                "median_exact_only": statistics.median(er) if er else None,
                "gmean_exact_only": round(gmean(er), 3) if er else None,
                "improved": sum(1 for r in rs if r["work_ratio"] < 1),
                "worse": sum(1 for r in rs if r["work_ratio"] > 1),
                "median_sel_loss_ratio": statistics.median(
                    [r["sel_loss_ratio_b_over_a"] for r in rs]) if rs else None}

    # ---- P8: oracle gaps ----
    orc = []
    for r in p2:
        orc.append({"parent": r["parent"],
                    "native_over_oracle": r["native_over_min"],
                    "memo10k_over_oracle": r["memo10k_over_min"]})

    summary = {
        "n_loss_children": len(ds_rows),
        "n_parents": len(parents),
        "replication": {"native_first_match": n_verify_a,
                        "border_first_match": n_verify_b},
        "selected_loss": p2,
        "median_native_loss_rank": statistics.median(
            r["native_loss_rank"] for r in p2),
        "median_memo10k_loss_rank": statistics.median(
            r["memo10k_loss_rank"] for r in p2),
        "median_native_over_min": statistics.median(
            r["native_over_min"] for r in p2),
        "median_memo10k_over_min": statistics.median(
            r["memo10k_over_min"] for r in p2),
        "median_sel_loss_ratio_b_over_a": statistics.median(
            r["sel_loss_ratio_b_over_a"] for r in p2),
        "cor_overall": cor_overall,
        "cor_pooled_rank": cor_pooled,
        "cor_median_parent_spearman": cor_medparent,
        "legal_count": p4,
        "tiebreak": tb,
        "S1": {**grp(s1), "parents": [r["parent"] for r in s1]},
        "S2": {**grp(s2), "parents": [r["parent"] for r in s2]},
        "oracle": orc,
        "median_native_over_oracle": statistics.median(
            r["native_over_oracle"] for r in orc),
        "median_memo10k_over_oracle": statistics.median(
            r["memo10k_over_oracle"] for r in orc),
    }
    with (BENCH / "loss_proof_cost_summary.json").open("w") as f:
        json.dump(summary, f, indent=1)

    # ---- stdout report ----
    print("\n== P2 selected-LOSS cost ==")
    for r in sorted(p2, key=lambda r: r["work_ratio"]):
        print(f'{r["parent"]:>10} wr={r["work_ratio"]:.2f} '
              f'Aent={r["a_entered"]} Bent={r["b_entered"]} '
              f'nat#{r["native_loss_rank"]}/{r["n_loss"]} '
              f'x{r["native_over_min"]} B#{r["memo10k_loss_rank"]}/{r["n_loss"]} '
              f'x{r["memo10k_over_min"]} selB/A={r["sel_loss_ratio_b_over_a"]}')
    print("\n== P3/P5/P9 correlations (LOSS-only; overall | pooled-rank | med-parent) ==")
    for feat in feats:
        o, pl, mp = cor_overall[feat], cor_pooled[feat], cor_medparent[feat]
        f = lambda v: "n/a" if v is None else f"{v:+.3f}"
        print(f"{feat:>18} S overall {f(o['spearman'])} "
              f"pooled {f(pl['spearman'])} medParent {f(mp)} "
              f"K overall {f(o['kendall'])}")
    print("\n== P4 legal-count top-k ==")
    for c in p4:
        print(f'{c["parent"]:>10} top1==min {c["top1_iscoupled"]} '
              f'top1/min x{c["top1_over_min"]} top3 {c["top3_hits_min"]} '
              f'top5 {c["top5_hits_min"]}')
    print("\n== tie-break (count,key) vs (count,memo,key) first-selected/oracle ==")
    for t in tb:
        print(f'{t["parent"]:>10} base x{t["base_over"]} plus x{t["plus_over"]}')
    print("\n== P6b entered-prefix (proxy via independent exacts) ==")
    for r in sorted(p2, key=lambda r: r["work_ratio"]):
        print(f'{r["parent"]:>10} A:pos{r["a_first_loss_pos"]} '
              f'waste={r["a_win_waste_proxy"]} sel={r["a_sel_proxy"]} '
              f'B:pos{r["b_first_loss_pos"]} waste={r["b_win_waste_proxy"]} '
              f'sel={r["b_sel_proxy"]} proxyB/A={r["proxy_ratio_b_over_a"]} '
              f'exactOnly={r["exact_only_ratio"]:.2f} ok={r["a_entered_ok"]}/{r["b_entered_ok"]}')
    print(f'\n== P7 S1 {summary["S1"]} ==\n== P7 S2 {summary["S2"]} ==')
    print(f'== P8 oracle: native med x{summary["median_native_over_oracle"]}, '
          f'10k med x{summary["median_memo10k_over_oracle"]} ==')


if __name__ == "__main__":
    main()

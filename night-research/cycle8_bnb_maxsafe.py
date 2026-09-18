#!/usr/bin/env python3
"""Cycle 8 clean branch-and-bound for constrained max safe sets (n<=7).

Independent of cycle8_lib.max_safe_under.
Geometry: integer 4x4 det of [x^2+y^2,x,y,1].
Every run reports node count, constraint, and complete/incomplete.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import RES, corners, det4, load_n7, occupancy_vector, stones  # noqa: E402


def build_triples(n: int):
    v = n * n
    rows = [[x * x + y * y, x, y, 1] for y in range(n) for x in range(n)]
    triples = [[] for _ in range(v)]
    nq = 0
    for a in range(v - 3):
        for b in range(a + 1, v - 2):
            for c in range(b + 1, v - 1):
                for d in range(c + 1, v):
                    if det4([rows[a], rows[b], rows[c], rows[d]]) != 0:
                        continue
                    nq += 1
                    q = (1 << a) | (1 << b) | (1 << c) | (1 << d)
                    for t in (a, b, c, d):
                        triples[t].append(q & ~(1 << t))
    return triples, nq


def mask_of(pts) -> int:
    m = 0
    for p in pts:
        m |= 1 << p
    return m


def xy_list(mask: int, n: int):
    return [(p % n, p // n) for p in stones(mask, n * n)]


class ConstrainedMax:
    def __init__(
        self,
        n: int,
        forced: int = 0,
        forbidden: int = 0,
        corner_count: int | None = None,
        node_budget: int = 30_000_000,
        triples=None,
        n_quads: int | None = None,
    ):
        self.n = n
        self.v = n * n
        if triples is None:
            self.triples, self.n_quads = build_triples(n)
        else:
            self.triples = triples
            self.n_quads = n_quads if n_quads is not None else -1
        self.forced = forced
        self.forbidden = forbidden
        self.corner_count = corner_count
        self.corners = corners(n)
        self.node_budget = node_budget
        self.nodes = 0
        self.best_size = -1
        self.best_mask = 0
        self.best_count = 0
        self.exhausted = True
        self.reason = "ok"

    def _corners_used(self, mask: int) -> int:
        return sum(1 for p in self.corners if (mask >> p) & 1)

    def _init_forced(self):
        all_cells = (1 << self.v) - 1
        mask = 0
        ccount = [0] * self.v
        for u in stones(self.forced, self.v):
            if self.forbidden & (1 << u):
                return None, None, "forced cell forbidden"
            mask |= 1 << u
            for o in self.triples[u]:
                pc = bin(o & mask).count("1")
                if pc == 2:
                    wmask = o & ~mask & all_cells
                    if wmask == 0:
                        return None, None, "forced creates forbidden quad"
                    w = (wmask & -wmask).bit_length() - 1
                    ccount[w] += 1
        cand = all_cells & ~self.forbidden & ~mask
        for p in range(self.v):
            if ccount[p] > 0:
                cand &= ~(1 << p)
        return mask, ccount, "ok"

    def search(self) -> dict:
        t0 = time.time()
        if self.forced & self.forbidden:
            return self._result(t0, "forced∩forbidden")
        mask0, ccount, msg = self._init_forced()
        if mask0 is None:
            return self._result(t0, msg)
        all_cells = (1 << self.v) - 1
        cand0 = all_cells & ~self.forbidden & ~mask0
        for p in range(self.v):
            if ccount[p] > 0:
                cand0 &= ~(1 << p)

        def dfs(cand: int, count: int, mask: int, cc: list[int]) -> None:
            if not self.exhausted:
                return
            self.nodes += 1
            if self.nodes > self.node_budget:
                self.exhausted = False
                self.reason = "node_budget"
                return
            if self.corner_count is not None:
                if self._corners_used(mask) > self.corner_count:
                    return
            room = count + cand.bit_count()
            if room < self.best_size:
                return
            if cand == 0:
                if self.corner_count is not None and self._corners_used(mask) != self.corner_count:
                    return
                if count > self.best_size:
                    self.best_size = count
                    self.best_mask = mask
                    self.best_count = 1
                elif count == self.best_size:
                    self.best_count += 1
                return
            u = (cand & -cand).bit_length() - 1
            # branch: skip u
            dfs(cand & ~(1 << u), count, mask, cc)
            if not self.exhausted:
                return
            # branch: take u
            newcand = cand & ~(1 << u)
            undo = []
            ok = True
            for o in self.triples[u]:
                pc = bin(o & mask).count("1")
                if pc == 2:
                    wmask = o & ~mask & all_cells
                    if wmask == 0:
                        ok = False
                        break
                    w = (wmask & -wmask).bit_length() - 1
                    if cc[w] == 0:
                        newcand &= ~(1 << w)
                    cc[w] += 1
                    undo.append(w)
            if ok:
                dfs(newcand, count + 1, mask | (1 << u), cc)
            for w in undo:
                cc[w] -= 1

        dfs(cand0, mask0.bit_count(), mask0, ccount)
        return self._result(t0, self.reason)

    def _result(self, t0: float, reason: str) -> dict:
        status = "complete" if (self.exhausted and reason == "ok") else reason
        if self.exhausted and reason == "ok":
            status = "complete"
        elif not self.exhausted:
            status = f"incomplete:{self.reason}"
        else:
            status = f"failed:{reason}"
        return {
            "n": self.n,
            "forced_xy": xy_list(self.forced, self.n),
            "forbidden_xy": xy_list(self.forbidden, self.n),
            "corner_count": self.corner_count,
            "max_size": self.best_size,
            "n_attainers_at_max": self.best_count,
            "example_xy": xy_list(self.best_mask, self.n) if self.best_mask else None,
            "nodes": self.nodes,
            "status": status,
            "n_quads": self.n_quads,
            "seconds": round(time.time() - t0, 3),
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RES / "cycle8_b_conditional_max_bnb.json"))
    ap.add_argument("--mode", choices=["quick", "suite"], default="suite")
    args = ap.parse_args()

    n = 7
    n7 = load_n7()
    center = 24  # (3,3)
    o03 = [3, 6 * 7 + 3, 3 * 7 + 0, 3 * 7 + 6]  # (0,3),(6,3),(3,0),(3,6)
    o23 = [2 * 7 + 3, 4 * 7 + 3, 3 * 7 + 2, 3 * 7 + 4]
    o22 = [2 * 7 + 2, 4 * 7 + 2, 2 * 7 + 4, 4 * 7 + 4]
    triples, nq = build_triples(n)
    print(f"quads n={n}: {nq}", flush=True)

    # occupancy of 16 (complete)
    occ = []
    keys = None
    for i, s in enumerate(n7):
        ov = occupancy_vector(s, n)
        if keys is None:
            keys = sorted(ov.keys())
        occ.append({"id": i, "center": bool((s >> center) & 1),
                    "occ": {f"{k[0]},{k[1]}": ov[k] for k in keys},
                    "sum": sum(ov.values())})
    distinct = {}
    for row in occ:
        key = tuple(row["occ"][f"{k[0]},{k[1]}"] for k in keys)
        distinct.setdefault(key, []).append(row["id"])
    print("distinct occupancy vectors among 16:", len(distinct), flush=True)
    for k, ids in distinct.items():
        print(" ", k, "->", ids, flush=True)

    if args.mode == "quick":
        cases = [
            ("force_center", 1 << center, 0, None),
            ("forbid_center", 0, 1 << center, None),
            ("force_2_2", 1 << o22[0], 0, None),
        ]
    else:
        cases = [
            ("force_center", 1 << center, 0, None),
            ("forbid_center", 0, 1 << center, None),
            ("force_0_3", 1 << o03[0], 0, None),
            ("forbid_orbit_0_3", 0, mask_of(o03), None),
            ("force_2_3", 1 << o23[0], 0, None),
            ("forbid_orbit_2_3", 0, mask_of(o23), None),
            ("force_2_2", 1 << o22[0], 0, None),
            ("forbid_orbit_2_2", 0, mask_of(o22), None),
            ("force_center_and_0_3", 1 << center | 1 << o03[0], 0, None),
            ("force_center_and_2_3", 1 << center | 1 << o23[0], 0, None),
            ("force_0_3_forbid_center", 1 << o03[0], 1 << center, None),
            ("force_2_3_forbid_center", 1 << o23[0], 1 << center, None),
        ]
        for c in range(0, 5):
            cases.append((f"corners_eq_{c}", 0, 0, c))

    results = {
        "board": "7x7",
        "enumeration_basis": "complete n=7 K=14 list (16 sets) for occupancy; constrained BnB for conditional max",
        "occupancy_distinct": [
            {"vector": {f"{k[0]},{k[1]}": kk[i] for i, k in enumerate(keys)}, "ids": ids}
            for kk, ids in distinct.items()
        ],
        "cases": [],
    }
    for name, forced, forbidden, cc in cases:
        print(f"RUN {name} ...", flush=True)
        eng = ConstrainedMax(n, forced=forced, forbidden=forbidden, corner_count=cc,
                             node_budget=25_000_000, triples=triples, n_quads=nq)
        r = eng.search()
        r["case"] = name
        print(f"  -> max={r['max_size']} nodes={r['nodes']} {r['status']} {r['seconds']}s", flush=True)
        results["cases"].append(r)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

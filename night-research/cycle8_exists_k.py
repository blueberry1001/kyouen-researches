#!/usr/bin/env python3
"""Cycle 8: target-size existence search for constrained safe sets on n=7.

Complete-enumeration facts already give K7=14 with exactly 16 max sets.
This script independently answers: under constraint C, does a safe set of
size K exist? Sequential downward from an upper bound yields conditional max.

Method: same incremental conflict-counter DFS as maxsafe_enum.cpp, but
targeted at a fixed cardinality and with forced/forbidden/corner filters.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import RES, corners, det4, load_n7, stones  # noqa: E402


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


class TargetSearch:
    def __init__(self, n, triples, target, forced=0, forbidden=0,
                 corner_count=None, node_budget=20_000_000, stop_at_first=True):
        self.n = n
        self.v = n * n
        self.triples = triples
        self.target = target
        self.forced = forced
        self.forbidden = forbidden
        self.corner_count = corner_count
        self.corners = corners(n)
        self.node_budget = node_budget
        self.stop_at_first = stop_at_first
        self.nodes = 0
        self.found = []
        self.exhausted = True
        self.status = "ok"

    def run(self) -> dict:
        t0 = time.time()
        if self.forced.bit_count() > self.target:
            return self._res(t0, "forced_gt_target")
        if self.forced & self.forbidden:
            return self._res(t0, "forced_forbidden")
        all_cells = (1 << self.v) - 1
        mask = 0
        ccount = [0] * self.v
        for u in stones(self.forced, self.v):
            mask |= 1 << u
            for o in self.triples[u]:
                pc = bin(o & mask).count("1")
                if pc == 2:
                    return self._res(t0, "forced_unsafe")
                # will fill ccount after all forced placed
        # recompute ccount after full forced mask
        ccount = [0] * self.v
        for u in stones(self.forced, self.v):
            for o in self.triples[u]:
                if bin(o & mask).count("1") == 2:
                    wmask = o & ~mask
                    if wmask == 0:
                        return self._res(t0, "forced_unsafe")
                    w = (wmask & -wmask).bit_length() - 1
                    ccount[w] += 1
        if self.corner_count is not None:
            used = sum(1 for p in self.corners if (mask >> p) & 1)
            if used > self.corner_count:
                return self._res(t0, "too_many_corners")
        cand = all_cells & ~self.forbidden & ~mask
        for p in range(self.v):
            if ccount[p] > 0:
                cand &= ~(1 << p)

        def dfs(cand, count, mask, cc):
            if not self.exhausted:
                return
            self.nodes += 1
            if self.nodes > self.node_budget:
                self.exhausted = False
                self.status = "node_budget"
                return
            need = self.target - count
            if need == 0:
                if self.corner_count is not None:
                    used = sum(1 for p in self.corners if (mask >> p) & 1)
                    if used != self.corner_count:
                        return
                self.found.append(mask)
                if self.stop_at_first:
                    self.exhausted = False
                    self.status = "found"
                return
            if cand.bit_count() < need:
                return
            if self.corner_count is not None:
                used = sum(1 for p in self.corners if (mask >> p) & 1)
                # remaining corners available
                free_corners = sum(1 for p in self.corners if (cand >> p) & 1)
                if used + free_corners < self.corner_count:
                    return
            # branch on a candidate; use min-degree heuristic optionally later
            u = (cand & -cand).bit_length() - 1
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
            if not self.exhausted:
                return
            # skip u
            dfs(cand & ~(1 << u), count, mask, cc)

        dfs(cand, mask.bit_count(), mask, ccount)
        return self._res(t0, self.status)

    def _res(self, t0, status):
        if status == "found":
            final = "found"
            complete = True  # existence witness
        elif status == "node_budget":
            final = "incomplete"
            complete = False
        elif status == "ok":
            final = "unsat" if self.exhausted else "incomplete"
            complete = self.exhausted
        else:
            final = status
            complete = True
        return {
            "n": self.n,
            "target": self.target,
            "forced_xy": xy_list(self.forced, self.n),
            "forbidden_xy": xy_list(self.forbidden, self.n),
            "corner_count": self.corner_count,
            "result": final,
            "n_witnesses_seen": len(self.found),
            "example_xy": xy_list(self.found[0], self.n) if self.found else None,
            "nodes": self.nodes,
            "complete": complete,
            "status": status,
            "seconds": round(time.time() - t0, 3),
        }


def conditional_max(n, triples, forced=0, forbidden=0, corner_count=None,
                    upper=14, lower=0, node_budget=20_000_000):
    """Find max K in [lower, upper] with a witness, by downward target search."""
    history = []
    best = None
    for K in range(upper, lower - 1, -1):
        eng = TargetSearch(n, triples, K, forced=forced, forbidden=forbidden,
                           corner_count=corner_count, node_budget=node_budget,
                           stop_at_first=True)
        r = eng.run()
        r["K"] = K
        history.append(r)
        print(f"    K={K} -> {r['result']} nodes={r['nodes']} {r['seconds']}s", flush=True)
        if r["result"] == "found":
            best = K
            break
        if r["result"] == "incomplete":
            best = {"incomplete_at": K}
            break
    return {"max_size": best, "search_history": history}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RES / "cycle8_b_conditional_max.json"))
    ap.add_argument("--node-budget", type=int, default=20_000_000)
    args = ap.parse_args()

    n = 7
    n7 = load_n7()
    triples, nq = build_triples(n)
    print(f"quads={nq}", flush=True)

    center = 24
    o03 = [3, 45, 21, 47]  # (0,3),(6,3),(3,0),(3,6)
    # recompute carefully
    o03 = [0 * 7 + 3, 6 * 7 + 3, 3 * 7 + 0, 3 * 7 + 6]
    o23 = [2 * 7 + 3, 4 * 7 + 3, 3 * 7 + 2, 3 * 7 + 4]
    o22 = [2 * 7 + 2, 4 * 7 + 2, 2 * 7 + 4, 4 * 7 + 4]

    # lower bounds from known complete list
    def has(pred):
        return any(pred(s) for s in n7)

    lb = {
        "unconstrained": 14,
        "force_center": 14 if has(lambda s: s & (1 << center)) else None,
        "forbid_center": 14 if has(lambda s: not (s & (1 << center))) else None,
        "force_0_3": 14 if has(lambda s: s & (1 << o03[0])) else None,
        "force_2_3": 14 if has(lambda s: s & (1 << o23[0])) else None,
        "force_2_2": None,
        "force_center_and_0_3": None,
        "force_center_and_2_3": None,
    }

    specs = [
        ("force_center", 1 << center, 0, None, 14),
        ("forbid_center", 0, 1 << center, None, 14),
        ("force_0_3", 1 << o03[0], 0, None, 14),
        ("forbid_orbit_0_3", 0, mask_of(o03), None, 14),
        ("force_2_3", 1 << o23[0], 0, None, 14),
        ("forbid_orbit_2_3", 0, mask_of(o23), None, 14),
        # try K=14 first so UNSAT@14 is an independent certificate that max<=13
        ("force_2_2", 1 << o22[0], 0, None, 14),
        ("forbid_orbit_2_2", 0, mask_of(o22), None, 14),
        ("force_center_and_0_3", (1 << center) | (1 << o03[0]), 0, None, 14),
        ("force_center_and_2_3", (1 << center) | (1 << o23[0]), 0, None, 14),
        ("force_0_3_forbid_center", 1 << o03[0], 1 << center, None, 14),
        ("force_2_3_forbid_center", 1 << o23[0], 1 << center, None, 14),
    ]

    out = {
        "board": "7x7",
        "method": "downward target existence DFS (cycle8_exists_k.py)",
        "complete_enum_K14": {"count": 16, "note": "inherited from Cycle 6/7; used as upper bound and occupancy source"},
        "occupancy_vectors": None,
        "conditional": {},
    }

    # occupancy (complete, no search)
    from cycle8_lib import occupancy_vector

    keys = sorted(occupancy_vector(n7[0], 7).keys())
    vecs = {}
    for i, s in enumerate(n7):
        ov = occupancy_vector(s, 7)
        key = tuple(ov[k] for k in keys)
        vecs.setdefault(key, []).append(i)
    out["occupancy_vectors"] = {
        "keys_xy": list(keys),
        "distinct": [
            {"ids": ids, "vector": list(vec)} for vec, ids in vecs.items()
        ],
    }
    print("occupancy distinct", len(vecs), flush=True)

    for name, forced, forbidden, cc, upper in specs:
        print(f"CASE {name} upper={upper}", flush=True)
        # If complete enum already witnesses `upper`, we can skip the search
        # for the upper bound EXCEPT when we need independent UNSAT at upper.
        # Always run target at `upper` for independence, then walk down if needed.
        r = conditional_max(
            n, triples,
            forced=forced, forbidden=forbidden, corner_count=cc,
            upper=upper, lower=max(0, upper - 4),
            node_budget=args.node_budget,
        )
        out["conditional"][name] = r

    # corner counts: max under exactly c corners (search from 14 down)
    out["conditional"]["corners"] = {}
    for c in range(0, 5):
        print(f"CASE corners_eq_{c}", flush=True)
        # witness from complete list if any
        wits = [i for i, s in enumerate(n7)
                if sum(1 for p in corners(7) if (s >> p) & 1) == c]
        upper = 14 if wits else 13
        r = conditional_max(n, triples, corner_count=c, upper=upper,
                            lower=max(0, upper - 3), node_budget=args.node_budget)
        r["witness_ids_from_complete_K14"] = wits
        out["conditional"]["corners"][str(c)] = r

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Wrote", args.out)


if __name__ == "__main__":
    main()

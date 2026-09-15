#!/usr/bin/env python3
"""Derive O structural strata and required unique roots from the 8x8 population.

Outcome-free. Reads artifacts/8x8-factorial-population.csv and writes:
  - artifacts/8x8-o-strata.csv
  - artifacts/8x8-o-required-roots.csv
  - artifacts/8x8-o-stratum-manifest.json
Also prints shared-child dependence audit stats and writes
  - artifacts/8x8-o-shared-child-audit.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POP = ROOT / "artifacts" / "8x8-factorial-population.csv"
STRATA = ROOT / "artifacts" / "8x8-o-strata.csv"
ROOTS = ROOT / "artifacts" / "8x8-o-required-roots.csv"
MANIFEST = ROOT / "artifacts" / "8x8-o-stratum-manifest.json"
AUDIT = ROOT / "artifacts" / "8x8-o-shared-child-audit.json"


def parse_parent(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in text.split(","))


def d4_transforms(p: tuple[int, ...]) -> list[tuple[int, ...]]:
    n = 8
    nm1 = n - 1
    out = []
    for g in range(8):
        q = []
        for v in p:
            x, y = v % n, v // n
            if g == 0:
                nx, ny = x, y
            elif g == 1:
                nx, ny = nm1 - y, x
            elif g == 2:
                nx, ny = nm1 - x, nm1 - y
            elif g == 3:
                nx, ny = y, nm1 - x
            elif g == 4:
                nx, ny = nm1 - x, y
            elif g == 5:
                nx, ny = x, nm1 - y
            elif g == 6:
                nx, ny = y, x
            else:
                nx, ny = nm1 - y, nm1 - x
            q.append(ny * n + nx)
        out.append(tuple(sorted(q)))
    return out


def canonical_5(p4: tuple[int, ...], move: int) -> tuple[int, ...]:
    p5 = tuple(sorted(p4 + (move,)))
    return min(d4_transforms(p5))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(top_t: int, top_te: int, top_to: int, top_raw: int) -> str | None:
    o_e0 = top_t != top_to
    o_e1 = top_te != top_raw
    if o_e0 and not o_e1:
        return "O0-only"
    if o_e0 and o_e1:
        return "O-overlap"
    if (not o_e0) and o_e1:
        return "O1-only"
    return None


REQUIRED_MOVES = {
    "O0-only": ("top_T", "top_TO"),
    "O-overlap": ("top_T", "top_TO", "top_TE", "top_raw"),
    "O1-only": ("top_TE", "top_raw"),
}


def main() -> int:
    if not POP.exists():
        print(f"missing {POP}", file=sys.stderr)
        return 1

    rows = []
    with POP.open(newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            parent = r["canonical_parent"]
            top_t = int(r["top_T"])
            top_te = int(r["top_TE"])
            top_to = int(r["top_TO"])
            top_raw = int(r["top_raw"])
            stratum = classify(top_t, top_te, top_to, top_raw)
            if stratum is None:
                continue
            rows.append(
                {
                    "canonical_parent": parent,
                    "stratum": stratum,
                    "top_T": top_t,
                    "top_TE": top_te,
                    "top_TO": top_to,
                    "top_raw": top_raw,
                    "orbit_size": r.get("orbit_size", ""),
                    "distinct_top_moves": r.get("distinct_top_moves", ""),
                }
            )

    # Write strata CSV.
    STRATA.parent.mkdir(parents=True, exist_ok=True)
    with STRATA.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "canonical_parent",
                "stratum",
                "top_T",
                "top_TE",
                "top_TO",
                "top_raw",
                "orbit_size",
                "distinct_top_moves",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Required roots: (canonical_parent, move) union, then canonical 5-stone child.
    raw_instances = 0
    unique_pairs: dict[tuple[str, int], str] = {}
    for r in rows:
        for field in REQUIRED_MOVES[r["stratum"]]:
            mv = int(r[field])
            raw_instances += 1
            key = (r["canonical_parent"], mv)
            unique_pairs[key] = r["stratum"]

    # Canonical 5-stone states for shared-child audit.
    child_of_pair: dict[tuple[str, int], tuple[int, ...]] = {}
    child_to_parents: dict[tuple[int, ...], list[tuple[str, int]]] = defaultdict(list)
    for parent_text, mv in unique_pairs:
        p4 = parse_parent(parent_text)
        c5 = canonical_5(p4, mv)
        child_of_pair[(parent_text, mv)] = c5
        child_to_parents[c5].append((parent_text, mv))

    # Write required-roots CSV (parent,move). Child canonical is outcome-free metadata.
    ROOTS.parent.mkdir(parents=True, exist_ok=True)
    with ROOTS.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "canonical_parent",
                "move",
                "stratum",
                "canonical_child5",
            ]
        )
        for (parent_text, mv), stratum in sorted(
            unique_pairs.items(), key=lambda kv: (kv[0][0], kv[0][1])
        ):
            c5 = child_of_pair[(parent_text, mv)]
            w.writerow([parent_text, mv, stratum, ";".join(map(str, c5))])

    # Shared-child dependence audit.
    child_instances = len(unique_pairs)
    unique_children = len(child_to_parents)
    shared = {c: ps for c, ps in child_to_parents.items() if len(ps) > 1}
    max_share = max((len(ps) for ps in child_to_parents.values()), default=0)
    share_hist = Counter(len(ps) for ps in child_to_parents.values())

    # Connected components over parents linked by shared children.
    parent_adj: dict[str, set[str]] = defaultdict(set)
    for ps in child_to_parents.values():
        parents = [p for p, _ in ps]
        for i, a in enumerate(parents):
            for b in parents[i + 1 :]:
                if a != b:
                    parent_adj[a].add(b)
                    parent_adj[b].add(a)
    all_parents = {r["canonical_parent"] for r in rows}
    # Also include parents that have roots but maybe isolated.
    for p, _ in unique_pairs:
        all_parents.add(p)
    seen: set[str] = set()
    comps: list[list[str]] = []
    for p in sorted(all_parents):
        if p in seen:
            continue
        stack = [p]
        seen.add(p)
        comp = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in parent_adj.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        comps.append(comp)
    comp_sizes = Counter(len(c) for c in comps)

    # Per-stratum root counts.
    stratum_counts = Counter(r["stratum"] for r in rows)
    stratum_raw_roots = Counter()
    stratum_unique_pairs = Counter()
    for r in rows:
        for field in REQUIRED_MOVES[r["stratum"]]:
            stratum_raw_roots[r["stratum"]] += 1
    for (parent_text, mv), stratum in unique_pairs.items():
        stratum_unique_pairs[stratum] += 1

    manifest = {
        "population_file": str(POP.relative_to(ROOT)),
        "population_sha256": sha256_file(POP),
        "population_d4_orbits": 2340,  # filled from log below if needed
        "stratum_counts": dict(stratum_counts),
        "O0_only_n": stratum_counts.get("O0-only", 0),
        "O_overlap_n": stratum_counts.get("O-overlap", 0),
        "O1_only_n": stratum_counts.get("O1-only", 0),
        "raw_root_instances": raw_instances,
        "unique_root_count": len(unique_pairs),
        "dedup_rate": (
            1.0 - (len(unique_pairs) / raw_instances) if raw_instances else 0.0
        ),
        "parent_count_with_roots": len({p for p, _ in unique_pairs}),
        "stratum_raw_roots": dict(stratum_raw_roots),
        "stratum_unique_pairs": dict(stratum_unique_pairs),
        "success_criterion": {
            "primary": "Δ_O(O0-only) > 0 AND Δ_O(O0-only) - Δ_O(O-overlap) >= 0.05",
            "threshold_gap": 0.05,
            "encoding": {"LOSS": 1, "WIN": 0},
            "O_effect_E0": "y01 - y00 where y00=outcome(top_T), y01=outcome(top_TO)",
        },
    }

    # Fix population orbit count from CSV.
    with POP.open(newline="") as f:
        manifest["population_d4_orbits"] = sum(1 for _ in csv.DictReader(f))

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")

    audit = {
        "child_instances": child_instances,
        "unique_child_states": unique_children,
        "shared_child_count": len(shared),
        "max_shared_degree": max_share,
        "share_degree_histogram": {str(k): v for k, v in sorted(share_hist.items())},
        "connected_component_count": len(comps),
        "component_size_histogram": {
            str(k): v for k, v in sorted(comp_sizes.items())
        },
        "max_component_size": max((len(c) for c in comps), default=0),
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n")

    print(json.dumps(manifest, indent=2))
    print("--- shared-child audit ---")
    print(json.dumps(audit, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

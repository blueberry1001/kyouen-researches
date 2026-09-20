#!/usr/bin/env python3
"""Geometry-only deterministic sampling for AB staged-V3 root-order holdout.

No child outcomes or game values are inspected. Excludes every 3-stone
state referenced in git history at HEAD (includes V1/V2/V3 and any prior
benchmark/tuning/counterexample work). Independent seed from V3.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED = "kyouen-10x10-ab-staged-v3-root-seed-20260913"
OUT_DIR = REPO_ROOT / "results" / "10x10" / "ab-staged-v3-root"
CHILDREN_DIR = OUT_DIR / "children"
PRIMARY_SAMPLE_SIZE = 16


def d4_point(p: int, k: int, n: int = 10) -> int:
    x, y = p % n, p // n
    xy = [
        (x, y), (n - 1 - x, y), (x, n - 1 - y), (n - 1 - x, n - 1 - y),
        (y, x), (n - 1 - y, x), (y, n - 1 - x), (n - 1 - y, n - 1 - x),
    ][k]
    return xy[1] * n + xy[0]


def canonical_3(pts: tuple[int, int, int]) -> tuple[int, int, int]:
    best = pts
    for k in range(1, 8):
        cand = tuple(sorted((d4_point(pts[0], k), d4_point(pts[1], k), d4_point(pts[2], k))))
        if cand < best:
            best = cand
    return best


def enumerate_all_canonical_3() -> list[tuple[int, int, int]]:
    canonical_set: set[tuple[int, int, int]] = set()
    for p1 in range(100):
        for p2 in range(p1 + 1, 100):
            for p3 in range(p2 + 1, 100):
                canonical_set.add(canonical_3((p1, p2, p3)))
    return sorted(canonical_set)


def add_spelled(excluded: set[tuple[int, int, int]], a: str, b: str, c: str) -> None:
    pts = tuple(sorted((int(a), int(b), int(c))))
    if len(set(pts)) == 3 and all(0 <= x < 100 for x in pts):
        excluded.add(canonical_3(pts))


def collect_exclusion_list() -> set[tuple[int, int, int]]:
    excluded: set[tuple[int, int, int]] = set()
    res = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    files = [f for f in res.stdout.splitlines() if f.endswith((".csv", ".txt", ".json", ".md"))]
    for fpath in files:
        if not ("10x10" in fpath or "probe" in fpath or "holdout" in fpath or "benchmark" in fpath):
            continue
        p = subprocess.run(
            ["git", "show", f"HEAD:{fpath}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if p.returncode != 0:
            continue
        for m in re.findall(r"\b(\d{1,2})[,\-](\d{1,2})[,\-](\d{1,2})\b", p.stdout):
            add_spelled(excluded, m[0], m[1], m[2])

    explicit = [
        REPO_ROOT / "results" / "10x10" / "clean-holdout-v2" / "holdout_v2_parents_primary.csv",
        REPO_ROOT / "results" / "10x10" / "holdout-parent-selection-preregistered.csv",
        REPO_ROOT / "results" / "10x10" / "clean-holdout-v2" / "sampling_manifest.json",
        REPO_ROOT / "results" / "10x10" / "parent-benchmark" / "protocol.json",
        REPO_ROOT / "results" / "10x10" / "staged-v3-holdout" / "holdout_v3_parents_primary.csv",
        REPO_ROOT / "results" / "10x10" / "staged-v3-holdout" / "sampling_manifest.json",
    ]
    for path in explicit:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.findall(r"\b(\d{1,2})[,\-](\d{1,2})[,\-](\d{1,2})\b", text):
            add_spelled(excluded, m[0], m[1], m[2])
    return excluded


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CHILDREN_DIR.mkdir(parents=True, exist_ok=True)

    print("Step 1: Enumerating D4-canonical 3-stone states...")
    universe = enumerate_all_canonical_3()
    print(f"Universe size: {len(universe)}")

    print("Step 2: Collecting exclusion list from git history + explicit lists...")
    exclusion_set = collect_exclusion_list()
    print(f"Excluded canonical parents: {len(exclusion_set)}")

    clean_universe = [p for p in universe if p not in exclusion_set]
    print(f"Clean universe size: {len(clean_universe)}")

    ex_path = OUT_DIR / "ab_exclusion_list.csv"
    with ex_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["parent_canonical"])
        for p in sorted(exclusion_set):
            w.writerow([f"{p[0]},{p[1]},{p[2]}"])

    ranked = []
    for p in clean_universe:
        p_str = f"{p[0]},{p[1]},{p[2]}"
        h = hashlib.sha256(f"{SEED}:{p_str}".encode("utf-8")).hexdigest()
        ranked.append((h, p_str))
    ranked.sort(key=lambda x: x[0])
    primary = ranked[:PRIMARY_SAMPLE_SIZE]

    primary_path = OUT_DIR / "ab_parents_primary.csv"
    with primary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "sha256_hash", "parent_canonical"])
        for r_idx, (h, p_str) in enumerate(primary, start=1):
            w.writerow([r_idx, h, p_str])

    manifest = {
        "seed": SEED,
        "universe_size": len(universe),
        "excluded_count": len(exclusion_set),
        "clean_universe_size": len(clean_universe),
        "primary_sample_size": PRIMARY_SAMPLE_SIZE,
        "primary_parents": [p_str for _, p_str in primary],
        "selection_rule": "SHA256(seed:canonical_parent) ascending on clean universe; no outcomes inspected",
        "excludes": "all 3-stone states referenced in git history at HEAD plus explicit V1/V2/V3 lists",
    }
    (OUT_DIR / "sampling_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Sampled {len(primary)} parents:")
    for r_idx, (h, p_str) in enumerate(primary, start=1):
        print(f"  [{r_idx:2d}] {p_str:<12} hash={h[:16]}...")
    print(f"Wrote artifacts to {OUT_DIR}")


if __name__ == "__main__":
    main()

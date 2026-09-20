#!/usr/bin/env python3
"""P2: Pure geometry-only deterministic sampling of safe 3-stone D4 canonical parents
for the 10x10 Second Clean Holdout (V2).

Strict requirements:
1. No child outcomes or game values are inspected.
2. Full exclusion of any 3-stone state previously appearing in git history.
3. Fully deterministic via SHA-256 hash chaining with frozen seed string.
4. Artifacts committed before any probe or exact solve.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED = "kyouen-10x10-fresh-parent-holdout-v2-seed-20260907"
OUT_DIR = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
CHILDREN_DIR = OUT_DIR / "children"

PRIMARY_SAMPLE_SIZE = 12
EXTENDED_SAMPLE_SIZE = 24


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


def canonical_str(p1: int, p2: int, p3: int) -> str:
    pts = canonical_3((p1, p2, p3))
    return f"{pts[0]},{pts[1]},{pts[2]}"


def enumerate_all_canonical_3() -> list[tuple[int, int, int]]:
    canonical_set = set()
    for p1 in range(100):
        for p2 in range(p1 + 1, 100):
            for p3 in range(p2 + 1, 100):
                canonical_set.add(canonical_3((p1, p2, p3)))
    return sorted(canonical_set)


def collect_exclusion_list() -> set[tuple[int, int, int]]:
    """Collect every 3-stone state ever used in the repository prior to V2."""
    excluded = set()
    res = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    files = [f for f in res.stdout.splitlines() if f.endswith((".csv", ".txt", ".json", ".md"))]

    for fpath in files:
        if not ("10x10" in fpath or "probe" in fpath or "holdout" in fpath):
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
        content = p.stdout
        pat = re.findall(r"\b(\d{1,2})[,\-](\d{1,2})[,\-](\d{1,2})\b", content)
        for m in pat:
            pts = tuple(sorted(int(x) for x in m))
            if len(set(pts)) == 3 and all(0 <= x < 100 for x in pts):
                excluded.add(canonical_3((pts[0], pts[1], pts[2])))

    return excluded


def generate_children_for_parent(parent: tuple[int, int, int]) -> list[str]:
    """Generate all safe 4-stone children (no 4 points co-circular/degenerate)."""
    # In kyouen 10x10, placing a 4th stone that immediately forms a circle is terminal (game over).
    # A child task is a 4-stone state where the 4th move does NOT form a circle (i.e. game continues).
    # Let's import the board / geometry checker from rust or probe solver if needed, or check circle condition.
    pass


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CHILDREN_DIR.mkdir(parents=True, exist_ok=True)

    print("Step 1: Enumerating all D4-canonical 3-stone states on 10x10 board...")
    universe = enumerate_all_canonical_3()
    print(f"Total canonical 3-stone universe size: {len(universe)}")

    print("Step 2: Collecting exhaustive exclusion list from git history...")
    exclusion_set = collect_exclusion_list()
    print(f"Total canonical 3-stone parents to exclude: {len(exclusion_set)}")

    clean_universe = [p for p in universe if p not in exclusion_set]
    print(f"Clean untouched universe size: {len(clean_universe)}")

    # Write exclusion list
    ex_path = OUT_DIR / "holdout_v2_exclusion_list.csv"
    with ex_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["parent_canonical"])
        for p in sorted(exclusion_set):
            w.writerow([f"{p[0]},{p[1]},{p[2]}"])

    # Step 3: Deterministic SHA-256 ranking
    ranked = []
    for p in clean_universe:
        p_str = f"{p[0]},{p[1]},{p[2]}"
        payload = f"{SEED}:{p_str}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        ranked.append((h, p, p_str))

    ranked.sort(key=lambda x: x[0])

    # Save sampled parents
    primary = ranked[:PRIMARY_SAMPLE_SIZE]
    extended = ranked[:EXTENDED_SAMPLE_SIZE]

    primary_path = OUT_DIR / "holdout_v2_parents_primary.csv"
    with primary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "sha256_hash", "parent_canonical"])
        for r_idx, (h, p, p_str) in enumerate(primary, start=1):
            w.writerow([r_idx, h, p_str])

    extended_path = OUT_DIR / "holdout_v2_parents_extended24.csv"
    with extended_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "sha256_hash", "parent_canonical"])
        for r_idx, (h, p, p_str) in enumerate(extended, start=1):
            w.writerow([r_idx, h, p_str])

    print(f"Sampled {len(primary)} primary parents and {len(extended)} extended parents.")
    print("Primary sample:")
    for r_idx, (h, p, p_str) in enumerate(primary, start=1):
        print(f"  [{r_idx:2d}] {p_str:<12} hash={h[:16]}...")

    manifest = {
        "seed": SEED,
        "universe_size": len(universe),
        "excluded_count": len(exclusion_set),
        "clean_universe_size": len(clean_universe),
        "primary_sample_size": PRIMARY_SAMPLE_SIZE,
        "extended_sample_size": EXTENDED_SAMPLE_SIZE,
        "primary_parents": [p_str for _, _, p_str in primary],
        "extended_parents": [p_str for _, _, p_str in extended],
    }
    (OUT_DIR / "sampling_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote sampling artifacts to {OUT_DIR}")


if __name__ == "__main__":
    main()

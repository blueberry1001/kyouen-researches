#!/usr/bin/env python3
"""Geometry-only stratified sampling for the F-E R-external 4-stone holdout.

Never reads outcome labels to build the cohort. Labels appear only as an
exclusion source (previously observed canonical keys).
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
N = 10
POINTS = N * N
R = frozenset({90, 61, 2, 73, 69, 66, 13, 91})
SEED = "kyouen-10x10-f-e-r-external-holdout-seed-20260922"
BASELINE = "224f0dae89f95bfafa20290e872d96b9567dc6d7"
PER_STRATUM = 12
OUT_DIR = ROOT / "results" / "10x10" / "f-e-r-external-holdout"
PREREG_REL = "docs/10X10_F_E_R_EXTERNAL_HOLDOUT_PREREG.md"


def d4_point(p: int, k: int) -> int:
    x, y = p % N, p // N
    xy = [
        (x, y), (N - 1 - x, y), (x, N - 1 - y), (N - 1 - x, N - 1 - y),
        (y, x), (N - 1 - y, x), (y, N - 1 - x), (N - 1 - y, N - 1 - x),
    ][k]
    return xy[1] * N + xy[0]


def canonical(pts) -> tuple[int, int, int, int]:
    best = None
    for k in range(8):
        cand = tuple(sorted(d4_point(p, k) for p in pts))
        if best is None or cand < best:
            best = cand
    return best


def canonical_key(pts) -> str:
    return ",".join(str(x) for x in canonical(pts))


def det3_batch(m: np.ndarray) -> np.ndarray:
    return (
        m[:, 0, 0] * (m[:, 1, 1] * m[:, 2, 2] - m[:, 1, 2] * m[:, 2, 1])
        - m[:, 0, 1] * (m[:, 1, 0] * m[:, 2, 2] - m[:, 1, 2] * m[:, 2, 0])
        + m[:, 0, 2] * (m[:, 1, 0] * m[:, 2, 1] - m[:, 1, 1] * m[:, 2, 0])
    )


def det4_batch(m: np.ndarray) -> np.ndarray:
    return (
        m[:, 0, 0] * det3_batch(m[:, 1:, 1:])
        - m[:, 0, 1] * det3_batch(m[:, [1, 2, 3]][:, :, [0, 2, 3]])
        + m[:, 0, 2] * det3_batch(m[:, [1, 2, 3]][:, :, [0, 1, 3]])
        - m[:, 0, 3] * det3_batch(m[:, 1:, :3])
    )


def dangerous_counts() -> tuple[np.ndarray, set[tuple[int, int, int, int]]]:
    counts = np.zeros(POINTS, dtype=np.int64)
    dangerous = set()
    chunk_size = 50_000
    chunk: list[tuple[int, int, int, int]] = []

    def consume(items: list[tuple[int, int, int, int]]) -> None:
        if not items:
            return
        c = np.asarray(items, dtype=np.int64)
        x = c % N
        y = c // N
        a = np.empty((len(c), 4, 4), dtype=np.int64)
        a[:, :, 0] = x * x + y * y
        a[:, :, 1] = x
        a[:, :, 2] = y
        a[:, :, 3] = 1
        bad = det4_batch(a) == 0
        if bad.any():
            np.add.at(counts, c[bad], 1)
            for row in c[bad]:
                dangerous.add((int(row[0]), int(row[1]), int(row[2]), int(row[3])))

    for quad in itertools.combinations(range(POINTS), 4):
        chunk.append(quad)
        if len(chunk) == chunk_size:
            consume(chunk)
            chunk.clear()
    consume(chunk)
    return counts, dangerous


STATE_RE = re.compile(r"\b(\d{1,2})[,:\-](\d{1,2})[,:\-](\d{1,2})[,:\-](\d{1,2})\b")


def add_state_from_match(m: re.Match, excluded: set[str]) -> None:
    pts = tuple(int(x) for x in m.groups())
    if len(set(pts)) != 4 or any(p < 0 or p >= POINTS for p in pts):
        return
    excluded.add(canonical_key(pts))


def collect_exclusions() -> set[str]:
    excluded: set[str] = set()

    for quad in itertools.combinations(sorted(R), 4):
        excluded.add(canonical_key(quad))

    for path in (
        ROOT / "results" / "10x10" / "four-stone-subsets-of-medium-loss.csv",
        ROOT / "results" / "10x10" / "five-stone-subsets-of-medium-loss.csv",
        ROOT / "results" / "10x10" / "six-stone-subsets-of-medium-loss.csv",
        ROOT / "results" / "10x10" / "three-stone-subsets-of-medium-loss.csv",
        ROOT / "results" / "10x10" / "two-stone-61-66-child-proof.csv",
        ROOT / "results" / "10x10" / "two-stone-90-61-child-proof.csv",
        ROOT / "results" / "10x10" / "two-stone-90-66-child-proof.csv",
        ROOT / "results" / "10x10" / "three-stone-9-10-30-child-proof.csv",
        ROOT / "results" / "10x10" / "four-stone-loss-proof-61-73-66-13.csv",
        ROOT / "results" / "10x10" / "five-stone-loss-proof-61-2-73-13-91.csv",
        ROOT / "results" / "10x10" / "six-stone-loss-proof-90-61-2-73-69-66.csv",
    ):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in STATE_RE.finditer(text):
            add_state_from_match(m, excluded)

    cache_candidates = [
        ROOT / "scratch" / "kyouen-local-handoff" / "outcome-cache.json",
        Path(
            r"D:\ghq\github.com\yuubinnkyoku\kyouen-1-to-9-classification"
            r"\.slim\worktrees\research-properties\scratch\kyouen-local-handoff\outcome-cache.json"
        ),
        Path(
            r"D:\ghq\github.com\yuubinnkyoku\kyouen-1-to-9-classification"
            r"\scratch\kyouen-local-handoff\outcome-cache.json"
        ),
    ]
    for cache_path in cache_candidates:
        if not cache_path.exists():
            continue
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for key in cache:
            parts = key.split(",")
            if len(parts) >= 4:
                for quad in itertools.combinations(sorted(int(x) for x in parts), 4):
                    excluded.add(canonical_key(quad))
            if len(parts) == 4 and all(0 <= int(x) < POINTS for x in parts):
                excluded.add(canonical_key(tuple(int(x) for x in parts)))

    # git history scan on this baseline tree only (committed files)
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    files = [
        f
        for f in proc.stdout.splitlines()
        if f.endswith((".csv", ".json", ".md", ".txt"))
        and any(tok in f for tok in ("10x10", "results", "artifacts", "docs"))
    ]
    for fpath in files:
        show = subprocess.run(
            ["git", "show", f"HEAD:{fpath}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        text = show.stdout.decode("utf-8", errors="replace") if show.stdout else ""
        if show.returncode != 0 or not text:
            continue
        for m in STATE_RE.finditer(text):
            add_state_from_match(m, excluded)

    for doc in (ROOT / "docs").glob("10X10_*.md"):
        text = doc.read_text(encoding="utf-8", errors="replace")
        for m in STATE_RE.finditer(text):
            add_state_from_match(m, excluded)

    return excluded


def build_universe(
    d: np.ndarray,
    excluded: set[str],
    dangerous: set[tuple[int, int, int, int]],
):
    universe = {}
    for pts in itertools.combinations(range(POINTS), 4):
        if set(pts) <= R:
            continue
        if pts in dangerous:
            continue
        key = canonical_key(pts)
        if key in excluded:
            continue
        sigma = int(sum(int(d[p]) for p in pts))
        universe[key] = (key, key, sigma)
    rows = list(universe.values())
    rows.sort(key=lambda x: x[0])
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    d, dangerous = dangerous_counts()
    anchors = {90: 1515, 61: 2289, 2: 1927, 73: 2395, 69: 2080, 66: 2499, 13: 2289, 91: 1730}
    for p, val in anchors.items():
        if int(d[p]) != val:
            raise SystemExit(f"d({p})={int(d[p])} != anchor {val}")

    np.save(OUT_DIR / "d_per_point.npy", d)
    print(f"dangerous quadruples: {len(dangerous)} (expect 54441)", flush=True)
    if len(dangerous) != 54441:
        print("WARNING: dangerous count differs from known 54441", flush=True)

    excluded = collect_exclusions()
    print(f"excluded canonical keys: {len(excluded)}", flush=True)

    universe = build_universe(d, excluded, dangerous)
    print(f"clean R-external safe canonical 4-stone universe: {len(universe)}", flush=True)
    if len(universe) < PER_STRATUM * 3:
        raise SystemExit("universe too small for stratified holdout")

    sigmas = np.array([u[2] for u in universe], dtype=np.int64)
    q1 = int(np.percentile(sigmas, 33))
    q2 = int(np.percentile(sigmas, 67))
    print(f"Σd tertile cutpoints: low<={q1}  middle<={q2}  high>{q2}", flush=True)

    strata = {"low": [], "middle": [], "high": []}
    for key, raw, sigma in universe:
        if sigma <= q1:
            st = "low"
        elif sigma <= q2:
            st = "middle"
        else:
            st = "high"
        payload = f"{SEED}:{key}".encode("utf-8")
        h = hashlib.sha256(payload).hexdigest()
        strata[st].append(
            {
                "stratum": st,
                "canonical_key": key,
                "raw_state": key,
                "sigma_d": sigma,
                "hash": h,
                "seed": SEED,
                "baseline_commit": BASELINE,
            }
        )

    for st in strata:
        strata[st].sort(key=lambda r: r["hash"])

    sample = []
    idx = 1
    for st in ("low", "middle", "high"):
        for row in strata[st][:PER_STRATUM]:
            row = dict(row)
            row["index"] = idx
            row["canonical_key"] = row["canonical_key"]
            row["raw_state"] = row["raw_state"]
            sample.append(row)
            idx += 1

    fields = [
        "index",
        "stratum",
        "canonical_key",
        "raw_state",
        "sigma_d",
        "hash",
        "seed",
        "baseline_commit",
    ]
    manifest_path = OUT_DIR / "sampling_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in sample:
            w.writerow({k: row[k] for k in fields})

    summary = {
        "prereg": PREREG_REL,
        "seed": SEED,
        "baseline_commit": BASELINE,
        "r_points": sorted(R),
        "excluded_canonical_keys": len(excluded),
        "clean_universe_size": len(universe),
        "sigma_tertiles": {"q33": q1, "q67": q2},
        "stratum_universe_sizes": {k: len(v) for k, v in strata.items()},
        "per_stratum_sample": PER_STRATUM,
        "sample_size": len(sample),
        "labels_used_for_sampling": False,
        "sample": [
            {
                "index": r["index"],
                "stratum": r["stratum"],
                "canonical_key": r["canonical_key"],
                "sigma_d": r["sigma_d"],
                "hash": r["hash"],
            }
            for r in sample
        ],
    }
    (OUT_DIR / "sampling_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"wrote {manifest_path}")
    print(f"sample size={len(sample)}")
    for r in sample:
        print(
            f"  [{r['index']:02d}] {r['stratum']:<6} "
            f"{r['raw_state']:<14} Σd={r['sigma_d']:<5} {r['hash'][:12]}"
        )


if __name__ == "__main__":
    main()

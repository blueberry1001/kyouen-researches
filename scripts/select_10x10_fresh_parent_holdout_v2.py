#!/usr/bin/env python3
"""Select the preregistered 10x10 fresh-parent holdout v2.

This script is intentionally outcome-blind. Historical repository text is used
only to conservatively blacklist 3-cell identities that have already appeared.
No labels, scores, witnesses, or solver statistics are parsed.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import re
import subprocess
from pathlib import Path

N = 10
BASE_SHA = "eaf40af27224ad5beb977dc401a787a59cefd2f0"
SEED = "kyouen-10x10-fresh-parent-holdout-v2-2026-09-07"
SAMPLE_N = 24
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "10x10" / "fresh-parent-holdout-v2"
OUT_CSV = OUT_DIR / "parents.csv"
MANIFEST = OUT_DIR / "selection_manifest.json"

TRIPLE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[, -]\s*(\d{1,2})\s*[, -]\s*(\d{1,2})(?!\d)")


def transform_point(p: int, k: int) -> int:
    x, y = p % N, p // N
    xy = (
        (x, y),
        (N - 1 - x, y),
        (x, N - 1 - y),
        (N - 1 - x, N - 1 - y),
        (y, x),
        (N - 1 - y, x),
        (y, N - 1 - x),
        (N - 1 - y, N - 1 - x),
    )[k]
    return xy[1] * N + xy[0]


def canonical(state: tuple[int, int, int]) -> tuple[int, int, int]:
    return min(tuple(sorted(transform_point(p, k) for p in state)) for k in range(8))


def historical_triples() -> set[tuple[int, int, int]]:
    # `git grep` is run at the frozen base SHA. Only matching text is inspected;
    # the parser never consumes outcome columns or neighboring labels.
    cmd = [
        "git", "grep", "-I", "-h", "-E",
        r"[0-9]{1,2}[, -][[:space:]]*[0-9]{1,2}[, -][[:space:]]*[0-9]{1,2}",
        BASE_SHA, "--", "docs", "results", "scripts",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if proc.returncode not in (0, 1):
        raise SystemExit(proc.stderr)
    out: set[tuple[int, int, int]] = set()
    for line in proc.stdout.splitlines():
        for m in TRIPLE_RE.finditer(line):
            vals = tuple(sorted(map(int, m.groups())))
            if len(set(vals)) != 3 or any(v < 0 or v >= 100 for v in vals):
                continue
            out.add(canonical(vals))
    return out


def all_canonical_parents() -> set[tuple[int, int, int]]:
    # Any 3-stone state is legal under the 4-on-a-line/circle losing condition;
    # no 4-point forbidden pattern can yet exist.
    return {canonical(s) for s in itertools.combinations(range(100), 3)}


def digest_for(state: tuple[int, int, int]) -> str:
    key = ",".join(map(str, state))
    return hashlib.sha256(f"{SEED}|{key}".encode()).hexdigest()


def main() -> None:
    universe = all_canonical_parents()
    excluded = historical_triples()
    eligible = sorted(universe - excluded)
    ranked = sorted(eligible, key=lambda s: (digest_for(s), s))
    selected = ranked[:SAMPLE_N]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["selection_index", "parent", "sha256_key"])
        for i, s in enumerate(selected, 1):
            w.writerow([i, ",".join(map(str, s)), digest_for(s)])

    csv_sha = hashlib.sha256(OUT_CSV.read_bytes()).hexdigest()
    manifest = {
        "base_sha": BASE_SHA,
        "seed": SEED,
        "sample_n_requested": SAMPLE_N,
        "d4_universe_count": len(universe),
        "historical_identity_exclusion_count": len(universe & excluded),
        "eligible_count": len(eligible),
        "selected_count": len(selected),
        "parents_csv_sha256": csv_sha,
        "selection_rule": "sha256(seed|canonical_parent), ascending",
        "historical_scan_paths": ["docs", "results", "scripts"],
        "historical_scan_semantics": "identity-only conservative blacklist; labels ignored",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

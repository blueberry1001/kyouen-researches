#!/usr/bin/env python3
"""Compare factorial-selected vs random safe 5-stone LOSS rates on 8x8."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "artifacts" / "8x8-o-census-outcomes.csv"
RANDOM = ROOT / "artifacts" / "8x8-random-safe-5stone-out.csv"
OUT = ROOT / "artifacts" / "8x8-loss-rate-comparison.json"


def load_outcomes(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    key = "child_outcome" if "child_outcome" in rows[0] else "outcome"
    return [r[key] for r in rows]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def main() -> None:
    census = load_outcomes(CENSUS)
    rand = load_outcomes(RANDOM)
    # unique-ish: census may have shared parents; count as-is (already unique roots)
    ck = sum(1 for o in census if o == "LOSS")
    rk = sum(1 for o in rand if o == "LOSS")
    cn, rn = len(census), len(rand)
    report = {
        "factorial_selected": {
            "n": cn,
            "LOSS": ck,
            "LOSS_rate": ck / cn,
            "wilson95": wilson(ck, cn),
        },
        "random_safe_5stone": {
            "n": rn,
            "LOSS": rk,
            "LOSS_rate": rk / rn,
            "wilson95": wilson(rk, rn),
            "seed": 20260915,
            "sample_script": "scripts/sample-8x8-random-safe-5stone.py",
        },
        "nine_nine_factorial_ref_loss_rates": {
            "T": 0.472441,
            "TE": 0.460630,
            "TO": 0.476378,
            "raw": 0.452756,
            "note": "docs/9X9_FACTORIAL_EXACT_PC_RUN_RESULT.md",
        },
        "enrichment": {
            "ratio_selected_over_random": (ck / cn) / (rk / rn) if rk else None,
            "absolute_pp": 100 * (ck / cn - rk / rn),
        },
        "interpretation": (
            "8x8 random safe 5-stone LOSS rate is ~4%, not zero. "
            "Factorial top-move selection is mildly enriched (~7.5%, ~1.9x). "
            "Both are far below the 9x9 factorial ~47% regime. "
            "The board-size base-rate collapse is not an artifact of selection alone."
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

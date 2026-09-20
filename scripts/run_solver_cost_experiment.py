#!/usr/bin/env python3
"""P6 (prepared, NOT YET RUN): measure total exact-solver cost with probe-guided child ordering.

Compares, on the same roots with fresh Solver processes:
  A. current deterministic/default child ordering
  B. cheap probe per candidate then memo-ascending exact order
  C. legal_move_count + memo tie-break
  D. memo only

Metrics per root: visited nodes, wall time, peak memo, first exact LOSS child position.
Total cost = probe cost + exact search cost (probe cost MUST be included).

Status: runner scaffold only. Evaluation waits until the V2 holdout primary
endpoint is complete, per preregistration.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

STRATEGIES = ("default", "probe_memo", "legal_plus_memo", "memo_only")


def main() -> None:
    raise SystemExit(
        "P6 runner is a scaffold: evaluation is gated on V2 holdout primary completion."
    )


if __name__ == "__main__":
    main()

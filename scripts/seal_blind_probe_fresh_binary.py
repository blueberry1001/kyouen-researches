#!/usr/bin/env python3
"""Seal the exact executable and frozen inputs before the corrected blind rerun.

Run this *after* building scripts/probe_cert_solver but *before* running any
primary probe.  The resulting JSON is deliberately outcome-blind and is used
by run_blind_probe_parent_fresh.py to reject a changed executable, runner, or
batch0 child list.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "results" / "10x10" / "blind_probe_children"
SOLVER = ROOT / "scripts" / "probe_cert_solver"
SOLVER_SRC = ROOT / "scripts" / "probe_cert_solver.cpp"
SOLVER_PARTS = ROOT / "scripts" / "probe_parts"
RUNNER = ROOT / "scripts" / "run_blind_probe_parent_fresh.py"
SEAL = ROOT / "results" / "10x10" / "blind-probe-fresh-executable-seal.json"
BUDGET = 1_000_000
SHRINK = 3
LOAD = 80
PARENTS = (
    "2,9,33",
    "4,9,33",
    "9,12,33",
    "9,19,33",
    "9,23,33",
    "0,31,36",
    "0,36,44",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if SEAL.exists():
        raise SystemExit(f"seal already exists; refusing overwrite: {SEAL}")
    existing_raw = sorted(DIR.glob(f"probe_fresh_*_batch0_{BUDGET}.csv"))
    if existing_raw:
        raise SystemExit(
            "primary raw probe already exists; executable must be sealed before any rerun: "
            + ", ".join(p.name for p in existing_raw)
        )
    for path in (SOLVER, SOLVER_SRC, RUNNER):
        if not path.exists():
            raise SystemExit(f"missing required file: {path}")

    part_files = sorted(SOLVER_PARTS.glob("*.inc"))
    if not part_files:
        raise SystemExit(f"no solver implementation parts found in {SOLVER_PARTS}")

    children: dict[str, dict[str, object]] = {}
    for parent in PARENTS:
        safe = parent.replace(",", "_")
        path = DIR / f"children_{safe}_batch0.txt"
        if not path.exists():
            raise SystemExit(f"missing frozen child list: {path}")
        states = [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        if len(states) != 20 or len(set(states)) != 20:
            raise SystemExit(f"{parent}: expected 20 unique batch0 children, got {len(states)}")
        children[parent] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(path),
            "count": len(states),
        }

    source_files = [SOLVER_SRC, *part_files]
    data = {
        "protocol": "corrected-blind-probe-fresh-executable-seal-v1",
        "outcomes_read": False,
        "budget": BUDGET,
        "shrink": SHRINK,
        "load": LOAD,
        "parents": list(PARENTS),
        "solver": {
            "path": str(SOLVER.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(SOLVER),
            "size": SOLVER.stat().st_size,
        },
        "runner": {
            "path": str(RUNNER.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(RUNNER),
        },
        "solver_sources": [
            {
                "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(p),
            }
            for p in source_files
        ],
        "children": children,
    }
    SEAL.parent.mkdir(parents=True, exist_ok=True)
    SEAL.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"sealed executable + runner + 7x20 frozen child lists -> {SEAL}")
    print(f"solver_sha256={data['solver']['sha256']}")
    print("No exact-outcome file was opened.")


if __name__ == "__main__":
    main()

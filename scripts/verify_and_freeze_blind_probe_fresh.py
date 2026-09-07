#!/usr/bin/env python3
"""Outcome-blind verifier + ranking freezer for the corrected seven-parent rerun.

Run only after all seven primary `probe_fresh_*_batch0_1000000.csv` files exist.
This program deliberately never opens exact-outcome files or blind-probe-results.csv.
It verifies the frozen task set, freshness sanity conditions, and writes the
memo-desc ranking that must be committed before outcomes are joined.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "results" / "10x10" / "blind_probe_children"
OUT = ROOT / "results" / "10x10" / "blind-probe-fresh-rankings-unrevealed.csv"
MANIFEST = ROOT / "results" / "10x10" / "blind-probe-fresh-ranking-manifest.json"
BUDGET = 1_000_000
PARENTS = (
    "2,9,33",
    "4,9,33",
    "9,12,33",
    "9,19,33",
    "9,23,33",
    "0,31,36",
    "0,36,44",
)


def norm(s: str) -> str:
    return "-".join(str(int(x)) for x in s.replace(",", "-").split("-") if x)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    if OUT.exists() or MANIFEST.exists():
        raise SystemExit(
            "ranking/manifest already exists; refusing to overwrite frozen primary artifacts"
        )

    ranking_rows: list[dict[str, object]] = []
    manifest: dict[str, object] = {
        "protocol": "corrected-blind-probe-fresh-v1",
        "feature": "memo",
        "direction": "descending",
        "budget": BUDGET,
        "batch": 0,
        "parents": list(PARENTS),
        "exact_outcomes_read": False,
        "freshness_invariants": {
            "memo_le_visited": True,
            "probe_rows_hit_exact_visited_budget": True,
        },
        "files": {},
    }

    global_seen: set[tuple[str, str]] = set()
    for parent in PARENTS:
        safe = parent.replace(",", "_")
        children_path = DIR / f"children_{safe}_batch0.txt"
        probe_path = DIR / f"probe_fresh_{safe}_batch0_{BUDGET}.csv"
        if not children_path.exists():
            raise SystemExit(f"missing frozen child list: {children_path}")
        if not probe_path.exists():
            raise SystemExit(f"missing fresh raw probe: {probe_path}")

        children = [
            norm(x.strip())
            for x in children_path.read_text(encoding="utf-8").splitlines()
            if x.strip()
        ]
        if len(children) != 20 or len(set(children)) != 20:
            raise SystemExit(
                f"{parent}: expected 20 unique frozen batch0 children, got {len(children)}"
            )

        rows = read_csv(probe_path)
        if len(rows) != 20:
            raise SystemExit(f"{parent}: expected 20 fresh probe rows, got {len(rows)}")
        required = {"state", "outcome", "visited", "memo", "maxdepth", "seconds"}
        if not required.issubset(rows[0]):
            raise SystemExit(f"{parent}: missing required columns {required - set(rows[0])}")

        by_state: dict[str, dict[str, str]] = {}
        for r in rows:
            state = norm(r["state"])
            if state in by_state:
                raise SystemExit(f"{parent}: duplicate fresh probe state {state}")
            by_state[state] = r
            key = (parent, state)
            if key in global_seen:
                raise SystemExit(f"duplicate parent/state pair: {key}")
            global_seen.add(key)

            outcome = r["outcome"].upper()
            visited = int(r["visited"])
            memo = int(r["memo"])
            if visited <= 0 or visited > BUDGET:
                raise SystemExit(f"{parent} {state}: invalid visited={visited}")
            if outcome not in {"PROBE", "WIN", "LOSS"}:
                raise SystemExit(f"{parent} {state}: unknown probe outcome={r['outcome']}")

            # Fresh-Solver invariant from Solver::win(): a state is counted in
            # `visited` before it can add at most one previously-empty memo entry.
            # Therefore one fresh Solver can never end with memo_used > visited.
            # The original contaminated batch run violated this once memo carried
            # over across children, so this is a direct regression guard rather
            # than a loose heuristic threshold.
            if memo < 0 or memo > visited:
                raise SystemExit(
                    f"{parent} {state}: freshness invariant violated: memo={memo} > visited={visited}"
                )

            # PROBE is emitted only by ProbeExhausted. With a visited-only budget
            # and no seconds budget, the exception fires exactly when visited
            # reaches BUDGET. Early exact WIN/LOSS is allowed and will have
            # visited <= BUDGET.
            if outcome == "PROBE" and visited != BUDGET:
                raise SystemExit(
                    f"{parent} {state}: PROBE must hit exact visited budget; "
                    f"visited={visited}, budget={BUDGET}"
                )

        if set(by_state) != set(children):
            missing = sorted(set(children) - set(by_state))
            extra = sorted(set(by_state) - set(children))
            raise SystemExit(f"{parent}: task mismatch missing={missing} extra={extra}")

        # Tie break is original batch/input order, as frozen in the audit doc.
        input_pos = {s: i for i, s in enumerate(children)}
        ranked = sorted(
            children,
            key=lambda s: (-int(by_state[s]["memo"]), input_pos[s]),
        )
        for rank, state in enumerate(ranked, 1):
            r = by_state[state]
            ranking_rows.append({
                "parent": parent,
                "rank": rank,
                "input_position": input_pos[state] + 1,
                "state": state,
                "probe_outcome": r["outcome"],
                "visited": int(r["visited"]),
                "memo": int(r["memo"]),
                "maxdepth": int(r["maxdepth"]),
                "seconds": r["seconds"],
            })

        manifest["files"][parent] = {
            "children": str(children_path.relative_to(ROOT)).replace("\\", "/"),
            "children_sha256": sha256_file(children_path),
            "probe": str(probe_path.relative_to(ROOT)).replace("\\", "/"),
            "probe_sha256": sha256_file(probe_path),
        }

    if len(ranking_rows) != 140:
        raise SystemExit(f"expected 140 frozen ranking rows, got {len(ranking_rows)}")

    with OUT.open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ranking_rows[0].keys()))
        w.writeheader()
        w.writerows(ranking_rows)
    manifest["ranking_file"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
    manifest["ranking_sha256"] = sha256_file(OUT)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("verified: 7 parents x 20 children = 140 fresh probe rows")
    print("verified freshness: memo <= visited; PROBE rows hit visited budget exactly")
    print("froze: memo descending, original-input-position tie break")
    print(f"ranking: {OUT}")
    print(f"manifest: {MANIFEST}")
    print("No exact-outcome file was opened.")


if __name__ == "__main__":
    main()

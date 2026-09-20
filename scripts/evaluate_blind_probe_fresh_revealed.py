#!/usr/bin/env python3
"""Evaluate the corrected seven-parent blind rerun after ranking freeze.

This script is intentionally written before corrected outcomes are joined.
It refuses to evaluate unless the outcome-blind ranking manifest and ranking
created by verify_and_freeze_blind_probe_fresh.py are present and hash-consistent.

It also refuses to parse any exact outcome CSV until all seven exact inputs have
been checked against a pre-reveal Git-blob seal. This prevents a later change to
an exact-label file from silently changing the revealed evaluation.

Primary comparison (frozen by docs/BLIND_PROBE_FRESHNESS_AUDIT.md):
  first-LOSS position of memo-desc@1M vs solver/input order and random order.

The random first-LOSS baseline is computed exactly from combinations, not from
Monte Carlo. For n children with k LOSS children,
  P(first LOSS > r) = C(n-r, k) / C(n, k).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "10x10"
CHILDREN_DIR = RESULTS / "blind_probe_children"
RANKING = RESULTS / "blind-probe-fresh-rankings-unrevealed.csv"
MANIFEST = RESULTS / "blind-probe-fresh-ranking-manifest.json"
EXACT_SEAL = RESULTS / "blind-probe-fresh-exact-input-seal.json"
OUT_CSV = RESULTS / "blind-probe-fresh-revealed-results.csv"
OUT_JSON = RESULTS / "blind-probe-fresh-revealed-analysis.json"

PARENTS = (
    "2,9,33",
    "4,9,33",
    "9,12,33",
    "9,19,33",
    "9,23,33",
    "0,31,36",
    "0,36,44",
)
EXPECTED_PROTOCOL = "corrected-blind-probe-fresh-v1"
EXPECTED_BUDGET = 1_000_000
EXPECTED_EXACT_SEAL_SCHEMA = "blind-probe-fresh-exact-input-seal-v1"


def norm(s: str) -> str:
    return "-".join(str(int(x)) for x in s.replace(",", "-").split("-") if x)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(path: Path) -> str:
    """Compute the Git SHA-1 blob id from raw bytes without parsing contents."""
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def first_loss(order: list[str], outcomes: dict[str, str]) -> int:
    for i, s in enumerate(order, 1):
        if outcomes[s] == "LOSS":
            return i
    return len(order) + 1


def random_first_loss_cdf(n: int, k: int, r: int) -> float:
    """Exact P(first LOSS <= r) under a uniformly random permutation."""
    if k <= 0:
        return 0.0
    if r <= 0:
        return 0.0
    if r >= n - k + 1:
        return 1.0
    return 1.0 - math.comb(n - r, k) / math.comb(n, k)


def random_first_loss_mean(n: int, k: int) -> float:
    return (n + 1) / (k + 1) if k > 0 else float(n + 1)


def random_first_loss_median(n: int, k: int) -> int:
    if k <= 0:
        return n + 1
    for r in range(1, n + 1):
        if random_first_loss_cdf(n, k, r) >= 0.5:
            return r
    raise AssertionError("unreachable")


def auc_loss_early(order: list[str], outcomes: dict[str, str]) -> float | None:
    """Pairwise AUC where 1 means every LOSS is ranked before every WIN."""
    losses = [i for i, s in enumerate(order) if outcomes[s] == "LOSS"]
    wins = [i for i, s in enumerate(order) if outcomes[s] == "WIN"]
    if not losses or not wins:
        return None
    good = sum(1 for li in losses for wi in wins if li < wi)
    return good / (len(losses) * len(wins))


def expected_exact_path(parent: str) -> Path:
    safe = parent.replace(",", "_")
    return CHILDREN_DIR / f"exact_{safe}_batch0.csv"


def verify_exact_seal_before_reveal() -> dict[str, dict[str, str]]:
    """Verify every exact file as raw bytes before any outcome CSV is parsed."""
    if not EXACT_SEAL.exists():
        raise SystemExit("pre-reveal exact-input seal is missing")
    seal = json.loads(EXACT_SEAL.read_text(encoding="utf-8"))
    if seal.get("schema") != EXPECTED_EXACT_SEAL_SCHEMA:
        raise SystemExit("exact-input seal schema mismatch")
    if seal.get("protocol") != EXPECTED_PROTOCOL:
        raise SystemExit("exact-input seal protocol mismatch")
    files = seal.get("files")
    if not isinstance(files, dict) or set(files) != set(PARENTS):
        raise SystemExit("exact-input seal parent set mismatch")

    resolved: dict[str, dict[str, str]] = {}
    # Deliberately finish verification for all parents before returning. No CSV
    # parser is called in this function.
    for parent in PARENTS:
        entry = files[parent]
        if not isinstance(entry, dict):
            raise SystemExit(f"{parent}: invalid exact-input seal entry")
        path = expected_exact_path(parent)
        expected_rel = path.relative_to(ROOT).as_posix()
        if entry.get("path") != expected_rel:
            raise SystemExit(f"{parent}: sealed exact path mismatch")
        expected_sha = entry.get("git_blob_sha1")
        if not isinstance(expected_sha, str) or len(expected_sha) != 40:
            raise SystemExit(f"{parent}: invalid sealed Git blob SHA-1")
        if not path.exists():
            raise SystemExit(f"{parent}: sealed exact input is missing")
        actual_sha = git_blob_sha1(path)
        if actual_sha != expected_sha:
            raise SystemExit(
                f"{parent}: exact input changed since pre-reveal seal: "
                f"{actual_sha} != {expected_sha}"
            )
        resolved[parent] = {"path": expected_rel, "git_blob_sha1": expected_sha}
    return resolved


def main() -> None:
    if OUT_CSV.exists() or OUT_JSON.exists():
        raise SystemExit("revealed outputs already exist; refusing to overwrite")
    if not RANKING.exists() or not MANIFEST.exists():
        raise SystemExit(
            "ranking freeze is missing; run verify_and_freeze_blind_probe_fresh.py "
            "and commit its artifacts before revealing outcomes"
        )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    required_manifest = {
        "protocol": EXPECTED_PROTOCOL,
        "feature": "memo",
        "direction": "descending",
        "budget": EXPECTED_BUDGET,
        "batch": 0,
        "parents": list(PARENTS),
        "exact_outcomes_read": False,
    }
    for key, expected in required_manifest.items():
        if manifest.get(key) != expected:
            raise SystemExit(
                f"ranking manifest mismatch: {key}={manifest.get(key)!r}, expected {expected!r}"
            )
    if manifest.get("ranking_sha256") != sha256_file(RANKING):
        raise SystemExit("frozen ranking SHA256 mismatch")

    ranking_rows = read_csv(RANKING)
    if len(ranking_rows) != 140:
        raise SystemExit(f"expected 140 ranking rows, got {len(ranking_rows)}")

    by_parent: dict[str, list[dict[str, str]]] = {p: [] for p in PARENTS}
    for r in ranking_rows:
        p = r["parent"]
        if p not in by_parent:
            raise SystemExit(f"unexpected parent in ranking: {p}")
        by_parent[p].append(r)

    # Crucial reveal boundary: all seven exact inputs are authenticated as raw
    # Git blobs here. Only after this succeeds may read_csv(exact_path) occur.
    sealed_exact = verify_exact_seal_before_reveal()

    result_rows: list[dict[str, object]] = []
    for parent in PARENTS:
        ranked_rows = sorted(by_parent[parent], key=lambda r: int(r["rank"]))
        if len(ranked_rows) != 20 or [int(r["rank"]) for r in ranked_rows] != list(range(1, 21)):
            raise SystemExit(f"{parent}: invalid frozen ranks")
        fixed_order = [norm(r["state"]) for r in ranked_rows]

        safe = parent.replace(",", "_")
        child_path = CHILDREN_DIR / f"children_{safe}_batch0.txt"
        exact_path = expected_exact_path(parent)
        if not child_path.exists() or not exact_path.exists():
            raise SystemExit(f"{parent}: missing child/exact batch0 input")
        if parent not in manifest.get("files", {}):
            raise SystemExit(f"{parent}: missing manifest file entry")
        mf = manifest["files"][parent]
        if mf.get("children_sha256") != sha256_file(child_path):
            raise SystemExit(f"{parent}: frozen child-list SHA256 mismatch")
        if sealed_exact[parent]["path"] != exact_path.relative_to(ROOT).as_posix():
            raise AssertionError("sealed exact path changed after preflight")

        solver_order = [norm(x.strip()) for x in child_path.read_text(encoding="utf-8").splitlines() if x.strip()]
        if len(solver_order) != 20 or len(set(solver_order)) != 20:
            raise SystemExit(f"{parent}: expected 20 unique solver-order children")
        if set(solver_order) != set(fixed_order):
            raise SystemExit(f"{parent}: ranking/child state-set mismatch")

        exact_rows = read_csv(exact_path)
        exact: dict[str, str] = {}
        for r in exact_rows:
            s = norm(r["state"])
            o = r["outcome"].strip().upper()
            if s in exact:
                raise SystemExit(f"{parent}: duplicate exact state {s}")
            if o not in {"WIN", "LOSS"}:
                raise SystemExit(f"{parent} {s}: exact outcome must be WIN/LOSS, got {o!r}")
            exact[s] = o
        if set(exact) != set(solver_order):
            missing = sorted(set(solver_order) - set(exact))
            extra = sorted(set(exact) - set(solver_order))
            raise SystemExit(f"{parent}: exact set mismatch missing={missing} extra={extra}")

        n = len(solver_order)
        k = sum(o == "LOSS" for o in exact.values())
        if k == 0:
            raise SystemExit(f"{parent}: frozen evaluation parent has no LOSS in batch0")

        fixed_pos = first_loss(fixed_order, exact)
        solver_pos = first_loss(solver_order, exact)
        random_median = random_first_loss_median(n, k)
        random_mean = random_first_loss_mean(n, k)
        # One-sided random percentile: small values mean an equally-or-more-early
        # first LOSS is uncommon under random ordering. Descriptive only; no
        # significance threshold is introduced post hoc.
        random_cdf_at_fixed = random_first_loss_cdf(n, k, fixed_pos)
        fixed_auc = auc_loss_early(fixed_order, exact)
        solver_auc = auc_loss_early(solver_order, exact)

        result_rows.append({
            "parent": parent,
            "n": n,
            "losses": k,
            "fixed_first_loss": fixed_pos,
            "solver_first_loss": solver_pos,
            "random_exact_median_first_loss": random_median,
            "random_exact_mean_first_loss": round(random_mean, 6),
            "fixed_over_random_median": round(fixed_pos / random_median, 6),
            "fixed_over_solver": round(fixed_pos / solver_pos, 6),
            "random_cdf_at_fixed": round(random_cdf_at_fixed, 9),
            "fixed_loss_early_auc": "" if fixed_auc is None else round(fixed_auc, 9),
            "solver_loss_early_auc": "" if solver_auc is None else round(solver_auc, 9),
            "first_fixed_loss_state": fixed_order[fixed_pos - 1],
            "first_solver_loss_state": solver_order[solver_pos - 1],
        })

    fixed = [int(r["fixed_first_loss"]) for r in result_rows]
    solver = [int(r["solver_first_loss"]) for r in result_rows]
    random_med = [int(r["random_exact_median_first_loss"]) for r in result_rows]

    summary = {
        "protocol": EXPECTED_PROTOCOL,
        "parents": len(result_rows),
        "primary_metric": "first LOSS position",
        "fixed_rule": "memo descending @ 1M, fresh Solver per child, input-order tie break",
        "fixed_median_first_loss": statistics.median(fixed),
        "solver_median_first_loss": statistics.median(solver),
        "random_exact_parentwise_median_of_medians": statistics.median(random_med),
        "fixed_better_than_solver_parents": sum(f < s for f, s in zip(fixed, solver)),
        "fixed_equal_solver_parents": sum(f == s for f, s in zip(fixed, solver)),
        "fixed_worse_than_solver_parents": sum(f > s for f, s in zip(fixed, solver)),
        "fixed_better_than_random_median_parents": sum(f < r for f, r in zip(fixed, random_med)),
        "fixed_equal_random_median_parents": sum(f == r for f, r in zip(fixed, random_med)),
        "fixed_worse_than_random_median_parents": sum(f > r for f, r in zip(fixed, random_med)),
        "fixed_rank_sum": sum(fixed),
        "solver_rank_sum": sum(solver),
        "random_median_rank_sum": sum(random_med),
        "ranking_sha256": sha256_file(RANKING),
        "exact_inputs": sealed_exact,
        "note": (
            "Random baseline is exact combinatorial first-LOSS distribution. "
            "All seven exact inputs were authenticated against the pre-reveal Git-blob seal before any exact CSV was parsed. "
            "No new pass/fail threshold is introduced by this evaluator."
        ),
    }

    with OUT_CSV.open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(result_rows[0].keys()))
        w.writeheader()
        w.writerows(result_rows)
    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_JSON}")


if __name__ == "__main__":
    main()

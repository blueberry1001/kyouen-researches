#!/usr/bin/env python3
import csv
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile


def write_fake_solver(path):
    path.write_text(
        r'''#!/usr/bin/env python3
import csv
import os
import sys

inp = sys.argv[1]
mode = os.environ.get("FAKE_FAILURE_MODE", "memo")
with open(inp, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
parents = []
seen = set()
for r in rows:
    p = r["canonical_parent"]
    if p not in seen:
        seen.add(p)
        parents.append(p)

fields = [
    "canonical_parent", "pair_top", "union_top",
    "pair_child_outcome", "other_child_outcome",
    "pair_visited", "other_visited", "pair_seconds", "other_seconds", "memo_used",
]
w = csv.DictWriter(sys.stdout, fieldnames=fields, lineterminator="\n")
w.writeheader()

if mode == "other":
    if rows:
        r = rows[0]
        w.writerow({
            "canonical_parent": r["canonical_parent"],
            "pair_top": r["pair_top"], "union_top": r["union_top"],
            "pair_child_outcome": "LOSS", "other_child_outcome": "LOSS",
            "pair_visited": 1, "other_visited": 1,
            "pair_seconds": 0, "other_seconds": 0, "memo_used": 1,
        })
    print("error: unrelated synthetic failure", file=sys.stderr)
    raise SystemExit(1)

if len(parents) > 2:
    # Deliberately emit a misleading partial row. The recovery runner must
    # quarantine this and later use only the fresh successful leaf result.
    if rows:
        r = rows[0]
        w.writerow({
            "canonical_parent": r["canonical_parent"],
            "pair_top": r["pair_top"], "union_top": r["union_top"],
            "pair_child_outcome": "LOSS", "other_child_outcome": "LOSS",
            "pair_visited": 999, "other_visited": 999,
            "pair_seconds": 0, "other_seconds": 0, "memo_used": 999,
        })
    print("error: memo table over 80%", file=sys.stderr)
    raise SystemExit(1)

memo = 0
for r in rows:
    memo += 10
    # All successful leaf results are WIN/WIN, intentionally different from
    # excluded partial LOSS/LOSS above.
    w.writerow({
        "canonical_parent": r["canonical_parent"],
        "pair_top": r["pair_top"], "union_top": r["union_top"],
        "pair_child_outcome": "WIN", "other_child_outcome": "WIN",
        "pair_visited": 10, "other_visited": 20,
        "pair_seconds": 0, "other_seconds": 0, "memo_used": memo,
    })
''',
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def write_input(path, n=5):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)  # intentionally CRLF, matching frozen workset transport
        w.writerow(["canonical_parent", "pair_top", "union_top"])
        for i in range(n):
            w.writerow([f'0,1,2,{10+i}', 20 + i, 40 + i])


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    repo = Path(__file__).resolve().parents[1]
    runner = repo / "scripts/run-9x9-factorial-shard-with-recovery.py"
    splitter = repo / "scripts/split-9x9-factorial-recovery-shard.py"

    with tempfile.TemporaryDirectory(prefix="factorial-recovery-test-") as td:
        root = Path(td)
        solver = root / "fake_solver.py"
        inp = root / "input.csv"
        out = root / "out"
        write_fake_solver(solver)
        write_input(inp, 5)

        p = subprocess.run(
            [
                sys.executable,
                str(runner),
                str(solver),
                str(inp),
                str(out),
                "--memo-power", "7",
                "--max-recovery-level", "4",
                "--splitter", str(splitter),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if p.returncode != 0:
            raise SystemExit(f"recovery runner unexpectedly failed:\n{p.stdout}\n{p.stderr}")

        rows = read_csv(out / "consolidated-results.csv")
        if len(rows) != 5:
            raise SystemExit(f"expected 5 consolidated rows, got {len(rows)}")
        if any(r["pair_child_outcome"] != "WIN" or r["other_child_outcome"] != "WIN" for r in rows):
            raise SystemExit("excluded partial LOSS outcome leaked into consolidated result")

        manifest = json.loads((out / "attempt-manifest.json").read_text(encoding="utf-8"))
        statuses = [r["status"] for r in manifest["attempts"]]
        if statuses.count("excluded_memo_limit_split") != 2:
            raise SystemExit(f"expected two deterministic splits, statuses={statuses}")
        if statuses.count("success") != 3:
            raise SystemExit(f"expected three successful leaves, statuses={statuses}")
        if manifest["error"] is not None:
            raise SystemExit(f"unexpected manifest error: {manifest['error']}")
        receipt = (out / "recovery-receipt.txt").read_text(encoding="utf-8")
        if "partial_failed_outputs_used=0" not in receipt:
            raise SystemExit("receipt does not assert exclusion of partial failed output")

        # A failure without the exact preregistered memo-limit marker must stop;
        # it must never trigger automatic subdivision.
        bad_inp = root / "bad-input.csv"
        bad_out = root / "bad-out"
        write_input(bad_inp, 2)
        env = dict(__import__("os").environ)
        env["FAKE_FAILURE_MODE"] = "other"
        q = subprocess.run(
            [
                sys.executable,
                str(runner),
                str(solver),
                str(bad_inp),
                str(bad_out),
                "--memo-power", "7",
                "--max-recovery-level", "4",
                "--splitter", str(splitter),
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if q.returncode == 0:
            raise SystemExit("non-preregistered failure incorrectly recovered")
        if (bad_out / "consolidated-results.csv").exists():
            raise SystemExit("fatal non-preregistered failure produced a consolidated result")
        bad_manifest = json.loads((bad_out / "attempt-manifest.json").read_text(encoding="utf-8"))
        if [r["status"] for r in bad_manifest["attempts"]] != ["fatal_nonpreregistered_failure"]:
            raise SystemExit(f"unexpected fatal statuses: {bad_manifest['attempts']}")

    print("memo_limit_recursive_recovery=PASS")
    print("failed_partial_output_exclusion=PASS")
    print("nonpreregistered_failure_no_split=PASS")
    print("crlf_to_lf_transport=PASS")


if __name__ == "__main__":
    main()

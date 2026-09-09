#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

MEMO_LIMIT_MARKER = "memo table over 80%"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parent_order(rows):
    seen = set()
    order = []
    for row in rows:
        p = row["canonical_parent"]
        if p not in seen:
            seen.add(p)
            order.append(p)
    return order


def normalize_transport(src, dst):
    data = Path(src).read_bytes()
    normalized = data.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise RuntimeError(f"unexpected bare CR in {src}")
    Path(dst).write_bytes(normalized)
    return len(data) - len(normalized)


def validate_success(input_path, output_path):
    inp = read_csv(input_path)
    out = read_csv(output_path)
    if len(inp) != len(out):
        raise RuntimeError(
            f"row-count mismatch: input={len(inp)} output={len(out)} for {input_path}"
        )
    last_memo = -1
    for i, (x, y) in enumerate(zip(inp, out), start=2):
        for col in ("canonical_parent", "pair_top", "union_top"):
            if x[col] != y.get(col):
                raise RuntimeError(
                    f"row {i}: {col} mismatch: {x[col]!r} != {y.get(col)!r}"
                )
        for col in ("pair_child_outcome", "other_child_outcome"):
            if y.get(col) not in {"WIN", "LOSS"}:
                raise RuntimeError(f"row {i}: bad {col}={y.get(col)!r}")
        try:
            memo = int(y["memo_used"])
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"row {i}: invalid memo_used") from e
        if memo < last_memo:
            raise RuntimeError(
                f"row {i}: memo_used decreased: {memo} < {last_memo}"
            )
        last_memo = memo
    return len(out), last_memo


def write_consolidated(original_input, leaf_outputs, destination):
    source_rows = read_csv(original_input)
    by_key = {}
    fieldnames = None
    for output in leaf_outputs:
        with open(output, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if fieldnames is None:
                fieldnames = reader.fieldnames
            elif reader.fieldnames != fieldnames:
                raise RuntimeError("leaf result headers differ")
            for row in reader:
                key = (
                    row["canonical_parent"],
                    int(row["pair_top"]),
                    int(row["union_top"]),
                )
                old = by_key.get(key)
                if old is not None and old != row:
                    raise RuntimeError(f"inconsistent repeated leaf result: {key}")
                by_key[key] = row

    expected = [
        (r["canonical_parent"], int(r["pair_top"]), int(r["union_top"]))
        for r in source_rows
    ]
    if len(set(expected)) != len(expected):
        raise RuntimeError("original primary shard contains duplicate rows")
    if set(expected) != set(by_key):
        raise RuntimeError(
            f"leaf result key mismatch: expected={len(expected)} actual={len(by_key)}"
        )
    if fieldnames is None:
        raise RuntimeError("no successful leaf outputs")

    with open(destination, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for key in expected:
            writer.writerow(by_key[key])


def main():
    p = argparse.ArgumentParser(
        description=(
            "Run one frozen 9x9 factorial union shard. Automatically bisect only "
            "on the preregistered 'memo table over 80%' failure; exclude all "
            "partial failed-attempt output from the consolidated result."
        )
    )
    p.add_argument("solver")
    p.add_argument("input_csv")
    p.add_argument("output_dir")
    p.add_argument("--memo-power", type=int, default=28)
    p.add_argument("--max-recovery-level", type=int, default=6)
    p.add_argument(
        "--splitter",
        default=str(Path(__file__).with_name("split-9x9-factorial-recovery-shard.py")),
    )
    args = p.parse_args()

    if args.memo_power <= 0:
        raise SystemExit("--memo-power must be positive")
    if args.max_recovery_level < 0:
        raise SystemExit("--max-recovery-level must be nonnegative")

    solver = Path(args.solver).resolve()
    primary = Path(args.input_csv).resolve()
    outdir = Path(args.output_dir).resolve()
    splitter = Path(args.splitter).resolve()
    if not solver.is_file():
        raise SystemExit(f"solver not found: {solver}")
    if not primary.is_file():
        raise SystemExit(f"input not found: {primary}")
    if not splitter.is_file():
        raise SystemExit(f"splitter not found: {splitter}")

    rows = read_csv(primary)
    if not rows:
        raise SystemExit("empty primary shard")
    required = {"canonical_parent", "pair_top", "union_top"}
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(f"primary input missing columns: {sorted(missing)}")
    parents = parent_order(rows)
    if parents != sorted(parents):
        raise SystemExit("primary parents are not in canonical_parent order")

    attempts_dir = outdir / "attempts"
    excluded_dir = outdir / "excluded-failed-attempts"
    split_dir = outdir / "recovery-inputs"
    for d in (outdir, attempts_dir, excluded_dir, split_dir):
        d.mkdir(parents=True, exist_ok=True)

    attempt_records = []
    leaf_outputs = []

    def run_node(input_path, node, level):
        input_path = Path(input_path).resolve()
        input_rows = read_csv(input_path)
        node_parents = parent_order(input_rows)
        attempt_dir = attempts_dir / node
        attempt_dir.mkdir(parents=True, exist_ok=True)
        executed = attempt_dir / "executed-input.csv"
        stdout = attempt_dir / "solver-output.csv"
        stderr = attempt_dir / "solver-stderr.txt"
        removed = normalize_transport(input_path, executed)

        start = time.monotonic()
        with open(stdout, "wb") as out_f, open(stderr, "wb") as err_f:
            proc = subprocess.run(
                [str(solver), str(executed), str(args.memo_power)],
                stdout=out_f,
                stderr=err_f,
                check=False,
            )
        elapsed = time.monotonic() - start
        stderr_text = stderr.read_text(encoding="utf-8", errors="replace")
        record = {
            "node": node,
            "level": level,
            "parent_count": len(node_parents),
            "input_rows": len(input_rows),
            "input_sha256": sha256(input_path),
            "executed_input_sha256": sha256(executed),
            "crlf_bytes_removed": removed,
            "returncode": proc.returncode,
            "elapsed_seconds": elapsed,
            "status": None,
            "output_sha256": sha256(stdout),
            "stderr_sha256": sha256(stderr),
        }

        if proc.returncode == 0:
            validated_rows, final_memo = validate_success(executed, stdout)
            record["status"] = "success"
            record["validated_rows"] = validated_rows
            record["final_memo_used"] = final_memo
            attempt_records.append(record)
            leaf_outputs.append(stdout)
            return

        # A failed attempt may contain already-computed outcomes. Preserve it only
        # as excluded diagnostics, never as an endpoint leaf result.
        excluded_node = excluded_dir / node
        if excluded_node.exists():
            shutil.rmtree(excluded_node)
        shutil.move(str(attempt_dir), str(excluded_node))
        stdout = excluded_node / "solver-output.csv"
        stderr = excluded_node / "solver-stderr.txt"
        record["output_sha256"] = sha256(stdout)
        record["stderr_sha256"] = sha256(stderr)

        allowed_memo_failure = MEMO_LIMIT_MARKER in stderr_text
        if not allowed_memo_failure:
            record["status"] = "fatal_nonpreregistered_failure"
            attempt_records.append(record)
            raise RuntimeError(
                f"{node}: solver failed with returncode {proc.returncode} without "
                f"the preregistered memo-limit marker"
            )
        if len(node_parents) < 2:
            record["status"] = "fatal_memo_limit_at_single_parent"
            attempt_records.append(record)
            raise RuntimeError(f"{node}: memo limit reached with one parent")
        if level >= args.max_recovery_level:
            record["status"] = "fatal_max_recovery_level"
            attempt_records.append(record)
            raise RuntimeError(
                f"{node}: memo limit reached at configured recovery level {level}"
            )

        record["status"] = "excluded_memo_limit_split"
        attempt_records.append(record)
        child_level = level + 1
        node_split_dir = split_dir / node
        node_split_dir.mkdir(parents=True, exist_ok=True)
        split_proc = subprocess.run(
            [
                sys.executable,
                str(splitter),
                str(input_path),
                str(node_split_dir),
                "--level",
                str(child_level),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        (node_split_dir / "splitter.stdout.txt").write_text(
            split_proc.stdout, encoding="utf-8"
        )
        (node_split_dir / "splitter.stderr.txt").write_text(
            split_proc.stderr, encoding="utf-8"
        )
        if split_proc.returncode != 0:
            raise RuntimeError(
                f"{node}: deterministic recovery splitter failed: {split_proc.stderr}"
            )

        candidates = sorted(node_split_dir.glob(f"*.r{child_level}[ab].csv"))
        if len(candidates) != 2:
            raise RuntimeError(
                f"{node}: expected two recovery inputs, found {len(candidates)}"
            )
        run_node(candidates[0], node + "a", child_level)
        run_node(candidates[1], node + "b", child_level)

    error = None
    try:
        run_node(primary, "p", 0)
    except Exception as e:
        error = str(e)

    manifest = outdir / "attempt-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "primary_input": str(primary),
                "primary_input_sha256": sha256(primary),
                "solver": str(solver),
                "solver_sha256": sha256(solver),
                "memo_power": args.memo_power,
                "max_recovery_level": args.max_recovery_level,
                "recovery_trigger": MEMO_LIMIT_MARKER,
                "policy": "only exact memo-limit marker auto-splits; all failed partial output excluded",
                "attempts": attempt_records,
                "error": error,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if error is not None:
        print(f"ERROR: {error}", file=sys.stderr)
        print(f"manifest={manifest}", file=sys.stderr)
        return 1

    consolidated = outdir / "consolidated-results.csv"
    write_consolidated(primary, leaf_outputs, consolidated)
    # Validate consolidated identity/order once more against an LF primary copy.
    primary_lf = outdir / "primary-executed-input.csv"
    normalize_transport(primary, primary_lf)
    validated_rows, _ = validate_success(primary_lf, consolidated)

    receipt = outdir / "recovery-receipt.txt"
    successful = sum(r["status"] == "success" for r in attempt_records)
    excluded = sum(r["status"] == "excluded_memo_limit_split" for r in attempt_records)
    receipt.write_text(
        "\n".join(
            [
                f"primary_input_sha256={sha256(primary)}",
                f"solver_sha256={sha256(solver)}",
                f"memo_power={args.memo_power}",
                f"validated_primary_rows={validated_rows}",
                f"successful_leaf_attempts={successful}",
                f"excluded_failed_attempts={excluded}",
                f"consolidated_sha256={sha256(consolidated)}",
                "partial_failed_outputs_used=0",
                "statistical_analysis_run=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(receipt.read_text(encoding="utf-8"), end="")
    print(f"manifest={manifest}")
    print(f"consolidated={consolidated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

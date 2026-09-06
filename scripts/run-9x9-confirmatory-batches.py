#!/usr/bin/env python3
"""
Confirmatory 1024 Runner with Deterministic Sharding, Checkpoint & Resume.
Maintains exact input order, no duplicate runs, validates completeness.
Does NOT compute or display WIN/LOSS statistics or p-values during execution.
"""

import sys
import os
import csv
import subprocess
import argparse
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Run 9x9 Confirmatory 1024 with checkpoint/resume.")
    parser.add_argument("--solver", required=True, help="Path to kyouen-solver-9-compare executable")
    parser.add_argument("--input", required=True, help="Path to confirmatory 1024 input CSV")
    parser.add_argument("--output", required=True, help="Path to final output results CSV")
    parser.add_argument("--work-dir", default="tmp/confirmatory_runs", help="Working directory for checkpoints/shards")
    parser.add_argument("--batch-size", type=int, default=128, help="Batch size for checkpoint chunks (default: 128)")
    parser.add_argument("--memo-power", type=int, default=29, help="Memo table power (default: 29)")
    return parser.parse_args()

def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        input_rows = list(reader)

    total_rows = len(input_rows)
    print(f"Total input rows: {total_rows}")
    if total_rows != 1024:
        print(f"WARNING: Expected 1024 rows, got {total_rows}", file=sys.stderr)

    # Chunk into deterministic batches
    batch_size = args.batch_size
    num_batches = (total_rows + batch_size - 1) // batch_size
    print(f"Batches: {num_batches} (batch size {batch_size})")

    batch_outputs = []
    completed_rows = 0

    for b in range(num_batches):
        start_idx = b * batch_size
        end_idx = min(total_rows, start_idx + batch_size)
        expected_count = end_idx - start_idx

        batch_in = work_dir / f"batch_{b:02d}_in.csv"
        batch_out = work_dir / f"batch_{b:02d}_out.csv"
        batch_outputs.append(batch_out)

        # Check if batch is already completed and valid
        is_done = False
        if batch_out.exists() and batch_out.stat().st_size > 0:
            with open(batch_out, "r", encoding="utf-8") as bf:
                out_reader = csv.reader(bf)
                out_header = next(out_reader, None)
                out_rows = list(out_reader)
                if len(out_rows) == expected_count:
                    # Verify first and last canonical_parent match
                    if out_rows[0][0] == input_rows[start_idx][0] and out_rows[-1][0] == input_rows[end_idx-1][0]:
                        is_done = True
                        completed_rows += expected_count
                        print(f"Batch {b:02d} [{start_idx}:{end_idx}] already completed ({expected_count} rows).")

        if not is_done:
            # Write batch input
            with open(batch_in, "w", newline="", encoding="utf-8") as bif:
                writer = csv.writer(bif)
                writer.writerow(header)
                writer.writerows(input_rows[start_idx:end_idx])

            print(f"Running batch {b:02d} [{start_idx}:{end_idx}] ({expected_count} rows)...")
            batch_tmp_out = work_dir / f"batch_{b:02d}_out.tmp"
            cmd = [str(args.solver), str(batch_in), str(args.memo_power)]
            
            with open(batch_tmp_out, "w", newline="", encoding="utf-8") as btof:
                proc = subprocess.run(cmd, stdout=btof, stderr=subprocess.PIPE, text=True)

            if proc.returncode != 0:
                print(f"ERROR: Solver failed on batch {b:02d} with code {proc.returncode}:\n{proc.stderr}", file=sys.stderr)
                sys.exit(1)

            # Validate tmp output
            with open(batch_tmp_out, "r", encoding="utf-8") as btof:
                tmp_reader = csv.reader(btof)
                tmp_header = next(tmp_reader, None)
                tmp_rows = list(tmp_reader)

            if len(tmp_rows) != expected_count:
                print(f"ERROR: Batch {b:02d} produced {len(tmp_rows)} rows, expected {expected_count}!", file=sys.stderr)
                sys.exit(1)

            # Atomic rename
            batch_tmp_out.replace(batch_out)
            completed_rows += expected_count
            print(f"Batch {b:02d} completed successfully. Progress: {completed_rows}/{total_rows} rows solved.")

    print(f"\nAll batches processed. Validating and combining into {output_path}...")
    combined_rows = []
    out_header = None

    for b, b_out in enumerate(batch_outputs):
        with open(b_out, "r", encoding="utf-8") as bf:
            reader = csv.reader(bf)
            h = next(reader)
            if out_header is None:
                out_header = h
            rows = list(reader)
            combined_rows.extend(rows)

    if len(combined_rows) != total_rows:
        print(f"ERROR: Combined row count {len(combined_rows)} != total rows {total_rows}", file=sys.stderr)
        sys.exit(1)

    # Validate parent alignment row-by-row
    for i in range(total_rows):
        if combined_rows[i][0] != input_rows[i][0]:
            print(f"ERROR: Row {i} canonical_parent mismatch! input: {input_rows[i][0]} vs combined: {combined_rows[i][0]}", file=sys.stderr)
            sys.exit(1)
        if combined_rows[i][1] != input_rows[i][1]:
            print(f"ERROR: Row {i} pair_top mismatch!", file=sys.stderr)
            sys.exit(1)
        if combined_rows[i][2] != input_rows[i][2]:
            print(f"ERROR: Row {i} other_top mismatch!", file=sys.stderr)
            sys.exit(1)

    # Write combined output atomically
    tmp_final = output_path.with_suffix(".tmp")
    with open(tmp_final, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(out_header)
        writer.writerows(combined_rows)
    tmp_final.replace(output_path)

    print(f"Successfully wrote {len(combined_rows)} verified rows to {output_path}.")
    print("NO outcome inspection performed (as required by confirmatory protocol).")

if __name__ == "__main__":
    main()

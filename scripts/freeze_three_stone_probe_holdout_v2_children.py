#!/usr/bin/env python3
"""Freeze legal 4-stone children for the v2 three-stone holdout.

This script is intentionally outcome-free. It reads only the parent column of
an already-frozen selection and reconstructs the historical child-input order:
legal fourth moves in increasing board-index order. Historical validation is
on the ordered line sequence; old files may use CRLF while the frozen v2 CSV
uses explicit LF.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
from pathlib import Path

N = 10
V = N * N
FULL_RE = re.compile(r"^children_(\d+)_(\d+)_(\d+)\.txt$")


def det3(a00: int, a01: int, a02: int,
         a10: int, a11: int, a12: int,
         a20: int, a21: int, a22: int) -> int:
    return (
        a00 * (a11 * a22 - a12 * a21)
        - a01 * (a10 * a22 - a12 * a20)
        + a02 * (a10 * a21 - a11 * a20)
    )


def forbidden4(ids: tuple[int, int, int, int]) -> bool:
    m: list[list[int]] = []
    for v in ids:
        x, y = v % N, v // N
        m.append([x * x + y * y, x, y, 1])
    d = 0
    for col in range(4):
        minor = [[m[r][c] for c in range(4) if c != col] for r in range(1, 4)]
        md = det3(*minor[0], *minor[1], *minor[2])
        d += (1 if col % 2 == 0 else -1) * m[0][col] * md
    return d == 0


def parse_parent(text: str) -> tuple[int, int, int]:
    vals = tuple(int(x) for x in text.split(","))
    if len(vals) != 3 or len(set(vals)) != 3:
        raise ValueError(f"expected three distinct points: {text!r}")
    if any(v < 0 or v >= V for v in vals):
        raise ValueError(f"point out of range: {text!r}")
    if vals != tuple(sorted(vals)):
        raise ValueError(f"parent must use canonical ascending point order: {text!r}")
    return vals


def child_lines(parent: tuple[int, int, int]) -> list[str]:
    occupied = set(parent)
    out: list[str] = []
    for move in range(V):
        if move in occupied:
            continue
        quad = tuple(sorted((*parent, move)))
        if forbidden4(quad):
            continue
        out.append(",".join(map(str, quad)))
    return out


def payload(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode("ascii")


def semantic_lines(data: bytes) -> list[str]:
    return data.decode("ascii").splitlines()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_historical(directory: Path) -> tuple[int, int, int]:
    full_files = []
    for path in sorted(directory.glob("children_*.txt")):
        m = FULL_RE.match(path.name)
        if m:
            full_files.append((path, tuple(map(int, m.groups()))))
    if not full_files:
        raise SystemExit(f"no historical three-stone child files found in {directory}")

    batch_files_checked = 0
    transport_differences = 0
    for path, parent in full_files:
        expected_lines = child_lines(parent)
        actual = path.read_bytes()
        actual_lines = semantic_lines(actual)
        if actual_lines != expected_lines:
            first = next(
                (i for i, (a, b) in enumerate(zip(actual_lines, expected_lines), start=1) if a != b),
                min(len(actual_lines), len(expected_lines)) + 1,
            )
            got = actual_lines[first - 1] if first <= len(actual_lines) else "<EOF>"
            want = expected_lines[first - 1] if first <= len(expected_lines) else "<EOF>"
            raise SystemExit(
                f"historical child-order semantic mismatch for {path.name} at line {first}: "
                f"committed={got!r} regenerated={want!r}; "
                f"rows={len(actual_lines)}/{len(expected_lines)}"
            )
        if actual != payload(expected_lines):
            transport_differences += 1

        safe = "_".join(map(str, parent))
        batch_lines: list[str] = []
        i = 0
        while True:
            bp = directory / f"children_{safe}_batch{i}.txt"
            if not bp.exists():
                break
            batch_lines.extend(semantic_lines(bp.read_bytes()))
            batch_files_checked += 1
            i += 1
        if batch_lines and batch_lines != actual_lines:
            raise SystemExit(f"historical batch semantic concatenation mismatch for {path.name}")
    return len(full_files), batch_files_checked, transport_differences


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("selection_csv", type=Path)
    ap.add_argument("output_csv", type=Path)
    ap.add_argument("--verify-existing-dir", type=Path)
    args = ap.parse_args()

    if args.verify_existing_dir is not None:
        parents_checked, batches_checked, transport_differences = verify_historical(args.verify_existing_dir)
        print(f"historical_parents_semantic_order_identical={parents_checked}")
        print(f"historical_batch_files_semantically_checked={batches_checked}")
        print(f"historical_full_files_with_transport_difference={transport_differences}")

    with args.selection_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows or "parent" not in rows[0]:
        raise SystemExit("selection must contain a parent column")

    forbidden_columns = {
        "loss_child", "outcome", "visited", "memo", "maxdepth", "seconds",
        "probe", "rank", "first_loss_rank",
    }
    bad = forbidden_columns.intersection(rows[0])
    if bad:
        raise SystemExit(f"selection contains forbidden result columns: {sorted(bad)}")

    records: list[dict[str, str | int]] = []
    seen_parents = set()
    for row in rows:
        parent_text = row["parent"]
        parent = parse_parent(parent_text)
        if parent in seen_parents:
            raise SystemExit(f"duplicate selected parent: {parent_text}")
        seen_parents.add(parent)
        children = child_lines(parent)
        if not children:
            raise SystemExit(f"selected parent has no legal child: {parent_text}")
        for rank, child in enumerate(children, start=1):
            child_points = list(map(int, child.split(",")))
            move = next(v for v in child_points if v not in parent)
            records.append({
                "parent": parent_text,
                "solver_default_rank": rank,
                "move": move,
                "child_state": child,
            })

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["parent", "solver_default_rank", "move", "child_state"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(records)

    data = args.output_csv.read_bytes()
    print(f"selected_parents={len(seen_parents)}")
    print(f"total_legal_children={len(records)}")
    counts: dict[str, int] = {}
    for r in records:
        counts[str(r["parent"])] = counts.get(str(r["parent"]), 0) + 1
    print("legal_children_per_parent=" + ",".join(f"{p}:{counts[p]}" for p in counts))
    print(f"output_sha256={sha256(data)}")
    print(f"output={args.output_csv}")


if __name__ == "__main__":
    main()

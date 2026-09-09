#!/usr/bin/env python3
"""Build the frozen v2 ranking from isolated probe outputs without labels.

This script deliberately never opens either source proof CSV.  It accepts only
(1) the already-frozen label-free holdout and (2) child input/probe files.
The ordering rule is the one frozen in THREE_STONE_PROBE_HOLDOUT_V2_PRE_RUN_RECEIPT.md:

  exact LOSS first; exact WIN excluded; unfinished PROBE by memo ascending;
  ties by the solver-default input order.

The child input text files are the authority for solver-default order.  Every
probe CSV must match its corresponding child file row-for-row, so file-system
ordering cannot silently change the tie break.
"""

import argparse
import csv
import hashlib
import re
from pathlib import Path

BUDGET = 1_000_000
CHILD_RE = re.compile(r"^children_(.+)_batch(\d+)\.txt$")
PROBE_RE = re.compile(r"^probe_isolated_(.+)_batch(\d+)_(\d+)\.csv$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parent_slug(parent: str) -> str:
    return parent.replace(",", "_")


def parse_state(text: str) -> tuple[int, ...]:
    try:
        vals = tuple(int(x) for x in text.split(","))
    except ValueError as exc:
        raise ValueError(f"bad state {text!r}") from exc
    if len(vals) != len(set(vals)):
        raise ValueError(f"duplicate point in state {text!r}")
    return vals


def child_of(parent: str, state: str) -> int:
    p = set(parse_state(parent))
    s = set(parse_state(state))
    if len(p) != 3 or len(s) != 4 or not p < s:
        raise ValueError(f"state {state!r} is not a one-child extension of {parent!r}")
    extra = s - p
    if len(extra) != 1:
        raise ValueError(f"cannot identify unique child for {parent!r} -> {state!r}")
    return next(iter(extra))


def read_holdout(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows or "parent" not in rows[0]:
        raise ValueError("holdout must contain parent column")
    forbidden = {"loss_child", "outcome", "label"}
    leaked = forbidden & set(rows[0])
    if leaked:
        raise ValueError(f"label-like columns forbidden in holdout: {sorted(leaked)}")
    parents = [r["parent"] for r in rows]
    if len(parents) != len(set(parents)):
        raise ValueError("duplicate parent in holdout")
    return parents


def discover_batches(probe_dir: Path, slug: str) -> tuple[dict[int, Path], dict[int, Path]]:
    children: dict[int, Path] = {}
    probes: dict[int, Path] = {}
    for path in probe_dir.iterdir():
        m = CHILD_RE.match(path.name)
        if m and m.group(1) == slug:
            idx = int(m.group(2))
            if idx in children:
                raise ValueError(f"duplicate child batch {idx} for {slug}")
            children[idx] = path
            continue
        m = PROBE_RE.match(path.name)
        if m and m.group(1) == slug and int(m.group(3)) == BUDGET:
            idx = int(m.group(2))
            if idx in probes:
                raise ValueError(f"duplicate probe batch {idx} for {slug}")
            probes[idx] = path
    if not children:
        raise ValueError(f"no child batches found for {slug}")
    if set(children) != set(probes):
        raise ValueError(
            f"child/probe batch mismatch for {slug}: "
            f"children={sorted(children)} probes={sorted(probes)}"
        )
    indices = sorted(children)
    if indices != list(range(indices[-1] + 1)):
        raise ValueError(f"non-contiguous batches for {slug}: {indices}")
    return children, probes


def read_parent_rows(parent: str, probe_dir: Path) -> list[dict[str, object]]:
    slug = parent_slug(parent)
    children, probes = discover_batches(probe_dir, slug)
    out: list[dict[str, object]] = []
    default_rank = 0
    seen_states: set[str] = set()

    for batch in sorted(children):
        expected = [
            x.strip()
            for x in children[batch].read_text(encoding="utf-8").splitlines()
            if x.strip()
        ]
        if not expected:
            raise ValueError(f"empty child batch: {children[batch]}")
        with probes[batch].open(newline="", encoding="utf-8") as f:
            got = list(csv.DictReader(f))
        if not got:
            raise ValueError(f"empty probe CSV: {probes[batch]}")
        required = {"state", "outcome", "memo"}
        missing = required - set(got[0])
        if missing:
            raise ValueError(f"probe CSV missing {sorted(missing)}: {probes[batch]}")
        got_states = [r["state"] for r in got]
        if got_states != expected:
            raise ValueError(
                f"probe rows do not match solver input order for {parent} batch {batch}"
            )

        for batch_rank, row in enumerate(got, start=1):
            state = row["state"]
            if state in seen_states:
                raise ValueError(f"duplicate child state for {parent}: {state}")
            seen_states.add(state)
            child = child_of(parent, state)
            outcome = row["outcome"].strip().upper()
            if outcome not in {"LOSS", "WIN", "PROBE"}:
                raise ValueError(f"unexpected outcome {outcome!r} for {state}")
            memo_text = row["memo"].strip()
            if not memo_text:
                raise ValueError(f"missing memo for {state}")
            try:
                memo = int(memo_text)
            except ValueError as exc:
                raise ValueError(f"non-integer memo {memo_text!r} for {state}") from exc
            if memo < 0:
                raise ValueError(f"negative memo for {state}")
            default_rank += 1
            out.append(
                {
                    "parent": parent,
                    "state": state,
                    "child": child,
                    "outcome": outcome,
                    "memo": memo,
                    "solver_default_rank": default_rank,
                    "batch_index": batch,
                    "batch_rank": batch_rank,
                }
            )
    return out


def sort_key(row: dict[str, object]) -> tuple[int, int, int]:
    outcome = str(row["outcome"])
    default_rank = int(row["solver_default_rank"])
    if outcome == "LOSS":
        return (0, 0, default_rank)
    if outcome == "PROBE":
        return (1, int(row["memo"]), default_rank)
    raise ValueError("WIN rows must be excluded before ranking")


def build(holdout: Path, probe_dir: Path, output: Path) -> None:
    parents = read_holdout(holdout)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "parent",
        "v2_rank",
        "state",
        "child",
        "probe_outcome",
        "memo",
        "solver_default_rank",
        "batch_index",
        "batch_rank",
        "rank_reason",
    ]
    rows_out: list[dict[str, object]] = []
    for parent in parents:
        measured = read_parent_rows(parent, probe_dir)
        candidates = [r for r in measured if r["outcome"] != "WIN"]
        ranked = sorted(candidates, key=sort_key)
        for rank, row in enumerate(ranked, start=1):
            outcome = str(row["outcome"])
            rows_out.append(
                {
                    "parent": parent,
                    "v2_rank": rank,
                    "state": row["state"],
                    "child": row["child"],
                    "probe_outcome": outcome,
                    "memo": row["memo"],
                    "solver_default_rank": row["solver_default_rank"],
                    "batch_index": row["batch_index"],
                    "batch_rank": row["batch_rank"],
                    "rank_reason": "exact_loss" if outcome == "LOSS" else "memo_ascending",
                }
            )

    with output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows_out)

    print(f"parents={len(parents)}")
    print(f"ranked_rows={len(rows_out)}")
    print(f"ranking_sha256={sha256(output)}")
    print(f"output={output}")
    print("source_proof_labels_opened=0")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("holdout", type=Path)
    p.add_argument("probe_dir", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    build(args.holdout, args.probe_dir, args.output)


if __name__ == "__main__":
    main()

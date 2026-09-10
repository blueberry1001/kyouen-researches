#!/usr/bin/env python3
"""Evaluate holdout-v2 only after the ranking has been frozen.

The evaluator implements docs/THREE_STONE_PROBE_HOLDOUT_V2_EVAL_AUDIT.md.
It joins labels by the frozen (source, source_index, parent) identity and compares
memo-order vs solver-default order on exactly the same unresolved PROBE rows.
"""

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def loss_labels(holdout: Path, source_dir: Path) -> dict[str, str]:
    labels: dict[str, str] = {}
    for h in read_csv(holdout):
        parent = h["parent"]
        src = source_dir / h["source"]
        rows = read_csv(src)
        i = int(h["source_index"])
        if i < 0 or i >= len(rows):
            raise ValueError(f"source_index out of range: {src}:{i}")
        r = rows[i]
        if int(r["index"]) != i or r["state"] != parent:
            raise ValueError(f"holdout/source identity mismatch for {parent}")
        loss = r["loss_child"].strip()
        if not loss:
            raise ValueError(f"missing loss_child for {parent}")
        labels[parent] = loss
    return labels


def median(xs: list[int]) -> float | None:
    return statistics.median(xs) if xs else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("holdout", type=Path)
    ap.add_argument("ranking", type=Path, help="already frozen ranking CSV")
    ap.add_argument("source_dir", type=Path)
    args = ap.parse_args()

    labels = loss_labels(args.holdout, args.source_dir)
    ranking = read_csv(args.ranking)
    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in ranking:
        by_parent[r["parent"]].append(r)

    unknown = set(by_parent) - set(labels)
    if unknown:
        raise ValueError(f"ranking contains parents outside holdout: {sorted(unknown)}")

    v2_ranks: list[int] = []
    default_ranks: list[int] = []
    better = tie = worse = 0
    probe_completion = 0
    rows_out: list[tuple[str, str, str, str]] = []

    for parent in labels:
        rows = by_parent.get(parent, [])
        if not rows:
            raise ValueError(f"ranking missing parent {parent}")
        loss = labels[parent]
        matching = [r for r in rows if r["state"] == loss]
        if not matching:
            # A true LOSS cannot be an exact WIN; absence therefore means a broken join/universe.
            raise ValueError(f"known loss child absent from ranked universe for {parent}: {loss}")
        lr = matching[0]
        outcome = lr["probe_outcome"].strip().upper()
        if outcome == "WIN":
            raise ValueError(f"known loss child was probed as WIN for {parent}: {loss}")
        if outcome == "LOSS":
            probe_completion += 1
            rows_out.append((parent, "probe-completion", "", ""))
            continue
        if outcome != "PROBE":
            raise ValueError(f"unexpected probe_outcome {outcome!r} for {loss}")

        unresolved = [r for r in rows if r["probe_outcome"].strip().upper() == "PROBE"]
        if not unresolved:
            raise ValueError(f"no unresolved rows for ordering parent {parent}")

        v2 = sorted(unresolved, key=lambda r: int(r["v2_rank"]))
        default = sorted(unresolved, key=lambda r: int(r["solver_default_rank"]))
        if {r["state"] for r in v2} != {r["state"] for r in default}:
            raise ValueError(f"asymmetric unresolved universe for {parent}")

        vr = next(i for i, r in enumerate(v2, 1) if r["state"] == loss)
        dr = next(i for i, r in enumerate(default, 1) if r["state"] == loss)
        v2_ranks.append(vr)
        default_ranks.append(dr)
        if vr < dr:
            better += 1
            verdict = "better"
        elif vr == dr:
            tie += 1
            verdict = "tie"
        else:
            worse += 1
            verdict = "worse"
        rows_out.append((parent, verdict, str(vr), str(dr)))

    success = bool(v2_ranks) and median(v2_ranks) < median(default_ranks) and better > worse

    print("parent,status,v2_unresolved_rank,default_unresolved_rank")
    for row in rows_out:
        print(",".join(row))
    print(f"ordering_parents={len(v2_ranks)}")
    print(f"probe_completion_parents={probe_completion}")
    print(f"v2_unresolved_median={median(v2_ranks)}")
    print(f"default_unresolved_median={median(default_ranks)}")
    print(f"better={better}")
    print(f"tie={tie}")
    print(f"worse={worse}")
    print(f"v2_rank_sum={sum(v2_ranks)}")
    print(f"default_rank_sum={sum(default_ranks)}")
    print(f"primary_success={'YES' if success else 'NO'}")


if __name__ == "__main__":
    main()

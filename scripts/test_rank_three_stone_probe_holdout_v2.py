#!/usr/bin/env python3
import csv
import importlib.util
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("rank_three_stone_probe_holdout_v2.py")
spec = importlib.util.spec_from_file_location("rank_v2", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def write_csv(path: Path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def make_fixture(root: Path):
    holdout = root / "holdout.csv"
    write_csv(
        holdout,
        ["source", "source_index", "parent", "selection_hash"],
        [
            {"source": "a.csv", "source_index": 40, "parent": "1,2,3", "selection_hash": "a"},
            {"source": "b.csv", "source_index": 41, "parent": "10,11,12", "selection_hash": "b"},
        ],
    )

    frozen = root / "frozen.csv"
    frozen_states = {
        "1,2,3": ["1,2,3,4", "1,2,3,5", "1,2,3,6", "1,2,3,7", "1,2,3,8"],
        "10,11,12": ["10,11,12,13", "10,11,12,14"],
    }
    frozen_rows = []
    for parent in ("1,2,3", "10,11,12"):
        for rank, state in enumerate(frozen_states[parent], start=1):
            frozen_rows.append({
                "parent": parent,
                "solver_default_rank": rank,
                "move": state.split(",")[-1],
                "child_state": state,
            })
    write_csv(frozen, ["parent", "solver_default_rank", "move", "child_state"], frozen_rows)

    (root / "children_1_2_3_batch0.txt").write_text(
        "1,2,3,4\n1,2,3,5\n1,2,3,6\n", encoding="utf-8"
    )
    (root / "children_1_2_3_batch1.txt").write_text(
        "1,2,3,7\n1,2,3,8\n", encoding="utf-8"
    )
    fields = ["state", "outcome", "visited", "maxdepth", "memo", "seconds"]
    write_csv(
        root / "probe_isolated_1_2_3_batch0_1000000.csv", fields,
        [
            {"state": "1,2,3,4", "outcome": "PROBE", "visited": 100, "maxdepth": 5, "memo": 50, "seconds": 1},
            {"state": "1,2,3,5", "outcome": "WIN", "visited": 80, "maxdepth": 4, "memo": 20, "seconds": 1},
            {"state": "1,2,3,6", "outcome": "PROBE", "visited": 100, "maxdepth": 5, "memo": 30, "seconds": 1},
        ],
    )
    write_csv(
        root / "probe_isolated_1_2_3_batch1_1000000.csv", fields,
        [
            {"state": "1,2,3,7", "outcome": "LOSS", "visited": 70, "maxdepth": 3, "memo": 99, "seconds": 1},
            {"state": "1,2,3,8", "outcome": "PROBE", "visited": 100, "maxdepth": 5, "memo": 30, "seconds": 1},
        ],
    )
    (root / "children_10_11_12_batch0.txt").write_text(
        "10,11,12,13\n10,11,12,14\n", encoding="utf-8"
    )
    write_csv(
        root / "probe_isolated_10_11_12_batch0_1000000.csv", fields,
        [
            {"state": "10,11,12,13", "outcome": "PROBE", "visited": 100, "maxdepth": 5, "memo": 9, "seconds": 1},
            {"state": "10,11,12,14", "outcome": "PROBE", "visited": 100, "maxdepth": 5, "memo": 4, "seconds": 1},
        ],
    )
    return holdout, frozen


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        holdout, frozen = make_fixture(root)
        out1 = root / "ranking1.csv"
        out2 = root / "ranking2.csv"
        mod.build(holdout, frozen, root, out1)
        mod.build(holdout, frozen, root, out2)
        if out1.read_bytes() != out2.read_bytes():
            raise SystemExit("ranking output is not byte deterministic")

        with out1.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        p1 = [r for r in rows if r["parent"] == "1,2,3"]
        if [r["state"] for r in p1] != ["1,2,3,7", "1,2,3,6", "1,2,3,8", "1,2,3,4"]:
            raise SystemExit(f"unexpected parent-1 order: {p1}")
        if any(r["state"] == "1,2,3,5" for r in rows):
            raise SystemExit("exact WIN leaked into LOSS-candidate ranking")
        p2 = [r for r in rows if r["parent"] == "10,11,12"]
        if [r["state"] for r in p2] != ["10,11,12,14", "10,11,12,13"]:
            raise SystemExit(f"unexpected parent-2 order: {p2}")
        if set(rows[0]) & {"loss_child", "label"}:
            raise SystemExit("label column leaked into ranking")

        # If both an input batch and its probe result disappear, the old code
        # silently accepted the truncated parent. Frozen-universe checking must reject it.
        child_b1 = root / "children_1_2_3_batch1.txt"
        probe_b1 = root / "probe_isolated_1_2_3_batch1_1000000.csv"
        child_bytes, probe_bytes = child_b1.read_bytes(), probe_b1.read_bytes()
        child_b1.unlink(); probe_b1.unlink()
        try:
            mod.build(holdout, frozen, root, root / "missing-both.csv")
        except ValueError as e:
            if "incomplete or altered probe child sequence" not in str(e):
                raise
        else:
            raise SystemExit("missing child+probe batch pair was silently accepted")
        child_b1.write_bytes(child_bytes); probe_b1.write_bytes(probe_bytes)

        # Row-order mismatch must fail.
        bad = root / "probe_isolated_10_11_12_batch0_1000000.csv"
        with bad.open(newline="", encoding="utf-8") as f:
            bad_rows = list(csv.DictReader(f)); bad_fields = list(bad_rows[0])
        write_csv(bad, bad_fields, list(reversed(bad_rows)))
        try:
            mod.build(holdout, frozen, root, root / "bad.csv")
        except ValueError as e:
            if "solver input order" not in str(e):
                raise
        else:
            raise SystemExit("mismatched probe/input order was accepted")

    print("v2_ranking_synthetic_test=PASS")
    print("exact_loss_priority=PASS")
    print("exact_win_exclusion=PASS")
    print("memo_ascending=PASS")
    print("solver_default_tie_break=PASS")
    print("byte_determinism=PASS")
    print("label_free_output=PASS")
    print("input_order_guard=PASS")
    print("complete_frozen_child_universe_guard=PASS")
    print("missing_input_and_probe_pair_rejected=PASS")


if __name__ == "__main__":
    main()

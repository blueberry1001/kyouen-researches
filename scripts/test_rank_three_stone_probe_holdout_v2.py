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

    # Parent 1: exact WIN is excluded, exact LOSS is first regardless of memo,
    # then PROBE rows are memo ascending with default-order tie break.
    (root / "children_1_2_3_batch0.txt").write_text(
        "1,2,3,4\n1,2,3,5\n1,2,3,6\n", encoding="utf-8"
    )
    (root / "children_1_2_3_batch1.txt").write_text(
        "1,2,3,7\n1,2,3,8\n", encoding="utf-8"
    )
    fields = ["state", "outcome", "visited", "maxdepth", "memo", "seconds"]
    write_csv(
        root / "probe_isolated_1_2_3_batch0_1000000.csv",
        fields,
        [
            {"state": "1,2,3,4", "outcome": "PROBE", "visited": 100, "maxdepth": 5, "memo": 50, "seconds": 1},
            {"state": "1,2,3,5", "outcome": "WIN", "visited": 80, "maxdepth": 4, "memo": 20, "seconds": 1},
            {"state": "1,2,3,6", "outcome": "PROBE", "visited": 100, "maxdepth": 5, "memo": 30, "seconds": 1},
        ],
    )
    write_csv(
        root / "probe_isolated_1_2_3_batch1_1000000.csv",
        fields,
        [
            {"state": "1,2,3,7", "outcome": "LOSS", "visited": 70, "maxdepth": 3, "memo": 99, "seconds": 1},
            {"state": "1,2,3,8", "outcome": "PROBE", "visited": 100, "maxdepth": 5, "memo": 30, "seconds": 1},
        ],
    )

    # Parent 2: no exact completion; exercise memo ordering alone.
    (root / "children_10_11_12_batch0.txt").write_text(
        "10,11,12,13\n10,11,12,14\n", encoding="utf-8"
    )
    write_csv(
        root / "probe_isolated_10_11_12_batch0_1000000.csv",
        fields,
        [
            {"state": "10,11,12,13", "outcome": "PROBE", "visited": 100, "maxdepth": 5, "memo": 9, "seconds": 1},
            {"state": "10,11,12,14", "outcome": "PROBE", "visited": 100, "maxdepth": 5, "memo": 4, "seconds": 1},
        ],
    )
    return holdout


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        holdout = make_fixture(root)
        out1 = root / "ranking1.csv"
        out2 = root / "ranking2.csv"
        mod.build(holdout, root, out1)
        mod.build(holdout, root, out2)
        if out1.read_bytes() != out2.read_bytes():
            raise SystemExit("ranking output is not byte deterministic")

        with out1.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        p1 = [r for r in rows if r["parent"] == "1,2,3"]
        if [r["state"] for r in p1] != [
            "1,2,3,7",  # exact LOSS first
            "1,2,3,6",  # memo 30, earlier default rank
            "1,2,3,8",  # memo 30, later default rank
            "1,2,3,4",  # memo 50
        ]:
            raise SystemExit(f"unexpected parent-1 order: {p1}")
        if any(r["state"] == "1,2,3,5" for r in rows):
            raise SystemExit("exact WIN leaked into LOSS-candidate ranking")
        p2 = [r for r in rows if r["parent"] == "10,11,12"]
        if [r["state"] for r in p2] != ["10,11,12,14", "10,11,12,13"]:
            raise SystemExit(f"unexpected parent-2 order: {p2}")
        if set(rows[0]) & {"loss_child", "label"}:
            raise SystemExit("label column leaked into ranking")

        # Row-order mismatch must fail: the child input files, not directory/file
        # ordering, are the authority for solver-default tie breaks.
        bad = root / "probe_isolated_10_11_12_batch0_1000000.csv"
        with bad.open(newline="", encoding="utf-8") as f:
            bad_rows = list(csv.DictReader(f))
            bad_fields = list(bad_rows[0])
        write_csv(bad, bad_fields, list(reversed(bad_rows)))
        try:
            mod.build(holdout, root, root / "bad.csv")
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


if __name__ == "__main__":
    main()

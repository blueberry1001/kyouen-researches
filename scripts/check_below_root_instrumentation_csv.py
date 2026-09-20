#!/usr/bin/env python3
import csv
import sys
from pathlib import Path

REQUIRED = {
    "state", "depth", "total_visited", "depth_visited", "expanded", "terminal",
    "entry_get", "entry_hit_loss", "entry_hit_win", "child_get",
    "child_hit_loss", "child_hit_win", "put_loss", "put_win",
    "unique_children", "cached_loss_children", "cached_win_children",
    "unknown_children", "children_entered", "win_nodes", "loss_nodes",
    "cutoff_index_sum", "work_into_win_child", "work_into_loss_child",
    "calls_into_win_child", "calls_into_loss_child",
}


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check_below_root_instrumentation_csv.py FILE.csv")
    path = Path(sys.argv[1])
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        fail("no data rows")
    missing = REQUIRED - set(rows[0])
    if missing:
        fail("missing columns: " + ",".join(sorted(missing)))

    total_by_state = {}
    depth_sum_by_state = {}
    for i, row in enumerate(rows, start=2):
        state = row["state"]
        try:
            d = int(row["depth"])
            v = {k: int(row[k]) for k in REQUIRED - {"state"}}
        except ValueError as e:
            fail(f"row {i}: non-integer counter: {e}")
        if not 0 <= d <= 100:
            fail(f"row {i}: depth out of range: {d}")
        total = v["total_visited"]
        old = total_by_state.setdefault(state, total)
        if old != total:
            fail(f"{state}: inconsistent total_visited")
        depth_sum_by_state[state] = depth_sum_by_state.get(state, 0) + v["depth_visited"]

        if v["depth_visited"] != v["terminal"] + v["expanded"]:
            fail(f"{state} depth {d}: depth_visited != terminal + expanded")
        if v["entry_get"] != v["depth_visited"] + v["entry_hit_loss"] + v["entry_hit_win"]:
            fail(f"{state} depth {d}: entry lookup accounting mismatch")
        if v["child_get"] != v["unique_children"]:
            fail(f"{state} depth {d}: child_get != unique_children")
        if v["child_get"] != v["child_hit_loss"] + v["child_hit_win"] + v["unknown_children"]:
            fail(f"{state} depth {d}: child-prefetch accounting mismatch")
        if v["cached_loss_children"] != v["child_hit_loss"] or v["cached_win_children"] != v["child_hit_win"]:
            fail(f"{state} depth {d}: cached-child counters disagree with prefetch hits")
        if v["children_entered"] < v["calls_into_win_child"] + v["calls_into_loss_child"]:
            fail(f"{state} depth {d}: recursive calls exceed consumed children")
        if 9 <= d <= 17:
            if v["put_loss"] + v["put_win"] != v["depth_visited"]:
                fail(f"{state} depth {d}: memo put accounting mismatch")
        elif v["put_loss"] or v["put_win"]:
            fail(f"{state} depth {d}: memo put outside supported depth 9..17")
        if v["win_nodes"] + v["loss_nodes"] != v["depth_visited"]:
            fail(f"{state} depth {d}: completed outcome accounting mismatch")
        if v["work_into_win_child"] > total or v["work_into_loss_child"] > total:
            fail(f"{state} depth {d}: inclusive work exceeds total visited")

    for state, total in total_by_state.items():
        if depth_sum_by_state[state] != total:
            fail(f"{state}: sum(depth_visited)={depth_sum_by_state[state]} != total_visited={total}")

    print(f"PASS: {len(rows)} rows, {len(total_by_state)} states")


if __name__ == "__main__":
    main()

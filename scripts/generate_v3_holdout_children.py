#!/usr/bin/env python3
"""Generate safe non-terminal children for Staged Probe V3 Holdout parents."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V3_DIR = REPO_ROOT / "results" / "10x10" / "staged-v3-holdout"
CHILDREN_DIR = V3_DIR / "children"
PRIMARY_PARENTS_CSV = V3_DIR / "holdout_v3_parents_primary.csv"
BATCH_SIZE = 20


def det3(a, b, c, d, e, f, g, h, i):
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def forbidden(a, b, c, d, n=10):
    pts = [a, b, c, d]
    m = []
    for p in pts:
        x = p % n
        y = p // n
        m.append([x * x + y * y, x, y, 1])
    z = 0
    for col in range(4):
        sub = []
        for r in range(1, 4):
            row = [m[r][j] for j in range(4) if j != col]
            sub.append(row)
        md = det3(sub[0][0], sub[0][1], sub[0][2], sub[1][0], sub[1][1], sub[1][2], sub[2][0], sub[2][1], sub[2][2])
        sign = -1 if col % 2 else 1
        z += sign * m[0][col] * md
    return z == 0


def generate_children(parent: tuple[int, int, int]) -> list[str]:
    p1, p2, p3 = parent
    children = []
    for p4 in range(100):
        if p4 in (p1, p2, p3):
            continue
        if not forbidden(p1, p2, p3, p4):
            children.append(",".join(str(x) for x in sorted((p1, p2, p3, p4))))
    return sorted(children)


def main() -> None:
    CHILDREN_DIR.mkdir(parents=True, exist_ok=True)
    with PRIMARY_PARENTS_CSV.open(newline="", encoding="utf-8") as f:
        parents = [tuple(int(x) for x in r["parent_canonical"].split(",")) for r in csv.DictReader(f)]

    all_tasks = []
    parent_stats = []
    for p in parents:
        p_str = f"{p[0]},{p[1]},{p[2]}"
        safe_p = f"{p[0]}_{p[1]}_{p[2]}"
        children = generate_children(p)
        (CHILDREN_DIR / f"children_{safe_p}.txt").write_text("\n".join(children) + "\n", encoding="utf-8")
        batches = [children[i : i + BATCH_SIZE] for i in range(0, len(children), BATCH_SIZE)]
        for b_idx, b_children in enumerate(batches):
            (CHILDREN_DIR / f"children_{safe_p}_batch{b_idx}.txt").write_text("\n".join(b_children) + "\n", encoding="utf-8")
            for pos, state in enumerate(b_children):
                all_tasks.append({"parent": p_str, "batch": b_idx, "batch_position": pos, "state": state})
        parent_stats.append({"parent": p_str, "children_count": len(children), "batches_count": len(batches)})

    task_csv = V3_DIR / "exact_task_list.csv"
    with task_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["parent", "batch", "batch_position", "state"])
        w.writeheader()
        w.writerows(all_tasks)

    h = hashlib.sha256()
    for t in all_tasks:
        data = json.dumps([t["parent"], int(t["batch"]), int(t["batch_position"]), t["state"]], separators=(",", ":")).encode("utf-8")
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    task_digest = h.hexdigest()
    manifest = {
        "parent_count": len(parents),
        "total_tasks": len(all_tasks),
        "task_set_sha256": task_digest,
        "parent_stats": parent_stats,
    }
    (V3_DIR / "tasks_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Generated tasks for {len(parents)} parents.")
    print(f"Total tasks: {len(all_tasks)}")
    print(f"Task set SHA256: {task_digest}")
    for ps in parent_stats:
        print(f"  Parent {ps['parent']:<12} children: {ps['children_count']}")


if __name__ == "__main__":
    main()

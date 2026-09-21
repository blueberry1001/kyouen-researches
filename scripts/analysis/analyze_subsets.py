#!/usr/bin/env python3
"""8石LOSSルート部分集合の構造解析。

10x10 LOSSルート R = {90,61,2,73,69,66,13,91} の部分集合の勝敗構造を
既存CSVから機械的に再構築し、LOSS族のコア構造・探索コストの偏りを報告する。
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # research-properties ワークツリー
RES = ROOT / "results" / "10x10"
SCRATCH = ROOT / "scratch" / "kyouen-local-handoff"

R = {90, 61, 2, 73, 69, 66, 13, 91}


def parse_state(s: str) -> frozenset:
    return frozenset(int(x) for x in s.split(","))


def load_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    # 層別 LOSS 部分集合
    loss_by_count: dict[int, list[frozenset]] = defaultdict(list)
    win_by_count: dict[int, list[frozenset]] = defaultdict(list)

    # (ファイル, 石数)
    files = [
        (RES / "three-stone-subsets-of-medium-loss.csv", 3),
        (RES / "four-stone-subsets-of-medium-loss.csv", 4),
        (RES / "five-stone-subsets-of-medium-loss.csv", 5),
        (RES / "six-stone-subsets-of-medium-loss.csv", 6),
        (RES / "seven-stone-subsets-of-medium-loss.csv", 7),
    ]
    for p, n in files:
        for row in load_csv(p):
            st = parse_state(row["state"])
            if len(st) != n:
                print(f"  [warn] {p.name}: state len mismatch: {row['state']}")
            if row["outcome"] == "LOSS":
                loss_by_count[n].append(st)
            else:
                win_by_count[n].append(st)

    # 2石 (HANDOFF.md と child-proof CSV から)
    loss_by_count[2] = [frozenset({61, 66}), frozenset({90, 61})]
    loss_by_count[8] = [R]

    print("=== R = {90,61,2,73,69,66,13,91} の部分集合の LOSS 数 ===")
    for k in sorted(loss_by_count):
        n_loss = len(loss_by_count[k])
        n_win = len(win_by_count[k])
        total = n_loss + n_win
        print(f"  {k}石: LOSS {n_loss:3d} / WIN {n_win:3d} (total {total})")

    print("\n=== LOSS の層別構造 ===")
    for k in sorted(loss_by_count):
        losses = sorted(loss_by_count[k], key=lambda s: sorted(s))
        # 共通部分集合
        inter = set.intersection(*[set(s) for s in losses]) if losses else set()
        inter = frozenset(inter)
        # 各 LOSS が含む最小コア候補
        print(f"  {k}石 LOSS {len(losses)}個:")
        print(f"    共通部分: {sorted(inter)}")
        print(f"    全リスト: {[sorted(s) for s in losses]}")

    print("\n=== 3石の探索コスト (EXACT_INDEPENDENT_SEARCH のみ) ===")
    rows3 = [r for r in load_csv(RES / "three-stone-subsets-of-medium-loss.csv")]
    exact3 = [r for r in rows3 if r["classification_source"] == "EXACT_INDEPENDENT_SEARCH"]
    costs = []
    for r in exact3:
        try:
            visited = int(r["visited"])
        except ValueError:
            continue
        st = parse_state(r["state"])
        costs.append((visited, st, r["outcome"]))
    costs.sort(reverse=True)
    print("  上位10 (visited, stones, outcome):")
    for visited, st, out in costs[:10]:
        print(f"    {visited:>12,}  {sorted(st)}  {out}")
    print("  下位5:")
    for visited, st, out in costs[-5:]:
        print(f"    {visited:>12,}  {sorted(st)}  {out}")

    # 3石 LOSS と WIN のコスト分布
    loss_costs = [v for v, s, o in costs if o == "LOSS"]
    win_costs = [v for v, s, o in costs if o == "WIN"]
    if loss_costs:
        print(f"  LOSS visited: {loss_costs}")
    if win_costs:
        print(f"  WIN visited 平均={sum(win_costs)/len(win_costs):,.0f} "
              f"中央値={sorted(win_costs)[len(win_costs)//2]:,} min={min(win_costs):,}")

    print("\n=== 3石探索コストと石の位置 (表形式) ===")
    # 座標: id = y*10 + x
    def coord(i):
        return (i % 10, i // 10)

    def on_edge(i):
        x, y = coord(i)
        return x in (0, 9) or y in (0, 9)

    def on_corner(i):
        x, y = coord(i)
        return x in (0, 9) and y in (0, 9)

    for visited, st, out in sorted(costs, reverse=True):
        print(f"  {sorted(st)}".ljust(22), f"visited={visited:>12,}", out.ljust(4),
              f"edge={sum(on_edge(i) for i in st)}/3 corner={sum(on_corner(i) for i in st)}")

    # 90-69-results.csv の解析
    print("\n=== 90-69-results.csv の TABLE_FULL の座標 ===")
    r69 = SCRATCH / "90-69-results.csv"
    if r69.exists():
        for row in load_csv(r69):
            if row["outcome"] in ("TABLE_FULL", "TIMEOUT", "ERROR"):
                print(f"  {row['index']}: {row['state']} {row['outcome']} "
                      f"visited={row['visited']} memo={row['memo']} shrink={row['shrink']} "
                      f"load={row['load']}")


if __name__ == "__main__":
    main()
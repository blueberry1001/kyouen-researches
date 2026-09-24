#!/usr/bin/env python3
"""探索6: 証明書 witness 鎖・石数分布・最適対局長、円上格子点の真の成長。"""
from __future__ import annotations

import json
import math
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
OUT.mkdir(parents=True, exist_ok=True)
CERTS = ROOT / "night-research"


def parse_cert(path: Path):
    with path.open("rb") as f:
        magic = f.read(8)
        version, board = struct.unpack("<II", f.read(8))
        node_count = struct.unpack("<Q", f.read(8))[0]
        root_lo = struct.unpack("<Q", f.read(8))[0]
        root_hi, forbidden = struct.unpack("<II", f.read(8))
        nodes = []
        for _ in range(node_count):
            data = f.read(16)
            lo, hi, outcome, witness, rank, reserved = struct.unpack("<QIBBBB", data)
            nodes.append({
                "lo": lo,
                "hi": hi,
                "outcome": outcome,
                "witness": witness,
                "rank": rank,
            })
    return {
        "magic": magic,
        "version": version,
        "board": board,
        "node_count": node_count,
        "root_lo": root_lo,
        "root_hi": root_hi,
        "forbidden": forbidden,
        "nodes": nodes,
    }


def state_of(node, board):
    """lo/hi から占有点集合を復元。hi は board<=64 なら実質0。"""
    pts = []
    bits = node["lo"]
    for i in range(min(64, board * board)):
        if bits & (1 << i):
            pts.append(i)
    bits = node["hi"]
    for i in range(64, board * board):
        if bits & (1 << (i - 64)):
            pts.append(i)
    return pts


def analyze_cert(path: Path):
    c = parse_cert(path)
    n = c["board"]
    V = n * n
    nodes = c["nodes"]
    by_key = {}
    for node in nodes:
        key = (node["lo"], node["hi"])
        by_key[key] = node

    # stone histogram
    stones = Counter(V - node["rank"] for node in nodes)
    outcome_by_stones = defaultdict(lambda: Counter())
    for node in nodes:
        k = V - node["rank"]
        outcome_by_stones[k]["LOSS" if node["outcome"] == 1 else "WIN"] += 1

    # witness chain: start at root, follow witness while WIN
    key = (c["root_lo"], c["root_hi"])
    chain = []
    seen = set()
    while key in by_key and key not in seen:
        seen.add(key)
        node = by_key[key]
        k = V - node["rank"]
        pts = state_of(node, n)
        chain.append({
            "stones": k,
            "outcome": "LOSS" if node["outcome"] == 1 else "WIN",
            "witness": node["witness"],
            "n_occupied": len(pts),
        })
        if node["outcome"] != 2:  # not WIN
            break
        w = node["witness"]
        if w == 255 or w >= V:
            break
        # child = parent + witness
        lo, hi = node["lo"], node["hi"]
        if w < 64:
            lo |= (1 << w)
        else:
            hi |= (1 << (w - 64))
        key = (lo, hi)

    # terminal nodes: LOSS with no children in cert = deepest LOSS
    max_stones = max(stones)
    terminals = [node for node in nodes if (V - node["rank"]) == max_stones]

    # distribution of legal-move counts is not in cert; instead: witness uniqueness
    # parent of each node via reverse index (who points to me)
    children_of = defaultdict(list)
    for node in nodes:
        if node["outcome"] == 2:
            w = node["witness"]
            if w == 255 or w >= V:
                continue
            lo, hi = node["lo"], node["hi"]
            if w < 64:
                lo |= (1 << w)
            else:
                hi |= (1 << (w - 64))
            children_of[(node["lo"], node["hi"])].append(((lo, hi), "witness"))
        else:
            # LOSS: all legal children should be in cert — we cannot regenerate
            # legal moves without geometry; skip
            pass

    return {
        "n": n,
        "nodes": c["node_count"],
        "forbidden": c["forbidden"],
        "root_outcome": "LOSS" if by_key[(c["root_lo"], c["root_hi"])]["outcome"] == 1 else "WIN",
        "stone_hist": dict(sorted(stones.items())),
        "max_stones_in_cert": max_stones,
        "min_stones_in_cert": min(stones),
        "terminal_count_at_max": len(terminals),
        "witness_chain_length": len(chain),
        "witness_chain_stones": [x["stones"] for x in chain],
        "witness_chain_outcomes": [x["outcome"] for x in chain],
        "witness_chain": chain,
        "loss_fraction": sum(1 for node in nodes if node["outcome"] == 1) / len(nodes),
        "outcome_by_stones": {k: dict(v) for k, v in sorted(outcome_by_stones.items())},
    }


def true_max_circle(n):
    best = 0
    info = None
    for i2 in range(-1, 2 * n + 1):
        for j2 in range(-1, 2 * n + 1):
            dist = Counter()
            for x in range(n):
                for y in range(n):
                    d4 = (2 * x - i2) ** 2 + (2 * y - j2) ** 2
                    dist[d4] += 1
            for d4, cnt in dist.items():
                if d4 > 0 and cnt > best:
                    best = cnt
                    info = (i2, j2, d4, cnt)
    return best, info


def main():
    report = {"certs": {}}

    print("=== 証明書 witness 鎖と石数分布 ===")
    for n in range(1, 10):
        path = CERTS / f"kyouen-{n}x{n}.cert"
        if not path.exists():
            print(f"  n={n}: missing")
            continue
        r = analyze_cert(path)
        report["certs"][n] = r
        print(f"  n={n}: nodes={r['nodes']:,} root={r['root_outcome']} "
              f"chain_stones={r['witness_chain_stones']} maxK={r['max_stones_in_cert']} "
              f"terminals={r['terminal_count_at_max']} loss_frac={r['loss_fraction']:.4f}")
        print(f"       stone_hist={r['stone_hist']}")

    print("\n=== 円上格子点: n=13..24 の真の最大 (公式破綻後の追跡) ===")
    circles = {}
    for n in range(13, 25):
        best, info = true_max_circle(n)
        circles[n] = {"max": best, "info": info}
        print(f"  n={n:2d}: max={best:2d}  center=({info[0]}/2,{info[1]}/2) N={info[2]}")
    report["max_circle_13_24"] = circles

    # Compare with K_n and winner
    print("\n=== witness 鎖の最終石数 vs K_n ===")
    K_true = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 14, 8: 15, 9: 17}
    for n, r in report["certs"].items():
        chain_end = r["witness_chain_stones"][-1] if r["witness_chain_stones"] else None
        print(f"  n={n}: chain_end={chain_end} cert_max={r['max_stones_in_cert']} "
              f"K_true={K_true.get(n)} chain_outcomes={r['witness_chain_outcomes']}")

    out = OUT / "exploration_report_6.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

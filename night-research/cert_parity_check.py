#!/usr/bin/env python3
"""Read KYOENC3 certificates and check parity locking + extract K_n."""

import struct
import sys
from collections import defaultdict


def analyze(path):
    with open(path, "rb") as f:
        magic = f.read(8)
        version, board_size = struct.unpack("<II", f.read(8))
        node_count = struct.unpack("<Q", f.read(8))[0]
        root_lo = struct.unpack("<Q", f.read(8))[0]
        root_hi, forbidden = struct.unpack("<II", f.read(8))
        V = board_size * board_size
        rank_outcome = defaultdict(lambda: defaultdict(int))
        for _ in range(node_count):
            data = f.read(16)
            lo, hi, outcome, witness, rank, reserved = struct.unpack("<QIBBBB", data)
            k = V - rank
            rank_outcome[k][outcome] += 1
    K = max(rank_outcome.keys())
    parity_locked = True
    mixed = []
    for k in sorted(rank_outcome):
        d = rank_outcome[k]
        loss, win = d.get(1, 0), d.get(2, 0)
        locked = (k % 2 == 0 and win == 0) or (k % 2 == 1 and loss == 0)
        if not locked:
            parity_locked = False
            mixed.append((k, loss, win))
    return {
        "n": board_size,
        "nodes": node_count,
        "forbidden": forbidden,
        "K": K,
        "parity_locked": parity_locked,
        "mixed_layers": mixed,
        "layers": {
            k: {"LOSS": rank_outcome[k].get(1, 0), "WIN": rank_outcome[k].get(2, 0)}
            for k in sorted(rank_outcome)
        },
    }


if __name__ == "__main__":
    import json

    results = {}
    for n in range(1, 10):
        path = f"night-research/kyouen-{n}x{n}.cert"
        try:
            r = analyze(path)
        except FileNotFoundError:
            print(f"n={n}: cert not found, skipping")
            continue
        results[n] = r
        status = "LOCKED" if r["parity_locked"] else f"MIXED at {r['mixed_layers'][:5]}"
        print(f"n={n}: K={r['K']} nodes={r['nodes']} parity={status}")
    with open("night-research/cycle6-cert-parity.json", "w") as f:
        json.dump(results, f, indent=2)
    print("wrote night-research/cycle6-cert-parity.json")

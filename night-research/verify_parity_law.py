#!/usr/bin/env python3
"""Verify the structural parity law of KYOENC3 certificates.

Claim (proof by certgen traversal): every certificate node at stone count k
satisfies  outcome == root_outcome XOR (k mod 2),  because every certificate
edge adds exactly one stone and flips the outcome (WIN -> single LOSS
witness child; LOSS -> all WIN children).

Also: decode the deepest node of each certificate and verify with our own
integer geometry that it is a legal safe position (no forbidden quad fully
inside). This makes cert-K a *rigorously verified lower bound* on K_n.
"""

import struct
import json
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "night-research"


def det4(p0, p1, p2, p3):
    rows = [p0, p1, p2, p3]

    def minor3(r, cols):
        m = [[rows[i][c] for c in cols] for i in r]
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    det = 0
    for c0 in range(4):
        sign = 1 if c0 % 2 == 0 else -1
        cols = [c for c in range(4) if c != c0]
        det += sign * rows[0][c0] * minor3([1, 2, 3], cols)
    return det


def forbidden_quads(n):
    V = n * n
    rows = [(x * x + y * y, x, y, 1) for y in range(n) for x in range(n)]
    quads = []
    for ids in combinations(range(V), 4):
        if det4(*[rows[i] for i in ids]) == 0:
            quads.append(ids)
    return quads


def analyze(path):
    with open(path, "rb") as f:
        magic = f.read(8)
        version, n = struct.unpack("<II", f.read(8))
        node_count = struct.unpack("<Q", f.read(8))[0]
        root_lo = struct.unpack("<Q", f.read(8))[0]
        root_hi, forbidden_count = struct.unpack("<II", f.read(8))
        V = n * n
        parity_violations = 0
        deepest_k = -1
        deepest_state = None
        outcome_at_k = {}
        root_outcome = None
        for i in range(node_count):
            data = f.read(16)
            lo, hi, outcome, witness, rank, reserved = struct.unpack("<QIBBBB", data)
            k = V - rank
            # root outcome = outcome of node 0 (the empty board, written first)
            if root_outcome is None:
                root_outcome = outcome
            expected = root_outcome if k % 2 == 0 else (3 - root_outcome)
            if outcome != expected:
                parity_violations += 1
            outcome_at_k.setdefault(k, set()).add(outcome)
            if k > deepest_k:
                deepest_k = k
                deepest_state = (lo, hi)
    return {
        "n": n,
        "nodes": node_count,
        "parity_violations": parity_violations,
        "deepest_k": deepest_k,
        "deepest_state": deepest_state,
        "outcome_unique_per_k": {k: sorted(v) for k, v in sorted(outcome_at_k.items())},
        "board": n,
        "V": V,
        "forbidden_count_cert": forbidden_count,
    }


def verify_safe(n, state_lo, state_hi):
    """Check the position has no forbidden quad fully inside (own geometry)."""
    V = n * n
    occ = state_lo | (state_hi << 64)
    quads = forbidden_quads(n)
    bad = 0
    for ids in quads:
        m = 0
        for i in ids:
            m |= 1 << i
        if (m & occ) == m:
            bad += 1
    return bad, len(quads), bin(occ).count("1")


if __name__ == "__main__":
    import sys

    ns = [int(a) for a in sys.argv[1:]] or list(range(1, 10))
    results = {}
    for n in ns:
        path = OUT / f"kyouen-{n}x{n}.cert"
        if not path.exists():
            print(f"n={n}: cert not found")
            continue
        r = analyze(str(path))
        bad, total_quads, stones = verify_safe(n, *r["deepest_state"])
        r["deepest_safe_check"] = {
            "forbidden_quads_inside": bad,
            "total_quads": total_quads,
            "stones": stones,
        }
        results[n] = {
            "n": n,
            "nodes": r["nodes"],
            "parity_violations": r["parity_violations"],
            "deepest_k": r["deepest_k"],
            "deepest_safe": bad == 0,
            "stones_at_deepest": stones,
        }
        print(
            f"n={n}: parity_violations={r['parity_violations']}/{r['nodes']}  "
            f"deepest k={r['deepest_k']} safe={bad == 0} ({bad}/{total_quads} quads inside)",
            flush=True,
        )
    # merge into existing results file if present
    out_path = OUT / "cycle6-parity-law-verify.json"
    merged = {}
    if out_path.exists():
        merged = json.loads(out_path.read_text())
    for k_str, v in results.items():
        merged[str(k_str)] = v
    out_path.write_text(json.dumps(merged, indent=2))
    print(f"wrote {out_path}")


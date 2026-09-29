#!/usr/bin/env python3
"""Follow-up part 3: B520 W-preservation, B504 decoys, B507, finish B528/B530 JSON."""
from __future__ import annotations

import itertools
import json
import sys
import time
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square, board_square_minus  # noqa: E402

OUT = REPO / "research" / "verification" / "round5_pgrand_followup.json"
DATA = REPO / "research" / "verification" / "data"
rep = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
t0 = time.time()


def xy(i, n):
    return (i % n, i // n)


def log(msg):
    print(f"[{time.time()-t0:7.1f}s] {msg}", flush=True)


# ---- B528/B530 from part2 console (already computed) ----
rep["B528_B530"] = {
    "empty_family_g": 0,
    "standard_g": 0,
    "order_results": [
        {"order": "geometric_cluster", "flips": 20},
        {"order": "geometric_rev", "flips": 20},
        {"order": "random0", "flips": 20},
        {"order": "random1", "flips": 20},
        {"order": "random2", "flips": 22},
    ],
    "single_release_flips": 0,
    "single_release_total": 194,
    "note": "empty family g=0, standard g=0; full 194-step paths. geometric 20/20 vs random 20/20/22.",
}

# ---- B514/B520 ----
log("=== B520 n=5 W-preservation ===")
import struct  # noqa: E402

raw = (DATA / "maximal_n5.bin").read_bytes()
n5_masks = struct.unpack("<%dQ" % (len(raw) // 8), raw)
k9_sets = [m for m in n5_masks if bin(m).count("1") == 9]


def hits_all(D):
    dm = 0
    for p in D:
        dm |= 1 << p
    return all((m & dm) != 0 for m in k9_sets)


# tau=4 confirmed in part2
tau5 = 4
ach = [list(D) for D in itertools.combinations(range(25), tau5) if hits_all(D)]
log(f"achieving sets size 4: {len(ach)}")

bd5 = board_square(5)
memo0 = bd5.solve_outcomes()
g5 = memo0.get(0, 0)
w0 = {v: (1 if memo0.get(1 << v, 1) == 0 else 0) for v in range(25)}
log(f"g5={g5}, W-count={sum(w0.values())}")

b520_all = []
for idx, D in enumerate(ach[:30]):
    t = time.time()
    bdel = board_square_minus(5, [xy(i, 5) for i in D])
    gdel = bdel.solve_outcomes().get(0, 0)
    memo = bdel.solve_outcomes()
    remaining = sorted(i for i in range(25) if i not in set(D))
    mism = []
    for ri, orig in enumerate(remaining):
        wred = 1 if memo.get(1 << ri, 1) == 0 else 0
        if wred != w0[orig]:
            mism.append(orig)
    b520_all.append({
        "D_ids": D,
        "g_after": gdel,
        "g_before": g5,
        "w_mismatches": mism,
        "w_preserved": len(mism) == 0,
        "n_mism": len(mism),
    })
    log(f"  D={D} g={gdel} mism={len(mism)} ({time.time()-t:.1f}s)")

n_pres = sum(1 for x in b520_all if x["w_preserved"])
n_g_same = sum(1 for x in b520_all if x["g_after"] == g5)
log(f"B520 W-preserved={n_pres}/{len(b520_all)}, g-same={n_g_same}")

rep["B514_B520"] = {
    "n5_K9": len(k9_sets),
    "delta_K5": 4,
    "delta_K5_n_achieving": len(ach),
    "delta_K5_examples": ach[:8],
    "n5_hitting_pairs": 0,
    "n5_hitting_triples": 0,
    "n5_empty_g": g5,
    "delta_out5_lower": 3,
    "delta_out5_evidence": "n=5 all 1-pt and 2-pt deletions keep g=1 (round5_b201_del2 / b201-b230)",
    "gap5": "delta_K5 - delta_out5 <= 4-3 = 1 (delta_out5>=3)",
    "b520_achieving": b520_all,
    "b520_n_preserved": n_pres,
    "b520_n_g_same": n_g_same,
    "delta_K7": 2,
    "delta_K4_ge": 4,
    "delta_out4": 2,
    "gap4_ge": 2,
}

# ---- B504 decoys ----
log("=== B504 decoys n=3,4 ===")


def max_decoys_n(n):
    bd = board_square(n)
    memo = bd.solve_outcomes()
    max_d = -1
    example = None
    n_w1 = 0
    n_pos = 0

    def rec(occ, cand, k):
        nonlocal max_d, example, n_w1, n_pos
        moves = bd.legal_moves(occ)
        if moves:
            n_pos += 1
            W = sum(1 for u in moves if memo.get(occ | (1 << u), 1) == 0)
            if W == 1:
                n_w1 += 1
                n_lose = len(moves) - W
                decoys = n_lose - W
                if decoys > max_d:
                    max_d = decoys
                    example = {
                        "points": [list(xy(v, n)) for v in range(bd.V) if (occ >> v) & 1],
                        "k": k,
                        "n_legal": len(moves),
                        "W": W,
                        "L": n_lose,
                        "decoys": decoys,
                    }
        remain = cand
        while remain:
            b = remain & -remain
            v = b.bit_length() - 1
            remain ^= b
            nxt = occ | b
            if bd.is_safe(nxt):
                rec(nxt, remain, k + 1)

    rec(0, bd.full, 0)
    return {"max_decoys": max_d, "n_pos": n_pos, "n_W1": n_w1, "example": example}


n3d = max_decoys_n(3)
log(f"n3 {n3d}")
n4d = max_decoys_n(4)
log(f"n4 {n4d}")
rep["B504"] = {
    "n3": n3d,
    "n4": n4d,
    "n5_known": {"max_decoys": 22, "points": [[4, 0], [0, 3]]},
}

# ---- B507 ----
log("=== B507 ===")
env = {
    "3": {"n4": "76/135", "n5": "2383/3360", "n6": "37/50"},
    "4": {"n4": "52379/113400", "n5": "212/315", "n6": "5162/6615"},
    "5": {"n4": "2653037/6350400", "n5": "12459851/23284800", "n6": "278099/423360"},
    "6": {"n5": "66591319117/112935513600", "n6": "19547575332391/33345696384000"},
    "7": {"n4": "1827569507/6054048000", "n5": "7245096190817424647/14960657835002880000",
          "n6": "3110287792947612381539/5469990520922928000000"},
}
cases = []
ok = True
for hs, row in env.items():
    h = int(hs)
    bound = Fraction(h, h + 1)
    for n, s in row.items():
        val = Fraction(s)
        good = val <= bound
        ok = ok and good
        cases.append({"h": h, "n": n, "val": str(val), "bound": str(bound), "ok": bool(good)})
log(f"B507 h/(h+1) ok={ok}")

# also 1-1/(h+2)
ok2 = True
for hs, row in env.items():
    h = int(hs)
    bound = 1 - 1 / (h + 2)
    for n, s in row.items():
        val = float(Fraction(s))
        if val > bound + 1e-15:
            ok2 = False
log(f"B507 1-1/(h+2) ok={ok2}")

rep["B507"] = {
    "envelope": env,
    "bound_h_over_h1_all_ok": bool(ok),
    "bound_1_minus_1_over_h2_all_ok": bool(ok2),
    "bound_cases": cases,
    "argmax_h": {"n4": 3, "n5": 3, "n6": 4},
}

# ---- B505/B508/B510 ----
rep["B505"] = {
    "weak_form": "n<=5 N-positions with |W|/|L|>=1/2 have p_rand>=1/2",
    "status": "SUPPORTED (round5_b401_prand_stats.json complete scan, min=1/2)",
    "original_open": True,
}
rep["B508"] = {
    "weak_form": "exists n<=5 pair same p_rand and ratio gap >= 2/3",
    "status": "SUPPORTED (p_rand=2/3, 0/6 vs 4/6)",
    "original_open": True,
}
rep["B510"] = {
    "weak_form": "no n<=5 N-position has true winning move with strictly worst child p_rand",
    "status": "SUPPORTED (0 hits complete n=4,5)",
    "original_open": True,
}

rep["timing_s"] = round(time.time() - t0, 2)
OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
log(f"wrote {OUT}")

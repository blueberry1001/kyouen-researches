"""Enumerate safe 4-stone 9x9 parents, D4-canonicalize, find discordant orbits.

pairTop  = argmax S_pair(v)   (unique top required)
exactTop = argmax S_mob(v)    (unique top required)
discordant orbit: pairTop child != exactTop child (as canonical child sets).

Strategy (compute-aware):
  - Phase 1 (this script, pure python, checkpointed): enumerate all C(81,4)
    safe 4-sets? Too many (1.6M) x response cost. Instead sample-free full
    enumeration is ~1.66M * cheap forbidden checks for safety (~seconds),
    then for each safe parent compute pair/exact tops. Response-set
    computation is the expensive part (~81 candidates x pair checks); run
    with resume + progress, D4-dedup at the end.
  - Exact solving of the 2 children per discordant orbit stays in C++/Lean
    (task runner script emits a task list; solving is a follow-up step).

Outputs:
    results/9x9/pairmob_discordant_orbits.csv   (one row per discordant orbit)
    results/9x9/pairmob_scan_state.json         (resume checkpoint)
    results/9x9/pairmob_summary.json

For this session: run the scan in the background, checkpointed; analyze
whatever completes. If full enumeration is too slow, fall back to a seeded
random sample of safe parents (still D4-deduped) and label it as such.
"""

import csv
import json
import random
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kyouen9_pairsum as k9
try:
    import kyouen9_fast as k9fast
    k9fast.load()
    K9 = k9fast
    ENGINE = "fast-cached"
except Exception as e:
    K9 = k9
    ENGINE = f"slow ({e})"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "results" / "9x9"
OUT_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = OUT_DIR / "pairmob_scan_state.json"
ORBITS_FILE = OUT_DIR / "pairmob_discordant_orbits.csv"
SUMMARY_FILE = OUT_DIR / "pairmob_summary.json"

MODE = sys.argv[1] if len(sys.argv) > 1 else "sample"
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 7
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 400


def scan_parent(P):
    """Return (pair_top, exact_top, stats) or None if tops not unique / no safe child."""
    P = tuple(sorted(P))
    legal = sorted(K9.legal_moves(P))
    safe_children = [v for v in legal if K9.is_safe(tuple(sorted(P + (v,))))]
    if not safe_children:
        return None
    scored = []
    for v in safe_children:
        sp = K9.pair_sum(P, v)
        sm = K9.exact_mobility(P, v)
        scored.append((v, sp, sm))
    sp_sorted = sorted(scored, key=lambda t: -t[1])
    sm_sorted = sorted(scored, key=lambda t: -t[2])
    if len(sp_sorted) < 2 or sp_sorted[0][1] == sp_sorted[1][1]:
        return None
    if len(sm_sorted) < 2 or sm_sorted[0][2] == sm_sorted[1][2]:
        return None
    pair_top = sp_sorted[0][0]
    exact_top = sm_sorted[0][0]
    o_pair = sp_sorted[0][1] - sm_sorted[[t[0] for t in sm_sorted].index(pair_top)][2] \
        if pair_top in [t[0] for t in sm_sorted] else 0
    return {
        "pair_top": pair_top, "exact_top": exact_top,
        "pair_top_S": sp_sorted[0][1],
        "exact_top_M": sm_sorted[0][2],
        "n_safe_children": len(safe_children),
        "discordant": pair_top != exact_top,
    }


def random_safe_parents(rng, n):
    out = []
    tries = 0
    while len(out) < n and tries < n * 500:
        tries += 1
        P = tuple(sorted(rng.sample(range(K9.V), 4)))
        if K9.is_safe(P):
            out.append(P)
    return out, tries


def main():
    rng = random.Random(SEED)
    t0 = time.time()
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    else:
        state = {"done": [], "orbits": {}, "n_scanned": 0, "n_unique_top": 0,
                 "mode": MODE, "seed": SEED}

    parents, tries = random_safe_parents(rng, LIMIT)
    print(f"sampled {len(parents)} safe 4-sets ({tries} tries), scanning...", flush=True)
    new_discord = 0
    for i, P in enumerate(parents):
        key = ",".join(map(str, P))
        if key in state["done"]:
            continue
        r = scan_parent(P)
        state["n_scanned"] += 1
        if r is None:
            state["done"].append(key)
            continue
        state["n_unique_top"] += 1
        canon = ",".join(map(str, K9.canonical(P)))
        if r["discordant"] and canon not in state["orbits"]:
            state["orbits"][canon] = {
                "parent": key, "pair_top": r["pair_top"], "exact_top": r["exact_top"],
                "pair_top_S": r["pair_top_S"], "exact_top_M": r["exact_top_M"],
                "n_safe_children": r["n_safe_children"],
            }
            new_discord += 1
        state["done"].append(key)
        if (i + 1) % 25 == 0:
            STATE_FILE.write_text(json.dumps(state))
            print(f"  {i + 1}/{len(parents)} scanned, discordant orbits={len(state['orbits'])} "
                  f"elapsed={time.time() - t0:.0f}s", flush=True)
        if (i + 1) % 5 == 0:
            STATE_FILE.write_text(json.dumps(state))
    STATE_FILE.write_text(json.dumps(state, indent=2))
    with ORBITS_FILE.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["orbit_canonical", "parent", "pair_top",
                                          "exact_top", "pair_top_S", "exact_top_M",
                                          "n_safe_children"])
        w.writeheader()
        for canon, o in sorted(state["orbits"].items()):
            w.writerow({"orbit_canonical": canon, **o})
    summary = {"mode": MODE, "seed": SEED, "n_scanned": state["n_scanned"],
               "n_unique_top": state["n_unique_top"],
               "n_discordant_orbits": len(state["orbits"]),
               "elapsed_s": round(time.time() - t0, 1)}
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    print(f"done: {summary} new_discord_this_run={new_discord}")


if __name__ == "__main__":
    main()

"""Recompute 10x10 LOSS-core enrichment from repo CSVs (task 9).

For each stone count with classified subsets, and for candidate pairs
{61,66}, {90,91}, {13,91} (plus discovered top pairs), compute:
  n_total, n_loss, pair count, P(LOSS|pair), P(LOSS|no pair), enrichment,
  Fisher exact two-sided p (stdlib implementation).

Sources: every results/10x10/*.csv with (state, outcome) columns.
Family-selection bias is discussed in the output doc, not hidden.

Outputs:
    results/10x10/loss-core-enrichment.csv
    results/10x10/loss-core-enrichment.json
"""

import csv
import glob
import json
import math
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IN_DIR = REPO_ROOT / "results" / "10x10"
OUT_CSV = IN_DIR / "loss-core-enrichment.csv"
OUT_JSON = IN_DIR / "loss-core-enrichment.json"

CANDIDATE_PAIRS = [(61, 66), (90, 91), (13, 91)]


def fisher_two_sided(a, b, c, d):
    """Two-sided Fisher exact p via hypergeometric enumeration (stdlib)."""
    n = a + b + c + d
    r1, r2 = a + b, c + d
    c1 = a + c
    obs = (math.comb(r1, a) * math.comb(r2, c1 - a)) / math.comb(n, c1)

    def prob(x):
        return (math.comb(r1, x) * math.comb(r2, c1 - x)) / math.comb(n, c1)

    lo = max(0, c1 - r2)
    hi = min(r1, c1)
    return sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= obs + 1e-15)


def parse_state(s):
    return tuple(sorted(int(x) for x in s.replace("-", ",").split(",") if x != ""))


def load_classified():
    """Load (state, outcome, stones, source) from all 10x10 CSVs with those columns."""
    rows = []
    for f in sorted(glob.glob(str(IN_DIR / "*.csv"))):
        try:
            with open(f, newline="") as fh:
                r = csv.DictReader(fh)
                if r.fieldnames is None or not {"state", "outcome"} <= set(r.fieldnames):
                    continue
                for row in r:
                    if row["outcome"] not in ("WIN", "LOSS"):
                        continue
                    try:
                        st = parse_state(row["state"])
                    except ValueError:
                        continue
                    rows.append({"state": st, "outcome": row["outcome"],
                                 "stones": len(st), "source": Path(f).name})
        except (OSError, csv.Error):
            continue
    # dedup by state: prefer LOSS (a state proven LOSS anywhere is LOSS)
    best = {}
    for r in rows:
        k = r["state"]
        if k not in best or (best[k]["outcome"] == "WIN" and r["outcome"] == "LOSS"):
            best[k] = r
    return list(best.values())


def main():
    data = load_classified()
    by_stones = defaultdict(list)
    for r in data:
        by_stones[r["stones"]].append(r)
    print(f"classified states: {len(data)} across stones {sorted(by_stones)}")

    # discover top co-occurring pairs in LOSS states (exploratory, labelled)
    pair_loss = defaultdict(int)
    for r in data:
        if r["outcome"] != "LOSS":
            continue
        st = r["state"]
        for i in range(len(st)):
            for j in range(i + 1, len(st)):
                pair_loss[(st[i], st[j])] += 1

    results = []
    for stones in sorted(by_stones):
        group = by_stones[stones]
        n = len(group)
        nl = sum(1 for r in group if r["outcome"] == "LOSS")
        pairs = list(CANDIDATE_PAIRS)
        # add top-3 empirical LOSS pairs at this stone count
        local = defaultdict(int)
        for r in group:
            if r["outcome"] != "LOSS":
                continue
            for i in range(len(r["state"])):
                for j in range(i + 1, len(r["state"])):
                    local[(r["state"][i], r["state"][j])] += 1
        for p, _ in sorted(local.items(), key=lambda kv: -kv[1])[:3]:
            if p not in pairs:
                pairs.append(p)
        for pair in pairs:
            a = sum(1 for r in group if pair[0] in r["state"] and pair[1] in r["state"]
                    and r["outcome"] == "LOSS")
            b = sum(1 for r in group if pair[0] in r["state"] and pair[1] in r["state"]
                    and r["outcome"] == "WIN")
            c = nl - a
            d = (n - nl) - b
            p_with = a / (a + b) if (a + b) else None
            p_without = c / (c + d) if (c + d) else None
            base = nl / n if n else None
            enrich = (p_with / base) if (p_with is not None and base) else None
            pval = fisher_two_sided(a, b, c, d) if min(a + b, c + d) > 0 else None
            results.append({
                "stones": stones, "pair": f"{pair[0]},{pair[1]}",
                "n_total": n, "n_loss": nl, "pair_n": a + b,
                "pair_loss": a, "p_loss_given_pair": round(p_with, 4) if p_with is not None else "",
                "p_loss_given_nopair": round(p_without, 4) if p_without is not None else "",
                "base_rate": round(base, 4), "enrichment": round(enrich, 3) if enrich else "",
                "fisher_p": f"{pval:.3g}" if pval is not None else "",
                "preregistered": pair in CANDIDATE_PAIRS,
            })
            pstr = f"{pval:.3g}" if pval is not None else "n/a"
            print(f"stones={stones} pair={pair[0]},{pair[1]} n={a + b} "
                  f"P(loss|pair)={p_with} base={round(base, 3) if base else None} "
                  f"enrich={round(enrich, 2) if enrich else None} p={pstr} "
                  f"{'PRE' if pair in CANDIDATE_PAIRS else 'exploratory'}")

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    with OUT_JSON.open("w") as f:
        json.dump({"n_states": len(data),
                   "note": "exploratory unless preregistered=true; no multiple-testing correction applied",
                   "rows": results}, f, indent=2)
    print(f"wrote {OUT_CSV.name} + {OUT_JSON.name}")


if __name__ == "__main__":
    main()

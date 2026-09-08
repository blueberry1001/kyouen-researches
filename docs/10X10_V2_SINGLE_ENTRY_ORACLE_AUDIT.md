# 10x10 V2 single-entry oracle audit

This is a post-benchmark mechanism analysis only. It performs **no new solver
runs** and does not alter the preregistered parent-benchmark endpoint.

Inputs are the frozen V2 exact child outcomes and the completed native-parent
benchmark raw rows.

## Why the `A_entered=1 && B_entered=1` subgroup matters

For 9 of the 12 V2 parents, both strategy A (native ordering) and strategy B
(10k-memo root ordering) entered exactly one root child. Every benchmark parent
was WIN, so that one entered child is necessarily a LOSS child.

Therefore, in this subgroup:

- there is no earlier root child whose memo entries could pollute a later child;
- the A/B exact-work difference is directly a difference in the proof cost of
  the first selected LOSS subtree (up to the common root overhead);
- the cheapest exact LOSS child among the frozen V2 children gives an oracle
  lower bound for what root ordering could achieve on this mechanism.

## Results

`oracle` is the minimum exact `visited` among LOSS children of that parent.
`A` and `B` are the exact visited counts of the first selected LOSS child,
matched via the benchmark `root_first_{lo,hi}` canonical key.

| parent | oracle LOSS | A native LOSS | B 10k LOSS | A/oracle | B/oracle | B/A |
|---|---:|---:|---:|---:|---:|---:|
| `11,38,44` | 11,705,499 | 17,051,434 | 20,853,831 | 1.4567 | 1.7815 | 1.2230 |
| `11,78,87` | 5,164,504 | 9,928,497 | 22,490,279 | 1.9224 | 4.3548 | 2.2652 |
| `12,24,68` | 10,411,803 | 11,677,826 | 13,269,932 | 1.1216 | 1.2745 | 1.1363 |
| `13,52,57` | 5,541,299 | 11,651,702 | 9,708,729 | 2.1027 | 1.7521 | 0.8332 |
| `14,64,74` | 4,342,653 | 4,342,653 | 18,108,564 | 1.0000 | 4.1699 | 4.1699 |
| `23,44,45` | 6,452,531 | 7,188,932 | 11,523,195 | 1.1141 | 1.7858 | 1.6029 |
| `3,47,63` | 5,711,577 | 5,711,577 | 10,229,825 | 1.0000 | 1.7911 | 1.7911 |
| `3,53,84` | 7,184,953 | 7,184,953 | 14,732,400 | 1.0000 | 2.0505 | 2.0505 |
| `4,42,54` | 6,977,108 | 6,977,108 | 16,722,419 | 1.0000 | 2.3968 | 2.3968 |

Aggregate summaries over these 9 parents:

- native A / oracle median: **1.1141**
- native A / oracle geometric mean: **1.2483**
- native chooses an exact cheapest LOSS: **4/9**
- 10k B / oracle median: **1.7911**
- 10k B / oracle geometric mean: **2.1851**
- 10k chooses an exact cheapest LOSS: **0/9**
- B/A selected-LOSS cost median: **1.7911**
- B/A selected-LOSS cost geometric mean: **1.7505**
- B chooses a cheaper LOSS than A: **1/9**
- B chooses a more expensive LOSS than A: **8/9**

## Interpretation

This sharply weakens the cross-root-child memo-pollution explanation for the
parent-benchmark failure. In these 9 parents there is no preceding root child.
The failure is instead explained directly by **which LOSS subtree is selected**.

The 10k memo signal is useful for finding LOSS children, but it is not aligned
with the conditional cost of proving a LOSS. Native ordering is already close
to the cheapest available LOSS in this clean subgroup: median overhead over the
oracle is only about 11%, and it hits the exact cheapest LOSS in 4/9 parents.
The 10k treatment moves away from that oracle, with a median proof-cost overhead
of about 79%.

This supports shifting the main question from LOSS classification to
**conditional LOSS proof-cost prediction**. It also suggests that the remaining
headroom for root-only ordering may be modest unless a cheap feature can beat
the native `legal_move_count + canonical key` ordering specifically *within
LOSS children*.

## Next analysis (no heavy run)

`scripts/analyze_v2_loss_proof_cost.py` now computes from the frozen data:

- parent-wise Spearman and Kendall tau-b against exact LOSS visited;
- 10k memo / probe depth / probe seconds / legal move count / move id;
- LOSS-vs-WIN AUC separately from conditional LOSS proof-cost correlation;
- legal-only, legal+memo, and memo-only conditional-LOSS selectors;
- top-1/top-3/top-5 cheapest-LOSS coverage for legal ordering;
- the same S1 native/10k/oracle decomposition above.

Do not start a new 100k/1M probe cohort until that zero-new-solver analysis has
been inspected.

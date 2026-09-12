# Probe budget head-recall follow-up

This is an exploratory follow-up to the frozen 1M holdout.  The 10k and 100k
probe files already exist, so no new probe run is needed for this analysis.

## First-LOSS rank by budget

Using ascending `memo` within each parent:

| budget | sum of first-LOSS ranks | parents with first LOSS <= 6 | worst first-LOSS rank |
|---:|---:|---:|---:|
| 10k | 42 | 8 / 11 | 11 |
| 100k | 39 | 10 / 11 | 17 |
| 1M | 16 | 11 / 11 | 6 |

Thus the post-hoc `top-6` property observed at 1M does **not** survive budget
reduction: 10k fails on `0,1,13` (rank 7), `0,13,21` (rank 11), and
`0,3,13` (rank 10); 100k fails on `0,3,13` (rank 17).  In particular,
`0,3,13` moves 10 -> 17 -> 1 as budget grows, so first-LOSS rank is not
monotone in probe budget.

The existing stability audit is consistent with this: mean top-5 Jaccard is
0.420 for 10k/100k but only 0.109 for 100k/1M, while top-1 agreement is 1/11
and 0/11 respectively.  The useful LOSS signal therefore strengthens with
budget without preserving the exact head ordering.

## Exact random-order null at each budget

For a parent with `N` legal children and `L` LOSS children, the random-order
first-LOSS rank has

`P(R=r) = C(N-r, L-1) / C(N, L)`.

Convolving the 11 parent-specific distributions gives the exact one-sided
probability `P(sum R <= observed)`:

| budget | observed sum | exact p |
|---:|---:|---:|
| 10k | 42 | 6.703629115496289e-05 |
| 100k | 39 | 3.487712229923814e-05 |
| 1M | 16 | 1.2274608418538772e-09 |

So 10k and 100k are not useless: both retain a strong LOSS-ranking signal
relative to random order.  What fails is the stronger operational claim that
a fixed top-6 shortlist catches a LOSS in every parent.

## New staged-funnel hypothesis

The minimum `K` that retrospectively contains a LOSS for every one of these 11
parents is 11 at 10k, 17 at 100k, and 6 at 1M.  This suggests a separate,
explicitly exploratory two-stage design:

1. probe every child at 10k;
2. retain the top 11 by ascending `memo`;
3. probe only those 11 candidates at 1M and rerank them;
4. then exact-search in the reranked order.

For 92--94-child parents, fresh 1M probes on all children cost 92--94 million
visited-node budget units.  The proposed funnel costs about
`N*10k + 11*1M = 11.92--11.94 million`, an approximately 87% reduction in
probe budget before exact search.

`K=11` is chosen *after seeing this cohort* and therefore is not evidence of
generalization.  It must be frozen before a new parent cohort.  The existing
cohort can still be used for a retrospective feasibility check: rerank each
10k top-11 set using its already-recorded 1M memo values and measure first-LOSS
rank within the funnel.  If that loses the 1M head advantage badly, abandon the
funnel before spending on a new cohort.

## Mechanistic implication

All 1M probes were unresolved and hit the same visited-node budget.  Therefore
ascending `memo` is effectively ranking by *fewer distinct memoized states per
fixed number of visited nodes* (equivalently, greater transposition/revisit
redundancy).  The budget dependence above makes a depth- or time-resolved
memo-growth curve a more plausible next feature than a single terminal memo
count.  Recording memo size/hits at logarithmic checkpoints (e.g. 10k, 30k,
100k, 300k, 1M) would test whether LOSS subtrees have a characteristic growth
slope or curvature that can be recognized earlier than 1M.

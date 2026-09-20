# 10x10 probe budget economics: 10k should be tested before 100k

Status: **exploratory/post-hoc resource-planning analysis**. This does not alter the completed V1 or V2 confirmatory endpoints.

Base: `10x10-clean-holdout-v2` at `451ece8674e167d9a3dec5dbc29c16518b8ab6fb`.

## Why revisit the proposed 100k next step?

V2 P6 established that probing every child to 1M and then solving in memo-ascending order is not an end-to-end optimization: its median total-cost ratio versus file order is about 5.0, and only 1/12 parents improves.

The natural follow-up was a 100k probe-all experiment. Existing V1 budget-stability data, however, show that 100k buys surprisingly little improvement in the endpoint that matters for exact search: first exact-LOSS position.

### V1 first-LOSS rank by budget

| budget | rank sum (11 parents) | mean | median | worst |
|---|---:|---:|---:|---:|
| 10k | 42 | 3.818 | 2 | 11 |
| 100k | 39 | 3.545 | 2 | 17 |
| 1M | 16 | 1.455 | 1 | 6 |

The exact-random expected rank sum for these same fixed parents is 190.9717.
Relative to the improvement from random order to the 1M result, the 10k ordering already captures **85.14%** of that rank-sum gain; 100k captures **86.86%**. Thus increasing the per-child probe budget by 10x from 10k to 100k improves aggregate first-LOSS rank by only **3 positions** (42 -> 39) across all 11 parents.

This differs from AUC, which improves more smoothly (mean 0.748 -> 0.781 -> 0.820). For an exact solver that stops after finding a LOSS child, first-LOSS cost is the more direct optimization target.

A further useful observation is that at 10k the first LOSS is within the top 11 on every V1 parent. This is post-hoc and must not be treated as a future guarantee, but it makes a cheap direct 10k cost test particularly informative.

## V2 P6 break-even screen

For each V2 parent, let

`S = exact_cost(file order to first LOSS) - exact_cost(1M memo order to first LOSS)`.

If probe wall time scaled linearly with visited budget and, unrealistically optimistically, the same 1M memo-first LOSS stayed first at a lower budget, the break-even budget would be

`B* = 1,000,000 * S / probe_cost_1M`.

The resulting B* values (visited states per child) are approximately:

| parent | optimistic B* |
|---|---:|
| 0,11,35 | 264k |
| 11,38,44 | 186k |
| 11,78,87 | 71k |
| 12,24,68 | 123k |
| 12,32,55 | 493k |
| 13,52,57 | 113k |
| 14,64,74 | 50k |
| 23,44,45 | 76k |
| 3,47,63 | 173k |
| 3,53,84 | 1,036k |
| 4,24,26 | 509k |
| 4,42,54 | 388k |

Median B* is about **179k**.

Under the same deliberately optimistic assumptions:

- 100k would be favorable for only 9/12 parents, with median projected total-cost ratio about **0.617**;
- 10k would be favorable for 12/12, with median projected ratio about **0.230**.

These ratios are **not measured lower-budget results**. In particular, V1 shows top-1 agreement between 100k and 1M is 0/11, so preserving the 1M winning candidate is known to be an unrealistic assumption. The screen is useful only for deciding which real measurement should be run first.

## Decision

The next resource-allocation experiment should be **V2 10k probe-all before V2 100k probe-all**.

Use the already frozen V2 parent/task set and already known exact outcomes. This is no longer a confirmatory prediction experiment; it is an explicit post-hoc solver-cost optimization experiment.

For each V2 parent at 10k, measure:

1. first exact-LOSS rank under fresh-solver memo ascending;
2. exact wall time accumulated in that 10k order until first LOSS;
3. total wall time = all-child 10k probe cost + exact-to-first-LOSS cost;
4. ratio to existing file-order exact cost;
5. rank sum, AUC, and top-k LOSS recall as diagnostics.

Only after seeing the 10k end-to-end cost should 100k-all be run as the next comparison. If 10k already wins robustly, a 10k -> selective 100k staged policy can then be designed, but any value of k chosen from these data is exploratory and requires a future frozen holdout for confirmation.

## Reproducer

`scripts/analyze_10x10_probe_budget_economics.py` recomputes the rank-efficiency and break-even screen directly from the committed V1 P4 and V2 P6 artifacts.

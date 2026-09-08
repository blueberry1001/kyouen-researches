# 10x10 LOSS proof-cost analysis (existing data only)

Companion to `docs/10X10_PARENT_BENCHMARK_MECHANISM_REFINEMENT.md` (S1/S2
split) and `docs/10X10_V2_SINGLE_ENTRY_ORACLE_AUDIT.md` (S1 oracle table).
S1 medians there (exact-only 1.7911, gmean 1.7505, B/A selected 1.7911)
are reproduced here from an independent solver-order replication, extended to
all 12 parents, 18 cheap features, and the entered-prefix decomposition.
The replication itself is cross-validated: numpy determinant-scan vs
`generate_v2_holdout_children.forbidden` agree on canonical keys 1136/1136
and legal_move_count 1136/1136.

## 0. Replication (trust anchor)

Native root order (`legal_move_count` asc, canonical key asc — confirmed in
`scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc::order_children`)
was re-implemented in Python (determinant rule + dihedral canonicalization)
and checked against solver-observed diagnostics:

- native first child == A `root_first` surrogate key: **12/12**
- B order-file first line == B `root_first`: **12/12**
- unique root-child count == `root_unique` (A and B): **12/12**
- entered count == first-LOSS position in that strategy's order: **24/24**

The replication is therefore exact at every observable point. All "native rank"
and "legal_move_count" values below are recomputed, not logged, quantities.

Dataset: 556 file-state LOSS outcomes collapse to **516 unique canonical LOSS
children** (40 symmetric duplicates; duplicates always agree on outcome).

## 1. Parent benchmark failure, reconfirmed

Median work ratio (B/A) 1.84, improved 2/12, aggregate 225.4M -> 336.3M,
median exact-only ratio 1.70. 9/12 parents have A_entered == B_entered == 1.

## 2. S1/S2 decomposition (shared-memo falsification)

- **S1** (A_entered == B_entered == 1, no cross-child memo possible): n=9,
  median exact-only ratio **1.79**, gmean 1.75, improved 1/9,
  median selected-LOSS cost ratio B/A **1.79**.
- **S2** (either side entered > 1): n=3 (`0,11,35`, `12,32,55`, `4,24,26`),
  median exact-only 1.12, improved 1/3.

S1 fails harder than the full cohort while shared memo is impossible there.
**"Shared memo pollution" is falsified as the primary mechanism.** It can at
most be a second-order term (see §7).

## 3. LOSS-conditional proof cost (P2)

Per parent, first LOSS in each strategy's unique root order:

| parent | work ratio | native LOSS cost-rank | native/min | 10k LOSS cost-rank | 10k/min | sel B/A |
|---|---|---|---|---|---|---|
| 0,11,35 | 0.53 | 2/10 | 1.18x | 4/10 | 1.50x | 1.27 |
| 13,52,57 | 0.91 | 12/50 | 2.10x | 8/50 | 1.75x | 0.83 |
| 4,24,26 | 1.13 | 3/9 | 1.51x | 1/9 | 1.00x | 0.66 |
| 12,24,68 | 1.22 | 2/23 | 1.12x | 4/23 | 1.28x | 1.14 |
| 11,38,44 | 1.28 | 6/38 | 1.46x | 13/38 | 1.78x | 1.22 |
| 23,44,45 | 1.73 | 6/90 | 1.11x | 26/90 | 1.79x | 1.60 |
| 3,47,63 | 1.95 | 1/43 | 1.00x | 10/43 | 1.79x | 1.79 |
| 3,53,84 | 2.19 | 1/63 | 1.00x | 19/63 | 2.05x | 2.05 |
| 11,78,87 | 2.36 | 4/47 | 1.92x | 28/47 | 4.36x | 2.27 |
| 4,42,54 | 2.53 | 1/47 | 1.00x | 24/47 | 2.40x | 2.40 |
| 14,64,74 | 4.38 | 1/78 | 1.00x | 66/78 | 4.17x | 4.17 |
| 12,32,55 | 12.21 | 1/18 | 1.00x | 5/18 | 2.74x | 2.74 |

Medians: native cost-rank **2.0**, native/min **1.12x**; 10k cost-rank **11.5**,
10k/min **1.79x**. Native picks the cheapest-or-near-cheapest LOSS in 9/12
parents; 10k does so in 1/12 (`4,24,26`).

## 4. legal_move_count predicts LOSS proof cost (P3/P4)

LOSS-only Spearman vs exact visited (overall | demeaned pooled-rank |
median-per-parent):

- legal_move_count: **+0.72 | +0.65 | +0.69** (Kendall +0.56)
- 10k probe memo: +0.37 | +0.34 | +0.36
- 10k maxdepth: +0.14 | +0.12 | +0.13; probe seconds ~0; move id ~0;
  canonical rank ~0.
- Per-parent count|cost Spearman is positive in 11/12 parents (0.26..0.86);
  the exception is `0,11,35` (-0.06, only 10 LOSS children).

legal-count top-k coverage of the cheapest LOSS: top-1 hits 5/12, top-3 hits
7/12, top-5 hits 8/12. Median top-1/min ratio 1.18x.

Tie-break experiment (LOSS-only first selection): `(count, key)` vs
`(count, memo10k, key)` differ in **1/12** parents (`13,52,57`: 2.10x ->
1.38x), identical elsewhere. Memo has almost no tie-breaking value on top of
count — count ties at the minimum are rare or memo agrees.

## 5. Memo: strong classifier, weak cost predictor (P5)

- LOSS vs WIN: probe-memo quartile LOSS rates Q1 0.761 / Q2 0.577 /
  Q3 0.394 / Q4 0.225 (plus existing AUC ~0.642). Classification signal: strong.
- LOSS-conditional cost: Spearman +0.34, less than half of count's +0.65.
- memo vs count overall Spearman is **0.139**: the two orders are nearly
  orthogonal. Memo-ascending therefore scrambles count-ascending and routinely
  lands on an expensive LOSS (median cost-rank 11.5 vs native 2.0).

Verdict: **"memo predicts LOSS outcome but not proof difficulty" is
supported.** Direction is right (small memo -> cheaper, +0.34), magnitude is
too weak to drive root ordering, and independence from count makes it actively
harmful as a primary key.

## 6. Case studies (P6)

- `12,32,55` (12.21x, worst): two stacked effects. B entered 5 children:
  4 WINs first (68.1M proxy waste) then a LOSS at 2.74x oracle. A entered 1
  (cheapest LOSS). Selected-LOSS ratio 2.74x explains only part; the WIN
  prefix explains the rest (proxy total 12.33x vs actual 12.08x).
- `14,64,74` (4.38x): pure selection. Both entered 1. Native took the cheapest
  LOSS; 10k's first-memo child is a LOSS but the 66th-cheapest (4.17x oracle).
  Selected ratio 4.17x ~= work ratio 4.38x.
- `0,11,35` (0.53x, best): reversed roles. Native count-order put 5 WINs
  before its first LOSS (A entered 6, 60.4M waste); memo-order put only 2
  WINs first (B entered 3, 12.9M waste). B wins on waste despite selecting a
  slightly pricier LOSS (1.27x). Also the one parent where count|cost
  correlation is ~0.
- `13,52,57` (0.91x): both entered 1; 10k's pick (8/50, 1.75x) beat native's
  (12/50, 2.10x). Genuine but small 10k selection win; the only parent where
  the memo tie-break experiment also helps.

Prefix decomposition (P6b): summing independent-exact visited over each
strategy's entered prefix (WIN waste + selected LOSS) reproduces the observed
exact-only ratios within ~2% on all 12 parents (worst: 12.33 vs 12.08).
Root order alone explains the benchmark; nothing else is needed.

## 7. Falsified and surviving mechanisms

- FALSIFIED (primary): cross-child shared-memo pollution — S1 fails at 1.79x
  with pollution impossible; additive proxy matches without any memo term.
- FALSIFIED: "native wins by proving fewer WINs" as a general story — in 10/12
  parents both sides entered exactly 1 child; the gap is purely which LOSS.
- SURVIVING (primary): 10k memo-asc selects expensive LOSSes because memo is
  nearly orthogonal to the cost-driving feature (count) — median 11.5th
  cheapest vs native 2nd cheapest.
- SURVIVING (secondary, 1 parent): WIN-prefix waste when memo-asc ranks WINs
  before the first LOSS (`12,32,55`: 4 WINs, 68M).
- Second-order only: shared memo / proof reuse across root children (proxy
  residual <= ~2%).

## 8. Oracle gap (P8)

Cheapest-LOSS-first oracle vs selected: native median **1.12x** oracle, 10k
median **1.79x** oracle. Native is already near the best achievable by any
LOSS-first root ordering, so the headroom for root-order heuristics is ~12%.

## 9. Cheap features (P9, exploratory, all 18 reported)

`banned_child` (-0.65 pooled), `newly_banned` (-0.64), `raw_pair_sum`/`T`
(-0.65) mirror `legal_move_count` — they are near-deterministic transforms of
it (count = 96 - |banned \ state|), not independent signals. Geometry
summaries (pair-dist mean +0.34, bbox +0.30, center-dist +0.35, rows/cols
+0.16..+0.21) are all weaker than count. `E`/`O` are identically zero on this
cohort (pair response sets are disjoint and fresh vs parent-banned) and carry
no signal. **No cheap feature beats legal_move_count; none is a clear +1.**

## 10. Decision (P10): Case A + Case D

Count predicts LOSS proof cost well (Case A), but native already converts that
into near-oracle selection (1.12x — Case D). Root-order headroom is small and
the one natural follow-up (`count` primary + memo tie-break) changes 1/12
selections in-sample with unknown sign out-of-sample. Recommendation:

1. Do NOT run a confirmatory parent benchmark on root-order tweaks — expected
   value is ~10% on a subset of parents at full benchmark cost.
2. Shift priority to below-root internals: memo lookup/hit/put
   instrumentation, proof-structure/certificate-reuse analysis, deeper-layer
   ordering — the 1.12x residual and the S2 WIN-prefix waste live there.
3. If root order is ever revisited, the preregistered candidate is
   `(legal_move_count, memo10k, canonical key)`; its exploratory effect size
   is one parent (`13,52,57`, 2.10x -> 1.38x selected-cost).

## 11. Answers to the preregistered questions

- LOSS children: 556 file-state outcomes / **516 unique canonical**.
- S1/S2: 9 / 3; S1 exact-only median **1.79**.
- Native selected LOSS: median cost-rank 2.0, 1.12x oracle.
- 10k selected LOSS: median cost-rank 11.5, 1.79x oracle.
- count|cost: +0.72/+0.65/+0.69; memo|cost: +0.37/+0.34/+0.36.
- Oracle gap: native 1.12x, 10k 1.79x (medians).
- `12,32,55`: expensive LOSS pick (2.74x) + 4-WIN prefix (68M).
- `0,11,35`: native entered 6 with 5-WIN waste; B entered 3.
- Shared-memo pollution as primary cause: **no**.
- Memo classifies LOSS but barely predicts cost: **yes, supported**.
- Next heuristic: none with positive expected value at root; instrument
  below-root instead.
- New heavy experiments needed: **no**.

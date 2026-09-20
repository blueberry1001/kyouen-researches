# Move-ordering research: blind-probe audit + pair-sum/mobility (10x10 + 9x9)

Branch: `audit-blind-probe-and-move-ordering` (from `probe-two-stone-subsets`
at `24401d0`). Audited commit: `b5172a4`. **All blind-validation results
below are 10x10, not 9x9.** Old result files are untouched; every new
artifact uses a new filename.

## 1. P0 — blind-probe audit: CONFIRMED BUG (cumulative `probe_memo`)

Generator: `scripts/probe_cert_solver` = `scripts/probe_cert_solver.cpp` +
`scripts/probe_parts/*.inc`. The multi-state path
(`kyouen_solver_10_kyoenc4_resume_4.inc`) constructs **one `Solver` per
process invocation** (one batch file = 20 children), loops over candidates,
and reports the **solver-global** `memo_used()` per row. There is **no
memo clear** between candidates (`clear` does not occur in the loop file);
only `Solver::Stats st` (visited/maxdepth/depth_visited) is per-task.
Probe budget = per-candidate cap on `st.visited` (`check_probe_budget`);
memo hits do **not** increment visited, so 1M visited covers different real
effort for early vs late candidates.

Consequences, all verified from raw CSVs (see `scripts/audit_blind_probe.py`,
`results/10x10/blind-probe-audit.json/.csv`):

- `probe_memo`, `memo_used_d*`, `seconds` are **cumulative** (row k ≈ k×1M);
  `visited`, `maxdepth`, `depth_visited_*` are per-task (independent).
- Batch files are processed in **input-file order (numeric ascending)**;
  `run_blind_probe_parent.py`/`run_blind_probe_batch.py` pass the file
  straight to the solver, one process per batch.
- Memo-desc sort with move-index tie-break therefore yields **exactly the
  reverse of input order for all 8 batch0 parents** (no memo ties observed).
  `fixed_rank == m - move_index` holds for all 160 rows.
- Memo resets only at **batch boundaries** (new process per batch file).
- The reported "fixed rule vs solver-default" comparison is effectively
  **reverse-vs-forward order of the same children file**; exact-search cost
  comparisons additionally inherit the solver's internal fewest-legal-moves
  child ordering (`win()` sorts by `count`), so they are not clean either.
- LOPO/prediction-era `probe-features.csv` is **unaffected**: it ran one
  state per invocation (fresh memo per row).

Fixed rule ≠ geometric pair-sum. The frozen rule is "3-stone: 1M-visited
probe memo, descending" — a search-statistic feature, not the geometric
`S = Σ s_ab(v)` heuristic. Do not conflate them; do not count
solver-default agreement as independent confirmation where the orderings
coincide mathematically.

## 2. P1 — corrected experiment (independent memo + order swap)

`scripts/corrected_blind_probe.py`, outputs in
`results/10x10/blind-probe-corrected/` (7 LOSS parents × batch0 × 1M,
shrink 3 / load 80, same as original):

- **Independent probe** (one process per candidate, fresh memo): memo-desc
  ranking vs exact outcomes.
- **Order swap** (shared-memo binary, reversed input): memo strictly
  increasing in processing order for **all 7 parents** — ranking is fully
  order-determined, as predicted.

| parent | m | l | orig (buggy) | indep | solver | E[R] |
|---|---|---|---|---|---|---|
| 2,9,33 | 20 | 6 | 1 (q=.300) | 9 (q=.988) | 2 (q=.521) | 3.0 |
| 4,9,33 | 20 | 2 | 16 (q=.968) | 19 (q=1) | 3 (q=.284) | 7.0 |
| 9,12,33 | 20 | 1 | 3 (q=.150) | 20 (q=1) | 18 (q=.900) | 10.5 |
| 9,19,33 | 20 | 1 | 13 (q=.650) | 16 (q=.800) | 8 (q=.400) | 10.5 |
| 9,23,33 | 20 | 2 | 1 (q=.100) | 15 (q=.947) | 3 (q=.284) | 7.0 |
| 0,31,36 | 20 | 15 | 1 (q=.750) | 2 (q=.947) | 1 (q=.750) | 1.31 |
| 0,36,44 | 20 | 4 | 3 (q=.509) | 9 (q=.932) | 6 (q=.793) | 4.2 |

`q(r;m,l) = 1 - C(m-r,l)/C(m,l)`, `E[R] = (m+1)/(l+1)`.
Independent-memo-desc is **worse than the simulated random median in 7/7
parents** (exact two-sided sign test p = 0.0156 — significantly *worse*
than random, not better). The original "median 3.0 vs random 6.0" verdict
(C, weak effect) is **invalid**: under the corrected measurement the fixed
memo-desc rule shows no benefit; if anything it anti-predicts LOSS at 1M
on these parents. Verdict C must be re-examined, not merely widened.

## 3. P2 — density-adjusted baseline included above

Random baseline uses exact `q(r;m,l)` per parent (loss-density aware),
not just "median 6". The stored `theoretical_expected_first_loss_position`
was cross-checked against `(m+1)/(l+1)` — matches. `0,36,43` (l=0 in
batch0) correctly excluded from LOSS-parent aggregates.

## 4. P3 — 9x9 pair-sum vs exact mobility: NEGATIVE result for the experiment

`scripts/kyouen9_pairsum.py` (+ cached `scripts/kyouen9_fast.py`,
quad-completion table over C(81,3) triples) implements, for safe parent P
and safe child v, per-pair dangerous responses
`W_ab(v) = {r : {a,b,v,r} forbidden, all other quads of P+v+r safe}`,
`S_pair = Σ|W_ab|`, `S_mob = |∪W_ab|`, `O = S_pair - S_mob`, with
circle/line split (`forbidden_kind`). Forbidden = solver determinant
(zero of `[x²+y²,x,y,1]`), verified against exact integer determinants on
300 random quads; collinear **and** cocircular both detected
(`tests/test_pairsum.py`, 4/4 pass without pytest).

Findings (seed 7, 1998 scanned safe 4-sets, 1635 with unique tops):

- **Zero discordant orbits**: pairTop == exactTop in 1635/1635 cases.
- Stronger: **O = 0 in all ~180k sampled (P, v) pairs** (random + triple-rich
  targeted hunt), hence `S_pair == S_mob` identically in practice and the
  pairTop-vs-exactTop McNemar test is degenerate (no discordant pairs).
- The `O ≤ 3` bound holds trivially (max observed 0); the partition argument
  in the task appears sound but vacuous here — shared responses essentially
  never occur because any r in two quads `{a,b,v,r}`, `{c,d,v,r}` forces a
  second forbidden quad inside P+v+r (or P+v unsafety), filtering r out.
- Consequence: on 9x9 4-stone parents, **pair-sum and exact-mobility
  orderings coincide**; the discriminative exact-solve experiment cannot
  separate them. `F_alpha = S_mob + alpha·O` rankings are alpha-independent
  on this data (breakpoints 1/3, 1/2, 2/3 moot). Do not claim independent
  confirmation from their agreement.

3-stone disjointness holds: on sampled safe 3-stone parents the three
`W_ab(v)` are pairwise disjoint and each is ⊆ killed safe replies
(`(legal(P)-{v}) - legal(P+v)`), tested.

## 5. P4 — 10x10 LOSS-core re-aggregation (exploratory)

`scripts/loss_core_enrichment.py` recomputed from **repo CSVs only**
(997 deduped classified states; LOSS-anywhere-wins dedup):
`results/10x10/loss-core-enrichment.{csv,json}` with Fisher two-sided p
(stdlib), preregistered vs exploratory pairs labelled, no multiplicity
correction.

- `{61,66}`: 4-stone P(LOSS|pair) = 0.80, base 0.044, enrich ≈ 18×,
  p ≈ 7.7e-17 — but the 4-stone LOSS set is dominated by two
  family-structured files (`four-stone-subsets-of-medium-loss`,
  `four-stone-loss-proof`), so this is **family-selection bias until
  proven otherwise**, not a validated "core".
- `{90,91}` / `{13,91}`: only 5-stone shows modest enrichment (~2×,
  p ≈ 0.001–0.01, uncorrected); 3/4/6-stone ≈ null.
- Verdict: **no LOSS-core claim is confirmed**; the one eye-catching number
  rides on biased sampling. Needs family-stratified validation.

## 6. Taxonomy (do not conflate)

- probe-based ordering (search statistics: memo/visited/maxdepth)
- exact-solver default ordering (children-file order + internal
  fewest-legal-moves-first search)
- random ordering (density-adjusted baseline above)
- geometric pair-sum score `S_pair`
- exact distinct-response mobility `S_mob`
- hybrid `F_alpha` (degenerate here since O = 0)

## 7. Corrections to prior docs

- `docs/10X10_PROBE_BLIND_VALIDATION.md` §4–§6 (median 3.0 vs 6.0,
  verdict C, cost-improvement claims): invalid as stated — the ranking was
  reverse file order, not a learned signal. Keep the file; this memo
  supersedes its conclusions.
- Blind branch is **10x10**; nothing here transfers to 9x9 without redoing.
- Fixed probe rule ≠ pair-sum heuristic; solver-default ≠ pair-sum.

## 8. Hypotheses / next best experiment

1. (Highest value) Redo blind validation with **independent-memo probes**
   across *all* batches (not just batch0) and several budgets
   (10k/100k/1M), pre-registered, to test whether *any* probe statistic
   (esp. per-task `maxdepth`/`depth_visited_*`, which are order-free)
   predicts LOSS. Cost: ~7 parents × ~92 children × 3 budgets ≈ 1900 probes.
2. Test pair-sum/mobility as **move ordering inside exact search** (node
   counts), not as LOSS-rank predictors — the theory was about search
   guidance, and O = 0 makes them cheap.
3. Family-stratified LOSS-core validation (leave-one-family-out).
4. 9x9 full-classification recount of max-O (exhaustive, not sampled).

## Artifacts

- `scripts/audit_blind_probe.py` → `results/10x10/blind-probe-audit.json`,
  `results/10x10/blind-probe-audit-parents.csv`
- `scripts/corrected_blind_probe.py` → `results/10x10/blind-probe-corrected/`
  (7× `independent_probe_*.csv`, 7× `order_desc_*.csv`,
  `corrected-analysis.json`, `corrected-parents.csv`)
- `scripts/kyouen9_pairsum.py`, `scripts/kyouen9_fast.py`,
  `scripts/scan_9x9_discordant.py` → `results/9x9/pairmob_*`
- `scripts/loss_core_enrichment.py` → `results/10x10/loss-core-enrichment.*`
- `tests/test_pairsum.py` (stdlib runner noted inside; pytest absent in env)

# 8×8 O-stratum night research — structural follow-up

Status: descriptive / post-hoc only. Frozen primary definitions are unchanged.
Branch: `replicate-8x8-o-stratum`
Follows: `docs/8X8_O_STRATUM_REPLICATION_RESULT.md`

## 1. What the frozen 8×8 census already decided

Primary criterion (frozen before any 8×8 outcome):

- success iff Δ_O(O0-only) > 0 **and** gap ≥ +0.05

Observed:

- Δ_O(O0-only) = −0.0424
- gap = −0.0295
- **verdict: FAIL**

This rejects the 9×9 claim that O is much more useful (higher LOSS-select rate) in O0-only than O-overlap, as a board-size-stable law.

## 2. New structural fact: LOSS base-rate collapse

Among the 848 unique exact-solved factorial-selected 5-stone children:

| sample | n | LOSS | LOSS rate | Wilson 95% |
|---|---:|---:|---:|---|
| **8×8 factorial top-moves** | 848 | 64 | **0.075** | [0.060, 0.095] |
| **8×8 random safe 5-stone** | 200 | 8 | **0.040** | [0.020, 0.077] |
| 9×9 factorial top-moves (T/TE/TO/raw) | — | — | **~0.45–0.48** | — |

Random sample: `scripts/sample-8x8-random-safe-5stone.py` seed=20260915,
solved with `cpp/solvers/kyouen_solver_8_root.exe`.

Refined statements:

1. **Population base rate on 8×8 is ~4%, not zero** (earlier n=40 validation was all-WIN by chance).
2. **Factorial selection is mildly enriched** for LOSS (7.5% / 4.0% ≈ 1.9×), so the scores carry some signal even here.
3. **Board-size regime gap is not a selection artifact**: both random and selected 8×8 rates are far below 9×9 factorial ~47%.

Local 1-ply geometry (safe-child mobility, collinear triples, blocked completions, span)
does **not** separate the 63 unique 8×8 LOSS children from the 779 WIN children
(`artifacts/8x8-five-stone-loss-geometry.json`). LOSS here is a deep game-tree property,
not an obvious local cramping signature.

Consequences for the O-stratum experiment:

- O-induced change rate on 8×8 is ~0.10–0.17 per stratum
- same quantity on 9×9 exploratory reference is ~0.44
- Δ estimates on 8×8 are driven by a tiny discordant set (17 / 16 / 17 parents)

This is a **board-size property of the experimental regime**, not a solver defect
(solver already passed brute-force, D4, fresh-process, and memo_power checks).

## 3. Proposition candidates (falsifiable)

### P1 — change-rate collapse (SUPPORTED on this census)

On 8×8 eligible O-stratum parents, O-induced exact-outcome change rate is ≤ 0.17 in every stratum, versus ~0.44 on 9×9.

Falsifier: any 8×8 stratum on the same frozen population with change_rate > 0.20; or a 7×7 / 10×10 census with change_rate ~0.44 under identical definitions.

### P2 — O0-only sign is not board-stable (SUPPORTED as non-replication)

Δ_O(O0-only): 9×9 holdout +0.091 vs 8×8 census −0.042.

Falsifier: independent 7×7 or 10×10 O0-only census with Δ > +0.05 using the same frozen definitions.

### P3 — O1-only net hurt on 8×8 (CANDIDATE, needs independent data)

On 8×8 O1-only, adding O at E=1 increases LOSS-select rate: Δ_O_E1 = +0.088 (13 hurt vs 4 helped). Magnitude exceeds the 9×9 O1-only reference (+0.018).

Falsifier: 7×7 or 10×10 O1-only census with Δ_O_E1 ≤ 0.

### P4 — E×O interaction ≈ 0 is board-stable (SUPPORTED)

8×8 O-overlap: I = 0 for all 155 parents. 9×9 full 4-outcome set: mean I = 0 on n=470.

Falsifier: any board with |mean I| > 0.02 on a full O-overlap census under the same I definition.

### P5 — pure shallow parity (REJECTED)

Naive claim “all safe 5-stone positions on 8×8 are WIN” is false:
census contains **64 LOSS** factorial-selected children; random sample contains **8/200 LOSS**.
Parity-like base rates are strong but not absolute.

### P6 — local geometry predicts 5-stone LOSS (REJECTED on 8×8)

Outcome-free 1-ply features (safe-child mobility, collinear triples among the 5 stones,
blocked completions, bounding-box span) do not separate LOSS from WIN
(mobility means 33.9 vs 35.4; heavy overlap). LOSS is not locally “cramped” in an obvious way.

## 4. Cross-board table

| stratum | n 8×8 | n 9×9 | Δ 8×8 | Δ 9×9 | change 8×8 | change 9×9 |
|---|---:|---:|---:|---:|---:|---:|
| O0-only | 165 | 296 | −0.0424 | +0.0912 | 0.103 | 0.436 |
| O-overlap | 155 | 419 | −0.0129 | −0.0143 | 0.103 | 0.444 |
| O1-only | 102 | 220 | +0.0882 | +0.0182 | 0.167 | 0.436 |

Note on sign: LOSS=1, so positive Δ means the O-enabled top move is *more often labeled LOSS* (better at finding an opponent-losing child) under the factorial encoding used in the 9×9 docs.

## 5. Interpretation

The cleanest reading of tonight’s data:

1. The 9×9 O0-only “O hurts / helps more” pattern does **not** replicate on 8×8.
2. The reason 8×8 is a weak test of that pattern is now measurable: **almost no 5-stone outcome signal**.
3. Shared-parent E×O interaction remains essentially zero — that part of the 9×9 story is robust.
4. A secondary O1-only positive Δ on 8×8 is real in this census but is **not** promoted to a new primary claim; it needs another independent board/holdout.

## 6. Artifacts added tonight

- `scripts/analyze-8x8-o-posthoc-structure.py`
- `scripts/audit-8x8-o-base-rates.py`
- `scripts/analyze-8x8-five-stone-loss-geometry.py`
- `scripts/sample-8x8-random-safe-5stone.py`
- `scripts/compare-8x8-loss-rates.py`
- `artifacts/8x8-o-posthoc-structure.json`
- `artifacts/8x8-o-flip-classes.csv`
- `artifacts/8x8-o-base-rate-audit.json`
- `artifacts/8x8-five-stone-loss-geometry.json` / `.csv`
- `artifacts/8x8-random-safe-5stone-sample.csv` / `-out.csv`
- `artifacts/8x8-loss-rate-comparison.json`
- this document

## 7. Next highest-value experiments

1. Independent O1-only census on 7×7 or 10×10 (same score / stratum definitions).
2. Measure 5-stone LOSS base rate on 7×7 and 10×10 with a random safe sample (not factorial-selected) to locate where the ~0.47 regime appears.
3. Characterize the 64 eight-by-eight 5-stone LOSS children geometrically (why parity-like base rate fails there).

## 8. Self-assessment

Did new knowledge increase?

- **Yes, modestly and honestly.**
- We did **not** confirm the 9×9 structural claim.
- We **did** turn a failed replication into a measurable regime explanation (LOSS base-rate collapse) and kept one robust negative result (zero interaction).
- The O1-only lead is explicitly secondary and unfrozen for future primary use.

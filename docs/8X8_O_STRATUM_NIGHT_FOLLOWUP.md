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

### P7 — 8×8 shallow depth profile has a 5-stone WIN peak (SUPPORTED on random samples)

Random safe positions on 8×8, solved with `kyouen_solver_8_root.exe`:

| stones | n | LOSS | LOSS rate | visited median |
|---:|---:|---:|---:|---:|
| 0 (empty) | — | — | **1.0** (known: 8×8 second-player win) | — |
| 3 | 150 | 4 | **0.027** | 106742 |
| 4 | 150 | 92 | **0.613** | 115079 |
| 5 | 200 | 8 | **0.040** | 3636 |
| 6 | 150 | 44 | **0.293** | 1148 |

Reading:

- **5 stones is a sharp WIN peak** (96% WIN) — this is why the O-stratum factorial
  experiment sits in a low-signal regime.
- **Simple stone-count parity is false**: even depths are not ~100% LOSS
  (4-stone 61%, 6-stone 29%). Odd≈WIN holds approximately at 3 and 5.
- Visit cost collapses as stones increase (branching shrinks); 3–4 stones are
  ~30× more expensive than 5–6 stones at this board size.

Artifacts: `artifacts/8x8-random-depth-profile.json`,
`scripts/sample-k-stone.py`, `scripts/summarize-8x8-depth-profile.py`,
`artifacts/8x8-random-safe-{3,4,5,6}stone-*.csv`.

### P8 — 4↔5 impartial identity on 8×8 (SUPPORTED)

Expanded 40 random safe 4-stone parents (20 LOSS + 20 WIN) to all legal 5th moves
and exact-solved every child (n=2138):

- **0 violations** of `parent LOSS ⇔ all children WIN` / `parent WIN ⇔ ∃ LOSS child`
- child outcomes: 2043 WIN / **95 LOSS** (4.4%)
- all 95 LOSS children come from the 20 WIN parents (~4.8 LOSS children each)

This is a solver-provenance audit for P7: the 5-stone WIN peak is not an
artifact of independent sampling; it is exactly the complement of the 4-stone
LOSS majority under the impartial-game recursion.

Artifacts: `artifacts/8x8-depth-audit-consistency.json`,
`scripts/audit-8x8-depth-consistency.py`.

### P9 — board-dependent shallow LOSS-depth peak (SUPPORTED, cross-board)

Random safe positions, exact-solved with `kyouen_solver_{8,9}_root.exe`:

| board | 4-stone LOSS | 5-stone LOSS | 6-stone LOSS | empty (player to move) |
|---|---:|---:|---:|---|
| **8×8** (second-player win) | **0.613** (n=150) | **0.040** (n=200) | 0.293 (n=150) | LOSS |
| **9×9** (first-player win) | **0.000** (n=80) | **0.620** (n=100) | **0.0125** (n=80) | WIN |

The profile is essentially **inverted** across boards:

- On 8×8, LOSS concentrates at **4 stones**; the 4→5 transition (the factorial
  experiment’s depth) is a near-all-WIN low-signal regime.
- On 9×9, LOSS concentrates at **5 stones**; the same 4→5 transition is high-signal.

This is the structural explanation for why the 9×9 O-stratum effect sizes
(~0.44 change rate) do not transfer to 8×8 (~0.10): the factorial design
samples a different region of the shallow game tree on each board.

Falsifier: a board where both 4-stone and 5-stone random LOSS rates sit in the
same intermediate band (e.g. both in [0.3, 0.5]) under identical sampling.

Artifacts: `artifacts/cross-board-depth-profile.json`,
`artifacts/9x9-random-safe-{4,5,6}stone-*.csv`,
`scripts/summarize-cross-board-depth-profile.py`.

### P9b — peak depth tracks empty-board winner on 6×6…9×9 (SUPPORTED)

Random safe LOSS rates after fixing a V<64 legal-mask bug in the 6/7 solvers
(`legal` had bits ≥ V set, which made N<8 solvers explode):

| board | empty (player to move) | 4-stone | 5-stone | 6-stone | **peak depth** |
|---|---|---:|---:|---:|---|
| 6×6 (first-player win) | WIN | 0.005 (n=200) | **0.300** (n=200) | 0.100 (n=80) | **5** |
| 7×7 (second-player win) | LOSS | **0.200** (n=200) | 0.085 (n=200) | 0.150 (n=80) | **4** |
| 8×8 (second-player win) | LOSS | **0.613** (n=150) | 0.040 (n=200) | 0.293 (n=150) | **4** |
| 9×9 (first-player win) | WIN | 0.000 (n=80) | **0.620** (n=100) | 0.013 (n=80) | **5** |

Pattern:

- **First-player-win boards peak at 5 stones**; **second-player-win boards peak at 4**.
- **Peak height grows with board size** (mild on 6×6/7×7, extreme on 8×8/9×9).

Falsifier: any board in this set where the modal shallow depth contradicts the
empty-board winner, with n≥200 at the two candidate depths.

Provenance: 6×6/7×7 solvers are mechanical N/V ports of `kyouen_solver_8_root.cpp`
plus a legal-mask fix for V<64. Move ordering / memo / WIN-LOSS semantics unchanged.

Artifacts: `artifacts/cross-board-depth-profile-6789.json`,
`cpp/solvers/kyouen_solver_{6,7}_root.cpp`,
`scripts/summarize-depth-profile-6789.py`.

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

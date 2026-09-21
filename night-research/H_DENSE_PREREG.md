# Pre-registration — H-dense independent test (freeze)

Status: **FROZEN for future independent boards only**  
Date: 2026-09-17 (Cycle 4)  
Hypothesis id: **H-dense**

## Statement (frozen)

Among first-player-win kyouen boards, **only exceptional boards can have a
non-full winning first-move set**. Empirically for n≤10 the exceptional set is
exactly `{5}`:

- F-win n∈{1,2,3,6,9}: density = 1 (all cells win) — **complete exact data**
- F-win n=5: density = 9/25 = 0.36 — **complete exact data**
- S-win n∈{4,7,8,10}: density = 0 by definition

Exploratory formulation (Cycle 2/3): “Among F-win n≤10, only n=5 has any
losing first move.”

## Why this is not an independent confirmation

n=9 completed to all-win **after** H-dense was formulated, but the formulation
was made while partial 9×9 data already pointed that way. n=10 density=0 is
definitional from S-win. Therefore n≤10 does **not** provide a clean holdout.

## Independent confirmation criterion (frozen)

Let n₁ < n₂ < … be the next F-win board sizes strictly greater than 10 whose
empty-board winner is certified FIRST_WIN by a complete proof/certificate.
For each such n:

- **Support** if every first move is FIRST_WIN (density = 1.0), **or** if a
  non-full winning set occurs only when a separately justified structural
  criterion (to be frozen before that board’s first-move outcomes are computed)
  names n as exceptional.
- **Refute** if any F-win n>10 has at least one FIRST_LOSS cell **without**
  a pre-frozen structural exceptional-label.

## Non-claims

- H-dense does not separate F-boards from S-boards.
- H-dense does not predict *which* n are F vs S.
- Density-1 first moves do not imply simple local geometry (n=5 WIN set looks
  lattice-like but does not embed-stably transfer; Cycle 3).

## Related rejected hypotheses (do not revive without new mechanism)

- H1 terminal-parity locking — REJECTED (n=4)
- H3-abs even-sum-minus-corners as cross-size rule — REJECTED on 9×9
- H-embed center-relative transfer 5×5→9×9 — REJECTED (3 MATCH / 3 FLIP)
- H4 static pair-witness count as depth-uniform law — REJECTED at k=5
- Local 1-ply geometry predicts LOSS — REJECTED on 8×8

## Frozen artifacts backing the exploratory base rate

- `night-research/cycle4-density-table.json`
- `night-research/cycle4-exact-n5.json`
- `night-research/first-moves-9x9.csv`
- `night-research/CYCLE3_RESULTS.md`, `CYCLE4_EXACT_STRUCTURE.md`

## Next independent board protocol

1. Do **not** peek at first-move outcomes on the test board while choosing any
   structural exceptional-label rule.
2. Run complete first-move classification (D4 orbits) only after freeze.
3. Record outcome in `night-research/CYCLE*_RESULTS.md` with verdict
   SUPPORTED / REFUTED / UNDECIDED (if board is S-win, H-dense is silent —
   density 0 is definitional).

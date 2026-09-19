# Cycle 8–14 — consolidated main result (n=7 K=14 structure)

Branch `cycle8-n7-structure`, base `2d3855a`.
Independent verifies: `results/cycle8_verify.json`, `results/cycle11_verify.json` (all PASS).
C++ regression gate: `results/cycle13_128bit_regression.json` (PASS: 16,464,8,0).

## COMPLETE selection theorem (computer-assisted)

On 7×7 kyouen, K7=14 and the maximizing family has **16 sets / 2 D4 phases**.

**Occupancy order:** orbits `(0,0)(0,1)(0,2)(0,3)(1,1)(1,2)(1,3)(2,2)(2,3)(3,3)`.

1. **Realized vectors (COMPLETE enum):**
   - A = (2,3,2,0,1,3,2,0,0,1) — 8 sets
   - B = (3,1,2,1,1,3,1,0,2,0) — 8 sets
2. **Phase A ≡ center ∧ corners=2** (count=8 COMPLETE).
3. **Phase B ≡ ¬center ∧ corners=3 ∧ require(0,3)∧require(2,3)** (count=8 COMPLETE).
4. **Mandatory orbits** (forbid-orbit@14 = 0 COMPLETE for five of them; census 16/16 for all six):
   `(0,0),(0,1),(0,2),(1,1),(1,2),(1,3)`.
5. **Forbidden orbit:** `(2,2)` never used; force@14 count=0 COMPLETE.
6. **Exclusivity (COMPLETE zeros):** center ∧ require(0,3)/(2,3)/(2,2) = 0;
   ¬center ∧ forbid(0,3)∧forbid(2,3) = 0.
7. **Capacity edges (COMPLETE):** (2,2)⇒max13; center+(0,3)⇒13; center+(2,3)⇒**12**;
   forbid(0,2)⇒**12**; corners=4⇒≤12; K=14 corners ∈{2,3} only.
8. **Exchange geometry (COMPLETE on the 16):** unique D4 5→5 template;
   min_det=2 all 16; no 1-swap; d*=5; all 224 thirteen-subsets uniquely complete;
   edit-paths between distinct max sets visit size ≤12 (full board) / ≤11 (union).
9. **τ≥3** to free any empty (2,2) cell from any max set (COMPLETE blockers on 16×4).

## Contrast (COMPLETE censuses)

| | n=4 K=7 | n=5 K=9 | n=6 K=11 | n=7 K=14 |
|---|---:|---:|---:|---:|
| # max sets | 64 | 100 | 464 | **16** |
| mandatory orbits | 3/3 | 4 | 4 | **6** |
| empty orbit at max | none | none (center optional 44/100) | none ((2,2) used 360/464) | **(2,2)** |
| occupancy vectors | 4 | 9 | 22 | **2** |
| min_det min | 3–4 | 3 | 3 | **2** |
| K vs 2n−1 | 2n−1 | 2n−1 | 2n−1 | **2n** |

n=8 SAMPLE (not complete): 45 occupancy patterns / 53 sets via occ; (2,2) often used;
forbid-orbit first@15 finds witnesses omitting most orbits — crystal does **not** transfer.

## Maximum-layer sharpness

K=13 SAMPLE occ: 150 patterns / 1116 seen; center+(2,2) legal at 13 (24 COMPLETE);
corners=4 still 0 at 13. Forbid (0,2) @size12 layer is diffuse (176 patterns) and uses (2,2).
Selection/exclusivity are **K=14 peak phenomena**.

## Capacity decomposition (Cycle 15 COMPLETE)

Let M = six mandatory orbits. Then:
- max on M only (forbid center, (0,3), (2,3), (2,2)) = **13** COMPLETE
- max on M∪{center} (forbid B-bundle∪(2,2)) = **14** COMPLETE (8 = A)
- max on M∪{(0,3),(2,3)} (forbid center∪(2,2)) = **14** COMPLETE (8 = B)
- (2,2) never lifts above 13; center and B-bundle cannot combine at 14

> K7=2n is bought by a **mutually exclusive** phase extension of a skeleton
> that already supports 2n−1. See `CYCLE15_CAPACITY_DECOMPOSITION.md`.
>
> Refined: partial B-bundle (only (0,3) or only (2,3)) peaks at **13** COMPLETE;
> full B-bundle required for 14. Orbit `(0,2)` is mandatory already at **K=13**
> COMPLETE; it touches **48%** of n=7 quads — but n=6 has even higher edge-orbit
> incidence and still diffuse maxima, so **density alone is rejected** as the
> explanation (see Cycle 16 note in the decomposition file).

### Cycle 24–28 addenda
- n=4/5/6 COMPLETE omit-cost mostly −1; n=7 (0,2) −2; n=4 omit(0,1) also −2 → omit-cost alone ≠ crystal.
- n=6 require(2,2)@11=360 COMPLETE; forbid(2,2) still max=11 (104) COMPLETE.
- Cycle 27: A-core/B-core explicit; cross-phase quads named; independent is_safe PASS.
- Cycle 28: K=13 require center=280 COMPLETE; K=12 forbid(0,2)=3464 COMPLETE; forbid(2,2)@14 global=16 COMPLETE.

### n=6 skeleton contrast (COMPLETE)

| n=6 constraint | max |
|---|---:|
| forbid (2,2) only | **11** COMPLETE (104 at 11) — full K achieved without (2,2) |
| forbid (1,1)∧(2,2) | **10** COMPLETE (1272 at 10) |
| forbid (1,1) at K=11 | **8** COMPLETE (some max sets omit (1,1)) |

n=6 already attains 2n−1 on a reduced orbit set; n=7’s +1 requires the
exclusive phase extension.

## What this does / does not prove

**Does:** a finite COMPLETE selection theorem for the n=7 maximizing family,
with sharp n=4/5/6 censuses and n=8 sample contrast; unique phase-exchange
template; min_det / isolation paradox; capacity map around the peak.

**Does not:** a board-size derivation of K7=2n from first principles;
full n=8 classification; K9; full Grundy n=7.

## Open (priority)
1. Geometric proof of the selection theorem from forbidden quads alone.
2. Why n=7 reaches 2n while neighbors sit at 2n−1.
3. n=8 complete orbit-necessity if affordable.
4. K9 128-bit implementation **after** keeping the C++ regression gate green
   (`CYCLE9H_K9_128BIT_DESIGN.md`); no long UNSAT from design alone.

## File index
- `night-research/CYCLE8_N7_STRUCTURE.md` — cycle 8 narrative
- `night-research/CYCLE8_11_MAIN_RESULT.md` — this family of summaries
- `night-research/CYCLE10_OCCUPANCY_SELECTION.md`
- `night-research/CYCLE11_ORBIT_NECESSITY.md`
- `night-research/CYCLE12_K13_LAYER.md`, `CYCLE12_OMIT_MANDATORY.md`
- `night-research/CYCLE14_CAPACITY_NEIGHBORHOOD.md`
- `night-research/CYCLE14H_N8_CONSTRAINED.md`
- `night-research/CYCLE15_CAPACITY_DECOMPOSITION.md`
- `night-research/CYCLE9_G1_NOTES.md`, `CYCLE9_G2_NOTES.md`
- `night-research/CYCLE9H_K9_128BIT_DESIGN.md`
- `docs/compose/spec/cycle8-n7-structure-explain.md`

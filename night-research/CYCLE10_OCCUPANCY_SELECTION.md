# Cycle 10 — why K=14 occupancy on n=7 is only types A and B

Evidence mix (explicit):
- **COMPLETE enum**: 16 max sets realize exactly 2 occupancy vectors.
- **COMPLETE constrained first/count** via `night-research/cycle8_b_maxsafe.exe`
  (complete=true ⇒ exhaustive for that constraint at the stated size).
- Theoretical count of sum=14 vectors within orbit-size caps: **304,752**
  (combinatorial only — not a search).

## Realized vectors (COMPLETE)

Orbit order: `(0,0)(0,1)(0,2)(0,3)(1,1)(1,2)(1,3)(2,2)(2,3)(3,3)`

| type | vector | ids | corners | center |
|---|---|---|---:|---:|
| **A** | (2,3,2,0,1,3,2,0,0,1) | 0,2,5,9,10,11,12,15 | 2 | 1 |
| **B** | (3,1,2,1,1,3,1,0,2,0) | 1,3,4,6,7,8,13,14 | 3 | 0 |

Always-used on all 16 (count>0 in both A and B): `(0,0),(0,1),(0,2),(1,1),(1,2),(1,3)`.
Never-used on all 16: `(2,2)`.
Phase-exclusive: center / `(0,3)` / `(2,3)`.

## COMPLETE constraint table (first/count @ K=14)

| constraint | result | complete? |
|---|---:|---|
| force center | 8 (= all A) | yes |
| force one `(0,3)` cell | 2 | yes |
| force one `(2,3)` cell | 4 | yes |
| force one `(2,2)` cell | **0** | yes |
| require orbit center | 8 | yes |
| center ∧ require `(0,3)` | **0** | yes |
| center ∧ require `(2,3)` | **0** | yes |
| center ∧ require `(2,2)` | **0** | yes |
| center ∧ corners=3 | **0** | yes |
| no-center ∧ forbid `(0,3)`∧`(2,3)` | **0** | yes |
| force 3 specific `(1,3)` | **0** | yes |
| force 3 specific `(0,1)` | **0** | yes |
| force 3 specific `(2,3)` | **0** | yes |
| force 4 `(2,3)` | unsafe (−1) | yes |
| force two specific `(1,3)` | 2 | yes |
| forbid orbit `(2,2)` | still possible (16 exist) | enum |
| corners=4 @14 | **0** | yes (Package B) |

Incomplete-but-informative (node cap): require `(1,1)/(1,2)/(0,2)` ≥10 hits
(consistent with always-used); require `(0,3)` or `(2,3)` ≥6 (B side);
no-center∧corners=2 incomplete 0 (B uses 3 corners);
no-center∧require(0,3)∧require(2,3) count≥7 incomplete (expect 8=all B).

### Phase characterization (COMPLETE)

| phase | COMPLETE defining constraints @K=14 | count |
|---|---|---:|
| **A** | center ∧ corners=2 | **8** complete |
| **B** | ¬center ∧ corners=3 | **8** complete |
| A excluded from B-orbits | center ∧ require(0,3) or require(2,3) or require(2,2) | **0** complete |
| B needs its orbits | ¬center ∧ forbid(0,3)∧forbid(2,3) | **0** complete |

> **Phase lemma.** The 16 n=7 max safe sets are exactly
> `{center ∧ corners=2}` ⊔ `{¬center ∧ corners=3}` (8+8 COMPLETE),
> and the no-center branch cannot omit the `(0,3)/(2,3)` orbits.

## Selection lemma (compressed)

> On 7×7, a size-14 safe set’s D4-orbit occupancy vector must satisfy:
> 1. `(2,2)=0` (COMPLETE).
> 2. corners ∈ {2,3} only; corners=4 impossible at 14 (COMPLETE).
> 3. center ∈ {0,1}; if center=1 then `(0,3)=(2,3)=0` (COMPLETE exclusivity).
> 4. if center=0 then the set **must** use both orbits `(0,3)` and `(2,3)`
>    — forbidding them together with no center leaves **zero** K=14 sets (COMPLETE).
> 5. Local caps: `(1,3)≤2`, `(2,3)≤2`, and the specific-cell force tests above.
> 6. Under (1)–(5) and orbit-size caps, the census realizes **exactly two**
>    full vectors A and B (COMPLETE enum of 16).
>
> Among 304,752 theoretical sum=14 vectors respecting only orbit *sizes*,
> only these two survive the geometry.

This is the strongest available compression of “why only two phases at K=14”:
not an average trend, but a **finite COMPLETE selection rule** on occupancy,
with the no-center branch *forcing* the B-side orbits on.

## Relation to K7=14 / n=7 anomaly

- K7=14=2n is still inherited (not re-proved).
- Cycle 10 explains the **shape** of the maximizing family, not yet a
  board-size criterion for why n=7 reaches 2n.
- n=8 SAMPLE shows many occupancy patterns — the two-phase selection is
  not a generic max-safe phenomenon.

## Artifacts

- `results/cycle10_occupancy_probes.json`
- `night-research/cycle10_occupancy_probes.py`
- Solver: `night-research/cycle8_b_maxsafe.exe`

## Next probes

1. COMPLETE count @14 under `no-center ∧ require (0,3) ∧ require (2,3)`
   (expect 8 = all B) — require both orbits without center.
2. COMPLETE max under forcing the *counts* of A vs B via enough forced cells
   from each orbit bundle.
3. Independent Python recompute of the COMPLETE zeros in the table.

# Cycle 14 — capacity neighborhood of the A/B crystal (n=7 K=14)

Evidence: `cycle8_b_maxsafe.exe` COMPLETE counts unless noted.

## COMPLETE phase re-confirmation

| constraint | @K=14 |
|---|---:|
| center ∧ corners=2 ∧ require(1,2) | **8** complete (= all A) |
| ¬center ∧ corners=3 ∧ require(0,3)∧require(2,3) | **8** complete (= all B) |
| center ∧ corners=2 ∧ forbid(2,3) | max=**14** complete (8 at 14) |

Phase A never needs (2,3); forbidding it is non-binding on the A branch.
Phase B is exactly the no-center / 3-corner / B-orbit branch.

## Capacity edges near the crystal

| constraint | max / count | status |
|---|---|---|
| forbid entire corners orbit | max≤13 (seen 12) | incomplete |
| forbid (0,2) | max=**12** | COMPLETE |
| force (2,2) | max=**13** | COMPLETE |
| center+(2,3) | max=**12** | COMPLETE |
| corners=4 | max≤12 | COMPLETE (no 13, no 14) |
| center+(0,3) | max=**13** | COMPLETE |

## Lemma

> The K=14 family sits at a sharp peak: any of several local deviations
> (use (2,2); add center+(2,3); omit (0,2); use 4 corners) drops the maximum
> by 1–2 stones. The two peaks A and B are the only ways to stay at 14,
> each fully characterized by COMPLETE constraint counts (8+8).

## Artifacts
- this note
- `night-research/CYCLE10_OCCUPANCY_SELECTION.md`
- `night-research/CYCLE11_ORBIT_NECESSITY.md`
- `results/cycle10_occupancy_probes.json`

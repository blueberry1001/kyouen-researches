# Selection theorem — COMPLETE evidence checklist

For each claim, evidence type and where to re-run.

## Inherited (do not re-prove without need)

| claim | evidence |
|---|---|
| K7=14, 16 max sets | `maxsafe_enum.exe count 7 14` → 16 |
| K6=11, 464 max sets | `maxsafe_enum.exe count 6 11` → 464 |
| K8=15 | prior Cycle 5/6 |

## Occupancy / phases (COMPLETE)

| claim | evidence |
|---|---|
| exactly 2 occupancy vectors A,B | enum of 16; `cycle11_verify.py` |
| A ≡ center ∧ corners=2 (8) | `cycle8_b_maxsafe.exe first/count 7 14 --force 24 --corners 2` → 8 complete |
| B ≡ ¬center ∧ corners=3 ∧ require(0,3)∧(2,3) (8) | `first 7 14 --forbid 24 --corners 3 --require-orbit 0,3 --require-orbit 2,3` → 8 complete |
| center ∧ require(0,3)/(2,3)/(2,2) = 0 @14 | COMPLETE zeros |
| ¬center ∧ forbid(0,3)∧forbid(2,3) = 0 @14 | COMPLETE zero |
| mandatory orbits (0,0)(0,1)(0,2)(1,1)(1,2) forbid@14=0 | COMPLETE zeros |
| (1,3) census 16/16 | enum |
| (2,2) force@14=0 | COMPLETE |
| theoretical sum14 vectors under caps = 304752 | combinatorial count |

## Capacity edges (COMPLETE)

| constraint | max |
|---|---:|
| (2,2) forced | 13 |
| center+(0,3) | 13 |
| center+(2,3) | 12 |
| forbid (0,2) | 12 |
| corners=4 | ≤12 (no 13, no 14) |
| skeleton M only | 13 |
| M∪{center} | 14 (8 sets) |
| M∪B-bundle | 14 (8 sets) |

## Exchange / pinning (COMPLETE on the 16)

| claim | evidence |
|---|---|
| unique D4 5→5 exchange | `cycle8_a_verify.py` |
| min_det=2 all 16 | `cycle8_c_determining.py` + verify |
| min_det≥3 on n=4,5,6 max sets | `cycle9_small_n_min_det.py` |
| no 1-swap | verify + exchange csv |
| 224/224 unique 13-completion | verify |
| τ∈{3,4} on (2,2) vs max sets | `cycle8_g1_*` + independent |

## Layer sharpness

| layer | occupancy richness |
|---|---|
| K=14 | 2 COMPLETE |
| skeleton K=13 | 6 COMPLETE |
| unrestricted K=13 | 150 SAMPLE / 1116 seen |
| forbid(0,2) K=12 | 176 SAMPLE |

## Contrasts

n=6: no empty orbit; (2,2) used 360/464; 22 occ vectors; min_det≥3;
forbid(2,2) still max=11 COMPLETE.
n=8 SAMPLE: (2,2) and center-block flexible; many occ patterns.

## Independent verifies
- `results/cycle8_verify.json` PASS
- `results/cycle11_verify.json` PASS
- `night-research/CYCLE15_VERIFY.md` (skeleton@14 unsat Python)
- `results/cycle13_128bit_regression.json` PASS (16,464,8,0)

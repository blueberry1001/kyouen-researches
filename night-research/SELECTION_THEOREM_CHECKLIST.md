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
| corners=2 ∧ require center @14 | 8 COMPLETE |
| corners=3 ∧ require center @14 | 0 COMPLETE |
| corners=2 ∧ require both B-orbits @14 | 0 seen (incomplete; census says 0) |
| corners=3 ∧ require (2,3) @14 | **8 COMPLETE** (=B) clean |
| corners=2 ∧ forbid both B-orbits @14 | **8 COMPLETE** (=A) clean |
| corners=3 ∧ require both B-orbits @14 | **8 COMPLETE** (=B) clean |
| corners=2 ∧ require center @14 | **8 COMPLETE** (=A) clean |
| corners=3 ∧ require (0,3) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require (2,3) @14 | **8 COMPLETE** (=B) clean |
| require center ∧ corners=2 @14 | 8 COMPLETE (=A) |
| require (0,2) ∧ corners=3 @14 | 8 COMPLETE (= all B) |
| forbid B∪(2,2) @14 | 8 COMPLETE (=A) |
| forbid center∪(2,2) @14 | 8 COMPLETE (=B) |
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
| forbid (0,0) corners @14 | **0 COMPLETE** |
| require corners orbit @14 | ≥15 incomplete (census 16/16) |
| corners=4 @14 | **0 COMPLETE** |
| corners=1 @14 | 0 seen (census 0) |
| corners=2 @14 | 8 COMPLETE (phase A via require center) |
| corners=3 @14 | 8 COMPLETE (phase B) |
| corners=2 ∧ require center @14 | **8 COMPLETE** (=A) |
| corners=3 ∧ forbid center @14 | **8 COMPLETE** (=B) clean |
| corners=2 ∧ require center @14 | **8 COMPLETE** (=A) clean |
| corners=3 ∧ require corners @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require corners @14 | **8 COMPLETE** (=B) clean |
| corners=2 ∧ forbid (0,2) @14 | **0 COMPLETE** clean |
| corners=2 ∧ forbid (0,2) @14 | **0 COMPLETE** clean |
| corners=2 ∧ forbid (1,2) @14 | **0 COMPLETE** clean |
| corners=2 ∧ forbid (1,3) @14 | **0 COMPLETE** clean |
| corners=2 ∧ forbid (1,1) @14 | **0 COMPLETE** clean |
| corners=2 ∧ forbid (0,1) @14 | **0 COMPLETE** clean |
| corners=2 ∧ forbid corners @14 | **0 COMPLETE** clean |
| corners=3 ∧ forbid corners @14 | **0 COMPLETE** clean |
| corners=3 ∧ forbid (0,3) @14 | **0 COMPLETE** clean |
| corners=3 ∧ forbid (2,3) @14 | **0 COMPLETE** clean |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) clean reconfirm |
| corners=3 ∧ forbid (2,2) @14 | **8 COMPLETE** (=B) clean |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) clean |
| corners=3 ∧ forbid (0,1) @14 | **0 COMPLETE** clean |
| corners=3 ∧ require (0,2) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require (1,2) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require corners @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ forbid center @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require both B-orbits @14 | **8 COMPLETE** (=B) clean |
| corners=2 ∧ forbid center @14 | **0 COMPLETE** clean |
| corners=3 ∧ require corners @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ forbid center @14 | **8 COMPLETE** (=B) clean |
| corners=2 ∧ forbid center ∧ require (0,3) @14 | 0 seen (census 0) |
| corners=3 ∧ forbid center ∧ require center @14 | **0 COMPLETE** (contradiction) |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) |
| corners=2 ∧ require center @14 | **8 COMPLETE** (=A) |
| corners=3 ∧ require (1,3) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require (1,2) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require (0,2) @14 | **8 COMPLETE** (=B) |
| corners=3 ∧ require (0,1) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require (0,3) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require (0,3) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require (2,3) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require (1,1) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require (1,1) @14 | **8 COMPLETE** (=B) clean |
| corners=3 ∧ require corners orbit @14 | **8 COMPLETE** (=B) |
| corners=2 ∧ forbid (0,3)∧(2,3) @14 | **8 COMPLETE** (=A) clean |
| corners=2 ∧ forbid (0,3) alone @14 | **8 COMPLETE** (=A) clean |
| corners=2 ∧ forbid (2,3) alone @14 | **8 COMPLETE** (=A) clean |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) clean reconfirm |
| corners=3 ∧ forbid (2,2) @14 | **8 COMPLETE** (=B) clean |
| corners=2 ∧ forbid both B-orbits @14 | **8 COMPLETE** (=A) clean |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) clean |
| corners=3 ∧ forbid corners @14 | **0 COMPLETE** clean |
| corners=2 ∧ forbid (0,3) alone @14 | **8 COMPLETE** (=A) clean |
| corners=2 ∧ forbid corners @14 | **0 COMPLETE** clean |
| corners=2 ∧ forbid corners @14 | **0 COMPLETE** clean |
| corners=3 ∧ forbid corners @14 | **0 COMPLETE** clean |
| corners=3 ∧ forbid (2,2) @14 | **8 COMPLETE** (=B) |
| corners=2 ∧ forbid (2,3) @14 | **8 COMPLETE** (=A) |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) |
| corners=2 ∧ forbid (0,2) @14 | **0 COMPLETE** reconfirm |
| corners=3 ∧ forbid (2,2) @14 | **8 COMPLETE** (=B) |
| corners=2 ∧ forbid (1,2) @14 | **0 COMPLETE** reconfirm |
| corners=3 ∧ forbid (1,2) @14 | **0 COMPLETE** reconfirm |
| corners=2 ∧ forbid (0,0) @14 | **0 COMPLETE** (A has 2 corners) |
| corners=2 ∧ forbid (0,1) @14 | **0 COMPLETE** reconfirm |
| corners=3 ∧ forbid (0,0) @14 | **0 COMPLETE** |
| corners=3 ∧ forbid (0,1) @14 | **0 COMPLETE** reconfirm |
| corners=3 ∧ forbid (0,2) @14 | **0 COMPLETE** |
| corners=3 ∧ forbid (0,3) @14 | **0 COMPLETE** |
| corners=3 ∧ forbid (2,3) @14 | **0 COMPLETE** |
| corners=3 ∧ forbid (1,1) @14 | **0 COMPLETE** reconfirm |
| corners=3 ∧ forbid (1,3) @14 | **0 COMPLETE** reconfirm |
| corners=2 ∧ forbid (1,1) @14 | **0 COMPLETE** reconfirm |
| corners=2 ∧ forbid (1,3) @14 | **0 COMPLETE** reconfirm |
| corners=2 ∧ require (0,3) @14 | **0 COMPLETE** |
| corners=2 ∧ require (2,3) @14 | **0 COMPLETE** |
| corners=2 ∧ require (2,2) @14 | **0 COMPLETE** |
| corners=3 ∧ require (2,2) @14 | **0 COMPLETE** |
| corners=3 ∧ require center @14 | **0 COMPLETE** |
| corners=2 ∧ require (0,2) @14 | ≥7 incomplete (census A has (0,2)=2) |
| corners=2 ∧ require corners orbit @14 | ≥7 incomplete (census 8=A all have 2 corners) |
| corners=2 ∧ require (1,1) @14 | ≥6 incomplete (census A has (1,1)=1) |
| corners=2 ∧ require (0,1) @14 | ≥6 incomplete (census A has (0,1)=3) |
| forbid (0,1) @14 | **0 COMPLETE** |
| forbid (0,2) @14 | 0 COMPLETE |
| forbid (1,2) @14 | 0 COMPLETE |
| forbid (1,1) @14 | 0 seen (census 16/16) |
| forbid (0,2) @13 | **0 COMPLETE** |
| forbid (1,2) @13 | **0 COMPLETE** |
| forbid (0,2)∧(1,2) | max **11** COMPLETE (3592@11; 0@12 COMPLETE) |
| forbid (0,2)∧(0,1) | max **11** COMPLETE (696@11) |
| forbid (0,3) alone @14 | **8 COMPLETE** (phase A remains) |
| forbid (0,1) @13 | 24 COMPLETE (optional at 13) |
| corners=4 | ≤12 (no 13, no 14) |
| skeleton M only | 13 COMPLETE |
| M∪{center} | 14 (8 sets) COMPLETE |
| M∪{(0,3)} only | 13 COMPLETE (288@13) |
| M∪{(2,3)} only | 13 COMPLETE (304@13) |
| M∪{(0,3),(2,3)} full B-bundle | 14 (8 sets) COMPLETE via require |

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
forbid(2,2) still max=11 COMPLETE; higher edge-orbit quad incidence than n=7.
n=5: center split 44/56 COMPLETE at K=9 — center alone ≠ crystal.
n=8 SAMPLE: (2,2) and center-block flexible; many occ patterns; d=4 pair exists.

## Cross-board omit-cost (COMPLETE max probes)

| omitted | n=5 | n=6 | n=7 |
|---|---:|---:|---:|
| center/(2,2) | 0 still K=9 (56 without / 44 with) | 0 still K=11 (104 without / 360 with) | forbidden @14 |
| (0,2) | −1 (max 8) | −1 (max 10) | **−2** (max 12) |
| (1,2) | −1 (max 8) | −1 (max 10) | **−2** |

## Phase cores (Cycle 27)

| test | result |
|---|---|
| A-core = A0\\center (13) extends to A0 | witness found |
| B-core = B0\\B-bundle (11) extends to B0 | witness found |
| A-core ∪ B-bundle | unsafe |
| B-core ∪ center | unsafe |

## K=13 layer (Cycle 28)

| constraint @13 | result |
|---|---|
| require center | **280 COMPLETE** |
| forbid (0,2) or (1,2) | **0 COMPLETE** (hard) |
| corners=4 | **0 COMPLETE** |

## Independent verifies
- `results/cycle8_verify.json` PASS
- `results/cycle11_verify.json` PASS
- `night-research/CYCLE15_VERIFY.md` (skeleton@14 unsat Python)
- `results/cycle13_128bit_regression.json` PASS (16,464,8,0)

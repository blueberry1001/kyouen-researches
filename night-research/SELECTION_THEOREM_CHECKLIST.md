# Selection theorem — COMPLETE evidence checklist

For each claim, evidence type and where to re-run.

## Inherited (do not re-prove without need)

| claim | evidence |
|---|---|
| K7=14, 16 max sets | `maxsafe_enum.exe count 7 14` → 16 |
| K6=11, 464 max sets | `maxsafe_enum.exe count 6 11` → 464 |
| K8=15 | prior Cycle 5/6 |

## Geometric root (Cycles 30–32)

| claim | evidence |
|---|---|
| every D4-orbit on any n×n lies on a center circle | `cycle31b_orbit_circles_all_n.py` (constant r2x4; all-4-subset det0) COMPLETE |
| local occupancy ≤3 on every orbit ≥4 | orbit–circle lemma (first principles) |
| n=7 M-orbits all concyclic; pair max 6 or 5; selected triple max 9 | `cycle30b` solver COMPLETE |
| α(M)=13, omit (1,2) in M → 11, omit (0,1)/(0,2) in M → 12 | `cycle30b` COMPLETE |
| all C(6,4) 4-subsets of M max ≤12 COMPLETE; 5-subsets 11–13; M=13 | `cycle30c` COMPLETE |
| LP local+4-orbit caps still allow spurious occ sum 14 | `cycle30c` integer LP |
| **120/120 sum-14 occ vectors (o≤3) unrealizable on M** | `cycle34` COMPLETE decision |
| known sum-13 occ A/dom/Bcore realizable (controls) | `cycle34` COMPLETE |
| **α(M)≤13 occupancy-lattice certificate** | `CYCLE34_OCCUPANCY_LATTICE_CERTIFICATE.md` COMPLETE |
| A/B phase occ Σ=14 realizable; mixed phase sums not | `cycle35` COMPLETE decision |
| force (2,2) cell @14 max=13 COMPLETE n_at=160 | `cycle36b` solver COMPLETE |
| structured sum-14 occ with o_(2,2)≥1 unrealizable (SAMPLE) | `cycle36b` decision |
| witness occ (2,2,3,0,1,3,1,1,0,0) Σ=13 with F=1 realizable | `cycle36b` control |
| K/Σceil n=5/6/7 = 0.60 / 0.61 / **0.52** | `cycle35` COMPLETE local |
| restricted widest A–B path on union=19 is **width 11** | `cycle39c` COMPLETE Dijkstra |
| center∧B-bundle co-occurring quads = 360 | `cycle30_skeleton_geometry.py` |
| cross-shell multi-orbit quad fractions n=4..8 | `cycle32_cross_shell_quads.py` COMPLETE local (n=7: 96.6%) |

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
| corners=2 ∧ forbid (0,1) @14 | **0 COMPLETE** reconfirm |
| corners=3 ∧ forbid (0,1) @14 | **0 COMPLETE** reconfirm |
| corners=2 ∧ forbid (1,1) @14 | **0 COMPLETE** reconfirm |
| corners=3 ∧ forbid (1,1) @14 | **0 COMPLETE** reconfirm |
| corners=2 ∧ forbid (1,3) @14 | **0 COMPLETE** reconfirm |
| corners=3 ∧ forbid (1,3) @14 | **0 COMPLETE** reconfirm |
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
| corners=2 ∧ forbid (2,3) @14 | **8 COMPLETE** (=A) reconfirm |
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
| forbid (2,2) @14 global | **16 COMPLETE** (all max sets remain) |
| forbid (0,3) @14 global | **8 COMPLETE** (=A) stable |
| forbid (2,3) @14 global | **8 COMPLETE** (=A) stable |
| forbid (0,2) @14 global | **0 COMPLETE** stable |
| forbid (1,2) @14 global | **0 COMPLETE** stable |
| forbid (0,0) @14 global | **0 COMPLETE** stable |
| forbid (0,1) @14 global | **0 COMPLETE** stable |
| forbid (1,1) @14 global | **0 COMPLETE** stable |
| forbid (1,3) @14 global | **0 COMPLETE** stable |
| forbid (2,2)∪(0,3)∪(2,3) @14 | **8 COMPLETE** (=A) stable |
| forbid (2,2)∪center @14 | **8 COMPLETE** (=B) stable |
| corners=2 ∧ forbid center ∧ require nothing else | **0 COMPLETE** (same as A forbid center) |
| corners=3 ∧ require center | **0 COMPLETE** stable |
| corners=2 ∧ require (2,2) | **0 COMPLETE** stable |
| corners=3 ∧ require (2,2) | **0 COMPLETE** stable |
| corners=2 ∧ require (0,3) @14 | **0 COMPLETE** stable (prior 8–10M) |
| corners=3 ∧ require both B-orbits @14 | **8 COMPLETE** (=B) stable |
| corners=3 ∧ forbid (0,3) @14 | **0 COMPLETE** stable |
| corners=3 ∧ forbid (2,3) @14 | **0 COMPLETE** stable |
| corners=2 ∧ forbid (0,3)∧(2,3) @14 | **8 COMPLETE** (=A) stable2 |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) stable2 |
| corners=2 ∧ forbid center @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ forbid (0,2) @14 | **0 COMPLETE** stable2 |
| corners=3 ∧ forbid (0,2) @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ forbid (1,2) @14 | **0 COMPLETE** stable2 |
| corners=3 ∧ forbid (1,2) @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ forbid (0,1) @14 | **0 COMPLETE** stable2 |
| corners=3 ∧ forbid (0,1) @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ forbid corners @14 | **0 COMPLETE** stable2 |
| corners=3 ∧ forbid corners @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ forbid (1,1) @14 | **0 COMPLETE** stable2 |
| corners=3 ∧ forbid (1,1) @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ forbid (1,3) @14 | **0 COMPLETE** stable2 |
| corners=3 ∧ forbid (1,3) @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ require center @14 | **8 COMPLETE** (=A) stable2 |
| corners=3 ∧ require center @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ forbid center @14 | **0 COMPLETE** stable2 |
| corners=3 ∧ forbid center @14 | **8 COMPLETE** (=B) stable2 |
| corners=2 ∧ forbid (0,3) alone @14 | **8 COMPLETE** (=A) stable2 |
| corners=2 ∧ forbid (2,3) alone @14 | **8 COMPLETE** (=A) stable2 |
| corners=3 ∧ require (0,3) @14 | **8 COMPLETE** (=B) stable2 |
| corners=3 ∧ require (2,3) @14 | **8 COMPLETE** (=B) stable2 |
| corners=2 ∧ require (2,2) @14 | **0 COMPLETE** stable2 |
| corners=3 ∧ require (2,2) @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ require (0,3) @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ require (2,3) @14 | **0 COMPLETE** stable2 |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) stable3 |
| corners=3 ∧ forbid (2,2) @14 | **8 COMPLETE** (=B) stable3 |
| forbid (2,2) @14 global | **16 COMPLETE** stable3 |
| forbid (0,3) @14 global | **8 COMPLETE** (=A) stable3 |
| forbid (2,3) @14 global | **8 COMPLETE** (=A) stable3 |
| forbid center @14 global | **8 COMPLETE** (=B; census) stable3 |
| forbid (0,2) @14 global | **0 COMPLETE** stable3 |
| forbid (1,2) @14 global | **0 COMPLETE** stable3 |
| forbid (0,0) @14 global | **0 COMPLETE** stable3 |
| forbid (0,1) @14 global | **0 COMPLETE** stable3 |
| forbid (1,1) @14 global | **0 COMPLETE** stable3 |
| forbid (1,3) @14 global | **0 COMPLETE** stable3 |
| forbid (0,0) @14 global | **0 COMPLETE** stable3 |
| forbid (0,1) @14 global | **0 COMPLETE** stable3 |
| forbid (1,1) @14 global | **0 COMPLETE** stable3 |
| forbid (1,3) @14 global | **0 COMPLETE** stable3 |
| forbid (2,2)∪B-orbits @14 | **8 COMPLETE** (=A) stable3 |
| forbid (2,2)∪center @14 | **8 COMPLETE** (=B) stable3 |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) stable3 |
| corners=3 ∧ forbid (2,2) @14 | **8 COMPLETE** (=B) stable3 |
| corners=3 ∧ require both B-orbits @14 | **8 COMPLETE** (=B) stable3 |
| corners=2 ∧ require corners @14 | ≥7 incomplete (census A has 2 corners) |
| corners=2 ∧ require (0,1) @14 | ≥7 incomplete (census A has (0,1)=3) |
| corners=2 ∧ require (0,2) @14 | ≥7 incomplete (census A has (0,2)=2) |
| corners=2 ∧ require (1,2) @14 | ≥7 incomplete (census A has (1,2)=3) |
| corners=2 ∧ require (1,3) @14 | ≥7 incomplete (census A has (1,3)=2) |
| corners=2 ∧ require center @14 | **8 COMPLETE** (=A) stable3 |
| corners=3 ∧ require (0,1) @14 | **8 COMPLETE** (=B) stable3 |
| corners=3 ∧ require (0,2) @14 | **8 COMPLETE** (=B) stable3 |
| corners=3 ∧ require (1,1) @14 | **8 COMPLETE** (=B) stable3 |
| corners=3 ∧ require (1,2) @14 | **8 COMPLETE** (=B) stable3 |
| corners=3 ∧ require (1,3) @14 | **8 COMPLETE** (=B) stable3 |
| corners=3 ∧ require corners @14 | **8 COMPLETE** (=B) stable3 |
| corners=2 ∧ require (1,3) @14 | **8 COMPLETE** (=A) stable3 (9M prior) |
| corners=2 ∧ require (1,1) @14 | **8 COMPLETE** (=A) stable3 (9.7M prior) |
| corners=2 ∧ require corners @14 | 8 seen incomplete @10M (census 8) |
| corners=2 ∧ require (0,1) @14 | 8 seen incomplete @10M (census 8) |
| corners=2 ∧ require (0,2) @14 | 8 seen incomplete @10M (census 8) |
| corners=2 ∧ forbid (0,3) alone @14 | **8 COMPLETE** (=A) stable3 |
| corners=2 ∧ forbid (2,3) alone @14 | **8 COMPLETE** (=A) stable3 |
| corners=3 ∧ require both B-orbits @14 | **8 COMPLETE** (=B) stable3 |
| corners=2 ∧ forbid (0,3)∧(2,3) @14 | **8 COMPLETE** (=A) stable3 |
| corners=2 ∧ forbid center @14 | **0 COMPLETE** stable3 |
| corners=3 ∧ forbid center @14 | **8 COMPLETE** (=B) stable3 |
| corners=2 ∧ forbid (0,2) @14 | **0 COMPLETE** stable3 |
| corners=3 ∧ forbid (0,2) @14 | **0 COMPLETE** stable3 |
| corners=2 ∧ forbid (1,2) @14 | **0 COMPLETE** stable3 |
| corners=3 ∧ forbid (1,2) @14 | **0 COMPLETE** stable3 |
| corners=2 ∧ forbid corners @14 | **0 COMPLETE** stable3 |
| corners=3 ∧ forbid corners @14 | **0 COMPLETE** stable3 |
| corners=2 ∧ forbid (0,1) @14 | **0 COMPLETE** stable3 |
| corners=3 ∧ forbid (0,1) @14 | **0 COMPLETE** stable3 |
| corners=2 ∧ forbid (1,1) @14 | **0 COMPLETE** stable3 |
| corners=3 ∧ forbid (1,1) @14 | **0 COMPLETE** stable3 |
| corners=2 ∧ forbid (1,3) @14 | **0 COMPLETE** stable3 |
| corners=3 ∧ forbid (1,3) @14 | **0 COMPLETE** stable3 |
| corners=2 ∧ require center @14 | **8 COMPLETE** (=A) final |
| corners=3 ∧ require center @14 | **0 COMPLETE** final |
| corners=2 ∧ forbid center @14 | **0 COMPLETE** final |
| corners=3 ∧ forbid center @14 | **8 COMPLETE** (=B) final |
| corners=2 ∧ forbid (0,3) alone @14 | **8 COMPLETE** (=A) final |
| corners=2 ∧ forbid (2,3) alone @14 | **8 COMPLETE** (=A) final |
| corners=3 ∧ require (0,3) @14 | **8 COMPLETE** (=B) final |
| corners=3 ∧ require (2,3) @14 | **8 COMPLETE** (=B) final |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) final |
| corners=3 ∧ forbid (2,2) @14 | **8 COMPLETE** (=B) final |
| corners=3 ∧ require (2,2) @14 | **0 COMPLETE** final |
| corners=2 ∧ require (2,2) @14 | **0 COMPLETE** final (7M prior) |
| corners=2 ∧ forbid (0,3)∧(2,3) @14 | **8 COMPLETE** (=A) final |
| forbid (2,2) @14 global | **16 COMPLETE** final |
| forbid (0,3) @14 global | **8 COMPLETE** (=A) final |
| forbid (2,3) @14 global | **8 COMPLETE** (=A) final |
| require center @14 global | **8 COMPLETE** (=A) final |
| corners=3 ∧ require both B-orbits @14 | **8 COMPLETE** (=B) final |
| corners=3 ∧ forbid (0,3) @14 | **0 COMPLETE** final |
| corners=3 ∧ forbid (2,3) @14 | **0 COMPLETE** final |
| corners=3 ∧ forbid center @14 | **8 COMPLETE** (=B) final |
| corners=3 ∧ forbid (2,2) @14 | **8 COMPLETE** (=B) final |
| forbid (2,2) @14 global | **16 COMPLETE** final |
| forbid (0,3) @14 global | **8 COMPLETE** (=A) final |
| forbid (2,3) @14 global | **8 COMPLETE** (=A) final |
| forbid (0,2) @14 global | **0 COMPLETE** final |
| forbid (1,2) @14 global | **0 COMPLETE** final |
| forbid (0,0) @14 global | **0 COMPLETE** final |
| forbid (0,1) @14 global | **0 COMPLETE** final |
| forbid (1,1) @14 global | **0 COMPLETE** final |
| forbid (1,3) @14 global | **0 COMPLETE** final |
| forbid center @14 global | **8 COMPLETE** (=B; census) final |
| forbid (2,2)∪(0,3)∪(2,3) @14 | **8 COMPLETE** (=A) final |
| corners=2 ∧ require center @14 | **8 COMPLETE** (=A) ultra |
| corners=3 ∧ require center @14 | **0 COMPLETE** ultra |
| corners=2 ∧ forbid center @14 | **0 COMPLETE** ultra |
| corners=3 ∧ forbid center @14 | **8 COMPLETE** (=B) ultra |
| corners=3 ∧ require (0,3) @14 | **8 COMPLETE** (=B) ultra |
| corners=3 ∧ require (2,3) @14 | **8 COMPLETE** (=B) ultra |
| corners=3 ∧ forbid (0,3) @14 | **0 COMPLETE** ultra |
| corners=2 ∧ forbid (0,3) alone @14 | **8 COMPLETE** (=A) ultra |
| corners=2 ∧ forbid (2,3) alone @14 | **8 COMPLETE** (=A) ultra |
| corners=2 ∧ forbid (2,2) @14 | **8 COMPLETE** (=A) ultra |
| forbid (2,2) @14 global | **16 COMPLETE** ultra |
| forbid (0,3) @14 global | **8 COMPLETE** (=A) ultra |
| forbid (2,3) @14 global | **8 COMPLETE** (=A) ultra |
| forbid (0,2) @14 global | **0 COMPLETE** ultra |
| forbid (1,2) @14 global | **0 COMPLETE** ultra |
| require center @14 global | **8 COMPLETE** (=A) ultra |
| forbid (0,0) @14 global | **0 COMPLETE** ultra |
| forbid (0,1) @14 global | **0 COMPLETE** ultra |
| forbid (1,1) @14 global | **0 COMPLETE** ultra |
| forbid (1,3) @14 global | **0 COMPLETE** ultra |
| forbid (1,1) @14 global | **0 COMPLETE** final |
| forbid (1,3) @14 global | **0 COMPLETE** final |
| require center @14 global | **8 COMPLETE** (=A) final |
| corners=2 ∧ require corners @14 | 8/8 incomplete @8–10M (census 8) |
| corners=2 ∧ require (0,1) @14 | 8/8 incomplete @8–10M (census 8) |
| corners=2 ∧ require (0,2) @14 | 8/8 incomplete @8–10M (census 8) |
| corners=2 ∧ require (1,2) @14 | 8/8 incomplete @8–10M (census 8) |
| corners=2 ∧ require center @14 | **8 COMPLETE** (=A) final |
| corners=3 ∧ require (0,1) @14 | **8 COMPLETE** (=B) final |
| corners=3 ∧ require (0,2) @14 | **8 COMPLETE** (=B) final |
| corners=3 ∧ require corners @14 | **8 COMPLETE** (=B) final |
| corners=3 ∧ require (1,1) @14 | **8 COMPLETE** (=B) final |
| corners=3 ∧ require (1,2) @14 | **8 COMPLETE** (=B) final |
| corners=3 ∧ require (1,3) @14 | **8 COMPLETE** (=B) final |
| corners=3 ∧ require (0,3) @14 | **8 COMPLETE** (=B) final |
| forbid (2,2) @14 global | **16 COMPLETE** stable3 |
| corners=2 ∧ require (2,3) @14 | **0 COMPLETE** stable (prior 7M) |
| forbid (2,3) @14 global | **8 COMPLETE** (= phase A) |
| forbid center @14 global | **8 COMPLETE** (= phase B; corners=3∧forbid center) |
| forbid (0,2) @14 global | **0 COMPLETE** |
| forbid (1,2) @14 global | **0 COMPLETE** |
| forbid corners @14 global | **0 COMPLETE** |
| forbid (1,1) @14 global | **0 COMPLETE** |
| forbid (1,3) @14 global | **0 COMPLETE** |
| require (0,2) @14 global | ≥13 incomplete (census 16/16) |
| require (1,2) @14 global | ≥15 incomplete (census 16/16) |
| require corners @14 global | ≥15 incomplete (census 16/16) |
| require (0,1) @14 global | ≥14 incomplete (census 16/16) |
| corners=3 ∧ forbid center @14 | **8 COMPLETE** (=B) reconfirm3 |
| corners=2 ∧ forbid center @14 | **0 COMPLETE** reconfirm |
| corners=2 ∧ forbid (0,2) @14 | **0 COMPLETE** reconfirm |
| corners=3 ∧ forbid (0,2) @14 | **0 COMPLETE** reconfirm |
| corners=2 ∧ forbid (1,2) @14 | **0 COMPLETE** reconfirm |
| corners=3 ∧ forbid (1,2) @14 | **0 COMPLETE** reconfirm |
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

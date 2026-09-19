# Cycle 35 — phase lift decision + n=5/6/7 shell contrast

## Shell ceilings vs known K

| n | K_n | #orbits | #≥4 | Σceil(≥4) | K/Σceil |
|---:|---:|---:|---:|---:|---:|
| 5 | 9 | 6 | 5 | 15 | 0.6 |
| 6 | 11 | 6 | 6 | 18 | 0.611 |
| 7 | 14 | 10 | 9 | 27 | 0.519 |

## n=7 phase-lift occupancy decision (exact caps, COMPLETE if not aborted)

| configuration | Σocc | realizable? | nodes | aborted |
|---|---:|---|---:|---|
| A_phase_full | 14 | True | 14 | False |
| B_phase_full | 14 | True | 2944 | False |
| A_plus_partialB | 15 | False | 551 | False |
| B_plus_center | 15 | False | 2022 | False |
| A_plus_fullB | 17 | False | 374 | False |

Expected: A_phase_full and B_phase_full **realizable** (census witnesses).
Cross configurations (other phase’s stones on top) **unrealizable** —
occupancy-lattice form of Cycle 27 named-quad exclusivity.

## n=5 sum=10 sample ({'nvec_tested': 81, 'found': 0, 'aborted': 0})

Artifact: `results/cycle35_phase_lift_contrast.json`

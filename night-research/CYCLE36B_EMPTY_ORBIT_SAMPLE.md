# Cycle 36b — empty (2,2): structured SAMPLE + solver COMPLETE

- solver max 7 14 --force 16: max_size=**13**, n_at_best=160, complete=true
- solver first 7 13 --force 16: count=160 complete, witness `449020192407`

| structured occ | sum | realizable? | nodes | aborted |
|---|---:|---|---:|---|
| A_wo_c_with_F (non-witness shape) | 13 | no SAMPLE | 5461 | no |
| A_center_drop01_addF | 14 | no | 270 | no |
| A_center_drop02_addF | 14 | no | 350 | no |
| A_center_drop12_addF | 14 | no | 94 | no |
| B_drop23_addF | 14 | no | 45133 | no |
| B_full_plus_F | 15 | no | 15805 | no |
| ceil_mix_sum14_withF | 14 | no | 25373 | no |
| **witness** occ (2,2,3,0,1,3,1,1,0,0) | 13 | **yes** | 1113 | no |

Empty (2,2) at K=14 is COMPLETE by solver (force cell 16). Lattice SAMPLE
agrees on structured sum-14 vectors; true sum-13 control with F=1 is realizable.

Artifact: `results/cycle36b_empty_orbit_sample.json`

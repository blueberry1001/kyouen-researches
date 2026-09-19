# Cycle 36b — empty (2,2): structured SAMPLE + solver COMPLETE

- solver max 7 14 --force 16: `{'mode': 'max', 'n': 7, 'K': 14, 'max_size': 13, 'nodes': 3294434, 'complete': True, 'n_at_best': 160, 'first': '449020192407', 'seed': 0, 'known_upper': 14, 'quads': 6364, 'force': '10000', 'forbid': '0', 'corners': -1, 'require_orbits': 0}`
- solver first 7 13 --force 16: `{'mode': 'first', 'n': 7, 'K': 13, 'target': 13, 'count': 160, 'nodes': 3292499, 'complete': True, 'first': '449020192407', 'quads': 6364, 'force': '10000', 'forbid': '0', 'corners': -1, 'require_orbits': 0}`

| structured occ | sum | realizable? | nodes | aborted |
|---|---:|---|---:|---|
| A_wo_c_with_F_sum13 | 13 | False | 5461 | False |
| A_center_drop01_addF_sum14 | 14 | False | 270 | False |
| A_center_drop02_addF_sum14 | 14 | False | 350 | False |
| A_center_drop12_addF_sum14 | 14 | False | 94 | False |
| B_drop23_addF_sum14 | 14 | False | 45133 | False |
| B_full_plus_F_sum15 | 15 | False | 15805 | False |
| ceil_mix_sum14_withF | 14 | False | 25373 | False |

Artifact: `cycle36b_empty_orbit_sample.json`

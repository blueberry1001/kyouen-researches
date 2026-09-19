# Cycle 30c — multi-orbit capacity on M (COMPLETE solver)

Local ceiling: each mandatory orbit is concyclic ⇒ occ ≤ 3 (Cycle 30b).
Sum ceilings on M = 18. COMPLETE α(M)=13 ⇒ deficit 5 from cross quads.

## 4-orbit subsets
| keep | max | n_at | complete | sum ceil | deficit |
|---|---:|---:|---|---:|---:|
| 0,0+0,1+0,2+1,1 | 10 | 64 | True | 12 | 2 |
| 0,0+0,1+0,2+1,2 | 12 | 8 | True | 12 | 0 |
| 0,0+0,1+0,2+1,3 | 10 | 360 | True | 12 | 2 |
| 0,0+0,1+1,1+1,2 | 10 | 416 | True | 12 | 2 |
| 0,0+0,1+1,1+1,3 | 9 | 736 | True | 12 | 3 |
| 0,0+0,1+1,2+1,3 | 11 | 56 | True | 12 | 1 |
| 0,0+0,2+1,1+1,2 | 10 | 368 | True | 12 | 2 |
| 0,0+0,2+1,1+1,3 | 9 | 16 | True | 12 | 3 |
| 0,0+0,2+1,2+1,3 | 11 | 32 | True | 12 | 1 |
| 0,0+1,1+1,2+1,3 | 9 | 624 | True | 12 | 3 |
| 0,1+0,2+1,1+1,2 | 10 | 1064 | True | 12 | 2 |
| 0,1+0,2+1,1+1,3 | 9 | 1480 | True | 12 | 3 |
| 0,1+0,2+1,2+1,3 | 11 | 40 | True | 12 | 1 |
| 0,1+1,1+1,2+1,3 | 10 | 24 | True | 12 | 2 |
| 0,2+1,1+1,2+1,3 | 10 | 16 | True | 12 | 2 |

## 5-orbit subsets
| keep | max | n_at | complete | sum ceil | deficit |
|---|---:|---:|---|---:|---:|
| 0,0+0,1+0,2+1,1+1,2 | 12 | 112 | True | 15 | 3 |
| 0,0+0,1+0,2+1,1+1,3 | 11 | 56 | True | 15 | 4 |
| 0,0+0,1+0,2+1,2+1,3 | 13 | 8 | True | 15 | 2 |
| 0,0+0,1+1,1+1,2+1,3 | 12 | 8 | True | 15 | 3 |
| 0,0+0,2+1,1+1,2+1,3 | 12 | 8 | True | 15 | 3 |
| 0,1+0,2+1,1+1,2+1,3 | 12 | 8 | True | 15 | 3 |

## Full M
- {'0,0+0,1+0,2+1,1+1,2+1,3': {'max': 13, 'n_at': 88, 'complete': True, 'nodes': 852415, 'sum_ceiling': 18, 'sum_size': 36, 'deficit_vs_ceiling': 5}}

## Integer occupancy bound (local ceilings + COMPLETE 4-orbit maxima)
- bound = **14**, attaining occ = {'0,0': 2, '0,1': 2, '0,2': 3, '1,1': 1, '1,2': 3, '1,3': 3}
- If this bound is 13, the multi-orbit capacity table is a COMPLETE
  geometric explanation of the skeleton peak (no full-board census needed).


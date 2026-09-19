# Cycle 31 — D4 orbit circle lemma + occupancy-cap search

## Lemma (first principles, all odd n)

> The dihedral group D4 acting on an odd n×n board preserves
> Euclidean distance from the board center. Therefore **every D4-orbit
> lies on a single circle centered at the board center**.
> Any 4 points on a circle are concyclic, hence form a forbidden
> kyouen 4-set. Consequently **every orbit with ≥4 cells has
> occupancy ≤ 3 in any safe set**.

This is a geometric proof of the local ceiling used in Cycle 30 —
it does not require census data.

## Orbit radii (COMPLETE)

### n=5 ({'n_orbits': 6, 'on_single_circle': 6, 'multi_radius_or_size_lt2': 0, 'size>=4_on_circle': 5})
| orbit | size | r² from center | on one circle |
|---|---:|---|---|
| (0,0) | 4 | [8] | True |
| (0,1) | 8 | [5] | True |
| (0,2) | 4 | [4] | True |
| (1,1) | 4 | [2] | True |
| (1,2) | 4 | [1] | True |
| (2,2) | 1 | [0] | True |

### n=6 ({'n_orbits': 6, 'on_single_circle': 0, 'multi_radius_or_size_lt2': 6, 'size>=4_on_circle': 0})
| orbit | size | r² from center | on one circle |
|---|---:|---|---|
| (0,0) | 4 | [8, 13, 18] | False |
| (0,1) | 8 | [5, 8, 10, 13] | False |
| (0,2) | 8 | [4, 5, 9, 10] | False |
| (1,1) | 4 | [2, 5, 8] | False |
| (1,2) | 8 | [1, 2, 4, 5] | False |
| (2,2) | 4 | [0, 1, 2] | False |

### n=7 ({'n_orbits': 10, 'on_single_circle': 10, 'multi_radius_or_size_lt2': 0, 'size>=4_on_circle': 9})
| orbit | size | r² from center | on one circle |
|---|---:|---|---|
| (0,0) | 4 | [18] | True |
| (0,1) | 8 | [13] | True |
| (0,2) | 8 | [10] | True |
| (0,3) | 4 | [9] | True |
| (1,1) | 4 | [8] | True |
| (1,2) | 8 | [5] | True |
| (1,3) | 4 | [4] | True |
| (2,2) | 4 | [2] | True |
| (2,3) | 4 | [1] | True |
| (3,3) | 1 | [0] | True |

### n=8 ({'n_orbits': 10, 'on_single_circle': 0, 'multi_radius_or_size_lt2': 10, 'size>=4_on_circle': 0})
| orbit | size | r² from center | on one circle |
|---|---:|---|---|
| (0,0) | 4 | [18, 25, 32] | False |
| (0,1) | 8 | [13, 18, 20, 25] | False |
| (0,2) | 8 | [10, 13, 17, 20] | False |
| (0,3) | 8 | [9, 10, 16, 17] | False |
| (1,1) | 4 | [8, 13, 18] | False |
| (1,2) | 8 | [5, 8, 10, 13] | False |
| (1,3) | 8 | [4, 5, 9, 10] | False |
| (2,2) | 4 | [2, 5, 8] | False |
| (2,3) | 8 | [1, 2, 4, 5] | False |
| (3,3) | 4 | [0, 1, 2] | False |

## n=7 skeleton M occupancy-cap search

Caps are per-orbit maxima. COMPLETE when nodes finished.

| trial | caps | max seen | nodes | reached 14? |
|---|---|---:|---:|---|
| lp14_attainer | {'0,0': 2, '0,1': 2, '0,2': 3, '1,1': 1, '1,2': 3, '1,3': 3} | 12 | 1500012 | False |
| A_on_M | {'0,0': 2, '0,1': 3, '0,2': 2, '1,1': 1, '1,2': 3, '1,3': 2} | 13 | 780578 | False |
| B_on_M | {'0,0': 3, '0,1': 1, '0,2': 2, '1,1': 1, '1,2': 3, '1,3': 1} | 11 | 943634 | False |
| all3_except_11_1 | {'0,0': 3, '0,1': 3, '0,2': 3, '1,1': 1, '1,2': 3, '1,3': 3} | 12 | 1500018 | False |
| all3_except_11_0 | {'0,0': 3, '0,1': 3, '0,2': 3, '1,1': 0, '1,2': 3, '1,3': 3} | 12 | 1500011 | False |
| cycle15_dom | {'0,0': 2, '0,1': 3, '0,2': 3, '1,1': 1, '1,2': 3, '1,3': 1} | 13 | 379432 | False |
| local_ceiling_3_only | {'0,0': 3, '0,1': 3, '0,2': 3, '1,1': 3, '1,2': 3, '1,3': 3} | 12 | 2000020 | False |

## Interpretation

- Circle lemma ⇒ local occ≤3 on every multi-cell orbit (why n-boards
  cannot pack more than ~3 per radial shell).
- COMPLETE solver: α(M)=13 despite local ceilings summing to 18.
- 4-orbit COMPLETE maxima still allow an integer occupancy vector
  summing to 14 (Cycle 30c LP). Occupancy-cap search tests whether
  that vector is geometrically realizable on M.

## Artifacts
- `results/cycle31_circle_lemma_occ.json`
- `night-research/CYCLE30B_ORBIT_CONCYCLICITY.md`
- `night-research/CYCLE30C_MULTI_ORBIT_CAPACITY.md`

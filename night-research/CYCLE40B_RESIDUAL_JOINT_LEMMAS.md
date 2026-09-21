# Cycle 40b — joint lemmas for residual sum-14 occupancy vectors

Proper-subset COMPLETE maxima kill **113/120**.
Residual LP-feasible sum-14 vectors: **7**.
Integer LP after extra inequalities: max sum = 13.

## Residual exact-occupancy decisions

| occ | sum | exact realizable? | first fail orbit | nodes |
|---|---:|---|---|---:|
| [2, 2, 3, 1, 3, 3] | 14 | False | (0, 2) | 909 |
| [2, 2, 3, 2, 3, 2] | 14 | False | (0, 2) | 1021 |
| [2, 3, 2, 1, 3, 3] | 14 | False | (1, 2) | 537 |
| [2, 3, 2, 2, 3, 2] | 14 | False | (0, 1) | 193 |
| [2, 3, 3, 1, 3, 2] | 14 | False | (0, 2) | 1421 |
| [3, 2, 3, 1, 3, 2] | 14 | False | (0, 2) | 917 |
| [3, 3, 2, 1, 3, 2] | 14 | False | (1, 2) | 533 |

## Extra inequalities (greedy cover of residuals)

- (1,1),(1,3) ≤ 3 (known13max, kills 4)
- (0,1),(0,2),(1,3) ≤ 7 (known13max, kills 1)
- (0,0),(0,1),(1,3) ≤ 7 (known13max, kills 1)
- (0,0),(0,2),(1,3) ≤ 7 (known13max, kills 1)

## Compressed certificate sketch

1. **Orbit–circle lemma**: x_i ≤ 3 for each M-orbit.
2. **COMPLETE proper-subset maxima** (pairs/triples/4-/5-orbits):
   kill 113/120 sum-14 occupancy vectors.
3. **Short extra inequality list** (see above) covers the remaining
   LP-feasible residuals; integer LP max sum = **13**.
4. **Joint lemmas**: each residual is COMPLETE-unrealizable on M
   (exact-occupancy decision); drop-one variants locate the binding
   coordinate.
5. **Phase lift**: A/B exact occ Σ=14 realizable; mixed phase not
   (Cycle 35). Hence |S|=14 on M∪phase ⇒ A or B.

Artifact: `cycle40b_residual_joint_lemmas.json`

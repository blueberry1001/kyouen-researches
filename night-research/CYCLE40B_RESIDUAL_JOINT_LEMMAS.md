# Cycle 40b — joint lemmas for residual sum-14 occupancy vectors

Proper-subset COMPLETE maxima kill **113/120**.
Residual proper-subset-feasible sum-14 vectors: **7**.
All seven are rejected by direct exact-occupancy decisions.

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

## Why no `known13max` inequalities appear here

An earlier draft greedily covered these residuals with inequalities inferred from already-known size-13 maximizers. Those are not certified universal proper-subset bounds. For example, the proposed `(1,1)+(1,3)≤3` conflicts with the COMPLETE proper-subset maximum **5**. They are therefore excluded from the proof rather than being used as a shortcut.

## Compressed certificate

1. **Orbit–circle lemma**: x_i ≤ 3 for each M-orbit.
2. **COMPLETE proper-subset maxima** (pairs/triples/4-/5-orbits): eliminate **113/120** sum-14 occupancy vectors.
3. **Joint exact-occupancy lemmas**: each of the seven surviving vectors is COMPLETE-unrealizable on M. Therefore all **120/120** sum-14 vectors are impossible, hence **α(M)≤13**.
4. A known realizable size-13 configuration gives **α(M)=13**.
5. **Phase lift**: A/B exact occupancy Σ=14 is realizable; mixed phase is not (Cycle 35). Hence the size-14 selection theorem reduces to the A/B alternatives established in the phase-lift analysis.

The seven joint decisions are the essential final obstruction: they are precisely the cases invisible to every available proper-subset capacity bound.

Artifact: `cycle40b_residual_joint_lemmas.json`

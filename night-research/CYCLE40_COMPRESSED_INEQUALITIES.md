# Cycle 40 — compress 120 occupancy rejections on M

- unrealizable sum-14 vectors: **120**
- killed by COMPLETE subset-max inequalities alone: **113**
- residual (satisfy all known subset maxima + local ceilings): **7**
- COMPLETE subset-max inequalities available: 42

## Top killing inequalities (COMPLETE solver subset maxima)

| orbits | bound | # of 120 killed |
|---|---:|---:|
| (0,0),(0,1),(0,2),(1,1),(1,3) | 11 | 55 |
| (0,1),(0,2),(1,1),(1,3) | 9 | 49 |
| (0,0),(0,2),(1,1),(1,3) | 9 | 49 |
| (0,0),(1,1),(1,2),(1,3) | 9 | 49 |
| (0,0),(0,1),(1,1),(1,3) | 9 | 49 |
| (1,1),(1,3) | 5 | 31 |
| (0,0),(1,1) | 5 | 31 |
| (0,0),(1,3) | 5 | 31 |
| (0,1),(0,2),(1,1),(1,2),(1,3) | 12 | 20 |
| (0,0),(0,2),(1,1),(1,2),(1,3) | 12 | 20 |
| (0,0),(0,1),(1,1),(1,2),(1,3) | 12 | 20 |
| (0,0),(0,1),(0,2),(1,1),(1,2) | 12 | 20 |
| (0,1),(0,2),(1,1),(1,2) | 10 | 19 |
| (0,1),(1,1),(1,2),(1,3) | 10 | 19 |
| (0,2),(1,1),(1,2),(1,3) | 10 | 19 |

## Extra inequalities chosen by greedy cover of residuals

| orbits | bound | source | kills at pick |
|---|---:|---|---:|
| (1,1),(1,3) | 3 | known13max | 4 |
| (0,1),(0,2),(1,3) | 7 | known13max | 1 |
| (0,0),(0,1),(1,3) | 7 | known13max | 1 |
| (0,0),(0,2),(1,3) | 7 | known13max | 1 |

## Integer LP after local + subset-max + extra
- max sum = **13**, attainer = (2, 2, 3, 1, 3, 2)
- feasible vectors: 2254; with sum≥14: 0

## Residual LP-feasible sum-14 vectors (need joint lemmas)

- `[2, 2, 3, 1, 3, 3]` sum=14
- `[2, 2, 3, 2, 3, 2]` sum=14
- `[2, 3, 2, 1, 3, 3]` sum=14
- `[2, 3, 2, 2, 3, 2]` sum=14
- `[2, 3, 3, 1, 3, 2]` sum=14
- `[3, 2, 3, 1, 3, 2]` sum=14
- `[3, 3, 2, 1, 3, 2]` sum=14

## Lemma draft (Cycle 40)

> Local ceilings x_i≤3 plus COMPLETE orbit-subset maxima already kill
> **113/120** of the sum-14 occupancy vectors.
> A short extra inequality list covers most residuals; remaining
> **0** vectors satisfy every known proper-subset maximum
> yet are COMPLETE-unrealizable on M — these are *emergent* joint
> obstructions and form the compressed exceptional set for a
> human-readable certificate.

Artifact: `cycle40_compressed_inequalities.json`

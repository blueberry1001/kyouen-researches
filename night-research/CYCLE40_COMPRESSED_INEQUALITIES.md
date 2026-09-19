# Cycle 40 — compress 120 occupancy rejections on M

- unrealizable sum-14 vectors: **120**
- killed by COMPLETE proper-subset maxima alone: **113**
- residual (satisfy all COMPLETE proper-subset maxima + local ceilings): **7**
- COMPLETE proper-subset maxima available: 42

## Top killing inequalities (COMPLETE solver proper-subset maxima)

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

## Residual proper-subset-feasible sum-14 vectors

- `[2, 2, 3, 1, 3, 3]` sum=14
- `[2, 2, 3, 2, 3, 2]` sum=14
- `[2, 3, 2, 1, 3, 3]` sum=14
- `[2, 3, 2, 2, 3, 2]` sum=14
- `[2, 3, 3, 1, 3, 2]` sum=14
- `[3, 2, 3, 1, 3, 2]` sum=14
- `[3, 3, 2, 1, 3, 2]` sum=14

These seven vectors are **not** eliminated by any of the 42 COMPLETE proper-subset maxima. They therefore require joint exact-occupancy decisions; see Cycle 40b.

## Certificate (corrected)

> Local ceilings x_i≤3 plus COMPLETE proper-subset maxima eliminate
> **113/120** sum-14 occupancy vectors.  The remaining **7** satisfy
> every proper-subset bound but are each COMPLETE-unrealizable by an
> exact joint-occupancy decision.  Hence no sum-14 occupancy is
> realizable on M, so α(M)≤13.

The earlier `known13max` greedy-cover inequalities are intentionally **not used** in the certificate. In particular `(1,1)+(1,3)≤3` is not a universal proper-subset inequality: the COMPLETE proper-subset maximum for that pair is **5**. Such inequalities derived from already-known size-13 maximizers would risk circularity if promoted to universal constraints.

Artifact: `cycle40_compressed_inequalities.json`

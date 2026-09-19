# Cycle 30b — orbit concyclicity + M pair/triple capacity

## Concyclicity (COMPLETE local det tests)
| orbit | size | concyclic/collinear | note | local ceiling |
|---|---:|---|---|---:|
| (0,0) | 4 | True | quad_dets_zero=1/1 | 3 |
| (0,1) | 8 | True | quad_dets_zero=70/70 | 3 |
| (0,2) | 8 | True | quad_dets_zero=70/70 | 3 |
| (0,3) | 4 | True | quad_dets_zero=1/1 | 3 |
| (1,1) | 4 | True | quad_dets_zero=1/1 | 3 |
| (1,2) | 8 | True | quad_dets_zero=70/70 | 3 |
| (1,3) | 4 | True | quad_dets_zero=1/1 | 3 |
| (2,2) | 4 | True | quad_dets_zero=1/1 | 3 |
| (2,3) | 4 | True | quad_dets_zero=1/1 | 3 |
| (3,3) | 1 | False | too_few | 1 |

Sum of local ceilings on M = 18 (COMPLETE α(M)=13 ⇒ cross-orbit quads cut at least 5 more).

## Pair maxima on M-orbits (solver; COMPLETE if flagged)
| pair | max | n_at | complete | sum local ceilings |
|---|---:|---:|---|---:|
| 0,0+0,1 | 6 | 32 | True | 6 |
| 0,0+0,2 | 6 | 32 | True | 6 |
| 0,0+1,1 | 5 | 8 | True | 6 |
| 0,0+1,2 | 6 | 32 | True | 6 |
| 0,0+1,3 | 5 | 16 | True | 6 |
| 0,1+0,2 | 6 | 1216 | True | 6 |
| 0,1+1,1 | 6 | 32 | True | 6 |
| 0,1+1,2 | 6 | 1216 | True | 6 |
| 0,1+1,3 | 6 | 32 | True | 6 |
| 0,2+1,1 | 6 | 32 | True | 6 |
| 0,2+1,2 | 6 | 928 | True | 6 |
| 0,2+1,3 | 6 | 32 | True | 6 |
| 1,1+1,2 | 6 | 32 | True | 6 |
| 1,1+1,3 | 5 | 16 | True | 6 |
| 1,2+1,3 | 6 | 32 | True | 6 |

## Triple maxima (selected)
| triple | max | n_at | complete | sum ceilings |
|---|---:|---:|---|---:|
| 0,1+0,2+1,2 | 9 | 2280 | True | 9 |
| 0,0+0,1+0,2 | 9 | 16 | True | 9 |
| 0,1+0,2+1,1 | 9 | 16 | True | 9 |
| 0,2+1,2+1,3 | 9 | 16 | True | 9 |
| 0,0+0,1+1,2 | 9 | 256 | True | 9 |
| 0,1+1,1+1,2 | 9 | 8 | True | 9 |

## M-only / omit-inside-M
- M-only: 13 n_at=88 complete=True
- omit 0,1: max=12 complete=True
- omit 0,2: max=12 complete=True
- omit 1,2: max=11 complete=True

## Lemma (draft)
> Several mandatory D4-orbits on 7×7 are themselves concyclic point sets, so each contributes at most 3 stones before any cross-orbit interaction. Local ceilings alone only give 18; COMPLETE max on M is 13, so forbidden quads that mix orbits remove a further 5. Pair/triple capacity table quantifies which mixtures are most expensive.

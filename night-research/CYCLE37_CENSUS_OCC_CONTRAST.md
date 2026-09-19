# Cycle 37 — census occupancy contrast n=6 vs n=7 (COMPLETE bins)

- n=7: 16 max sets, **2** occupancy vectors
- n=6: 464 max sets, **22** occupancy vectors

## n=7 occupancy vectors

| occ (00,01,02,03,11,12,13,22,23,33) | count |
|---|---:|
| (2, 3, 2, 0, 1, 3, 2, 0, 0, 1) | 8 |
| (3, 1, 2, 1, 1, 3, 1, 0, 2, 0) | 8 |

## Orbit use rate (fraction of max sets with occ>0)

| orbit | n=7 rate | n=6 rate |
|---|---:|---:|
| 0,0 | 1.0 | 1.0 |
| 0,1 | 1.0 | 1.0 |
| 0,2 | 1.0 | 1.0 |
| 0,3 | 0.5 | — |
| 1,1 | 1.0 | 0.983 |
| 1,2 | 1.0 | 1.0 |
| 1,3 | 1.0 | — |
| 2,2 | 0.0 | 0.776 |
| 2,3 | 0.5 | — |
| 3,3 | 0.5 | — |

## n=6 orbits use rate

| orbit | rate | used |
|---|---:|---:|
| 0,0 | 1.0 | 464 |
| 0,1 | 1.0 | 464 |
| 0,2 | 1.0 | 464 |
| 1,1 | 0.983 | 456 |
| 1,2 | 1.0 | 464 |
| 2,2 | 0.776 | 360 |

n=7 crystallizes to 2 occupancy vectors with (2,2) empty in all;
n=6 stays diffuse with no orbit empty in all max sets.

Artifact: `cycle37_census_occ_contrast.json`

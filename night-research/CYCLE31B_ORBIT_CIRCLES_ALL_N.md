# Cycle 31b — D4 orbit = center circle (all n), local ceiling 3

Board center for D4 is always ((n-1)/2,(n-1)/2). In doubled coords
r2x4=(2x-(n-1))^2+(2y-(n-1))^2. Each D4-orbit has **constant r2x4**
(symmetries preserve radius), hence lies on one circle centered at
the board center — for **every** n, odd or even.

Any 4 points on a circle are concyclic ⇒ forbidden kyouen ⇒
**occupancy ≤ 3 on every orbit with ≥4 cells** (first principles).

| n | #orbits | #orbits≥4 | #on center-circle | #all-4-subsets det0 | naive Σceil(≥4) | known K_n |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 3 | 2 | 3 | 2 | 6 | None |
| 4 | 3 | 3 | 3 | 3 | 9 | 7 |
| 5 | 6 | 5 | 6 | 5 | 15 | 9 |
| 6 | 6 | 6 | 6 | 6 | 18 | 11 |
| 7 | 10 | 9 | 10 | 9 | 27 | 14 |
| 8 | 10 | 10 | 10 | 10 | 30 | 15 |
| 9 | 15 | 14 | 15 | 14 | 42 | None |

## Per-orbit (n=7)

| orbit | size | r2x4 | concyclic | ceiling |
|---|---:|---|---|---:|
| (0,0) | 4 | [72] | True | 3 |
| (0,1) | 8 | [52] | True | 3 |
| (0,2) | 8 | [40] | True | 3 |
| (0,3) | 4 | [36] | True | 3 |
| (1,1) | 4 | [32] | True | 3 |
| (1,2) | 8 | [20] | True | 3 |
| (1,3) | 4 | [16] | True | 3 |
| (2,2) | 4 | [8] | True | 3 |
| (2,3) | 4 | [4] | True | 3 |
| (3,3) | 1 | [0] | False | 1 |

## Per-orbit (n=6) — contrast

| orbit | size | r2x4 | concyclic | ceiling |
|---|---:|---|---|---:|
| (0,0) | 4 | [50] | True | 3 |
| (0,1) | 8 | [34] | True | 3 |
| (0,2) | 8 | [26] | True | 3 |
| (1,1) | 4 | [18] | True | 3 |
| (1,2) | 8 | [10] | True | 3 |
| (2,2) | 4 | [2] | True | 3 |

## Lemma (corrected)

> **Orbit–circle lemma.** On any n×n grid, every D4-orbit lies on a
> circle centered at the board center. Hence local occupancy ≤3 per
> multi-cell orbit is universal — it does **not** single out n=7.
>
> What singles out n=7 is the **radial shell stratification + cross-shell
> interference**: ten orbits (unique center shell r²=0; empty inner
> shell (2,2) at the K=14 maximum; exclusive outer phases) combined
> with COMPLETE capacity max(M)=13, max(M∪center)=14, max(M∪B)=14.
> Even boards also have center-circles, but n=6 censuses stay diffuse
> (22 occupancy vectors; (2,2) usable) — shell interference differs.

## Artifacts
- `results/cycle31b_orbit_circles_all_n.json`
- `results/cycle31_circle_lemma_occ.json`
- `night-research/CYCLE31_CIRCLE_ORBIT_LEMMA.md`
- `night-research/CYCLE30B_ORBIT_CONCYCLICITY.md`

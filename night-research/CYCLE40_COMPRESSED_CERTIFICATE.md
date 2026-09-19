# Cycle 40 — compressed occupancy certificate for α(M)=13

Branch `cycle8-n7-structure` (pushed). Evidence COMPLETE unless noted.

## Setup

M-orbits order: `(0,0)(0,1)(0,2)(1,1)(1,2)(1,3)` (indices 0..5).  
Local ceiling from **orbit–circle lemma**: \(x_i \le 3\).

There are **120** integer vectors with \(\sum x_i = 14\), \(0\le x_i\le 3\).
Cycle 34: all 120 are COMPLETE-unrealizable on M (exact-occupancy decision).

## Compression (Cycle 40)

Exclude the circular full-M bound \(\sum\le 13\). Use only **proper-subset**
COMPLETE solver maxima (pairs / triples / 4-orbits / 5-orbits):

| layer | #120 killed |
|---|---:|
| proper-subset COMPLETE maxima alone | **113** |
| residual (satisfy every proper-subset max + local ceilings) | **7** |

Dominant proper-subset inequalities (COMPLETE solver; kill counts overlap):

| orbits | bound | example kill count |
|---|---:|---:|
| (0,0)+(0,1)+(0,2)+(1,1)+(1,3) | 11 | 55 |
| several 4-orbits containing (1,1)+(1,3) | 9 | 49 |
| (1,1)+(1,3) | 5 | 31 |
| (0,0)+(1,1) | 5 | 31 |
| (0,0)+(1,3) | 5 | 31 |
| various 5-orbits | 12 | 20 |

## The 7 residual vectors (COMPLETE joint lemmas)

Exact-occupancy decision on each residual: **found=false**, not aborted.

| occ \((x_0..x_5)\) | sum | exact | drop-one → realizable |
|---|---:|---|---|
| (2,2,3,1,3,3) | 14 | no | drop (1,3) |
| (2,2,3,2,3,2) | 14 | no | drop (1,1) |
| (2,3,2,1,3,3) | 14 | no | drop (1,3) |
| (2,3,2,2,3,2) | 14 | no | drop (1,1) |
| (2,3,3,1,3,2) | 14 | no | drop (0,1)/(0,2)/(1,3) |
| (3,2,3,1,3,2) | 14 | no | drop (0,0)/(0,2)/(1,3) |
| (3,3,2,1,3,2) | 14 | no | drop (0,0)/(0,1) |

These sit on the boundary of many proper-subset maxima yet cannot be
realized jointly — **emergent** obstructions, not visible to any single
orbit-subset capacity.

## Invalid shortcuts (rejected)

Greedy “extra inequalities” taken only from the 7 known max-13 patterns
(e.g. \(x_{11}+x_{13}\le 3\)) are **not** valid on all safe sets: COMPLETE
pair max on (1,1)+(1,3) is **5**. Do **not** use known13max bounds as
universal inequalities without a solver COMPLETE max on that subset.

## Compressed certificate (α(M)≤13)

1. Orbit–circle lemma ⇒ \(x_i\le 3\).
2. COMPLETE proper-subset maxima ⇒ any sum-14 occupancy must be one of
   the **7 residual** vectors.
3. Each residual is COMPLETE-unrealizable (Cycle 40b decision).
4. Hence no safe set on M has size 14; with COMPLETE witness max(M)=13,
   **α(M)=13**.

This replaces the undifferentiated “reject all 120” with **~dozens of
subset capacity facts + 7 named joint lemmas**.

## Phase lift (already COMPLETE, Cycle 35)

| configuration | Σ | realizable? |
|---|---:|---|
| A (M-occ + center) | 14 | yes |
| B (M-occ + (0,3)+(2,3) stones) | 14 | yes |
| mixed phase | >14 | no |

So \(|S|=14\) on the full board forces skeleton occupancy among the 7
residuals (impossible) **or** a phase extension of a size-13 skeleton
pattern — and only A/B exact occ work.

## Artifacts

- `results/cycle40_compressed_inequalities.json`
- `results/cycle40b_residual_joint_lemmas.json`
- `night-research/CYCLE40B_RESIDUAL_JOINT_LEMMAS.md`
- `night-research/CYCLE34_OCCUPANCY_LATTICE_CERTIFICATE.md`
- `night-research/CYCLE35_PHASE_LIFT_CONTRAST.md`

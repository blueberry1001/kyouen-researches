# Cycle 34 — COMPLETE occupancy-lattice certificate for α(M)=13

Local orbit–circle ceiling: each M-orbit occupancy o_i ∈ {0,1,2,3}.
There are **120** occupancy vectors with Σ o_i = 14.
Each is decided by exact-orbit combination search on M (COMPLETE if not aborted).

- realizable sum-14 vectors: **0**
- unrealizable: **120**
- aborted: **0**

### Known sum-13 controls

- A occ=[2, 3, 2, 1, 3, 2]: found=True nodes=80
- dom occ=[2, 3, 3, 1, 3, 1]: found=True nodes=361
- Bcore occ=[3, 1, 2, 1, 3, 1]: found=True nodes=25

### Lemma

> **Cycle 34 occupancy-lattice lemma (COMPLETE if aborted=0 and realizable=0).**
> On the six-orbit skeleton M of the 7×7 board, every safe set satisfies
> o_i ≤ 3 by the orbit–circle lemma. No occupancy vector with Σ o_i = 14
> and o_i ≤ 3 is realizable. Hence **α(M) ≤ 13**. Together with the COMPLETE
> witness α(M)=13 (solver max / Cycle 15), α(M)=13 is explained by
> *local circle ceilings + cross-shell incompatibility of high occupancies*,
> not by the full-board K=14 census.

Artifact: `cycle34_occupancy_lattice_certificate.json`

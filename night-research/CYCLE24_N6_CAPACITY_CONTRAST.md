# Cycle 24 — n=6 capacity contrast vs n=7 crystal (COMPLETE unless noted)

Solver: `night-research/cycle8_b_maxsafe.exe`. Boards n=6 (K=11=2n−1) vs n=7 (K=14=2n).

## n=6 COMPLETE constrained counts / maxima

| constraint @K=11 | result | complete? |
|---|---:|---|
| forbid orbit (2,2) | **104** | yes |
| require orbit (2,2) | **360** | yes |
| forbid orbit (1,1) | **8** | yes |
| forbid orbit (0,2) | **0** | yes |
| max with forbid (2,2) | **11** | yes (104 at 11) |
| max with forbid (1,2) | **10** | yes (688 at 10) |

## Contrast table

| property | n=7 K=14 | n=6 K=11 |
|---|---|---|
| use orbit (2,2) at max | **impossible** (force@14=0 COMPLETE) | **common** (360/464 COMPLETE require) |
| omit (2,2) still reach max | yes (all 16) | yes (104 sets) |
| omit (0,2) | max **12** COMPLETE (−2) | max **10** COMPLETE (−1; 136@10) |
| omit (0,1) | @14 forbid=0 COMPLETE | max **10** COMPLETE (−1) |
| omit (0,0) corners | @14 forbid=0 COMPLETE | max **10** COMPLETE (−1) |
| omit (1,2) | @14 forbid=0 COMPLETE | max **10** COMPLETE (−1; 688@10) |
| omit (1,1) | @14 forbid=0 COMPLETE | max 11 still (8 sets omit (1,1)) |
| occupancy vectors at max | **2** COMPLETE | **22** COMPLETE |
| empty orbit at max | **(2,2)** | **none** |

## Lemma (n=6 vs n=7)

> Reaching the board-specific maximum does **not** require avoiding (2,2)
> on n=6 (360 COMPLETE max-sets use it; 104 COMPLETE max-sets omit it).
> On n=7, (2,2) is empty in every max set and force@14 is COMPLETE 0.
> Omitting a hard edge orbit costs capacity on both boards, but the n=7
> crystal’s empty-orbit + two-phase selection is **absent** on n=6.

## Rejected

- “(2,2)-type orbits are always forbidden at maximum size” — false on n=6.
- “Any board’s max family has ≤2 occupancy vectors” — false on n=6 (22).

## Artifacts
- session exe logs (stdout in conversation; rerun commands above)
- `night-research/CYCLE11_ORBIT_NECESSITY.md` (census)
- `night-research/CYCLE15_CAPACITY_DECOMPOSITION.md` (n=7 skeleton)
- `night-research/FINAL_SELECTION_THEOREM.md`

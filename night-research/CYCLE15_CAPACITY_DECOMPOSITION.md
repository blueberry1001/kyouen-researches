# Cycle 15 — capacity decomposition of K7=14 (COMPLETE)

## Setup

Orbit roles on 7×7 (COMPLETE census + COMPLETE constrained maxima):

- **Mandatory skeleton M** = orbits `(0,0),(0,1),(0,2),(1,1),(1,2),(1,3)`
  (each forbid-orbit@14 = 0 COMPLETE; also truly mandatory on n=5/n=6 edges).
- **Forbidden F** = `(2,2)` (force@14 = 0 COMPLETE; max with F = 13 COMPLETE).
- **Phase orbits P** = center `(3,3)` vs B-bundle `{(0,3),(2,3)}`.

## COMPLETE capacity table

| allowed cells | max safe | complete? | interpretation |
|---|---:|---|---|
| M only (forbid P∪F) | **13** | yes (88 sets @13) | skeleton peaks at 2n−1 |
| M ∪ {center} (forbid B-bundle ∪ F) | **14** | yes (8 = all A) | phase A |
| M ∪ B-bundle (forbid center ∪ F) | **14** | yes (8 = all B) | phase B |
| M ∪ {center} ∪ B-bundle | impossible | yes (center∧B = 0 @14) | exclusivity |
| M ∪ F | **13** | yes | (2,2) does not lift capacity |
| full board | **14** | inherited enum 16 | only A ⊔ B |

## Lemma (capacity decomposition)

> **n=7 Cycle 15 lemma (COMPLETE).**
> Let M be the six mandatory D4-orbits. The maximum safe size on M alone is
> **13 = 2n−1**. Adjoining the center orbit raises the maximum to **14**,
> realized by exactly the 8 phase-A sets. Adjoining the B-bundle `(0,3),(2,3)`
> instead (center still forbidden) also raises the maximum to **14**, realized
> by exactly the 8 phase-B sets. Adjoining `(2,2)` never raises the maximum
> above 13. Center and the B-bundle cannot be combined at size 14.
>
> Hence K7=2n is attained only by **two exclusive phase extensions** of the
> same mandatory skeleton that already supports 2n−1.

This is the closest available explanation of “why n=7 can do +1”: the +1 is
not free on the skeleton; it is purchased by committing to one of two
mutually exclusive orbit extensions.

## Skeleton size-13 occupancy (COMPLETE occ)

`occ 7 13` with forbid center,(0,3),(2,3),(2,2): **88 sets, only 6 patterns**.

| occupancy on M-orbits (order 00,01,02,11,12,13) | count |
|---|---:|
| (2,2,3,1,3,2) | 8 |
| (2,3,2,1,3,2) | 8 |
| **(2,3,3,1,3,1)** | **32** |
| (3,2,2,1,3,2) | 8 |
| (3,2,3,1,3,1) | 24 |
| (3,3,3,1,0,1) | 8 |

Compare phase A @14: M-occupancy (2,3,2,1,3,2) + center=1 → the skeleton
pattern (2,3,2,1,3,2) is exactly **A with the center stone removed** (size 13).
Adding the center to that shape is how phase A buys the +1.

Unrestricted K=13 (SAMPLE) had 150 patterns; skeleton-only K=13 has **6**
(COMPLETE) — the skeleton is still selective, and the +1 is a single-orbit
commitment on top of a near-A / near-B 13-shape.

### n=5 skeleton contrast (COMPLETE)

| n=5 constraint | max |
|---|---:|
| forbid all 4 mandatory orbits | **4** COMPLETE |
| forbid (1,1)∧center `(2,2)` | **9** COMPLETE — full K=2n−1 without diagonals/center |

n=5 reaches 2n−1 on a **reduced** orbit set (no phase extension needed).
n=7’s 2n requires the exclusive A/B extension of a skeleton that only does 2n−1.

## Relation to n=6 / n=8

- n=6: K=11=2n−1; no empty orbit; 22 occupancy vectors — no analogous
  two-peak capacity decomposition at 2n.
- n=8 SAMPLE: both (2,2) and center-block are usable — skeleton/P split is
  not rigid.

## Artifacts
- exe: `night-research/cycle8_b_maxsafe.exe max 7 …` (stdout in session; COMPLETE flags above)
- `night-research/CYCLE10_OCCUPANCY_SELECTION.md`
- `night-research/CYCLE14_CAPACITY_NEIGHBORHOOD.md`
- `night-research/CYCLE8_11_MAIN_RESULT.md`

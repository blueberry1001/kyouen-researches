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

## Partial phase extensions (COMPLETE)

| allowed | max | complete? |
|---|---:|---|
| M ∪ {(0,3)} only (forbid center,(2,3),(2,2)) | **13** (288 @13) | yes |
| M ∪ {(2,3)} only (forbid center,(0,3),(2,2)) | **13** (304 @13) | yes |
| M ∪ {(0,3),(2,3)} (forbid center,(2,2)) | **14** (8 @14) | enum/require COMPLETE |
| M ∪ {center} (forbid B∪(2,2)) | **14** (8 @14) | yes |

> The B-phase +1 requires the **full B-bundle** `(0,3)∪(2,3)`. Either orbit
> alone only reaches 2n−1=13. Center alone is sufficient for phase A.

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
That skeleton class has **count=8**; M∪{center} @14 also has **count=8**
COMPLETE — so only that 13-class extends by the center to K=14.
The other 80 skeleton 13-sets (5 remaining patterns) do **not** become 14
by adding center (phase A count is 8 total).

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

## Skeleton internal geometry (COMPLETE local counts)

- |M| = 36 cells (six mandatory orbits).
- Forbidden quads **fully inside M**: **1771 / 6364**.
- On the skeleton 13-set “A minus center” (occupancy (2,3,2,1,3,2)), the empty
  center has **0** blocker triples — center is freely addable, recovering phase A.
- Other skeleton 13-patterns do not yield 14 when center is added (phase A
  count is only 8).

The +1 is therefore not blocked *on* the A-minus-center shape; it is that
**only that shape** (among skeleton max-13 occupancy classes) can accept the
center without creating a forbidden quad.

### Phase-B reconstruction (verified)

Phase-B representative B0 minus its three B-orbit stones `(0,3),(2,3)×2`
is a **safe 11-set** on M with occupancy (3,1,2,1,3,1). Target DFS with that
11-set forced **finds a size-14 completion** (includes B-orbit cells) — the
B-phase +1 is realized by restoring the full B-bundle onto an M-core, not by
center. Matches: partial bundle alone max=13; full bundle max=14.

## Orbit (0,2) is already mandatory at K=13 (COMPLETE)

| constraint | result |
|---|---|
| forbid orbit (0,2) @K=13 | **count=0 complete** |
| forbid (0,2) @K=12 | max=**12** complete |
| forbid (0,2)∧(1,2) | max=**11** complete (3592 @11) |

Omitting `(0,2)` is impossible already at size 13; omitting it **and** `(1,2)`
drops capacity to 11 = 2n−3. Mandatory-orbit structure is not merely a
max-layer census artifact — `(0,2)` is a hard geometric requirement from
size 13 upward.

### Orbit necessity at K=13 (forbid-orbit first@13)

| orbit | @13 verdict |
|---|---|
| `(0,2)` | **mandatory** (count=0 COMPLETE) |
| `(0,1)` | optional (count=24 COMPLETE) |
| `(0,0)` corners | optional (≥15 incomplete) |
| `(1,2)`,`(1,3)`,`(1,1)` | optional/incomplete witnesses exist |

Only `(0,2)` is proven mandatory at 13; the other five “K=14 mandatory”
orbits become required **only at the maximum layer**.

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

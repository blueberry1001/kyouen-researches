# Cycle 11 — orbit necessity census: n=6 vs n=7 (COMPLETE)

Inputs: complete enumerations only
- n=7: 16 max safe sets K=14
- n=6: 464 max safe sets K=11

An orbit is **mandatory on the census** if every max set uses ≥1 cell of it;
**never** if no max set uses it.

## n=7 (COMPLETE)

| orbit | size | used_in | class |
|---|---:|---:|---|
| (0,0) | 4 | 16/16 | **mandatory** |
| (0,1) | 8 | 16/16 | **mandatory** |
| (0,2) | 8 | 16/16 | **mandatory** |
| (0,3) | 4 | 8/16 | phase B |
| (1,1) | 4 | 16/16 | **mandatory** |
| (1,2) | 8 | 16/16 | **mandatory** |
| (1,3) | 4 | 16/16 | **mandatory** |
| (2,2) | 4 | **0/16** | **never** |
| (2,3) | 4 | 8/16 | phase B |
| (3,3) | 1 | 8/16 | phase A |

Distinct occupancy vectors: **2** (A and B).
Independent forbid-orbit @14 COMPLETE zeros for the five of the mandatory
orbits tested `(0,0),(0,1),(0,2),(1,1),(1,2)`; `(1,3)` census-mandatory
(forbid search incomplete but 16/16 usage).

## n=6 (COMPLETE)

| orbit | size | used_in | class |
|---|---:|---:|---|
| (0,0) | 4 | 464/464 | **mandatory** |
| (0,1) | 8 | 464/464 | **mandatory** |
| (0,2) | 8 | 464/464 | **mandatory** |
| (1,1) | 4 | 456/464 | almost (8 sets omit) |
| (1,2) | 8 | 464/464 | **mandatory** |
| (2,2) | 4 | **360/464** | **common, not forbidden** |

Distinct occupancy vectors: **22** (top frequency only 72/464).

## Contrast (universal on n=7, false on n=6)

| property | n=7 | n=6 |
|---|---|---|
| # mandatory orbits | **6** | **4** |
| orbit (2,2) never used | **yes** | **no** (360/464 use it) |
| # occupancy vectors | **2** | **22** |
| two-phase center XOR B-orbits | **yes** (8+8) | no single center cell (even board) |

## n=8 SAMPLE (incomplete forbid-orbit first@15)

Witnesses exist that omit (0,1),(0,3),(1,1),(1,2),(1,3),(2,3) and that
**use (2,2)** (5 hits under forbid-2,2 means sets *without* (2,2); separate
occ data shows many samples *with* (2,2)). n=7 crystal selection does not
transfer.

## Small-n extension (COMPLETE enums)

| n | K | #max sets | mandatory orbits | never-used orbit | occupancy vectors |
|---:|---:|---:|---|---|---:|
| 4 | 7 | 64 | all 3: (0,0)(0,1)(1,1) | **none** | 4 |
| 5 | 9 | 100 | 4: (0,0)(0,1)(0,2)(1,2) | **none** (center used 44/100) | 9 |
| 6 | 11 | 464 | 4: (0,0)(0,1)(0,2)(1,2) | **none** (2,2 used 360/464) | 22 |
| 7 | 14 | 16 | **6** + empty (2,2) | **(2,2)** | **2** |

Among complete max-set censuses n=4..7, **only n=7 has an entire cell orbit
empty**, and only n=7 collapses occupancy to two vectors while forbidding
that orbit.

## Capacity cost of omitting a mandatory orbit (n=7)

`max 7 --forbid-orbit …` (node-capped; COMPLETE noted):

| forbidden orbit | max safe size | status |
|---|---:|---|
| `(0,2)` | **12** | COMPLETE (3464 sets at 12) |
| `(1,2)` | 12 | incomplete (2104 at 12; no 13/14 seen) |
| `(1,1)` | 13 | incomplete (347 at 13) |
| `(0,0)` corners | 13 | incomplete (16 at 13) |

> Omitting the entire orbit `(0,2)` **costs two stones** vs K7=14
> (COMPLETE max=12). Mandatory orbits are capacity-critical, not merely
> census-correlated.

## n=6 forbid-orbit @K=11 (COMPLETE)

Forbidding any of the census-mandatory orbits `(0,0),(0,1),(0,2),(1,2)`
gives **count=0 complete** at K=11. n=6 mandatory orbits are truly
mandatory, not just frequent.

## n=7 size-13 layer (partial COMPLETE)

| constraint @K=13 | result |
|---|---:|
| force one `(2,2)` cell | ≥141 sets (incomplete count) |
| corners=4 | **0** complete |
| center ∧ require `(2,2)` | **24** complete |

> At K=14, center and (2,2) are incompatible (max 13 / force center+22 = 0
> at 14). At K=13 they **coexist** (24 COMPLETE with center+(2,2)).
> The exclusivity is a **maximum-layer** phenomenon, not a global ban on the
> pair. Corners=4 is impossible already at 13.

## Lemma

> The n=7 +1 maximum family is a **highly selected** object: six cell orbits
> are census-mandatory, one whole orbit `(2,2)` is empty, and occupancy
> collapses to two vectors implementing center XOR B-orbits.
> On n=6 the same census is **diffuse**: only four orbits are mandatory,
> `(2,2)` is commonly occupied, and 22 occupancy vectors appear.

## Artifacts

- This note; occupancy recompute inline via `cycle8_lib.load_n6/load_n7`
- Prior: `CYCLE10_OCCUPANCY_SELECTION.md`, `results/cycle10_occupancy_probes.json`

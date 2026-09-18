# Cycle 8–11 — consolidated main result (n=7 K=14 structure)

Branch `cycle8-n7-structure`, base `2d3855a`, current tip see `git log`.
This note is the human-readable compression the overnight cycle aimed for.
Evidence labels are mixed COMPLETE / SAMPLE; see per-cycle notes for detail.

## What is established (COMPLETE unless noted)

### Inherited (not re-proved)
- K7=14, 16 max safe sets, 2 D4 orbits (Cycle 6 enum)
- K6=11 with 464 max sets; K8=15; K4=7; K5=9
- Winner sequence and certificates unchanged

### Cycle 8 — phase geometry
1. Unique D4 class of 5→5 exchange between center phase A and no-center B.
2. All 224 thirteen-subsets of max sets uniquely complete → edit-paths between
   distinct max sets visit size ≤12 (full board); union-restricted width ≤11.
3. **min_det=2** on all 16 n=7 max sets; **min_det≥3** on all max sets for
   n=4,5,6 complete enums — locally pin-able only on n=7.
4. Conditional maxima: (2,2)⇒13; center+(0,3)⇒13; center+(2,3)⇒**12**;
   corners=4⇒≤12; K=14 corners ∈ {2,3}.

### Cycle 9 — obstruction depth
5. Every max set blocks each empty (2,2) cell with **τ∈{3,4}** (not 1-edit).
6. On A0∪B0, size-14 safe sets = {A0,B0} only; |core|=9 forces grow-both=0
   for k≥10; explicit A–B path bottlenecks (path-witness) use (2,2) and drop center.
7. n=8 SAMPLE occ: 53 sets / **45 occupancy patterns**; (2,2) often used.

### Cycle 10 — occupancy selection rule (COMPLETE)
8. Realized K=14 occupancy vectors: **exactly A and B**.
9. **A ≡ center ∧ corners=2** (count=8 COMPLETE).
10. **B ≡ ¬center ∧ corners=3 ∧ require(0,3)∧require(2,3)** (count=8 COMPLETE).
11. center ∧ require(0,3)/(2,3)/(2,2) = **0** COMPLETE.
12. ¬center ∧ forbid(0,3)∧forbid(2,3) = **0** COMPLETE.
13. forbid-orbit @14 = 0 COMPLETE for orbits (0,0)(0,1)(0,2)(1,1)(1,2);
    census also forces (1,3). (2,2) cannot be used.
14. Theoretical sum=14 vectors under orbit-size caps: 304,752; realized: 2.

### Cycle 11 — n=6 / small-n contrast (COMPLETE censuses)
15. Mandatory orbit counts: n=4:3/3, n=5:4, n=6:4, n=7:**6**.
16. Empty orbit at max: **only n=7** has one ((2,2)).
17. Occupancy vector counts: n=4:4, n=5:9, n=6:22, n=7:**2**.
18. n=6 uses (2,2) in 360/464 max sets — n=7 crystal does not generalize.

## Compressed lemma (main result candidate)

> **n=7 Cycle 8–11 selection theorem (computer-assisted, complete censuses).**
> On the 7×7 kyouen board, the maximum safe size is K=14 and the maximizing
> family has exactly 16 sets / 2 D4 phases. A size-14 safe set must meet each
> of the six orbits (0,0),(0,1),(0,2),(1,1),(1,2),(1,3), must avoid the
> entire orbit (2,2), and must fall into exactly one of
>   A: center ∧ exactly two corners, or
>   B: no center ∧ exactly three corners ∧ uses both (0,3) and (2,3).
> The two phases are joined only by a unique D4-class 5→5 exchange; no
> size-13 corridor exists between distinct max sets; every max set is
> determined by two stones (min_det=2) yet is exchange-isolated (d*≥5).
> On n=6 the analogous census is diffuse (4 mandatory orbits, (2,2) used,
> 22 occupancy vectors, min_det≥3, 1-swap edges exist).

This is **not** yet a board-size proof of why K7=2n; it is a complete
structural selection theorem for the maximizing family, with sharp n=6
(and n=4/5, n=8-sample) contrast.

## Open (highest value)
1. Derive the selection theorem from forbidden-quads geometry alone.
2. Explain why n=7 reaches 2n while n=6/8 sit at 2n−1.
3. n=8 complete orbit-necessity census if/when affordable.
4. K9 only after 128-bit regression (design in `CYCLE9H_K9_128BIT_DESIGN.md`).

## Key files
- `night-research/CYCLE8_N7_STRUCTURE.md`
- `night-research/CYCLE10_OCCUPANCY_SELECTION.md`
- `night-research/CYCLE11_ORBIT_NECESSITY.md`
- `night-research/CYCLE9_G1_NOTES.md`, `CYCLE9_G2_NOTES.md`
- `docs/compose/spec/cycle8-n7-structure-explain.md`

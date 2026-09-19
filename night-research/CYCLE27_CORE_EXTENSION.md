# Cycle 27 — skeleton cores vs A/B extensions (n=7)

Evidence: COMPLETE 16-set census + TargetSearch witnesses + `is_safe` on named sets.
Library: `cycle8_lib.py`, `cycle8_exists_k.py`.

## Phase cores (explicit)

**A-core** = A0 minus center (13 stones, safe):
`(0,0),(1,0),(5,0),(1,1),(2,1),(5,2),(6,2),(5,3),(0,4),(3,5),(4,5),(6,5),(0,6)`
Occupancy A without `(3,3)`: (2,3,2,0,1,3,2,0,0,**0**).

**B-core** = B0 minus B-bundle stones `(3,2),(4,3),(6,3)` (11 stones, safe):
`(0,0),(5,0),(6,0),(1,1),(2,1),(5,2),(0,4),(3,5),(4,5),(0,6),(4,6)`
Occupancy B without `(0,3),(2,3)`: (3,1,2,0,1,3,1,0,0,0).

## Extension tests

| test | result |
|---|---|
| A-core → size 14 | **found** = A0 (re-adds center only among the named completion) |
| B-core → size 14 | **found** = B0 (re-adds `(3,2),(4,3),(6,3)`) |
| A-core ∪ B-bundle (3 stones) | pop 16, **unsafe** |
| B-core ∪ {center} | pop 12, **unsafe** |

## Lemma

> The two phase cores lie on the mandatory-orbit skeleton but are **not**
> interchangeable. Each core completes to size 14 only by restoring its own
> phase bundle (center for A; the full B-bundle for B). Cross-adding the
> other phase’s exclusive stones creates a forbidden quad immediately.
>
> Combined with COMPLETE capacity: max(M)=13, max(M∪center)=14=A,
> max(M∪B-bundle)=14=B, partial B-bundle max=13.

This is the concrete geometric content of “mutually exclusive phase
extensions” behind the n=7 +1.

## Independent recompute

`is_safe` on the same masks agrees: A_wo safe pop13; B_wo safe pop11;
A_wo|B_b unsafe; B_wo|center unsafe; both cores are subsets of their phases.

## Related
- `CYCLE15_CAPACITY_DECOMPOSITION.md`
- `CYCLE10_OCCUPANCY_SELECTION.md`
- `FINAL_SELECTION_THEOREM.md`

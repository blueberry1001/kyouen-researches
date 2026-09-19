# Cycle 24 — reconstructing n=7 K=14 constraints from occupancy (notes)

Goal: start from the two COMPLETE occupancy vectors at K=14 and the
forbidden-quad incidence, and recover the selection rules without re-deriving
K_7 itself.

## Inputs (COMPLETE censuses)

Occupancy order `(0,0)(0,1)(0,2)(0,3)(1,1)(1,2)(1,3)(2,2)(2,3)(3,3)`:

- A = (2,3,2,0,1,3,2,0,0,1) ×8
- B = (3,1,2,1,1,3,1,0,2,0) ×8

Inherited geometry: 6364 forbidden quads on 7×7; (2,2) orbit touches 1997 of them.

## What occupancy already forces (COMPLETE probes)

1. **Empty (2,2)** — census 0/16 + force@14=0 COMPLETE.
2. **Corners ∈ {2,3}** — corners=1,4 @14 COMPLETE 0.
3. **Center XOR B-bundle** — center∧require(0,3|2,3|2,2)=0 COMPLETE;
   ¬center∧forbid(0,3)∧forbid(2,3)=0 COMPLETE.
4. **Mandatory six orbits** — both phases COMPLETE-forbid=0 on each orbit
   `(0,0)(0,1)(0,2)(1,1)(1,2)(1,3)`.
5. **B must take the full bundle** — require each of (0,3),(2,3) → 8 COMPLETE;
   partial M∪(0,3) or M∪(2,3) max=13 COMPLETE.

## Skeleton vs extensions (capacity decomposition COMPLETE)

| allowed cells | max |
|---|---:|
| M only | 13 |
| M∪{center} | 14 (=A) |
| M∪{(0,3),(2,3)} | 14 (=B) |
| M∪{(0,3)} only | 13 |
| M∪{(2,3)} only | 13 |
| M∪{(2,2)} | 13 |

So K=14 is **not** a generic packing of the mandatory skeleton; it is exactly
two exclusive 1-orbit-bundle upgrades of a 2n−1 skeleton.

## Geometric hooks (incomplete as a proof)

- Quads through center ∧ (0,3): 180; center ∧ (2,3): 244; center ∧ (2,2): 216.
- (0,2) touches ~48% of all quads — heavy incidence, but n=6 incidence is
  **higher** yet n=6 maxima are diffuse → density alone is not the rule
  (**rejected** in Cycle 16).
- On A0, empty (2,3)/(0,3) cells are heavily blocked; on B0, the center is
  blocked by (0,3)/(2,3) stones — exclusivity has local witnesses, not a
  single shared quad.

## Open proof obligation

Recover rules (1)–(5) from the **incidence structure** of forbidden quads
alone (no census). Candidate ingredients:

- a capacity inequality on orbits with high quads-per-cell and low orbit size;
- an incompatibility graph between center and B-bundle orbits;
- a packing bound that makes any third occupancy type drop to ≤13.

Until that exists, Cycle 10/15 remain a **COMPLETE selection theorem** for
the maximizing family, not a geometric proof of K_7=2n.

## Related
- `CYCLE10_OCCUPANCY_SELECTION.md`
- `CYCLE15_CAPACITY_DECOMPOSITION.md`
- `CYCLE24_N6_CAPACITY_CONTRAST.md`
- `FINAL_SELECTION_THEOREM.md`

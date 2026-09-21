# Cycle 42 — corridor width 11 vs static selection (unification note)

## Shared oracle (COMPLETE)

Both facts are computed from the **same** forbidden 4-set family (D0):

- **Static selection**: occupancy lattice + subset capacities + joint
  lemmas on skeleton M / phase orbits (`CYCLE40`, `CYCLE35`).
- **Dynamic corridor**: widest single-stone path on A∪B (19 cells),
  width **11** COMPLETE (`CYCLE39C`), using `is_safe` = no forbidden quad.

So a unified *local geometry* already underlies both. No second axiom.

## What is not yet unified

Open: a **static** certificate that every A↔B single-stone path has
bottleneck ≤11, expressed as occupancy / capacity inequalities of the
same style as Cycle 40 — without searching the path graph.

Candidate direction: any safe set of size 12–13 that touches both A-only
and B-only cells must violate a proper-subset capacity or sit outside the
union; classify size-≥12 safe sets meeting both phases.

## Status

- Shared forbidden-quad oracle: **yes** (definition-level).
- Static derivation of the 11 barrier from occupancy inequalities: **open**.
- PR judgment can proceed without this item; it is a strengthening, not a
  gap in the selection theorem proof chain (`CYCLE41`).

Artifact: this note · `CYCLE39C_WIDEST_PATH_FAST.md` · `CYCLE41_PROOF_DEPENDENCIES.md`

## Follow-up (2026-09-22)

The restricted-union static barrier is now certified by the two occupancy
difference layers d=2,3, each of capacity at most 12. A single-stone edge
between these layers must therefore visit size at most 11. This uses
point groups A\\B and B\\A, not just D4 cell-orbit occupancies.
The new work also proves that the missing fourth corner is mandatory even
on the full board at floor 12, and that the 16 maximum sets belong to
eight disjoint 903-state components at that floor. See
`DISCOVERY_CORNER_GATE_AND_COMPONENTS.md` and its independent checker.

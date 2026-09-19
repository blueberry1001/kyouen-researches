# n=7 Selection Theorem — ultra-complete constraint matrix

Evidence: COMPLETE C++ `cycle8_b_maxsafe.exe` counts + complete 16-set census.
Solver labels `complete=true` mean exhaustive for that constraint at K=14.

## Phase split (COMPLETE)

| constraint | count |
|---|---:|
| corners=2 ∧ require center | **8** (=A) |
| corners=3 ∧ require center | **0** |
| corners=2 ∧ forbid center | **0** |
| corners=3 ∧ forbid center | **8** (=B) |

## B-orbit exclusivity (COMPLETE)

| constraint | count |
|---|---:|
| corners=2 ∧ forbid (0,3) alone | **8** (=A) |
| corners=2 ∧ forbid (2,3) alone | **8** (=A) |
| corners=2 ∧ forbid (0,3)∧(2,3) | **8** (=A) |
| corners=3 ∧ require (0,3) | **8** (=B) |
| corners=3 ∧ require (2,3) | **8** (=B) |
| corners=3 ∧ require both B-orbits | **8** (=B) |
| corners=3 ∧ forbid (0,3) | **0** |
| corners=3 ∧ forbid (2,3) | **0** |

## (2,2) (COMPLETE)

| constraint | count |
|---|---:|
| force (2,2) @14 | **0** |
| corners=2 ∧ forbid (2,2) | **8** (=A) |
| corners=3 ∧ forbid (2,2) | **8** (=B) |
| forbid (2,2) global | **16** |
| corners=2/3 ∧ require (2,2) | **0 / 0** |

## Mandatory orbits (COMPLETE forbid)

Orbits `(0,0)(0,1)(0,2)(1,1)(1,2)(1,3)`:

- global forbid @14 → **0** (each)
- corners=2 ∧ forbid each → **0**
- corners=3 ∧ forbid each → **0**
- corners=3 ∧ require each → **8** (=B)
- corners=2 ∧ require center → **8** (=A)
- corners=2 ∧ require (1,1)/(1,3) → **8** (COMPLETE, 9–10M nodes)
- corners=2 ∧ require corners/(0,1)/(0,2)/(1,2) → census 8; DFS often 7–8/8 incomplete

## Global complementary (COMPLETE)

| constraint | count |
|---|---:|
| forbid (2,2) | 16 |
| forbid (0,3) | 8 (=A) |
| forbid (2,3) | 8 (=A) |
| forbid (2,2)∪(0,3)∪(2,3) | 8 (=A) |
| forbid (2,2)∪center | 8 (=B) |
| require center | 8 (=A) |
| forbid center | 8 (=B; census) |

## Capacity (COMPLETE, inherited Cycle 15)

M = six mandatory orbits; max(M)=13; max(M∪center)=14; max(M∪B-bundle)=14;
partial B-bundle max=13; (0,2) omit max=12; (0,2)+(1,2) omit max=11;
center+(2,3)=12; corners=4 ≤12.

## Hard orbits (0,2)/(1,2) — COMPLETE deeper facts

| constraint | result |
|---|---|
| forbid (0,2) @13 | **0 COMPLETE** (mandatory below max too) |
| forbid (1,2) @13 | **0 COMPLETE** |
| max with forbid (0,2) | **12 COMPLETE** (cost −2) |
| max with forbid (1,2) | **12** seen / combined (0,2)+(1,2) max **11 COMPLETE** |
| corners=3 ∧ require (0,2) | **8 COMPLETE** (=B) |
| corners=3 ∧ require (1,2) | **8 COMPLETE** (=B) |
| corners=2/3 ∧ forbid (0,2) or (1,2) @14 | **0 COMPLETE** |
| corners=3 ∧ require (0,1) | **8 COMPLETE** (=B) |
| corners=3 ∧ require corners | **8 COMPLETE** (=B) |
| corners=3 ∧ forbid (1,2) | **0 COMPLETE** |
| corners=2 ∧ forbid (0,0)/(0,1)/(1,1)/(1,3) | **0 COMPLETE** each |
| corners=3 ∧ forbid (0,0)/(0,1)/(1,1)/(1,3) | **0 COMPLETE** each |
| corners=2 ∧ forbid B-orbits alone / both | **8 COMPLETE** (=A) |
| corners=3 ∧ require B-orbits alone / both | **8 COMPLETE** (=B) |
| forbid (2,2) global | **16 COMPLETE** |
| corners=2/3 ∧ forbid center | **0 / 8 COMPLETE** (A/B) |
| require center global | **8 COMPLETE** (=A) |

## Related files

- `FINAL_SELECTION_THEOREM.md`
- `SELECTION_THEOREM_CHECKLIST.md`
- `CYCLE15_CAPACITY_DECOMPOSITION.md`
- `CYCLE27_CORE_EXTENSION.md`

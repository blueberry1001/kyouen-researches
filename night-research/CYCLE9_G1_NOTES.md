# Cycle 9 G1 — (2,2) geometric obstruction notes

Complete for the local questions. Parent owns `CYCLE8_N7_STRUCTURE.md`.
Inputs: `maxsafe_n7_K14.bin` (16, not re-enum), `forbidden_quads(7)` (n=6364).

## Board (Q = (2,2) orbit, c = center)

```
.......
.......
..Q.Q..
...c...
..Q.Q..
.......
.......
```

## Lemma A — forbidden quads through (2,2) (COMPLETE local list)

- Quads touching (2,2): **1997**
- Orbits that never appear as companions: **(none)**
- Quads through both (2,2) and center: **216**
- Quads through both (2,2) and some (2,3) cell: **652**
- Quads through both (2,2) and some corner: **402**
- Quads through both (2,2) and some (0,3) cell: **384**

Companion-cell frequency by orbit (cell appearances across those quads):
{
  "(0,0) corners": 440,
  "(0,1) edge-1": 520,
  "(0,2) edge-2": 1024,
  "(0,3) edge-3 / axle": 392,
  "(1,1) diag-1": 608,
  "(1,2) inner": 1120,
  "(1,3) near-center-axle": 692,
  "(2,3) knight-of-center": 696,
  "(3,3) center": 216
}

Top composition groups (n22 in quad | other orbits):
-  72×  n22=1 others=['(0,1) edge-1', '(0,2) edge-2', '(1,2) inner']  eg [[1, 0], [2, 0], [1, 2], [2, 2]]
-  72×  n22=1 others=['(0,2) edge-2', '(1,1) diag-1', '(1,3) near-center-axle']  eg [[2, 0], [1, 1], [3, 1], [2, 2]]
-  72×  n22=1 others=['(0,2) edge-2', '(1,2) inner', '(2,3) knight-of-center']  eg [[2, 0], [2, 1], [2, 2], [2, 3]]
-  72×  n22=1 others=['(1,2) inner', '(1,3) near-center-axle', '(2,3) knight-of-center']  eg [[2, 1], [3, 1], [2, 2], [3, 2]]
-  48×  n22=1 others=['(1,1) diag-1', '(1,2) inner', '(2,3) knight-of-center']  eg [[1, 1], [2, 1], [3, 2], [2, 4]]
-  40×  n22=1 others=['(0,1) edge-1', '(0,2) edge-2', '(2,3) knight-of-center']  eg [[1, 0], [2, 0], [4, 2], [4, 3]]
-  40×  n22=1 others=['(0,1) edge-1', '(1,1) diag-1', '(1,2) inner']  eg [[1, 0], [1, 1], [4, 1], [2, 2]]
-  40×  n22=1 others=['(0,2) edge-2', '(1,2) inner', '(1,2) inner']  eg [[2, 0], [2, 1], [2, 2], [2, 5]]

Full list: `results/cycle8_g1_quads_through_22.json`.

## Lemma B — every K=14 max set already blocks every (2,2) cell (COMPLETE)

On all 16 sets × 4 empty (2,2) cells:
- blocker-count histogram: **{5: 16, 6: 8, 7: 32, 9: 8}**
- min tau (deletions needed to free one (2,2) cell): **3**
- tau histogram: **{3: 40, 4: 24}**

So inserting a (2,2) cell into any max set requires deleting >= 3 stones,
giving size <= 14-3+1 = 12 along that 1-edit route (remove-then-add: after
3 removals size 11, add (2,2) → 12). The observed conditional max
with (2,2) occupied is **13** (Package B COMPLETE) via sets that are
**not** 1-edit neighborhoods of the 14-set census — (2,2)-using 13-sets
live elsewhere in the safe complex. This is stronger than a τ=1 picture:
(2,2) is deeply blocked from every max set (τ∈{3,4}).

Blocker cells come disproportionately from orbits:
- global: [('(1,2) inner', 312), ('(1,3) near-center-axle', 216), ('(2,3) knight-of-center', 152), ('(0,0) corners', 144), ('(0,2) edge-2', 136), ('(0,1) edge-1', 96)]
- phase A sets: [('(1,2) inner', 152), ('(1,3) near-center-axle', 144), ('(3,3) center', 88), ('(0,1) edge-1', 72), ('(0,2) edge-2', 72), ('(0,0) corners', 56)]
- phase B sets: [('(1,2) inner', 160), ('(2,3) knight-of-center', 152), ('(0,0) corners', 88), ('(1,3) near-center-axle', 72), ('(0,2) edge-2', 64), ('(0,3) edge-3 / axle', 48)]

## Lemma C — capacity / exclusion contrast

| constraint | max | status |
|---|---:|---|
| any (2,2) occupied | 13 | COMPLETE Package B |
| (2,2)+center | 13 | COMPLETE Package B (NOT <13) |
| (2,2)+(2,3) cell | 13 witness | <=13 inherited; witness only this package |
| center+(2,3) | **12** | COMPLETE Package B count@13=0 |
| center+(0,3) | 13 | COMPLETE Package B |
| corners=4 | <=12 | COMPLETE Package B |

The (2,3)-side of the center exclusion (cap 12) is **strictly stronger** than
the (2,2)-side (cap 13). (2,2) is not quad-adjacent to center or (2,3);
the caps are capacity/exclusion effects, not a single shared forbidden quad.

## Center+(2,3) = 12 (why 13 fails)

- Quads through center AND a (2,3) cell: **244**
- K=12 witness `104c001882207` (safe=True):
```
XXX....
..X...X
.....X.
..XC...
.......
...XX..
X.....X
```
- +1-cell probes on this witness: **0 legal adds**, of which safe 13-sets: **0** (must be 0; Package B COMPLETE count@13=0).
- Every other empty cell is blocked by >=1 forbidden triple inside the 12-set
  (details in `cycle8_g1_result.json` → `center_plus_23.plus1_on_witness.blocked_adds`).

## Human-checkable bundle statement

> On 7×7, the four (2,2) cells sit one knight/diagonal step from the center but
> **no single forbidden quad contains both a (2,2) cell and the center**, and
> **none contains both a (2,2) cell and a (2,3) cell**. Nevertheless every
> 14-stone max safe set already carries a nonempty blocker family on each empty
> (2,2) cell (tau>=1), so any (2,2)-using set loses >=1 stone vs K=14.
> By contrast center+(2,3) loses >=2 stones (cap 12), via quads that
> **do** fire inside the center+(2,3) pair's joint neighborhood.

Evidence labels:
- Lemma A, B: COMPLETE for the local question (full quad list; full 16-set blocker pass).
- Conditional maxima: COMPLETE inherited from Package B where noted; G1 capacity
  conjunctions beyond that are **witness-only** unless the JSON says COMPLETE.

Reproduce:
```powershell
& $env:MIMO_PYTHON night-research/cycle8_g1_22_geometry.py
```

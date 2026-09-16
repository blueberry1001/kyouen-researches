# Cycle 2 — 2026-09-17 ~01:00 JST

## Checked

- branch: `replicate-8x8-o-stratum` @ `8a53adf`
- night-research CYCLE1 artifacts present
- 9×9 first-move job was **stopped** at 8/14 (no live solver at cycle start)
- Restarted remaining 6 D4 classes (`run_first_moves_9x9.py`, memo=30, PARALLEL=1)
- Duplicate second launch detected and killed (two `kyouen_solver_9.exe 37 30` at ~12 GB each)
- Single remaining process solves absolute class `(1,4)` first (`first_id=37`)

## New exact facts

1. **9×9 first-move partial (10/15 including documented center): all WIN so far.**
   Completed absolute classes: `(0,0),(0,1),(0,2),(0,3),(0,4),(1,1),(1,2),(1,3),(1,4)` + center `(4,4)`.
   Cell-weighted: **57/81 winning first moves known**, all WIN. Density bounds [0.704, 1.000].
   Newest: `(1,4)` FIRST_WIN, 297,795,584 states, 594s (center-rel `(3,0)`).
   Remaining absolute classes: `(2,2),(2,3),(2,4),(3,3),(3,4)`.
   **Now solving `(2,2)`** (`kyouen_solver_9.exe 20 30`) — this is center-rel `(2,2)`, the 5×5 corner LOSS orbit. Critical H-embed test.

2. **Absolute even-sum-minus-corners (5×5 rule) does not transfer to 9×9 absolute coords.**
   Agreement only 4/8 on completed non-center classes.
   Counterexamples (actual WIN, rule predicts LOSS): `(0,0)` corner, `(0,1)`, `(0,3)`, `(1,2)`.
   Status: **REJECTED as a cross-size rule**. This was expected to be a negative control, not the embedding test.

3. **Embedding transfer test (center-relative orbits) — only `(0,0)` resolved.**
   Center `(0,0)`: 5×5 WIN, 9×9 WIN → **MATCH**.
   Other five transfer orbits still unsolved (they are absolute `(2,2),(2,3),(2,4),(3,3),(3,4)`).

4. **10×10 first-move classification is already complete (priority E — do not re-solve).**
   `rust/independent-verifier/evidence-sample/10x10-all-first-moves-winning-replies.csv`: all 100 cells LOSS.
   Empty 10×10 is second-player win, so density=0 is definitional.

5. **Winning first-move density by n (from published counts + this work):**
   n=1..10: `1,1,1,0,0.36,1,0,0,≥1/81,0`
   Non-trivial classification only needed on F-win boards `{1,2,3,5,6,9}`.
   Among those, only n=5 is known to have density < 1.

6. **Board-complete 6×6 A_L is NOT computable from existing data.**
   KYOENC3 certificates store only a witness LOSS child per WIN node; odd-stone
   LOSS layers are incomplete. Existing 6×6 random-safe CSVs have 1 child/parent.

7. **8×8 depth-audit sample A_L = 629** (independently recomputed).
   40 four-stone parents, 2138 children, 95 LOSS (all from 20 WIN parents).
   K-histogram: `{1:6, 2:5, 3:3, 5:2, 8:1, 9:1, 12:1, 31:1}`.
   One parent has K=31 — strong killer concentration in the sample.
   Artifact: `night-research/cycle2-a-l-8x8-sample.json`.

## Hypotheses

| id | statement | status |
|----|-----------|--------|
| H3-abs | even-sum-minus-corners describes winning first moves on any odd board | **REJECTED** on 9×9 absolute coords (4 counterexamples) |
| H-embed | center-rel D4 orbit outcome is invariant under embedding 5×5→9×9 | **open**; only (0,0) matches; need (1,0),(1,1),(2,0),(2,1),(2,2) |
| H-dense | among F-win n≤10, only n=5 has any losing first move | **exploratory**; dies as soon as one 9×9 orbit is FIRST_LOSS |
| H-A_L-board | board-complete small-board A_L available from certs | **REJECTED** — certs are not complete LOSS layers |

## Artifacts

- `night-research/cycle2-5x5-vs-9x9-transfer.json` — transfer table + absolute negative control
- `night-research/analyze_cycle2_transfer.py` — regenerates the above from CSV + 5×5 cargo log
- `night-research/cycle2-density-table.json` — cross-n winning-first-move density + H-dense status
- `night-research/analyze_cycle2_density.py` — density table builder
- `night-research/cycle2-a-l-8x8-sample.json` — sample A_L=629 + K histogram
- `night-research/analyze_cycle2_a_l_sample.py` — A_L recomputation
- `night-research/first-moves-9x9-rerun.out.log` — restarted driver
- `night-research/CYCLE2_RESULTS.md` — this file


## Next cycle (highest priority)

1. Harvest `(2,2)` when done — **decides H-embed for center-rel `(2,2)`** (5×5=LOSS).
   - FIRST_WIN → FLIP, H-embed weakened; H-dense survives
   - FIRST_LOSS → MATCH + first 9×9 LOSS orbit; **H-dense falsified immediately**
2. Then harvest `(2,3),(2,4),(3,3),(3,4)` and fill the six-orbit transfer table.
3. Do not start a second 9×9 root; RAM is the bottleneck (memo=30 ≈ 12–13 GB).
4. Optional no-solve work: 6×6 LOSS-child `A_L` if a complete layer dump exists (explore-2 report).


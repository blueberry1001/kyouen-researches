# Cycle 3 — 9×9 first-move classification COMPLETE

## Checked

- branch: `replicate-8x8-o-stratum` @ `8a53adf`
- `night-research/first-moves-9x9.csv` now has **14/14 D4 orbits**
- Restarted driver finished all remaining classes overnight (no live solver now)
- Cron job `4c276f2f` is registered but did not fire while this session sat idle
  (jobs only run when the REPL is idle; long-running turns block them)
- User reported the stall; this cycle is a manual catch-up harvest

## Headline exact result

**Every first move on 9×9 is a winning first move.**

- 15 D4 orbits (14 job classes + documented center `(4,4)`)
- **15/15 FIRST_WIN**
- Cell count: **81/81**
- Density: **1.000**
- Artifact: `night-research/first-moves-9x9.csv`, `first-moves-9x9-rerun.out.log`

Empty-board winner was already F; this strengthens it from “center is a witness”
to a **complete first-move classification**.

## H-embed (5×5 → 9×9 center-relative transfer) — REJECTED

| center-rel | size on 9×9 | 5×5 | 9×9 | result |
|---|---:|---|---|---|
| (0,0) | 1 | W | W | MATCH |
| (1,0) | 4 | L | W | **FLIP** |
| (1,1) | 4 | W | W | MATCH |
| (2,0) | 4 | W | W | MATCH |
| (2,1) | 8 | L | W | **FLIP** |
| (2,2) | 4 | L | W | **FLIP** |

**3 MATCH / 3 FLIP.** Every 5×5 LOSS orbit flipped to WIN on 9×9.
Every 5×5 WIN orbit stayed WIN.

Status: **local D4-orbit outcome is not embedding-invariant**.
The 5×5 losing first-move set does not survive as a losing set on 9×9.

## H3-abs (even-sum minus corners) — REJECTED (complete)

Already rejected on 8 completed orbits. Now complete: all 81 cells WIN, so the
rule’s predicted LOSS set (odd-sum plus corners) is entirely wrong on 9×9.

## H-dense — SUPPORTED on complete n≤9 data (still exploratory)

Winning first-move density:

| n | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| winner | F | F | F | S | F | F | S | S | F | S |
| density | 1 | 1 | 1 | 0 | **0.36** | 1 | 0 | 0 | **1** | 0 |

Among F-win boards `n ∈ {1,2,3,5,6,9}`, **only n=5 has any losing first move**.
S-win boards have density 0 by definition.

Caveat: H-dense was formed while 9×9 was already partial-all-win; n=9 completing
is not a fully independent holdout. Independent tests would be n=11+ F-win boards
or a re-derivation from a frozen rule that did not peek at 9×9.

## Proof-cost spread on 9×9 first-move orbits

| abs class | center-rel | states | seconds |
|---|---|---:|---:|
| (0,4) | (4,0) edge-center | 310,378,496 | 498 |
| (2,4) | (2,0) | 268,435,456 | 517 |
| (3,4) | (1,0) | 306,184,192 | 507 |
| (1,1) | (3,3) | 331,350,016 | 526 |
| (3,3) | (1,1) | 314,572,800 | 564 |
| (1,4) | (3,0) | 297,795,584 | 594 |
| (2,2) | (2,2) | 335,544,320 | 670 |
| (0,3) | (4,1) | 662,700,032 | 1098 |
| (1,3) | (3,1) | 599,785,472 | 1011 |
| (0,0) | (4,4) corner | 473,956,352 | 1099 |
| (2,3) | (2,1) | 583,008,256 | 1111 |
| (0,2) | (4,2) | 721,420,288 | 1209 |
| (1,2) | (3,2) | 696,254,464 | 1158 |
| (0,1) | (4,3) | 780,140,544 | 1346 |

Rough pattern: axis / near-axis / inner-diagonal orbits are cheaper;
near-edge non-axis orbits (center-rel `(4,3),(4,2),(3,2)`) are most expensive.
This is a proof-cost observation, not a game-theoretic law.

## A_L (from cycle 2, unchanged)

- Board-complete 6×6 A_L: **not computable** from existing certs/CSVs
- 8×8 depth-audit sample: **A_L=629**, K_max=31
  (`night-research/cycle2-a-l-8x8-sample.json`)

## Artifacts (this cycle)

- `night-research/first-moves-9x9.csv` — complete 14-orbit table
- `night-research/first-moves-9x9-rerun.out.log` — harvest of remaining 6
- `night-research/cycle2-5x5-vs-9x9-transfer.json` — updated transfer (3 MATCH / 3 FLIP)
- `night-research/cycle2-density-table.json` — density 9×9 = 81/81
- `night-research/CYCLE3_RESULTS.md` — this file

## Official-doc updates needed

Repo docs still say 9×9 first moves are not fully classified:

- `docs/RESULTS_AND_IMPLICATIONS.md` §4
- `README.md` (center-only witness claim)
- `results/results.csv` / `outcomes.csv` (`winning_first_moves = ≥1 (centre)`)

Should be updated to `81` / “all first moves win”.

## Next cycle priority

1. Update official results/docs to complete 9×9 first-move classification.
2. Formulate a **pre-registered** independent test for H-dense (e.g. n=11 F-win
   if that becomes feasible, or a structural rule frozen without 9×9 outcomes).
3. Do **not** re-solve any 9×9 first move or 10×10 first move.
4. Optional: 5×5 complete 2-stone layer (C(25,2)=300) for board-complete small A_L
   only if no other higher-value job is available.
5. Investigate why cron `4c276f2f` did not fire overnight; keep loops short
   and harvest-oriented so idle-time ticks can run.

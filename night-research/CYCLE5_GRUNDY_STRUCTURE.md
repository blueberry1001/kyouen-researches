# Cycle 5 — Exact Grundy (nimber) structure on n ≤ 6

## Checked

- branch: `replicate-8x8-o-stratum` @ `db50e40`
- New exact enumerator: `night-research/grundy_cycle5.cpp` (C++, iterative DFS + memo)
- Python reference: `night-research/grundy_cycle5.py` (n ≤ 5 cross-check, mex consistency 0 violations)
- Deep-dive: `night-research/analyze_cycle5_grundy.py` → `cycle5-grundy-deepdive.json`
- n = 6 evaluated with cap at 14 stones; the enumerated reachable set ends at
  k = 11, so the n = 6 table below is exact for all reachable positions (the
  cap layer never materialized).

## Headline exact results

Empty-board Grundy numbers reproduce the known winner table (g = 0 ⇔ S-win):

| n | winner | empty g | max nimber | nimbers seen | missing ≤ max |
|--:|:---:|:---:|:---:|:---|:---|
| 2 | F | 1 | 1 | {0,1} | none |
| 3 | F | 1 | 1 | {0,1} | none |
| 4 | S | 0 | 5 | {0..5} | none |
| 5 | F | 1 | 6 | {0..6} | none |
| 6 | F | 1 | 8 | {0..8} | none |

Consistency: mex condition re-verified on every enumerated position
(Python: 0 violations on n=2,3,4; C++ histograms match Python exactly).

## F1. n = 2, 3 are the only "tame" boards: nimbers ⊆ {0,1}

On n = 2 and n = 3 every reachable safe position has Grundy number 0 or 1,
and g = 0 iff popcount is odd. This is exactly the Cycle-4 parity locking
restated in nimber form: **parity locking ⇔ nimbers ⊆ {0,1}**. From n = 4
on, nimbers escape {0,1}.

## F2. n = 5 losing first moves all have Grundy number exactly 3

The k = 1 layer of n = 5 splits as

| first-move orbit | size | g | first-move result |
|---|--:|--:|---|
| (0,0) corner | 4 | 3 | LOSS |
| (1,0) edge non-center | 8 | 3 | LOSS |
| (2,1) interior axial | 4 | 3 | LOSS |
| (2,0) edge center | 4 | 0 | WIN |
| (1,1) interior diagonal | 4 | 0 | WIN |
| (2,2) center | 1 | 0 | WIN |

So on 5×5, **the first move is losing iff the resulting 1-stone position has
Grundy number exactly 3** — a single uniform nimber, not just "nonzero".
This sharpens the Cycle-4 finding (winning iff zero winning replies): all 16
losing first moves are equivalent to the same nim-heap *3*.

Child-nimber histograms of the three losing orbits show why mex = 3:

| orbit | child g=0 | g=1 | g=2 | replies |
|---|--:|--:|--:|--:|
| (0,0) | 4 | 14 | 6 | 24 |
| (1,0) | 2 | 18 | 4 | 24 |
| (2,1) | 2 | 12 | 10 | 24 |

Each covers {0,1,2} and never produces a child with g ≥ 3, so mex = 3.



## F3. n = 4, k = 2: g = 1 and g = 4 are completely absent from a 120-position layer

The 120 safe 2-stone positions of 4×4 have nimber histogram
`{0: 84, 2: 20, 3: 8, 5: 8}` — **g = 1 and g = 4 never occur**, even though
both occur at other layers of the same board. The 36 non-zero positions form
6 D4 orbits, each with a uniform nimber:

| example pair | orbit size | g |
|---|--:|--:|
| (0,0)-(2,0) | 8 | 5 |
| (1,0)-(3,1) | 8 | 3 |
| (1,0)-(1,2) | 8 | 2 |
| (1,0)-(1,3) | 4 | 2 |
| (1,0)-(3,2) | 4 | 2 |
| (0,0)-(2,2) | 4 | 2 |

Orbit-uniformity is expected (D4 is a game automorphism), but the *absence*
of g = 1 from an entire layer is a genuine mex-gap phenomenon: no 2-stone
4×4 position is equivalent to a nim-heap of size 1.

## F4. Layer-wise max nimber is unimodal with unit-slope decay

Max nimber per stone-count layer:

| n | k=1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 4 | 1 | 5 | 4 | 3 | 2 | 1 | 0 | | | | |
| 5 | 3 | 2 | 6 | 5 | 4 | 3 | 2 | 1 | 0 | | |
| 6 | 0 | 3 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |

On n = 4, 5, 6 the max nimber per layer decreases **strictly by 1** per
additional stone after the peak: `max_g(k) = peak − (k − peak_k)`, down to 0
at the terminal layer. Peaks: k = 2 (n = 4), k = 3 (n = 5, 6).

On n = 6 the k = 1 layer is uniformly g = 0 (all 36 first moves win, matching
the known density-1 classification), and the k = 2 layer uses only g ∈ {1,3}
— again with gaps ({0,2} absent).

## F5. 6×6 maximal safe sets have exactly 11 stones (464 of them)

The n = 6 enumeration terminated naturally at k = 11: no reachable safe
position with ≥ 12 stones exists, and all 464 reachable 11-stone safe sets
are terminal (LOSS, g = 0). This closes the Cycle-1 timeout: the maximal
kyouen-free set size on 6×6 is **exactly 11**, achieved by 464 sets.

## New non-trivial facts (summary)

1. **Uniform losing nimber on 5×5**: every losing first move has Grundy
   number exactly 3 (16/16). A single nimber characterizes the losing
   first-move set.
2. **Layer nimber gaps**: on 4×4 the entire 120-position k = 2 layer omits
   g = 1 and g = 4; on 6×6 the k = 2 layer omits g = 0 and g = 2.
3. **Unit-slope nimber decay**: on n = 4, 5, 6 the per-layer maximum nimber,
   after its peak, decreases by exactly 1 per added stone down to 0 at the
   terminal layer. Peak position is k = 2 (n = 4), k = 3 (n = 5, 6).
4. **6×6 maximal safe sets have exactly 11 stones** (464 of them, all
   terminal/LOSS), closing the Cycle-1 maximal-set timeout.

## Artifacts

- `night-research/grundy_cycle5.cpp` / `.exe` — exact enumerator (C++)
- `night-research/grundy_cycle5.py` — Python reference + mex verifier
- `night-research/cycle5-grundy-n{2,3,4,5}.json`, `cycle5-grundy-n6-cap14.json`
- `night-research/analyze_cycle5_grundy.py`, `cycle5-grundy-deepdive.json`
- `night-research/CYCLE5_GRUNDY_STRUCTURE.md` — this file

## Caveats and next steps

- n = 6 was computed with `max_stones = 14`; enumeration terminated at
  k = 11 so results are exact, but a no-cap rerun would be a cheap audit.
- n = 7 exact Grundy is plausibly feasible (n = 6 enumerated 5.1M reachable
  positions; expect ~10–100× for n = 7) — candidate for an overnight run.
- Open: does unit-slope decay `max_g(k) = peak − (k − peak_k)` hold on n = 7?
  What determines the peak nimber (5, 6, 8 for n = 4, 5, 6)?
- Open: is the uniform losing-nimber phenomenon (F2) specific to n = 5?
  No other F-board n ≤ 9 has losing first moves, so the next test case is
  the smallest F-board n ≥ 11 that has any losing first move.


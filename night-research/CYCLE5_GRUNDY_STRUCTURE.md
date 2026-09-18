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

## F4 (upgraded to theorem). Grundy ceiling and early saturation

Let $K_n$ be the maximal safe-set size on the n×n board and

$$M_n(k)=\max_{|S|=k} g(S)$$

the maximum Grundy number over reachable safe k-stone positions. Every child
of a k-stone position lies in layer k+1, and if $g(S)=m$ then mex requires a
child with value $m-1$; hence

$$M_n(k)\le M_n(k+1)+1.$$

Since $M_n(K_n)=0$ at the terminal layer, induction gives the universal
**Grundy ceiling**

$$\boxed{\,M_n(k)\le K_n-k\,}$$

and the ceiling deficit $D_n(k)=K_n-k-M_n(k)\ge0$ satisfies
$D_n(k)\ge D_n(k+1)$: deficits never shrink with depth, and **once the
ceiling is attained ($D_n(k)=0$), it is attained at every later layer**.
Moreover, if a k-stone position $S$ attains the ceiling, $g(S)=K_n-k=m$,
then mex forces its legal children to carry *exactly* the consecutive nimber
set $\{0,1,\dots,m-1\}$ (none can exceed $m-1$ by the ceiling), so a
**saturation chain** $m\to m-1\to\cdots\to1\to0$ runs from $S$ all the way
to a terminal position.

The measured max-nimber profiles

| n | K | k=1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 4 | 7 | 1 | **5** | 4 | 3 | 2 | 1 | 0 | | | | |
| 5 | 9 | 3 | 2 | **6** | 5 | 4 | 3 | 2 | 1 | 0 | | |
| 6 | 11 | 0 | 3 | **8** | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |

are therefore **not** a coincidental "unit-slope decay": each bold entry is a
single equality $M_n(k)=K_n-k$, and every later entry is forced by the
theorem. The genuine experimental content is the **saturation onset**

$$\boxed{\;\sigma_4=2,\qquad \sigma_5=3,\qquad \sigma_6=3\;}$$

i.e. on 4×4 the ceiling is already attained with just 2 stones on the board,
and on 5×5 / 6×6 with 3 stones. The sequences $5,4,3,2,1,0$ etc. after the
peak carry no extra information.

On n = 6 the k = 1 layer is uniformly g = 0 (all 36 first moves win, matching
the known density-1 classification), and the k = 2 layer uses only g ∈ {1,3}
— again with gaps ({0,2} absent).

**Corollary (cheap n ≥ 7 test).** To extend the table one does *not* need the
full Grundy distribution: determine $K_n$, then search shallow layers for a
single position with $g(S)=K_n-|S|$. The first such layer is $\sigma_n$, and
$M_n(k)=K_n-k$ for all $k\ge\sigma_n$ follows without further computation.

**Verification on existing data** (`verify_saturation.py`,
`cycle6-saturation-verify.json`): full deficit profiles

| n | K | D(0) | D(1) | D(2) | D(3) | D(4..K) | σ |
|--:|--:|--:|--:|--:|--:|:--:|--:|
| 4 | 7 | 7 | 5 | **0** | 0 | all 0 | 2 |
| 5 | 9 | 8 | 5 | 5 | **0** | all 0 | 3 |
| 6 | 11 | 10 | 10 | 6 | **0** | all 0 | 3 |

Deficits are non-increasing on every board, and no layer after σ has a
positive deficit — the theorem's predictions hold on all three exact boards.

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
3. **Grundy ceiling theorem + early saturation**: universally
   $M_n(k)\le K_n-k$, the deficit $D_n(k)$ is non-increasing, and one
   equality $M_n(\sigma)=K_n-\sigma$ forces equality at every deeper layer
   (with a saturation chain of exact consecutive child nimbers
   $\{0,\dots,m-1\}$ at each ceiling position). The measured onsets are
   $\sigma_4=2$, $\sigma_5=\sigma_6=3$ — the ceiling is reached with only
   2–3 stones on the board.
4. **6×6 maximal safe sets have exactly 11 stones** (464 of them, all
   terminal/LOSS), closing the Cycle-1 maximal-set timeout. The maximal
   safe-set sizes for n = 1..6 are $K_n = 1,3,5,7,9,11 = 2n-1$ (Cycle-1
   exact maximal-set enumeration); whether $K_7 = 13$ remains open (the
   7×7 certificate contains a 14-stone position, but certificate DAGs are
   pruned and only store one path per proof obligation, so certificate
   max-stones is a **lower bound** on $K_7$, not necessarily the exact
   value).

## Artifacts

- `night-research/grundy_cycle5.cpp` / `.exe` — exact enumerator (C++)
- `night-research/grundy_cycle5.py` — Python reference + mex verifier
- `night-research/cycle5-grundy-n{2,3,4,5}.json`, `cycle5-grundy-n6-cap14.json`
- `night-research/analyze_cycle5_grundy.py`, `cycle5-grundy-deepdive.json`
- `night-research/verify_saturation.py`, `cycle6-saturation-verify.json` —
  ceiling/deficit verification on n=4,5,6
- `night-research/saturation_cycle6.cpp` — n=7 saturation witness search
  (K_7 + σ_7; implemented, needs an overnight run)
- `night-research/cert_parity_check.py`, `cycle6-cert-parity.json` —
  certificate-level K and parity scan for n=1..9
- `night-research/CYCLE5_GRUNDY_STRUCTURE.md` — this file

## F6. Certificate-level parity scan (n = 1..9)

Reading the KYOENC3 certificates directly (`cert_parity_check.py`):

| n | cert K | parity locked on cert | winner |
|--:|--:|:--:|:--:|
| 1 | 1 | mixed | F |
| 2 | 3 | mixed | F |
| 3 | 5 | mixed | F |
| 4 | 6 | **LOCKED** | S |
| 5 | 9 | mixed | F |
| 6 | 11 | mixed | F |
| 7 | 14 | **LOCKED** | S |
| 8 | 14 | **LOCKED** | S |
| 9 | 17 | mixed | F |

("mixed" on F-boards is forced: the k = 0 empty board is WIN on F-boards but
even, so the parity pattern "even k = LOSS" is broken at the root by
definition.)

**Observation**: the three S-win boards (n = 4, 7, 8) are exactly the three
boards whose certificates are parity-locked, and the six F-win boards are
exactly the six that are not. This correlation is consistent with the
Cycle-4 finding that parity locking on n = 2, 3 does not separate F from S
(those boards are F-win but parity-locked on the full reachable set); the
certificate-level statement differs because certificates are pruned DAGs,
not the full reachable graph.

**Certificate-K is a lower bound**: e.g. on n = 4 the exact maximal safe
set has 7 stones (Cycle 1) but the certificate only reaches 6. The
certificate values 1,3,5,6,9,11,14,14,17 are therefore lower bounds on
$K_n$, exact only where the certificate happens to contain a maximal path.

## Caveats and next steps

- n = 6 was computed with `max_stones = 14`; enumeration terminated at
  k = 11 so results are exact, but a no-cap rerun would be a cheap audit.
- n = 7 exact Grundy is plausibly feasible (n = 6 enumerated 5.1M reachable
  positions; expect ~10–100× for n = 7) — candidate for an overnight run.
- Open: does unit-slope decay `max_g(k) = peak − (k − peak_k)` hold on n = 7?
  Superseded by the ceiling theorem: the n = 7 question reduces to (a) exact
  $K_7$ (conjectured 13 = 2·7−1 from the $K_n=2n-1$ pattern on n ≤ 6) and
  (b) the saturation onset $\sigma_7$ — the first layer containing a position
  with $g(S)=K_7-|S|$. Everything deeper is then forced.
- Open: what determines the peak nimber / onset ($\sigma_4=2$,
  $\sigma_5=\sigma_6=3$)?
- Open: is the uniform losing-nimber phenomenon (F2) specific to n = 5?
  No other F-board n ≤ 9 has losing first moves, so the next test case is
  the smallest F-board n ≥ 11 that has any losing first move.


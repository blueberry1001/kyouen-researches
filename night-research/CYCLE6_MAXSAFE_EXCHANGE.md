# Cycle 6 — Exchange structure of maximal safe sets: n=6 vs n=7

## Question (pre-registered in the task)

Does the n=7 "+1" anomaly ($K_7 = 14 > 2\cdot7-1 = 13$) have a structural
explanation in the exchange graph of maximal safe sets?

Decision criteria fixed **before** running:

- **A**: all n=7 maximal sets have $\rho \ge 2$ while n=6 has sets with
  $\rho = 1$ → supports "n=7 maximal sets are isolated under 1-stone
  exchange".
- **B**: some n=7 maximal set has $\rho = 1$ → the exchange-rigidity
  explanation is refuted.
- **C**: same $\rho$ behaviour but the component-size structure differs
  drastically → move the hypothesis from local rigidity to global
  fragmentation.

## Method

`maxsafe_enum.cpp` (new):

- `count` / `enum`: exhaustive DFS over safe sets with incremental conflict
  counters; every safe K-set is enumerated exactly once (K = maximum size,
  so these are exactly the maximal safe sets).
- `analyze`: for every empty point v, the **blocker family**
  $\mathcal B_S(v)=\{T\subseteq S: |T|=3,\ T\cup\{v\}\ \text{forbidden}\}$,
  the exact minimal hitting-set size $\tau_S(v)$ (brute force sizes 1..3 over
  the active stones), $\rho(S)=\min_v \tau_S(v)$, the 1-swap graph (edge for
  each $(v,r)$ with $S-r+v$ safe), D4 canonical keys, orbit/stabiliser
  sizes, connected components, and per-cell frequencies.

**Fast test used (as instructed):** $\tau_S(v)=1 \iff \bigcap_{T\in\mathcal B_S(v)} T \neq \varnothing$.

### Validation of the enumerator

| check | result |
|---|---|
| n=6, K=11 count | **464** — equals the independent Cycle-5 Grundy enumeration of terminal 11-stone positions |
| n=6, K=10 count | **35,316** — equals the Cycle-5 Grundy layer count for k=10 |
| n=7, K=14 count | 16 (12,826,299 DFS nodes) |
| swap destinations resolved | 608/608 on n=6, 0 unresolved (every swap lands in the enumerated list) |
| independent Python re-derivation (`verify_n7_rigidity.py`) | ρ histogram and τ histograms reproduce the C++ output exactly; 0/7,840 candidate swaps succeed |

## Results

| quantity | n=6 (K=11) | n=7 (K=14) |
|---|---:|---:|
| # maximal sets | 464 | **16** |
| # D4 orbits | 58 | **2** |
| orbit sizes | 8 (all 58 orbits) | 8 (both orbits) |
| ρ = 1 sets | **296** (63.8%) | **0** |
| ρ = 2 sets | 168 (36.2%) | **16** (100%) |
| 1-swap pairs (total) | 608 | **0** |
| 1-swap degree histogram | 0:168, 1:136, 2:80, 3:40, 4:16, 5:16, 6:8 | **0:16** |
| # components | 248 | **16** |
| component sizes | 1:168, 2:56, 5:8, 7:8, 11:8 | **1:16** |

**Verdict: A.** Every 7×7 maximal safe set is 1-swap rigid ($\rho = 2$ for all
16 sets, zero exchange edges), whereas 64% of 6×6 maximal sets admit at least
one single-stone exchange and the n=6 exchange graph has non-trivial
components up to size 11. The 16 n=7 maximal sets are pairwise isolated —
there is no way to move between them by replacing one stone.

## The two n=7 orbits (each orbit size 8, stabiliser 1)

Orbit A (contains the centre (3,3); τ-histogram over the 35 empty points
`2:3, 3:15, 4:17`):

```
X X . . . X .
. X X . . . .
. . . . . X X
. . . X . X .
X . . . . . .
. . . X X . X
X . . . . . .
```

Orbit B (no centre; τ-histogram `2:4, 3:18, 4:13`):

```
X X . . . . X
. . . . X X .
. X . X . . .
X . X . . . .
. . . . . . X
. . X X . . .
. . X . . . X
```

Every empty point of a 14-stone position needs **at least 2 stones removed**
before any stone can be added; for 13–17 of the 35 empty points even 4
removals are necessary. So the 14-stone configurations are not merely
locally stable — they are *maximally* rigid against local repair.

## n=7 cell frequency by D4 cell orbit (16 maximal sets)

| orbit rep | orbit size | total appearances | per-cell avg | max 16 |
|---|---:|---:|---:|---:|
| (3,3) centre | 1 | 8 | 8.00 | 8 |
| (0,0) corner | 4 | 40 | 10.00 | 10 |
| (2,1) | 8 | 48 | 6.00 | 6 |
| (3,1) | 4 | 24 | 6.00 | 6 |
| (1,0), (2,0) | 8 each | 32 each | 4.00 | 4 |
| (1,1), (3,2) | 4 each | 16 each | 4.00 | 4 |
| (3,0) | 4 | 8 | 2.00 | 2 |
| **(2,2)** | 4 | **0** | **0.00** | **0** |

Two further structural facts fall out:

1. The centre appears in exactly one of the two orbits (8/16 sets), and the
   corner orbit is used 10/16 — the two orbits do **not** share a common
   "mandatory" cell.
2. The interior diagonal orbit **(2,2) is never used** by any 14-stone
   maximal set, although it occurs in smaller safe sets. So the n=7 maximum
   configurations avoid one entire cell orbit.

The frequency spread (2 for (3,0) up to 10 for corners, with (2,2) at 0) is
the simplest structural signature of the n=7 anomaly found so far: it is a
*positional* constraint rather than an exchange-graph effect.

## Interpretation and next hypotheses

The n=7 maximum sets are (i) extremely few (16 vs 464), (ii) collapse to two
D4 orbits, (iii) completely exchange-isolated, and (iv) avoid the (2,2) cell
orbit entirely. Taken together this suggests the +1 anomaly is driven by a
small number of highly constrained, "crystal-like" configurations rather
than by a rich family connected through local moves.

Follow-ups (not run here):

- n=8: sample ~100–1000 of the 15-stone sets and test $\rho$ and component
  structure before any full enumeration (as instructed, no full n=8 pass).
- Does the (2,2)-avoidance and the centre/corner split persist for n=8
  (15 stones) and n=9 (17 stones, needs a 128-bit solver)?
- Relate $\tau$ histograms to the n=5 losing-first-move nimber finding:
  both are "local rigidity" invariants of maximal/near-maximal positions.

## Artifacts

- `night-research/maxsafe_enum.cpp` / `.exe` — enumerator + analyser
- `night-research/maxsafe_n6_K11.bin` (464 sets), `maxsafe_n7_K14.bin` (16 sets)
- `results/maxsafe_exchange_n6.csv`, `results/maxsafe_exchange_n7.csv`
- `results/maxsafe_swap_edges_n6.csv` (608 edges with canonical keys),
  `results/maxsafe_swap_edges_n7.csv` (header only — no swaps exist)
- `results/maxsafe_exchange_components_n6.csv`, `..._n7.csv`
- `results/maxsafe_cell_frequency_n6.csv`, `..._n7.csv`
- `night-research/verify_n7_rigidity.py` — independent Python re-derivation
- `night-research/summarize_cell_freq_n7.py` — cell-frequency summary
- `night-research/enum7_count.json`, `enum7.json` — run logs


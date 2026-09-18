# Cycle 9 G2 — union corridor facts (n=7)

Evidence: COMPLETE exact-size DFS on the 19 cells of A0∪B0
(`night-research/cycle8_g2_corridor.py` → `results/cycle8_g2_bottleneck_12.json`).
Inputs: complete 16-set list; Cycle 8A explicit path facts.

## Complete counts on A0∪B0

| k | safe k-sets on union |
|---:|---:|
| 12 | 366 |
| 13 | 39 |
| 14 | **2** (= {A0, B0} exactly) |

## Growability (safe single-cell adds only)

| size-12 class | count |
|---|---:|
| can grow to A0 and B0 | **0** |
| can grow to A0 only | 91 |
| can grow to B0 only | 91 |
| can grow to neither | 184 |

Size-13 subsets: only_A0=14, only_B0=14, subset of both=0, subset of neither=11
(mixed A/B cells — cannot grow to a phase without removals).

## Lemma (restricted corridor)

> On the 19-cell union, the only size-14 safe sets are A0 and B0.
> No size-12 set can be completed by additions alone into both phases.
> Every size-13 subset of a phase completes only to that phase.
> Therefore any single-stone path from A0 to B0 **restricted to union cells**
> must visit size **≤11** (agrees with Cycle 8A `path_min_width_on_union=11`).
> Full-board paths may use cells outside the union and have min width **12**
> (Cycle 8A explicit path; unique 13-completion among the global 16).

## n=6 contrast

n=6 has 1-swap edges (ρ=1 on 296/464 max sets), so some distinct max pairs
admit paths that stay at size K−1=10. n=7 has **no** such 1-swap and no
size-13 corridor between distinct max sets.

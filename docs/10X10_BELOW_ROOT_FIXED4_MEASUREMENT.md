# 10x10 below-root fixed-parent measurement

This note records the first independent-process run of the fixed four three-stone parents from Actions run `34472681351`, commit `5ea6b0d75a11c54ebf0ca78969f550dfe89d12b6`.

Each parent was launched in a fresh process with the instrumented exact solver, `shrink=3`, `load=80`.

## Completed parents

Three of the four parents completed and passed `scripts/check_below_root_instrumentation_csv.py`.

| parent | outcome | visited | maxdepth | memo |
|---|---|---:|---:|---:|
| `14,64,74` | WIN | 4,342,654 | 17 | 4,297,793 |
| `12,32,55` | WIN | 7,106,990 | 18 | 7,061,150 |
| `13,52,57` | WIN | 11,651,703 | 18 | 11,605,528 |

The fourth parent, `0,11,35`, ended with solver exit code 3 (`TableFull`) under `shrink=3, load=80`; it is therefore not treated as a completed measurement.

## Clean depth-5 test

Depth 5 is especially useful in these three completed runs because every visited node at that depth is a WIN node and `loss_nodes=0`. Therefore `work_into_win_child` at depth 5 is unambiguously work spent in failed WIN children before the eventual LOSS child; it is not contaminated by LOSS parents, for which exploring WIN children is necessary proof work.

Define

`waste_fraction = work_into_win_child / (work_into_win_child + work_into_loss_child)`.

| parent | WIN nodes | work into WIN child | work into LOSS child | waste fraction | failed WIN children / WIN node |
|---|---:|---:|---:|---:|---:|
| `14,64,74` | 72 | 1,902,330 | 2,440,250 | 43.81% | 4.10 |
| `12,32,55` | 79 | 2,010,654 | 5,096,255 | 28.29% | 2.15 |
| `13,52,57` | 75 | 5,598,617 | 6,053,009 | 48.05% | 1.95 |

Median depth-5 waste fraction is **43.81%**. All 3/3 completed parents exceed the preregistered 25% threshold.

This is direct evidence that meaningful search cost exists below the root in the ordering of children of WIN nodes. It does not yet show that any particular heuristic can recover that cost: a useful heuristic must identify the LOSS child cheaply enough that its own cost does not erase the saved search.

The next experiment should therefore target ordering at depth 5 rather than another root-only ranking experiment. Candidate rules should be evaluated on the same fixed nodes with the rule frozen before exact outcomes are consulted. The primary measurement should be change in `work_into_win_child` and total `visited`, with correctness/outcome required to remain identical.

## Boundary

Do not sum `work_into_win_child` across depths as independent work: subtree visit counts are inclusive and overlap across ancestor depths. At mixed depths, the aggregate also combines avoidable WIN-child work from WIN parents with necessary WIN-child work from LOSS parents. Depth 5 avoids both problems for this first test.

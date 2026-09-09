# 10x10 below-root instrumentation implementation

This note records the implementation of the preregistered below-root diagnostic
and the semantic smoke validation completed before interpreting any of the
frozen parent measurements.

## Lineage

Implementation branch: `implement-below-root-instrumentation-v1`

Parent preregistration/amendment tip:
`bd9d78b22350cc161e6e30964a605c3295b5b64b`

The normal `scripts/probe_cert_solver.cpp` is intentionally unchanged.  The
observational build is a separate translation unit,
`scripts/probe_cert_solver_below_root.cpp`, so the semantic baseline remains in
the same checkout.

## Counters

The instrumented build records the preregistered per-depth entry memo,
child-prefetch memo, expansion, deduplication, child-entry, WIN cutoff, outcome,
and recursive visited-delta counters.  Amendment-2 late-entry transposition hits
are recorded separately as `late_entry_hit_win` and `late_entry_hit_loss` when a
child was unknown at prefetch but its recursive call consumes zero new visited
nodes.

Recursive subtree deltas are not summed across depth.  TOTAL rows therefore
write `NA` for `work_into_win_child` and `work_into_loss_child`; unique work
localization uses `expanded[d] / visited`.

The implementation checks, among others:

- `entry_get = expanded + entry_hit_loss + entry_hit_win` per depth;
- `child_get = unique_children`;
- `unique_children + duplicate_children = generated_children`;
- cached LOSS + cached WIN + unknown = unique children;
- `put_loss + put_win = expanded`;
- `win_nodes + loss_nodes = expanded`;
- `sum_d expanded[d] = visited`;
- instrumented `expanded[d]` equals the solver's pre-existing
  `depth_visited[d]` counter.

## Fresh-process runner

`scripts/run_below_root_instrumentation.py` builds both baseline and
instrumented solvers and uses exactly one state per process.  A row is accepted
only when baseline and instrumented runs agree exactly on:

- outcome;
- visited;
- maxdepth;
- final memo used;
- root diagnostics (`unique`, `entered`, first canonical key, witness, outcome).

The frozen four-parent mode uses shrink=0, load=90 and an unbounded solver,
matching the parent benchmark exact configuration.

## Pre-measurement smoke result

GitHub Actions run `34323310066`, head
`ecf1e747cbd7e8d7857758be4d2e8e781301c6d8`, completed successfully on
2026-09-09 before the four-parent output was interpreted.

The deterministic 10x10 KYOENC4 smoke root was:

`7,16,17,28,30,33,41,48,54,68,69,71,81,92`

It has 14 stones and exercises the high 64-bit state word.  Baseline and
instrumented builds agreed with:

- outcome: WIN;
- visited: 2;
- maxdepth: 15;
- memo used: 2;
- active instrumented depths: 14 and 15.

All C++ and runner-side counter invariants passed.

No frozen four-parent counter result is interpreted in this note; that remains
a separate measurement stage.

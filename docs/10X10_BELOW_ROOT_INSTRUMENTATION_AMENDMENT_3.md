# 10x10 below-root instrumentation amendment 3

This amendment is made **before any below-root instrumented parent result is inspected**.
It fixes an experimental-independence problem in the existing multi-state execution path.

## Problem: the normal states-file mode reuses one Solver

The current non-certificate `main` constructs one solver before looping over all requested states:

```cpp
Solver solver(shrink,load);
for(auto& pts:tasks){
    Solver::Stats st;
    bool w=solver.solve(pts,st);
    ...
}
```

`Solver::solve` resets the per-call `Stats`, but it does **not** reset `memo_`. Therefore parent 2 starts with all transposition information retained from parent 1, parent 3 inherits parents 1+2, and so on.

That behavior is useful for throughput-oriented batch solving, but it is invalid for the planned below-root mechanism comparison, whose rows are intended to describe each frozen parent under the same initial solver state.

This is especially important because the planned endpoints explicitly include memo-hit rates, cached-child fractions, late-entry hits, and depth-localized visited work. Every one of those quantities can shift when earlier parents preload the memo.

## Frozen correction

Every instrumented parent must start from a **fresh Solver instance with an empty memo**.

Allowed execution patterns are:

1. launch a new solver process for each parent; or
2. add a dedicated instrumentation mode that constructs a fresh `Solver` inside the parent loop.

Do **not** use the existing multi-state batch mode unchanged for the four-parent or twelve-parent instrumentation cohorts.

The preferred first implementation is one process per parent because it also resets all solver-owned state and makes the independence condition easiest to audit.

## Required provenance

For each raw parent result record:

- record the exact commit SHA;
- record shrink/load parameters;
- record the parent state;
- record that the process contained exactly one requested parent;
- retain the ordinary outcome/visited/maxdepth/memo values together with the depth rows.

A run is invalid for cohort comparison if the solver process handled another parent first.

## Regression invariant

For each frozen parent, compare instrumented and uninstrumented **fresh-process** runs at identical parameters. They must agree exactly on:

- WIN/LOSS;
- `visited`;
- `maxdepth`;
- final memo used;
- existing root diagnostics when enabled.

This fresh-process requirement is in addition to the previously frozen counter consistency checks.

## Why this amendment is necessary before implementation

The earlier blind-probe work already showed that solver-state carry-over can reverse an apparent ordering result. The same class of contamination would be even more damaging here because memo behavior itself is one of the outcomes being measured.

Therefore no four-parent diagnostic output should be interpreted until parent isolation is enforced.
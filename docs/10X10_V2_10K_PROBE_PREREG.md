# Preregistration: V2 fresh 10k probe (cost experiment)

Date: 2026-09-08
Branch: `10x10-v2-10k-probe-cost`
Base: `10x10-clean-holdout-v2` @ `451ece8674e167d9a3dec5dbc29c16518b8ab6fb`
Status: **FROZEN BEFORE ANY 10k PROBE ROW IS COLLECTED**

This document freezes the 10k protocol before execution. No setting below
may change after the freeze commit. 1M outcomes were used only to motivate
the budget choice (V1 budget-stability signal); no 1M result tunes any 10k
choice below.

## 0. Scope (primary cohort is fixed)

- 12 frozen V2 parents, 1,136 children exactly as in
  `results/10x10/clean-holdout-v2/exact_task_list.csv`.
- No parent/child added, removed, or swapped.
- Canonical task-set digest (line-ending invariant, recomputed per
  `scripts/generate_v2_holdout_children.py`):
  `task_set_sha256 = aeccb6662a37ef25faf3fe6d0ab6707a9677718889139123060fff4a48566bc7`
- Task order is frozen: `exact_task_list.csv` row order == per-parent
  `children_<parent>.txt` order == `exact_outcomes.csv` row order
  (normalized comma/hyphen state spelling aside).
- Known artifact: raw byte SHA256 of `exact_task_list.csv` differs by
  checkout line endings (CRLF working file `708c2846...` vs LF blob
  `0b8a74ed...`); both normalize to the same git object and the same
  canonical tuple digest above. The canonical digest is authoritative;
  both byte SHAs are recorded for transparency.

## 1. Probe budget and solver settings (frozen)

- `probe budget = 10,000 visited / child` (BUDGET = 10000).
- Fresh solver process per child. Memo table sharing across children
  is forbidden (one `subprocess.run` per task, no in-process carryover).
- Solver binary: `tmp-kb/probe_holdout_native`
  - `solver_binary_sha256 = 15d805ea9b354cc11c5c5ee5329512b723241897e32d135bf5a82094cdccd585`
  - identical bytes to the V2 1M run (rebuilt only with the same flags
    if missing; any rebuild must reproduce this digest or the run stops).
- Solver sources digest:
  `solver_sources_sha256 = 9b6f227ffb9fd802851ae69bad3a5621ce78857af1c65084ae92d09aa67e47b3`
  over `scripts/probe_cert_solver.cpp` + `scripts/probe_parts/*.inc`.
- Compiler/build flags: `g++ -O2 -std=c++20 -o <bin> <src>`
  (observed toolchain: MSYS2 gcc 15.2.0).
- Solver CLI per child (identical to 1M except budget):
  `<bin> <state-tmpfile> 3 80 10000 0`
  i.e. `shrink = 3`, `load = 80`, `budget = 10000`.
- Non-instrumented primary binary. Mechanism counters (P9) are NOT
  collected with the primary run; any instrumented run uses a separate
  binary and never contributes primary `memo` values.

## 2. Ranking rule (frozen, identical to V2 1M)

Per-child ranking key (`corrected_key`, same implementation as V1/V2):

1. Probe-resolved LOSS first.
2. Unresolved PROBE: `memo_used` ascending.
3. Probe-resolved WIN last.
4. Tie-break within every stratum: 4th-move board index ascending
   (deterministic; `move_of(parent, child)`).

The primary 10k ranking is **memo_used ascending** under this key.
If any probe resolves exactly (WIN/LOSS at 10k), the row outcome is
recorded verbatim and the categorical key above applies; the fraction
of non-PROBE rows is reported explicitly (P4 must state whether the
10k ranking was all-PROBE or mixed).

## 3. Output schema (frozen)

Primary CSV: `results/10x10/clean-holdout-v2/independent_probe_10000.csv`
with header exactly:

```
parent,batch,batch_position,state,probe_outcome,visited,maxdepth,memo,seconds
```

- `parent`: e.g. `3,53,84` (comma spelling, as in task list).
- `batch`, `batch_position`: frozen task-list coordinates (strings).
- `state`: comma spelling, verbatim from task list.
- `probe_outcome`: solver-reported `outcome` verbatim (`PROBE`/`WIN`/`LOSS`).
- `visited`, `maxdepth`, `memo`: solver-reported integers as strings.
- `seconds`: solver-reported seconds as string (primary cost signal).

Sidecar run log (orchestration, never mixed into solver cost):
`results/10x10/clean-holdout-v2/independent_probe_10000.runlog.jsonl`,
one JSON object per attempted task:

```
{"parent": ..., "state": ..., "solver_exit": 0, "solver_seconds": ...,
 "wall_seconds": ..., "worker": ..., "attempt": 1, "ts": ...}
```

Failures append a runlog record with nonzero `solver_exit` (or
`TIMEOUT`) and no CSV row.

Protocol manifest:
`results/10x10/clean-holdout-v2/independent_probe_10000.protocol.json`
(frozen at freeze time, enforced on every run/resume).

## 4. Resume policy (frozen)

- Completed key = `(parent, state)` comma-spelling exact match.
- Resume appends only rows whose key is absent; never rewrites rows.
- On every invocation the runner recomputes the full protocol manifest
  and refuses to run if it differs from the frozen file.
- A nonempty CSV without its manifest is refused (provenance unknown).
- Output rows may land in completion order (parallel); set equality
  against the frozen task set is the acceptance check, not row order.

## 5. Failure / timeout policy (frozen)

- Solver `returncode != 0` → no CSV row; runlog failure record; task
  stays pending for the next resume invocation.
- Solver stdout not yielding exactly 1 CSV row → same as failure.
- No per-task timeout wrapper (10k probes are sub-second; a hung
  solver is killed manually and the task retried; any such event is
  disclosed in the final report).
- Experiment acceptance: 1136/1136 rows, zero duplicates, set-equal to
  the frozen task list.

## 6. Wall-time measurement (frozen)

- Primary cost signal: solver-reported `seconds` (inside-process CPU
  time; parallel-safe).
- Orchestration `wall_seconds` (around `subprocess.run`) is recorded
  only in the runlog for diagnostics; it is never substituted for
  `seconds` in P5/P6 cost ratios.
- Parallelism: `multiprocessing.Pool` over tasks (`--workers`, default
  12); workers do not share solver state.

## 7. Blindness (P3, frozen)

- No first-LOSS rank, AUC, LOSS/WIN-split memo, or cost-advantage
  computation until all 1136 probe rows are committed.
- Order of commits: (1) this freeze, (2) runner + resume commits if
  needed, (3) complete raw 10k probes, (4) join exact + analysis.
- The exact file `exact_outcomes.csv` is read only for the P0 set-identity
  check above and for post-completion analysis; it is never an input to
  the probe runner.

## 8. Analysis plan (locked, executed only after raw commit)

- P4: per-parent `memo_used`-ascending ranking with the frozen key;
  report m, LOSS count, first LOSS rank, normalized rank, AUC, top-1
  outcome, top-5 LOSS count, 1M first-LOSS rank, 10k-vs-1M rank
  correlation; globals: rank list/sum/median/max, mean/median AUC.
- P5: per-parent `ratio = (probe-all 10k cost + memo-order exact cost
  to first LOSS) / (file-order exact cost to first LOSS)`, all costs
  from solver-reported `seconds`; globals: median/geometric-mean ratio,
  improved/tie/worse counts, aggregate seconds.
- P6: 10k-vs-1M on rank diff, AUC diff, probe-cost ratio, total-cost
  ratio, count of parents where 10k total cost beats 1M total cost.
- P7: 100k go/no-go per the task spec thresholds (no 100k run here).
- P8: staged-strategy simulation on frozen 10k rows only, no new solves,
  clearly labeled exploratory and separate from the primary all-probe
  result.

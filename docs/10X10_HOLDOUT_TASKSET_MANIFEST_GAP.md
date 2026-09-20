# 10x10 holdout: task-set manifest gap

Date: 2026-09-06

This note records a pre-execution audit finding for the preregistered 10x10
holdout probe on `blind-probe-holdout-validation`.

## Finding

`run_probe_holdout_independent.py` currently freezes the following in
`independent_probe_1000000.protocol.json`:

- solver binary SHA-256;
- solver source digest;
- probe budget;
- shrink;
- load.

It does **not** freeze the selected parent/child task set itself.

The task set is reconstructed on each `--run` from

- `results/10x10/holdout-parent-selection-preregistered.csv`, and
- `results/10x10/blind_probe_children/children_*_batch*.txt`.

Therefore, after a partially completed run, one of those files could change
and a resumed run could append rows for a different holdout task set while
still satisfying the current protocol manifest. `completed_keys()` would
prevent duplicate `(parent,state)` rows, but it would not detect replacement,
addition, removal, batch reassignment, or within-batch reordering of tasks.

No holdout outcome was inspected to obtain this finding.

## Required fix before the primary run

Bind the exact ordered task list into the protocol manifest. A sufficient
canonical representation is the ordered sequence of

```text
(parent, batch, batch_position, state)
```

returned by `load_tasks()`.

Compute a SHA-256 digest over a deterministic serialization of that sequence
and store at least

```text
holdout_tasks_sha256
holdout_task_count
```

in the protocol manifest. On every resumed `--run`, recompute and require an
exact match before appending any row.

This protects the preregistered parent selection and child set from accidental
or silent drift in the same way the existing binary/source digest protects the
solver implementation.

## Status

The issue is identified before primary holdout execution. Do not start or
resume the 1M primary probe until the runner enforces this task-set binding.
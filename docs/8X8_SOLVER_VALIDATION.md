# 8×8 solver validation (pre-production)

Freeze commit already recorded solver source identity.
This report covers checks performed on **non-production** states only.
No production required-root outcome was read or inspected.

## Checks

1. Independent Python brute-force cross-check on 28 late (8–12 stone) safe states: **0 mismatches**
2. D4 outcome invariance on 8 transforms of one late-12 state: all **WIN**, memo-shared after first solve
3. Fresh-process reproducibility (same input, two runs): **identical**
4. `memo_power` ∈ {22, 24, 26} on late set: **identical outcomes**
5. Geometry of validation roots: safe 5-stone / late safe states only; not drawn from `artifacts/8x8-o-required-roots.csv`

## Non-production cost probe

40 random safe 5-stone roots (tagged `random` in validation input) solved in **1.34 s** wall clock
(`memo_power=26`). Per-root visited counts ~0.9k–17k. Production 848-root census is expected
to finish quickly; sharding still used for robustness and per-shard logs.

## Artifacts

- `artifacts/8x8-solver-validation-input.csv`
- `artifacts/8x8-solver-validation-late.csv`
- `artifacts/val-solver-out-a.csv`
- `artifacts/val-bruteforce.csv`
- `artifacts/val-d4-out.csv`
- `artifacts/val-solver-out-b.csv`
- `artifacts/val-solver-out-c22.csv`
- `artifacts/val-solver-out-c26.csv`

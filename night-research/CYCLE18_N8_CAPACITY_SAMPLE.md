# Cycle 18 — n=8 capacity SAMPLE (node-capped)

`cycle8_b_maxsafe.exe max 8 … --known-upper 15 --max-nodes 3e6` (**incomplete**):

| constraint | max_size seen | n_at_best | note |
|---|---:|---:|---|
| force corner pid 0 | **15** | 73 | full K still reached |
| forbid orbit (2,2) | **15** | 12 | full K without (2,2) |

Together with earlier first@15 witnesses that **use** (2,2) and that omit /
use the center-block, n=8 SAMPLE shows **no** analog of the n=7 exclusive
phase capacity map at the proven maximum size.

**Non-claim:** incomplete searches; not a proof that every n=8 max set is
flexible — only that both “with (2,2)” and “without (2,2)” (and with a
corner) reach size 15 in capped runs.

## Artifacts
- session exe logs; prior `results/cycle8_h_n8_sample.json`,
  `results/cycle14h_n8_witnesses.json`, `results/cycle15h_n8_occ.json`
- `night-research/CYCLE14H_N8_CONSTRAINED.md`

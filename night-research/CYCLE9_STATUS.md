# Cycle 9 — working notes (branch cycle8-n7-structure)

Base delivered: Cycle 8 @ `6c5969f` on `cycle8-n7-structure`.

## Side study complete (this session)

`night-research/cycle9_small_n_min_det.py` — complete enum of max safe sets
for n=3,4,5 with min_det / occupancy / 1-swap counts.
Artifact: `results/cycle9_small_n_min_det.json`.

Fact: min_det=2 occurs only at n=7 among n=3..7 (complete).
K_n=2n only at n=7 for n≤8 (inherited K4..K8).

## In flight (subagents)

- G1 / T8: (2,2) forbidden-quad geometry (`cycle8_g1_*`)
- G2 / T9: size≤12 corridor (`cycle8_g2_*`)
- G3 / T10: n=8 sample expansion (`cycle8_g3_*`)

## Quick geometry peek (orchestrator)

- Forbidden quads through (2,2)-orbit: 1997/6364 on n=7.
- On phase A0, blockers of (2,2): 7 triples; (4,2): 7; (2,4): 5; (4,4): 7.
  Many blockers involve the center (3,3) — consistent with center exclusivity.

## Next after G1–G3

1. Fold G1–G3 lemmas into CYCLE8 report or CYCLE9_G*.md.
2. If G1 yields a clean capacity lemma, try to state it without computer search
   (diagram-level).
3. Optional: n=5/n=6 orbit "never-used at max" check for all cell orbits
   (n=6 already: none empty; n=5 check pending if needed).
4. Still out of scope unless requested: full n=8 enum, σ7 full, K9 UNSAT.

# Cycle 9 — working notes (branch cycle8-n7-structure)

Base delivered: Cycle 8 @ `6c5969f` on `cycle8-n7-structure`.
Side study: `f85ca7d` min_det=2 unique to n=7 among n=3..7 complete enums.

## Completed this session (G1–G3)

| pkg | status | evidence | artifact |
|---|---|---|---|
| G1 (2,2) geometry | done | COMPLETE local quads + blockers on 16; capacity probes COMPLETE via b_maxsafe.exe | `CYCLE9_G1_NOTES.md`, `cycle8_g1_result.json`, `results/cycle8_g1_quads_through_22.json` |
| G2 union corridor | done | COMPLETE exact k=12,13,14 on A0∪B0 | `CYCLE9_G2_NOTES.md`, `results/cycle8_g2_bottleneck_12.json` |
| G3 n=8 sample | done-cut | SAMPLE n=2 (hard); rho=1, (2,2) used, d=1 pair | `results/cycle8_g3_n8_sample.json`, `cycle8_g3_n8_sample.cpp` |

### Key Cycle 9 lemmas

1. **τ≥3 on (2,2)**: every n=7 max set blocks each empty (2,2) cell with τ∈{3,4}.
   13-sets with (2,2) exist off the 1-edit neighborhood of the 16.
2. **Union corridor**: size-14 on A0∪B0 = {A0,B0} only; size-12 both-phase growability = 0; restricted path width ≤11; full-board width 12.
3. **min_det=2 only at n=7** among complete enums n=3..7; K_n=2n only at n=7 for n≤8.
4. **n=8 sampling is hard**: 2 sets only in budget — do not overclaim n=8 structure.

### Subagent note

C9a/b/c subagents failed/cancelled; orchestrator ran leftover scripts
(`cycle8_g1_22_geometry.py` after unhashable-key fix; wrote G2 fast; compiled G3 C++).

## Next candidates

1. Derive occupancy / K7=14 from forbidden quads without census (hard).
2. n=8: longer C++ sample run or structured search under forced orbits.
3. n=5 empty-orbit: already none; optional min_det witnesses.
4. Still out of scope: full n=8 enum, σ7 full table, K9 UNSAT without regression tests.

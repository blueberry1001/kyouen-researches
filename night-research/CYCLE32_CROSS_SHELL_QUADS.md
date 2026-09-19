# Cycle 32 — cross-shell forbidden quads (COMPLETE local)

A quad is *cross-shell* if its four points lie in ≥2 distinct D4 orbits
(radial shells about the board center).

| n | #quads | single-orbit | multi-orbit | multi% | by #distinct orbits |
|---:|---:|---:|---:|---:|---|
| 4 | 194 | 72 | 122 | 62.89 | {2: 58, 3: 64} |
| 5 | 826 | 74 | 752 | 91.04 | {2: 148, 3: 404, 4: 200} |
| 6 | 2491 | 213 | 2278 | 91.45 | {2: 438, 3: 1312, 4: 528} |
| 7 | 6364 | 216 | 6148 | 96.61 | {2: 772, 3: 2600, 4: 2776} |
| 8 | 14564 | 424 | 14140 | 97.09 | {2: 1996, 3: 6080, 4: 6064} |

Interpretation: local orbit-circles (single-orbit quads) are the
universal ceiling-3 mechanism. Cross-shell quads are what cut the
naive Σ3 down to K_n and, on n=7 only, reorganize the maximum into
a two-phase crystal with an empty shell (2,2).

Artifacts: `results/cycle32_cross_shell_quads.json`

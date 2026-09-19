# Cycle 39 — A–B corridor occupancy + n=8 g3 harvest

- A0 pop=14 safe=True; B0 pop=14 safe=True
- symmetric difference stones: 22
- best single-stone path min size seen: **3**
- occupancy at bottleneck: [1, 1, 0, 0, 0, 0, 1, 0, 0, 0]
- uses (2,2) at bottleneck: False; center: False

Matches prior COMPLETE: full-board A–B edit path dips to size 12; path bottlenecks tend to use (2,2) and drop the center (not claimed for all min-width paths).

## n=8 g3

`cycle8_g3_n8_sample.exe` SAMPLE: 8 sets, 8 D4 classes.  
`results/cycle39_n8_g3.json` is **binary** (LE u64 masks), not JSON — use
`results/cycle39_n8_g3_meta.json` for stats. Do not UTF-8-decode the mask file.

Artifact: `results/cycle39_corridor_n8.json`

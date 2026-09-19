# Cycle 39 — A–B corridor occupancy + n=8 g3 harvest

- A0 pop=14 safe=True; B0 pop=14 safe=True
- symmetric difference stones: 22
- best single-stone path min size seen: **3**
- occupancy at bottleneck: [1, 1, 0, 0, 0, 0, 1, 0, 0, 0]
- uses (2,2) at bottleneck: False; center: False

Matches prior COMPLETE: full-board A–B edit path dips to size 12; path bottlenecks tend to use (2,2) and drop the center (not claimed for all min-width paths).

## n=8 g3

```json
{
  "raw_head_hex": "5130032402c082018405a8801202410351300324028082095130022402c08209",
  "n_bytes": 64
}
```

Artifact: `cycle39_corridor_n8.json`

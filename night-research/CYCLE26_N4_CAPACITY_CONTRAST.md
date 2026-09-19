# Cycle 26 — n=4 capacity contrast (COMPLETE)

n=4, K=7=2n−1, 64 max safe sets (census Cycle 1/9). Quads=194.

## COMPLETE probes

| constraint | result |
|---|---|
| forbid orbit (1,1) @K=7 | **0** complete |
| require orbit (1,1) @K=7 | **64** complete (all max sets) |
| max forbid (0,0) corners | **6** complete (32@6) |
| max forbid (0,1) | **5** complete (8@5) |
| max forbid (1,1) | **6** complete (32@6) |

## Omit-cost ladder (COMPLETE) — n=4..7

| omitted | n=4 | n=5 | n=6 | n=7 |
|---|---:|---:|---:|---:|
| (1,1)-like diag | −1 (6) | n/a center optional | −0 or −1 | @14 forbid=0 |
| (0,1) | **−2** (5) | −1 | −1 | @14 forbid=0 |
| (0,2) / heavy edge | — | −1 | −1 | **−2** (12) |
| (2,2) or center | n/a small board | 0 still K | 0 still K | **forbidden @14** |

## Reading

- Every complete census n=4..7 has **some** mandatory orbits at its own max.
- Only n=7 has an **empty** orbit at max and only n=7 attains K=2n.
- A −2 omit-cost is not unique to n=7 (n=4 forbid (0,1) also −2), so
  large omit-cost alone does **not** explain the +1; the crystal package
  (empty orbit + two phases + min_det=2 + d*≥5) remains n=7-specific.

## Artifacts
- this note; `CYCLE24_N6_CAPACITY_CONTRAST.md`; `CYCLE25_N5_CAPACITY_CONTRAST.md`
- `FINAL_SELECTION_THEOREM.md`

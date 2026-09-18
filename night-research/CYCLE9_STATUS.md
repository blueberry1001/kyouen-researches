# Cycle 9 — working notes (branch cycle8-n7-structure)

Base: Cycle 8 delivered `6c5969f`. Side: `f85ca7d` min_det=2 unique to n=7.
HEAD after H: `8cc286b`.

## Packages

| pkg | status | evidence | artifact |
|---|---|---|---|
| G1 (2,2) geometry | done | COMPLETE local; τ∈{3,4} on 16×4 | `CYCLE9_G1_NOTES.md` |
| G2 union corridor | done | COMPLETE k=12,13,14 on A0∪B0; path-witness bottlenecks use (2,2) | `CYCLE9_G2_NOTES.md` |
| G3 random n=8 | cut | 3 sets; not informative alone | `results/cycle8_g3_n8_sample.json` |
| H occ n=8 | done | SAMPLE 53 sets / 45 occupancy patterns via `cycle8_b_maxsafe.exe occ` | `results/cycle8_h_n8_sample.json` |
| K9 128-bit | design only | regression + protocol; **no UNSAT** | `CYCLE9H_K9_128BIT_DESIGN.md` |

## Lemmas promoted

1. Every n=7 max set blocks each empty (2,2) with **τ≥3** (hist {3:40,4:24}).
2. On A0∪B0, size-14 safe sets are exactly {A0,B0}; |core|=9 ⇒ grow-both=0 for k≥10;
   edit-path bottleneck 12; restricted width 11.
3. min_det=2 only at n=7 among complete enums n=3..7; K_n=2n only n=7 (n≤8).
4. n=8 SAMPLE: occupancy heterogeneous (45/53); (2,2) often used — n=7 crystal does not transfer.
5. Explicit A–B path dips use (2,2) and drop center (path-witness, not universal).

## Next

- Which n=7 occupancy vectors of sum 14 admit *any* safe set? (beyond A/B)
- Longer n=8 harvest if needed; still no full n=8 enum.
- K9: implement Mask128 + pass n=6/7 regression before any UNSAT.

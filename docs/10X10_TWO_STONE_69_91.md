# 10×10 two-stone root 69,91: child classification and the four TableFull states

This experiment continues the two-stone frontier opened by
`docs/10X10_THREE_STONE_SUBSETS.md`. Coordinates use `id = y * 10 + x`; outcomes
are from the player to move.

## Result: the parent 69,91 is a WIN

All 98 three-stone children are now resolved by exact search. The four former
`TABLE_FULL` states were re-run with expanded memo profiles (compile-time
`EXPANDED_MEMO` variants, search logic byte-identical to the standard solver):

```text
WIN  = 95
LOSS =  3  (1,39,90; 7,8,30; 8,17,30)
TABLE_FULL = 0
```

A parent is a WIN iff it has at least one LOSS child. Three of the four
resolved states are LOSS, so **`69,91` is a WIN** — the previous "cannot be
proven LOSS unless every child is WIN" caveat is resolved in the opposite
direction: LOSS children exist, and they decide the parent immediately.

Machine-readable results:
[`results/10x10/two-stone-69-91-child-proof.csv`](../results/10x10/two-stone-69-91-child-proof.csv).
Expanded-memo run details (per-bucket usage):
[`results/10x10/69-91-expanded-memo.csv`](../results/10x10/69-91-expanded-memo.csv).

## The four former TABLE_FULL children, resolved

| child | outcome | visited | maxdepth | memo | wall time | profile |
|---|---:|---:|---:|---:|---:|---|
| `1,39,80` | WIN | 603,662,904 | 19 | 602,769,989 | 1802 s | v3 |
| `1,39,90` | LOSS | 827,783,863 | 19 | 826,696,649 | 2462 s | v4 |
| `7,8,30` | LOSS | 826,399,468 | 19 | 824,861,983 | 2474 s | v4 |
| `8,17,30` | LOSS | 819,209,782 | 19 | 817,829,824 | 2411 s | v4 |

Profiles (per-layer power, all others at base):

| profile | d11 | d12a | d12b | d13a | d14a | d15 | d16 | d17 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| base | 26 | 27 | 24 | 27 | 27 | 26 | 23 | 19 |
| v3 | 27 | 28 | 25 | 28 | 28 | 27 | 24 | 19 |
| v4 | 27 | 28 | 25 | **29** | 28 | 27 | 24 | **21** |

## Bucket usage at the resolution point (max_used = 2^power * 0.9)

| child | outcome | d12a | d13a | d14a | d15 | d16 | d17 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `1,39,80` | WIN (v3) | 127.9M | 175.9M | 152.0M | 61.5M | 9.2M | 424,948 |
| `1,39,90` | LOSS (v4) | 171.0M | 240.7M | 214.5M | 89.5M | 13.8M | 645,017 |
| `7,8,30` | LOSS (v4) | 181.2M | 240.8M | 200.3M | 77.6M | 11.0M | 480,771 |
| `8,17,30` | LOSS (v4) | 175.9M | 238.0M | 203.1M | 81.1M | 12.0M | 550,707 |

## The minimal capacities that would have sufficed

The v4 runs show that the *true* requirement is a chain, not a single layer:

- `d13a` is the sharpest constraint: `7,8,30` uses 240,796,468 entries =
  **99.7% of the 2^28 * 0.9 = 241.6M cap**. In theory 2^28 suffices, but the
  margin is 0.3% — 2^29 (v4) is the defensible choice. Under v3 (d13a = 2^28)
  these states died on `d17` first, at d13a ≈ 235M.
- `d16` usage 13.8M = 91% of the 2^24 cap — 2^24 was necessary (2^23 holds
  only 7.55M), and just barely sufficient.
- `d17` (2^19, 471,859) was the immediate fill trigger for both `1,39,90` and
  `7,8,30` under v3; max usage 645K fits in 2^20 (943,718), so **2^20 would
  have been enough**; v4's 2^21 is generous.
- `d11`, `d12a`, `d14a`, `d15` were saturated under base/v1 profiles and need
  the v3/v4 powers (2^27 / 2^28 / 2^28 / 2^27).

So the minimal coherent profile is v3 plus d17 = 2^20 (d13a stays 2^28 at
99.7% utilization — technically sufficient, practically too close to call).

## Why exactly these four are hard — resolved

The decisive observations from the expanded runs:

1. **The "hardness" is the tail of a size distribution, not a structural
   singularity.** All four states are simply large searches: their memo
   tables reach 603M–827M entries, above the total capacity the base profile
   can hold (~475M–518M). They saturate whatever layer is *next* in line, in
   order: base → d13a/d13b/d16; v1 → d12a/d15/d11; v3 → d17 (and d13a at 99%);
   v4 → resolves.

2. **The failure trigger moves with the capacity.** Each expansion pushed the
   bottleneck to the next layer:
   - base: `1,39,80`/`1,39,90` die on `d16` (7.55M cap); `7,8,30`/`8,17,30`
     die on `d13b` (30.2M).
   - v1 (+d13a/d14a/d16): all four now die on `d12a` (120.8M) or `d15` (60.4M).
   - v3 (+d11/d12a/d12b/d15): `1,39,80` resolves WIN; the three LOSS states
     die on `d17` (471,859) with d13a at ~235M.
   - v4 (+d13a/d17): all resolve.
   This is the classic boundary effect of fixed-capacity hash tables: the
   search is capacity-bound, not rule-bound. No state needed a rule change or
   a different algorithm — every one resolved once the tables were large
   enough.

3. **Three of the four are LOSS.** A LOSS state must exhaust its whole tree
   before it can be proven; WIN states can stop at the first winning line.
   That is why these three are so much heavier than the largest WIN
   (`8,30,72`, 518,980,323 visited): proof of LOSS requires visiting every
   node, ~827M here.

4. **The razor-thin line is confirmed and quantified.** The old doc noted
   `8,30,72` (WIN) ends at d13b = 99.5%. Now `7,8,30` (LOSS) needs d13a =
   240.8M vs a 241.6M cap — 0.3% from re-failing. The WIN/LOSS boundary is
   close in *size*, but the outcomes themselves are clean: WIN=95, LOSS=3.

5. **The three LOSS children are in two distinct D4 orbits** — `1,39,90` vs
   `7,8,30`/`8,17,30` — with the same legal-move count (98) as everything
   else, so orbit and geometry still do not discriminate. Their sibling
   `1,39,80` in the same orbit is a WIN. The distinction is search size, which
   is an emergent property, not a local invariant.

## Methodology note

- All expanded runs used the standard solver (`kyouen-local-handoff/solver.cpp`)
  recompiled with `-DEXPANDED_MEMO3` / `-DEXPANDED_MEMO4` and the profile
  tables above; no search-logic changes (verified: known WIN `8,30,72` and
  `8,10,30` reproduce identical visited/memo counts).
- Runs: single- or dual-process on the 41 GB machine, shrink=0, load=90,
  wall times 1802–2474 s each, peak RSS ≈ 6.5 GB (v3) / 7.8 GB (v4).
- `1,39,90` under v3 hit `std::bad_alloc` only when launched in parallel with
  another expanded process (free RAM ~5.6 GB); re-run alone it completed.

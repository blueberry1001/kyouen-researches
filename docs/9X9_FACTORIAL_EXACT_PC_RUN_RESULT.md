# 9x9 pair-component factorial exact result

最終更新: 2026-09-15
branch: `factorial-exact-pc-run`
base commit: `4152c1a0a74f17ecd89a3085cfdf9afc19fabaa8`
freeze commit: `9ebc79ea1e8c2b35fe8d76c397491cf984f216e2`
selector seed: `kyouen-9x9-pair-components-factorial-v1-2026-09-05`

## Holdout

- population: 5113
- excluded_unique: 1089 (pilot 64, confirmatory 1024 regenerated, first12, smoke)
- eligible: 4024
- E_at_O0: eligible 4020, selected 1024
- O_at_E0: eligible 715, selected 715 (census)
- E_at_O1: eligible 3944, selected 1024
- O_at_E1: eligible 639, selected 639 (census)
- unique_parents_to_solve: 2592
- E0∩E1 intersection_n: 254

## Exact solve

- solver: `kyouen-solver-9-compare` Release
- memo_power: 28
- shard_size: 12
- max_jobs: 6
- completed: 4/4 comparisons, 3403/3403 rows
- failed shards: 0
- memo_over: 0
- memo_power=29 escalations: 0
- elapsed_sec: 323.8

## Primary Holm family (pre-registered, unchanged)

| comparison | n | discordant | baseline_only | added_only | raw p | Holm p | reject | direction |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| E_at_O0 | 1024 | 463 | 210 | 253 | 0.05083205 | 0.2033282 | 0 | added_better |
| O_at_E0 | 715 | 317 | 148 | 169 | 0.2612727 | 0.7188043 | 0 | added_better |
| E_at_O1 | 1024 | 452 | 213 | 239 | 0.2396014 | 0.7188043 | 0 | added_better |
| O_at_E1 | 639 | 285 | 144 | 141 | 0.9057226 | 0.9057226 | 0 | baseline_better |

No comparison rejects under Holm FWER 0.05.

## Descriptive rates

| comparison | baseline_loss_rate | added_loss_rate | delta_loss_rate | change_rate |
|---|---:|---:|---:|---:|
| E_at_O0 | 0.475586 | 0.517578 | +0.041992 | 0.452148 |
| O_at_E0 | 0.530070 | 0.559441 | +0.029371 | 0.443357 |
| E_at_O1 | 0.488281 | 0.513672 | +0.025391 | 0.441406 |
| O_at_E1 | 0.544601 | 0.539906 | -0.004695 | 0.446009 |

## O census finite-population exact effects

These are exact descriptive quantities on the pre-fixed unobserved eligible
finite populations, not sampling estimates. Holm p-values above remain the
pre-registered tests and are not to be read as census sampling error.

- O_at_E0 n=715: ΔLOSS = +0.029371, change_rate = 0.443357
- O_at_E1 n=639: ΔLOSS = -0.004695, change_rate = 0.446009

## Secondary interaction (descriptive only)

Target: sample_E_at_O0 ∩ sample_E_at_O1, n=254.
I = y11 - y01 - y10 + y00 with LOSS=1, WIN=0.

- I histogram: -2:0, -1:3, 0:251, 1:0, 2:0
- I<0: 3, I=0: 251, I>0: 0, |I|=2: 0
- mean(I) = -0.011811
- median(I) = 0
- mean E effect at O=0 = -0.011811
- mean E effect at O=1 = -0.023622
- LOSS rates: T 0.472441, TE 0.460630, TO 0.476378, raw 0.452756

No new p-values. Holm family unchanged.

## Full O census reconstruction (secondary audit)

Design sizes O_at_E0=801 and O_at_E1=702 include already-observed parents.
Historical T-vs-raw outcome files do not supply the required TO/TE child
outcomes for those excluded parents.

- O_at_E0 excluded 86, reconstructable 0, missing child outcomes 86
- O_at_E1 excluded 63, reconstructable 0, missing child outcomes 63
- full 801/702 census: not reconstructable from saved historical outcomes

Missing-state lists are in `results/9x9/factorial/o-full-census-reconstruction-audit.json`.
Primary results are unchanged.

## Artifact SHA256

- holdout: `5e11b3bd514919c87e2702f60a8e21df026b45ea60fc9044cfa8335da62517fa`
- E_at_O0 merged: `8a77c6e875a39bae2421cc4b56c02214271c19f8698e51b5b5921186cf1afff6`
- O_at_E0 merged: `1be8157e9a356992297cc9d37d791a9cf0f7d6fa030327792e90b5c65b1145c0`
- E_at_O1 merged: `c0ef1d5f46ce3c8f4dc8e5e3962e3b87e23893531d5b467785697a967e987f28`
- O_at_E1 merged: `9f1841635366208ffeb42951fd92eb613875b7bb8526fdb106a98c75515d8ecd`
- primary-summary: `9d6309d21678e4ce0ef9b27be8ebcc04f0ed52dc05f0e6917186104ab45d3e07`
- secondary-interaction: `a14359c62e4af2aaecb5bbe555386f7db84771875ac3f2848b00492b97eaa434`
- o-census table: `ac77321d05e42cd91f8a1b9bfd5631e491dc4e59775478419f8cf5e3bcd6f8a9`

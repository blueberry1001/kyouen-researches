# 10x10 cache-aware below-root ordering — capacity-rescued rerun result

Date: 2026-09-08
Branch: `preregister-10x10-cache-aware-below-root-capacity-rerun`
Prereg: `b7a6649` (text) + `45af02f` (machine manifest), base C2 receipt
`5b50158`. Result computed only after verifier PASS.

## Endpoint: PASS (24/24 valid, fresh)

Frozen primary criterion, both required:

1. median R = **1.170872 > 1**
2. improved (A smaller visited) = **12/12 >= 7/12**

with `R = visited_B / visited_A` per parent, denominator frozen at 12.

## Completion

- 24/24 fresh processes completed; no TableFull, timeout, crash, or parse
  failure; verifier PASS (`verifier.log`), supplemental output audit PASS
  (`output_audit.log`).
- Parent `1,12,80` (rank 7) — the pair that made historical C2 INCOMPLETE by
  hitting the old d16 / d13 90% ceilings — completed exactly under the
  enlarged d12-16 capacities in both conditions:
  - A (cache-aware): LOSS, visited 555,114,540, memo 554,115,735
  - B (cache-blind): LOSS, visited 669,211,681, memo 668,210,054
  - R = 1.205538, consistent with the other 11 parents.

## Primary table (R = visited_B / visited_A)

| rank | parent | visited A | visited B | R |
|---|---|---|---|---|
| 1 | 12,21,58 | 41,253,019 | 48,565,266 | 1.177254 |
| 2 | 0,19,95 | 40,334,044 | 48,122,261 | 1.193093 |
| 3 | 2,11,61 | 27,789,159 | 32,749,276 | 1.178491 |
| 4 | 1,27,61 | 16,020,139 | 18,775,664 | 1.172004 |
| 5 | 1,68,74 | 14,174,908 | 16,534,371 | 1.166453 |
| 6 | 0,7,67 | 33,663,004 | 39,772,866 | 1.181501 |
| 7 | 1,12,80 | 555,114,540 | 669,211,681 | 1.205538 |
| 8 | 2,43,60 | 10,890,815 | 12,698,786 | 1.166009 |
| 9 | 23,37,45 | 11,864,773 | 13,822,908 | 1.165038 |
| 10 | 1,6,51 | 10,931,142 | 12,786,596 | 1.169740 |
| 11 | 12,13,67 | 6,524,427 | 7,563,460 | 1.159253 |
| 12 | 12,25,71 | 13,528,345 | 15,785,216 | 1.166825 |

- median R = 1.170872
- geometric mean R = 1.175032
- arithmetic mean R = 1.175100
- aggregate visited ratio = 1.197292 (936,388,351 / 782,088,315)
- improved/tie/worse = 12 / 0 / 0
- exact paired sign test (n_eff = 12): two-sided p = 0.000488,
  one-sided (A better) p = 0.000244

## Secondary highlights

- Solver seconds: A 2874.6, B 3449.9 (ratio 1.2001); wall: 2739.1 vs 3262.5
  (1.1911). The runtime ratio slightly exceeds the visited ratio on this
  cohort because `1,12,80` dominates total time.
- Final memo entries: A 780,360,682; B 934,657,582 (more visited states
  fill proportionally more memo slots).
- Mechanism: A prefetch_hit 0.2386, cached-omission 0.3497,
  cached-LOSS WIN-shortcut 0.5301; B same operations with 0.2818 / 0.4063 /
  0.5104. B's larger subtree visits strictly more nodes at depths 8-16;
  depth deltas confirm the gap accumulates from depth 8 upward (see
  analysis.md).
- A ordering-change counters: first-child changes on ~21-22% of nonterminal
  nodes; full-order changes ~33%; B exactly 0 (blind sort active), verified.

## Capacity check (rerun motivation)

Worst-of-A/B per-depth usage vs the preregistered enlarged 90% ceilings:

| depth | used (max) | ceiling | occupancy |
|---|---|---|---|
| 12 | 209,461,417 | 271,790,899 | 77.1% |
| 13 | 275,711,734 | 301,989,888 | 91.3% |
| 14 | 222,350,519 | 271,790,899 | 81.8% |
| 15 | 82,233,443 | 120,795,955 | 68.1% |
| 16 | 11,184,988 | 15,099,494 | 74.1% |

No table crossed 90%; `1,12,80` (B) reached 91.3% of the doubled d13
ceiling — the single largest headroom consumer — but completed exactly.
The one-bit enlargement was necessary and sufficient for this cohort.

## Replication context (descriptive only)

- C1 (original 12 parents, `d9b9a0f`): 12/12 improved, median R = 1.162010.
- This capacity rerun (independently frozen extended ranks 13-24): 12/12
  improved, median R = 1.170872, range 1.1593-1.2055.
- Pooled C1 + rerun (n = 24): median 1.166895, gmean 1.170225.
- The 11 parents that had completed in historical C2 reproduce their C2
  R values exactly (deterministic exact search; capacity change affects
  only saturated-table behavior). Historical C2 remains INCOMPLETE as an
  endpoint; this rerun is the completed confirmation on this cohort.

## Provenance

- Solver binary `tmp-kb/order_ab_native`
  SHA256 `a98ca5e41d67dfa988deaf491ff948cb4a82ae8596af8aea83376b9f259ebfd1`
  (built g++ (Ubuntu 13.3.0) -O2 -std=c++20, sources digest
  `3ab6c565bbfdae9e4bda2ca7eb00e20be54d9b4315616221d39389326c8e16a8`).
- One binary for A and B; conditions differ only by the runtime
  `--below-root-order` switch.
- Capacity change (only): d12a 27->28, d12b 24->25, d13a 27->28,
  d13b 25->26, d14a 27->28, d14b 24->25, d15 26->27, d16 23->24; d9-11/17,
  shrink=0, load=90, all semantics unchanged.
- Pre-run regression on light/medium/heavy successful C2 parents
  (12,13,67 / 1,27,61 / 0,7,67) reproduced the old-C2 outcome, visited,
  memo, maxdepth, root unique/entered/first/witness exactly in both A and B;
  B ordering-change counters 0; memo reuse alive; instrumentation
  identities held.
- Execution manifest frozen and committed before the first cohort run
  (`execution_manifest.json` includes binary/source/tool hashes, compiler,
  flags, prereg SHAs, cohort, and counterbalanced run order).
- Old C2 raw output was never an endpoint input; the audit confirmed no
  byte-identical raw rows were mixed in.

## Interpretation

Under a capacity regime that can represent the heavy-tail parent, the
cache-aware below-root ordering reduces exact visited work on 12/12
independently frozen parents, replicating C1's direction with a slightly
larger median effect (1.171 vs 1.162) and one heavy parent (1,12,80, R =
1.206) whose pair could never be observed before. This is a completed
confirmatory PASS; no reduced-denominator analysis was used anywhere.

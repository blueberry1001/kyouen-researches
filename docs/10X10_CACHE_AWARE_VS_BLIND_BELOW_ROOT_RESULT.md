# 10x10 cache-aware vs cache-blind below-root ordering — result

Prereg: `docs/10X10_CACHE_AWARE_VS_BLIND_BELOW_ROOT_PREREG.md`
Branch: `preregister-10x10-cache-aware-vs-blind-below-root`
Start SHA: `21e7bfe` (= stated prereg head; base `80b734b` confirmed).
End SHA: `54af4a5` (4 commits on top of prereg head; full: `54af4a563fb3b88b3873c16921dd4066a079f69c`).

One binary (`tmp-kb/order_ab_native`, `g++ -O2 -std=c++20`, Ubuntu 13.3.0),
runtime switch `--below-root-order cache-aware|cache-blind` (default
`cache-aware`). Diff touches only `scripts/probe_parts/`:

- `..._resume_2.inc`: new `kFrozenRootDepth=3`, `below_root_blind_` flag +
  setter; `order_children` gains one branch — blind applies **only** at
  `depth > 3` and sorts by `(legal_move_count, canonical key)`; every other
  depth (including root depth 3) keeps the native
  `(cached LOSS < uncached < cached WIN, count, key)` comparator.
- `..._resume_4.inc`: flag parsing/validation + setter call + stderr echo.

Untouched by construction (diff-verified): child generation, dedup,
prefetch (`Child.cached` population), cached-outcome consumption without
recursion, cached-LOSS WIN shortcut, memo put/get, root ordering, game
rules, instrumentation schema. No new counters were added (frozen schema);
in B mode the existing ordering-change counters read exactly 0, which
proves the cached key is ignored in the sort.

## 2. Regression (pre-freeze)

`scripts/test_order_ab_regression.py`: PASS, deterministic across 2 runs.
A (default and explicit) == frozen `parent_bench_native` on
`13,52,57,76` / `4,24,26,67` / `14,64,74` for outcome, visited, memo,
maxdepth, root unique/entered/first/witness. B: outcome == A, root diag ==
A, memo reuse alive (1.1–3.6M cached evals, 0.5–1.7M shortcuts),
ordering-change counters 0.

## 3. Execution

24/24 runs complete, 12/12 parents x A/B, all outcome WIN, 0
failures/timeouts. Fresh process per parent-condition, serial,
counterbalanced order (even parent index A-first, odd B-first).
Raw committed before verification/analysis (commit `9949873`).

## 4. Verification

`scripts/verify_10x10_cache_aware_vs_blind.py`: PASS.
A parity vs frozen memo-instrumentation cohort 12/12 (outcome, visited,
memo, maxdepth, root unique/entered/first/witness). A/B outcome agreement
12/12, all matching frozen outcomes. Root diagnostics identical 12/12.
Counter identities hold on all 384 depth rows. B ordering-change
counters 0 everywhere.

## 5. Primary endpoint: R = visited_blind / visited_aware

| parent | visited A | visited B | R |
|---|---|---|---|
| 0,11,35 | 85311102 | 101452455 | 1.189206 |
| 11,38,44 | 17051435 | 20031667 | 1.174779 |
| 11,78,87 | 9928498 | 11509441 | 1.159233 |
| 12,24,68 | 11677827 | 13627620 | 1.166965 |
| 12,32,55 | 7106990 | 8215176 | 1.155929 |
| 13,52,57 | 11651703 | 13655602 | 1.171983 |
| 14,64,74 | 4342654 | 4988016 | 1.148610 |
| 23,44,45 | 7188933 | 8356037 | 1.162347 |
| 3,47,63 | 5711578 | 6586155 | 1.153124 |
| 3,53,84 | 7184954 | 8346560 | 1.161672 |
| 4,24,26 | 51289701 | 60604679 | 1.181615 |
| 4,42,54 | 6977109 | 8096702 | 1.160467 |

- median R = 1.162010, gmean R = 1.165438, mean R = 1.165494
- aggregate = 265470110/225422484 = 1.177656
- improved(A better) = 12, tie = 0, worse = 0
- exact paired sign test: two-sided p = 0.000488, one-sided p = 0.000244
- **Prereg criterion (median > 1 and >= 7/12): PASS** (case C1).

## 6. Secondary endpoints

- solver seconds A=698.7 B=877.0 (ratio 1.255); wall A=685.9 B=857.8
  (ratio 1.251). Timing is secondary (serial runs, exact visited primary).
- final memo A=224648067 B=264695403 (B explores ~18% more, stores more).
- maxdepth identical per parent (17–19).
- prefetch hit rate: A 23.79% vs B 27.91%. B visits more nodes, so more
  memo entries exist to hit — availability is not the bottleneck.
- cached omission fraction: A 34.94% vs B 40.29% (B consumes more cached
  evals in absolute terms: 179.1M vs 121.1M) yet still visits more.
- cached-LOSS WIN shortcut rate: A 52.73% vs B 50.67% of solved WIN nodes.
  B converts its (larger) hit pool into immediate shortcuts *worse*.
- puts == visited exactly in both (225422484 / 265470110).

## 7. Depth decomposition (B − A, all parents)

| depth | visited Δ | recursive Δ | cached Δ | shortcut Δ |
|---|---|---|---|---|
| 3–7 | 0 | 0 | 0 | 0 |
| 8 | 0 | +136748 | +1380452 | −22734 |
| 9 | +136748 | +1204336 | +2394706 | −131882 |
| 10 | +1204336 | +4830925 | +7014505 | −112773 |
| 11 | +4830925 | +10484081 | +12873423 | +217519 |
| 12 | +10484081 | +13069948 | +16688163 | +1599609 |
| 13 | +13069948 | +8248195 | +11769007 | +3880522 |
| 14 | +8248195 | +1928896 | +5105237 | +3237881 |
| 15 | +1928896 | +141149 | +806736 | +658270 |
| 16–19 | small tail | — | — | — |

d3–d7 deltas are exactly 0: root region search is bit-identical (fresh
memo ⇒ aware == blind until hits appear). Divergence starts at d8 as
extra recursive + cached consumption per node (worse order ⇒ later LOSS
discovery ⇒ more children consumed), cascading into extra visits from d9
on, peaking at d12–13, fading by d16+. Early shortcut Δ is *negative*
(d8–d10): B has cached LOSS available but reaches it later.

## 8. Causal interpretation

C1: cache-aware below-root ordering has independent causal work value on
this fixed cohort — ~15–19% visited reduction per parent, 12/12
consistent (range 1.149–1.189), beyond what memo reuse alone provides.

M1/M3 division of labor: M1 (reuse/omission/shortcut) is the larger
mechanism (~35% omission, ~53% shortcuts) and stays fully active in B;
M3 (ordering) independently saves ~16% on top. B's higher raw hit rate
with lower shortcut conversion shows ordering determines how well reuse
opportunities are *exploited*, not just their availability.

## 9. Risks / limits

- Same 12 parents as all prior mechanism work: no generalization claim.
  A new frozen-cohort confirmatory is required (and now justified).
- Wall-clock ratios are secondary (serial, shared machine).
- 4-stone regression states order even their root blindly in B mode;
  cohort roots (depth 3) are always native — verifier pins this.

## 10. Next step

Per prereg C1: run a new-cohort confirmation (fresh frozen parents,
same A/B protocol, parent-level visited endpoint) before any
generalization claim; then investigate cheaper ways to preserve
cached-LOSS-first ordering.

## 11. Provenance

Commits: implementation+tooling, manifest freeze, raw 24/24, this report.
`main` untouched (verified via `git status` on main worktree / merge-base).
Push receipt: `54af4a5` pushed to `origin/preregister-10x10-cache-aware-vs-blind-below-root`; this receipt fix follows as final commit.

# V2 10k parent-solver benchmark — final report

## Verdict

**Treatment B loses on the primary endpoint.** 10k memo root ordering does
not reduce native parent-solver search work on the frozen V2 cohort:

- median work ratio (B/A) = **1.84** (criterion: < 1.0) — FAIL
- improved parents = **2/12** (criterion: ≥ 7) — FAIL
- geometric mean = 1.89, arithmetic mean = 2.70, aggregate = 1.49
  (225.4M → 336.3M visited)

Per preregistration interpretation this is the **"B loses despite
reconstructed P5 winning"** branch: shared-memo interactions and the
native legal-count baseline explain the discrepancy. The earlier
file-order desk result (median 0.85) must **not** be presented as solver
speedup. It remains valid only for the child-independent fresh-process
experiment it was measured in.

## Why it loses (mechanism, post-hoc description — no rule change)

Median **exact-only** visited ratio (B_exact/A_exact, probe cost excluded)
is **1.70**: even ignoring probe cost, solving the parent with the
memo-ordered root visits more nodes than native order. Evaluating the
small-memo ("most promising") child first appears to front-load search
into subtrees whose memo entries then steer the shared table away from
the native order's cheaper proof path. The native baseline
(cached-class → legal_move_count → canonical key) is itself a strong
ordering: most A solves enter exactly 1 root child (10/12 parents).

## Per-parent work ratios (B_work / A_work, visited)

| parent | A_visited | B_work | ratio | A/B outcome | P5 desk ratio |
|---|---|---|---|---|---|
| 0,11,35 | 85,311,102 | 45,205,249 | 0.53 | WIN/WIN | 0.92 |
| 13,52,57 | 11,651,703 | 10,628,730 | 0.91 | WIN/WIN | 1.30 |
| 4,24,26 | 51,289,701 | 58,199,684 | 1.13 | WIN/WIN | 0.56 |
| 12,24,68 | 11,677,827 | 14,229,933 | 1.22 | WIN/WIN | 0.97 |
| 11,38,44 | 17,051,435 | 21,823,832 | 1.28 | WIN/WIN | 0.65 |
| 23,44,45 | 7,188,933 | 12,443,196 | 1.73 | WIN/WIN | 1.62 |
| 3,47,63 | 5,711,578 | 11,149,826 | 1.95 | WIN/WIN | 0.75 |
| 3,53,84 | 7,184,954 | 15,702,401 | 2.19 | WIN/WIN | 0.21 |
| 11,78,87 | 9,928,498 | 23,460,280 | 2.36 | WIN/WIN | 1.76 |
| 4,42,54 | 6,977,109 | 17,662,420 | 2.53 | WIN/WIN | 0.37 |
| 14,64,74 | 4,342,654 | 19,008,565 | 4.38 | WIN/WIN | 2.56 |
| 12,32,55 | 7,106,990 | 86,793,418 | 12.21 | WIN/WIN | 0.77 |

P5 desk prediction and parent-level measurement disagree in direction on
7 parents (e.g. 3,53,84: 0.21 → 2.19; 4,42,54: 0.37 → 2.53). The desk
model's two errors compound: (a) file order understates the native
baseline, (b) fresh-process child sums ignore shared-memo interference.

## Secondary endpoints

- median solver-seconds ratio: 4.38 (visited ratio 1.84 amplified by memo
  pressure — B memo tables fill with less reusable entries)
- median wall-clock ratio: 1.55 (serial exacts; probe stage parallelized
  over 12 workers; no competing heavy processes)
- A/B outcome agreement: 12/12 (all WIN); parent outcomes consistent with
  child LOSS labels (every parent has ≥1 LOSS child)
- root child sets: A.unique == B.unique on all parents (incl. 11,78,87
  with 97 enumerated → 53 canonical children; symmetry dedup identical)
- fresh processes: 24 distinct solver pids; probes 1136 fresh processes
- fresh-probe determinism: re-run probes bit-identical to the frozen 10k
  CSV (1136/1136 memo, outcome, visited) — ordering provenance solid
- all probes PROBE (10000 visits); B_work = 10000·n + B_exact throughout

## Provenance (digests)

- cohort task_set_sha256: `aeccb666…bc7`, 12 parents / 1136 tasks
- probe binary `15d805ea…` (frozen), probe sources `9b6f227f…`
- bench binary `e0de57b3…` (g++ -O2 -std=c++20, WSL g++ 13.3, reproducible),
  bench sources `165ba068…` (root-order patch only; diff vs base reviewed)
- protocol: `results/10x10/parent-benchmark/protocol.json` (frozen pre-data)

## Reproduction

```
git checkout preregister-10x10-v2-10k-parent-benchmark
# regression (needs WSL/Linux for the ELF binaries):
wsl python3 scripts/test_parent_bench_regression.py
# full benchmark (probes parallel, exacts serial, counterbalanced):
wsl python3 scripts/run_parent_benchmark.py --workers 12
wsl python3 scripts/verify_parent_benchmark.py
wsl python3 scripts/analyze_parent_benchmark.py
```

## Risks / limits

- Exact parent solves are single-threaded solver runs; seconds/wall
  ratios carry OS noise — primary visited endpoint does not.
- Bench binary built with a different compiler than the frozen binary
  (g++ 13 vs unknown); regression guard 1 (outcome+visited+memo
  equality, 2 states) bounds this risk.
- `.inc` worktree files carry CRLF (git-clean via autocrlf); digests are
  computed over worktree bytes consistently at freeze and verify time.
- 11,78,87 canonical multiplicity (97→53) is handled by first-occurrence
  dedup, identical in A/B; order-file coverage asserted per run.

## Next: C-K10-asc blind validation (design, not executed)

P8's staged result (median ≈ 0.32) was post-hoc on V2 outcomes and is
additionally contradicted as a mechanism story by this benchmark (root
memo-ordering hurts under shared memo). If pursued, it needs a **new
cohort**: freeze direction (ascending legal-move count), K=10, selection
and ordering rule, and success criteria before any probe/exact outcome
is inspected there — plus a native parent-solve endpoint, not a desk
reconstruction. Given this benchmark's outcome, that experiment is
lower priority than investigating orderings that cooperate with (rather
than fight) the shared memo.

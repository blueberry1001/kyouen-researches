---
feature: night-cycle4-exact-structure
status: delivered
updated: 2026-09-17
branch: replicate-8x8-o-stratum
commits: uncommitted-additive-on-db50e40  # worktree add blocked; artifacts not yet committed
---

# Night Cycle 4 — Exact structure toward a non-trivial kyouen conclusion

## Report

**What was built** — Cycle 4 produced a complete first-move density table
(n=9 marked complete 81/81), an exact safe-set outcome enumerator, full depth
profiles and first-move reply mobility for n=2..5, an F/S invariant audit, and
a non-trivial conclusion note. Independent Rust `classify-first` matched the
Python enumerator on n=3,4,5.

**Verification** — `exact_structure_cycle4.py 2 3 4 5` reproduced forbidden
counts (1/14/194/826) and certificate winners; mobility densities matched
published first-move counts (4/4, 9/9, 0/16, 9/25); rust classify-first agreed
cell-for-cell on n=5 WIN set. Full command evidence in
`night-research/CYCLE4_EXACT_STRUCTURE.md`.

**Journey log** — (1) fresh `git worktree add` blocked by shared-registry
guard; continued additively on `replicate-8x8-o-stratum` @ `db50e40`.
(2) naive peak-of-loss-rate hit trivial layers; switched to full profiles +
interior peaks. (3) exact n=4/n=5 profiles are multi-modal — do not overclaim
P9b mid-depth peak as a universal exact law. (4) GitHub origin still lacks
local Cycle 3 commit `db50e40`. (5) Review C1: k=1 loss_rate on n=5 is
**winning** first-move density (player-to-move labeling) — prose corrected.
(6) Review N1: aggregate JSON regenerated for n=2..5 after a stale single-n
overwrite. Do not commit unless user/orchestrator asks; artifacts untracked.

## [S1] Problem

The repo already has a computer-assisted winner classification for kyouen on
n×n boards for 1 ≤ n ≤ 9 (and 10×10 empty board is second-player win), plus
Cycle 3’s complete 9×9 first-move classification. GitHub `origin` still lags
this local result. Prior night cycles rejected several simple laws (parity,
monotonicity, terminal-size locking, embedding transfer, local-geometry
predictors). What is still missing is a **non-trivial, evidence-backed
structural conclusion** that (a) uses the newest exact data, (b) adds new
exact small-board structure, and (c) states precisely what any future general
law must explain.

## [S2] Design

### Decided research direction (user: “なんでもいい” / overnight autonomous)

Primary question: **What does exact small-board game structure force, once
9×9 first moves are known to be universally winning?**

Work package:

1. **Hygiene** — mark n=9 first-move density complete (81/81) using Cycle 3
   artifacts; note GitHub origin still lacks commit `db50e40`.
2. **Exact shallow-depth profile (n ≤ 5, extend to 6 if cheap)** — enumerate
   every safe stone-set, compute normal-play outcome, record
   `LOSS_rate[k] = (# LOSS safe k-sets) / (# safe k-sets)`.
   This upgrades P9b (sample-based “peak depth tracks empty-board winner”)
   to exact truth on boards where full enumeration is feasible.
3. **Exact first-move reply mobility (n ≤ 5)** — for every cell, record
   outcome-for-first and the number of legal second-player replies; for LOSS
   first moves also record a winning reply if any.
4. **Invariant separation audit** — test whether simple exact quantities
   (forbidden-quad count, α from Cycle 1 maximal sets when available,
   first-move density, peak LOSS depth, root mobility) separate
   F-boards `{1,2,3,5,6,9}` from S-boards `{4,7,8,10}`.
5. **Research note** — `night-research/CYCLE4_EXACT_STRUCTURE.md` stating the
   strongest supported non-trivial conclusion and explicit non-claims.

### Implementation contracts

- Geometry: 4-point concyclic/collinear iff det of rows
  `[x²+y², x, y, 1]` is 0 (integer arithmetic, no floats).
- Point id: `id = y * n + x`.
- Position outcome: safe occupied set only; player to move; no legal move ⇒ LOSS.
- Exact enumerators must be deterministic; seed only for any residual sampling.
- New code lives under `night-research/`; outputs JSON + markdown.
- Do **not** re-solve 9×9 or 10×10 roots (Cycle 3 priority 3).
- Heavy multi-hour single solver runs are out of scope; prefer n≤5 exact and
  existing sample artifacts for larger boards.

### Workspace note

`git worktree add` for a new linked worktree was **blocked** by the session
guard (shared `.git` registry). Research proceeds on the active checkout
branch `replicate-8x8-o-stratum` using additive files under `night-research/`
and `docs/`, matching prior night-cycle practice. Existing lane
`.slim/worktrees/research-properties` is on an older base and is not used as
the implementation root.

## [S3] Out of Scope

- Re-classifying any 9×9 or 10×10 first move or empty-board winner.
- Publishing/pushing to GitHub (user/orchestrator decides).
- Lean formalization of new theorems.
- New certificate generation for n≥7.
- Claiming a closed-form winner law for all n.

## Tasks

- [x] T1: Write Cycle 4 density/hygiene artifact from Cycle 3 complete 9×9 data — acceptance: JSON shows n=9 status complete, density 1.0, 81/81 (covers: S2.1)
- [x] T2: Implement exact safe-set outcome enumerator + depth profile for n=2..5 — acceptance: JSON has per-n per-k safe counts and LOSS rates; script reruns cleanly (covers: S2.2)
- [x] T3: Implement exact first-move reply mobility for n=2..5 — acceptance: per-cell outcome + legal reply counts; matches known winner/density facts (covers: S2.3)
- [x] T4: Invariant separation audit vs F/S boards — acceptance: markdown table of candidate quantities; explicitly marks which do/do not separate (covers: S2.4)
- [x] T5: Write CYCLE4_EXACT_STRUCTURE.md non-trivial conclusion + journey notes — acceptance: conclusion cites exact artifacts; rejects overclaim (covers: S2.5)
- [x] T6: Cross-check mobility/outcome consistency against rust `classify-first` / certificates where available — acceptance: agreement noted or discrepancy documented (covers: S2.2; S2.3; depends: T2; T3)

---
feature: cycle8-n7-structure-explain
status: delivered
updated: 2026-09-19
branch: cycle8-n7-structure
commits: 2d3855a..HEAD
---

# Cycle 8 — Why only n=7 attains K=2n among nearby boards

## Report

**What was built** — Cycle 8 compressed Cycle 6–7 census facts about n=7
maximum safe sets (K7=14, 16 sets, 2 D4 phases) into small combinatorial
lemmas with complete-enumeration evidence and n=6 contrast, plus an n=8
D4-orbit sample. Independent verification (`cycle8_verify_lemmas.py`) passed
all checks. Package B added COMPLETE constrained counts via
`cycle8_b_maxsafe.exe`.

Main delivered lemmas (see `night-research/CYCLE8_N7_STRUCTURE.md`):
1. Unique D4 class of 5→5 phase exchange; 9/5/5 split; center XOR {(0,3)+2×(2,3)}.
2. All 224 thirteen-subsets of the 16 max sets have unique completion →
   single-stone paths between distinct max sets must drop to size ≤12.
3. min_det=2 for all 16 n=7 max sets vs min_det≥3 on all 464 n=6 max sets
   (local pin / global isolation paradox).
4. Occupancy vectors at K=14 are exactly A/B; (2,2) occupied ⇒ max=13
   (COMPLETE: count@14=0 + K=13 witnesses).
5. Tighter exclusivity (COMPLETE): center+(0,3) max=13; center+(2,3) max=**12**;
   corners=4 max≤12; K=14 only corner strata {2,3}.
6. n=8 SAMPLE (8 D4 images of one witness): ρ=1, 1-swap exists, (2,2) used —
   does not reproduce n=7 rigidity (sample, not complete).

**Verification** —
- `cycle8_verify_lemmas.py`: 14/14 PASS (`results/cycle8_verify.json`).
- Independent review (subagent): no critical errors; nits fixed in `f0a3e79`.
- Package B COMPLETE counts for force/forbid center, (0,3), (2,3), (2,2),
  corner strata, and exclusivity compounds (`cycle8_b_result.json`).

**Journey log** —
(1) `git worktree add` blocked by shared-registry guard; worked on
`cycle8-n7-structure` via `git switch -c` (Cycle 4 pattern).
(2) Python BnB without target pruning timed out on constrained K=14;
switched to downward target-existence DFS + C++ enum-style solver.
(3) force_2_2@K=14 primary proof is complete 16-set census (freq 0) plus
COMPLETE independent count@14=0 from Package B — not an unfinished search.
(4) n=8 random multi-witness DFS too expensive; cut to D4-orbit sample per
priority A–D first.
(5) Oriented exchange D4 key count is 1; unoriented is 2 — cite convention.
(6) center+(2,3) is stricter than center+(0,3) (max 12 vs 13).

## [S1] Problem

Cycle 6–7 established (complete enumeration, n=7):
K7=14, exactly 16 maximal safe sets, 2 D4 orbits (center / no-center),
ρ=2 for all sets, no 1-swap edges, inter-orbit minimum distance d*=5,
(2,2) orbit never used, center exclusive with (0,3)/(2,3).

These are census facts. They do not yet explain **why** n=7 alone reaches
K7=2n=14 (K6=11=2n-1, and the generic ceiling often cited is 2n-1), nor why
the maximum-set space collapses to two rigid phases connected only by a
unique 5-point exchange template.

Non-trivial target (user): compress the phenomenon to a small combinatorial
lemma, e.g.

> On 7×7, 14-stone safe sets exist in exactly two D4 phases; the phases are
> joined only by a unique 5→5 exchange template; the obstruction is a
> concrete family of forbidden quadruples on named cell orbits.

## [S2] Design

### Workspace override

`git worktree add` is blocked by the session shared-registry guard (same as
Cycle 4). Work proceeds on branch `cycle8-n7-structure` in the active
checkout, additive under `night-research/` + `results/` + `docs/compose/spec/`.
Do not rebase/merge/cherry-pick other branches. Do not modify the shared
worktree registry.

### Inherited facts (do not re-enumerate)

Base commit `2d3855a`. Inputs only:
- `night-research/maxsafe_n7_K14.bin` — 16 sets, K=14, complete
- `night-research/maxsafe_n6_K11.bin` — 464 sets, K=11, complete
- `results/maxsafe_exchange_n{6,7}.csv` — ρ, τ, D4 keys
- `results/maxsafe_pair_distance_n7.csv` — all 120 pair distances
- `results/maxsafe_orbit_profile_n7.csv` — A/B cell-orbit occupancy
- Geometry: det of `[x²+y²,x,y,1]` rows = 0; id = y*n+x

Forbidden re-work: full K=14 re-enum for n=7; full Grundy 7×7; K9 128-bit
UNSAT runs; re-deriving K7/K8.

### Work packages

**A — d=5 template decomposition (priority 1)**
Fix one representative pair (A0,B0) with d=5 (orbit A center, orbit B
no-center). Explicitly list A0∩B0 (9), A0\B0 (5), B0\A0 (5). Confirm under
D4 (stabilizer of the unordered pair, or of the difference) that this 5→5
exchange is unique. On the 10 difference points: sequential add/remove
legality, blocker triples / forbidden quads, bipartite or hypergraph of
A-side stones vs B-side stones that block each other, min hitting set /
vertex cut / min exchange set. Focus cells: center, (0,3) orbit, (2,3)
orbit, corners. Target lemma: phase transition requires this exact 5-set
exchange (or a precise statement of what smaller temporary drop allows).

**B — orbit occupancy constraints**
For all 16 max sets: occupancy vector on the 10 D4 cell orbits. Conditional
maximum safe-set size under forced/forbidden orbits:
center yes/no; (0,3) yes/no; (2,3) yes/no; (2,2) yes/no; corner count
0..4. Independent verification that any safe set containing a (2,2) cell has
size ≤13. Compress: “14-stone occupancy vectors are exactly these two types.”

**C — determining sets**
For each max set S (n=7 all 16; n=6 sample or all 464 if cheap), find min
|D| such that D⊂S and S is the unique max set containing D. Record sizes and
whether a small core (2–4 cells) determines the whole crystal. Compare A vs B.

**D — n=6 contrast**
Apply C’s determining-set notion and B-style orbit/constraint language to
n=6 464 max sets. Priority: properties that are **universal on n=7** and
**frequently false on n=6** (not mere mean differences). Candidates: min
determining set size distribution; presence of 1-swap edges; inter-orbit
distance spectrum; whether a single cell orbit is always empty; corner-count
support.

**E–G (only if A–D finish with a strong lemma)**
E: sample ≤1000 n=8 15-stone sets for ρ / d / orbit occupancy (no full enum).
F: no full σ7; only witness searches from known max sets if a ceiling attaining
position is needed. G: design-only 128-bit notes if time remains; no huge
UNSAT.

### Evidence standards

- Every numeric claim states: complete enumeration vs sample; input count;
  D4-dedup yes/no.
- Prefer universal statements + n=6 counterexample counts.
- Independent check scripts when a claim is used as a main lemma.
- Rejected hypotheses are recorded; do not re-run dead directions.

### Deliverables

- `night-research/cycle8_*.py` analysis scripts (reproducible)
- `results/cycle8_*.json` / csv artifacts
- `night-research/CYCLE8_N7_STRUCTURE.md` — main report with lemmas
- This spec finalized with Report + task checkboxes
- Commits on `cycle8-n7-structure` only

## [S3] Out of Scope

- Re-proving K7=14 / K8=15 / winner sequence
- Full 7×7 Grundy table
- Full n=8 maximal-set enumeration
- K9≥17 128-bit UNSAT search
- Push/merge to origin or other branches
- Modifying shared worktree registry / .slim worktree config

## Tasks

- [x] T1: Spec + shared geometry library — acceptance: `cycle8_lib.py` loads both bins, builds forbidden quads, D4 orbits; spec committed (covers: S2)
- [x] T2: A d=5 template — acceptance: JSON+markdown lists 9/5/5 cells, uniqueness under D4, blocker hypergraph, min hitting/cut; independent recompute matches (covers: S2.A)
- [x] T3: B orbit constraints — acceptance: conditional max table for center/(0,3)/(2,3)/(2,2)/corners; (2,2)⇒≤13 verified; occupancy classification of 16 sets (covers: S2.B)
- [x] T4: C determining sets — acceptance: for each of 16 n=7 sets, min determining |D| with witness D; A/B comparison (covers: S2.C)
- [x] T5: D n=6 contrast — acceptance: same invariants on 464 n=6 sets; table of universal-n=7 vs n=6 failure counts (covers: S2.D)
- [x] T6: E/F/G opportunistic — acceptance: only if A–D strong; sample stats or design notes with clear sample-size labels (covers: S2.E). Delivered: n=8 D4-orbit SAMPLE (ρ=1, (2,2) used) labeled sample-only; F/G skipped as instructed after A–D strength.
- [x] T7: Verify + review + finalize — acceptance: independent scripts pass; reviewer criticals fixed; report+spec committed (covers: S2). Review 2026-09-19: `cycle8_verify_lemmas.py` all PASS; no critical errors; non-critical report fixes in `night-research/cycle8_review_notes.md`

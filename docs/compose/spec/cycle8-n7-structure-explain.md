---
feature: cycle8-n7-structure-explain
status: review-passed
updated: 2026-09-19
branch: cycle8-n7-structure
commits: 2d3855a..dc14860 + review polish  # T6 still open if n=8 sample runs
---

# Cycle 8 — Why only n=7 attains K=2n among nearby boards

## Report

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
- [ ] T6: E/F/G opportunistic — acceptance: only if A–D strong; sample stats or design notes with clear sample-size labels (covers: S2.E)
- [x] T7: Verify + review + finalize — acceptance: independent scripts pass; reviewer criticals fixed; report+spec committed (covers: S2). Review 2026-09-19: `cycle8_verify_lemmas.py` all PASS; no critical errors; non-critical report fixes in `night-research/cycle8_review_notes.md`

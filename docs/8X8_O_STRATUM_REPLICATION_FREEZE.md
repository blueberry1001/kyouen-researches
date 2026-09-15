# 8×8 O-stratum replication — freeze manifest

Status: FROZEN BEFORE ANY 8×8 EXACT CHILD OUTCOME

Branch: `replicate-8x8-o-stratum`
Base commit: `5af0bf2f6b30124eec37e64d16b8ca90643931ae`
Board: N=8, V=64
Symmetry: D4 canonical orbits (full census, not a sample)

## Score definitions (identical to 9×9)

- T = newly lost safe responses
- E = re-counting of already-dangerous responses
- O = duplicate counting of the same newly-dangerous response
- S00 = T
- S10 = T + E
- S01 = T + O
- S11 = T + E + O = raw

Eligibility: all four scores have unique argmax; at least one top move differs.

## Primary success criterion (frozen)

Encode LOSS=1, WIN=0.

- O0-only: Δ_O = mean(y01 − y00), y00=outcome(top_T), y01=outcome(top_TO)
- O-overlap: Δ_O = mean(y01 − y00) with the same pair
- G = Δ_O(O0-only) − Δ_O(O-overlap)

Success requires BOTH:
1. Δ_O(O0-only) > 0
2. G ≥ +0.05

The +0.05 threshold is frozen prospectively and must not be tuned after outcomes.

## Geometry validation (outcome-free)

- all 4-stone sets: 635376 = C(64,4)
- forbidden 4-stone sets: 14564
- safe 4-stone parents: 620812
- orbit sizes ∈ {1,2,4,8}
- canonical parent D4-invariant
- top moves D4-covariant with matching scores
- all candidate moves in 0..63
- parent+top move is a legal 5-stone state

Result: VALIDATION PASS

## Population counts (outcome-free)

- safe_4stone_parents raw: 620812
- all4_unique_raw: 395592
- any_score_diff_raw: 18712
- D4 orbits (eligible population): 2340
- O0-only orbits: 165
- O-overlap orbits: 155
- O1-only orbits: 102

## Required unique roots (outcome-free)

- raw root instances: 1154
- unique (canonical_parent, move) roots: 848
- dedup rate: 0.2652
- O0-only unique pairs: 330
- O-overlap unique pairs: 314
- O1-only unique pairs: 204

## Shared-child dependence audit (outcome-free)

- child instances (unique parent,move): 848
- unique canonical 5-stone child states: 840
- shared child states (degree > 1): 7
- max shared degree: 3
- connected components: 414
- max component size: 3

Full finite-population census; shared children do not invalidate the descriptive contrast.

## Artifacts frozen

See `artifacts/SHA256SUMS-8x8-freeze.txt`.

## Prohibited after this freeze

- alter T/E/O definitions
- change unique-argmax eligibility
- alter O0-only / O-overlap / O1-only definitions
- change the +0.05 primary threshold
- drop parents based on outcomes
- add post-hoc minimum pair_E thresholds
- convert secondary results into the primary criterion

## Solver identity

Source: `cpp/solvers/kyouen_solver_8_root.cpp`
Reference semantics: `cpp/solvers/kyouen_solver_9_root.cpp` (Solver9)
Exporter: `scripts/export-8x8-factorial-population.cpp`

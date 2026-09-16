# Cycle results — 2026-09-16 night research

## H1 terminal-parity locking — REJECTED

Enumerated all maximal kyouen-free sets for n≤5 (n=6 timed out).

| n | maximal sets | sizes | parity locked? | winner |
|---:|---:|---|---|---|
| 1 | 1 | {1} | yes (odd) | F |
| 2 | 4 | {3} | yes (odd) | F |
| 3 | 56 | {5} | yes (odd) | F |
| 4 | 928 | {5,6,7} | **no** | S |
| 5 | 16860 | {5,6,7,8,9} | **no** | F |

**Minimal counterexample: n=4.** Maximal sets of sizes 5, 6, and 7 all exist.
Winner sequence is not the parity of a locked terminal length.

Artifact: `night-research/h1-terminal-parity.json`

## H3 central-3×3 first-move window — REJECTED; MODIFIED

Exact `classify-first --size 5` (Rust independent verifier):

Winning first moves on 5×5 (player to move = first player):

```
(2,0) (1,1) (3,1)
(0,2) (2,2) (4,2)
(1,3) (3,3) (2,4)
```

This is **not** the central 3×3 block. (2,0) and (0,2) are outside; (2,1) and (1,2) are inside the 3×3 and lose.

**Equivalent characterization (exact on 5×5):**

```
W₁(5) = { (x,y) : (x+y) even }  \  { four corners }
```

D4 orbit description:

| orbit | size | outcome |
|---|---:|---|
| center (2,2) | 1 | WIN |
| edge-centers (2,0) etc. | 4 | WIN |
| interior diagonal (1,1) etc. | 4 | WIN |
| corners | 4 | LOSS |
| edge non-centers | 8 | LOSS |
| interior axial (2,1) etc. | 4 | LOSS |

Does **not** generalize as stated to n=3 (all 9 win; even sublattice is only 5 points).
Status: **MODIFIED hypothesis, 5×5-only**. Independent test = 9×9 first-move job.

Artifacts: `night-research/first-moves-5x5-cargo.log`

## H4 geometric pair-witness count — PARTIAL SUPPORT / k=5 REJECTED

`w(a,b) = #{ forbidden 4-sets F : {a,b}⊂F⊂R∪board, |F∩R|≥2 }` on R = medium 10×10 LOSS root.

| depth | empirical LOSS core | core w | best w among LOSS pairs | claim |
|---:|---|---:|---|---|
| 3 | {90,91} | 87 | {90,91}=87 | **holds** |
| 4 | {61,66} | 165 | {61,66}=165 | **holds** |
| 5 | {13,91} | **24** | {66,73}=105 | **fails** |
| 6 | {61,66} among 3-loss family | 165 | {61,66}=165 | **holds** |

Static witness-count is **not** a depth-uniform law. Depth-5 cores prefer a low-w pair.
Global argmax w = {61,66} (w=165).

Artifacts: `night-research/h4-pair-witness.json`

## O1-only +0.088 — NOT promoted (adversarial kill)

- McNemar p=0.049 uncorrected; 1 flip among 13 kills significance
- All 13 positives share stones (one connected component; motifs of size 5/3/2)
- Independent 9×9 O1-only already at Δ=+0.018 (5× weaker)
- Frozen as secondary; next independent board must be 7×7 or 10×10 with Δ≥+0.04 floor

## E×O interaction I — algebraic alias, not deep identity

Correct force condition: `top_T==top_TE` and `top_TO==top_raw` ⇒ I≡0.

- 8×8 O-overlap: 151/155 forced, 4 free, 0 nonzero
- 9×9: ~97% forced, **4 pointwise I≠0** already exist

Do not treat I=0 as a game-theoretic finding. Report free-subset only.

## Background

- 9×9 first-move D4-orbit classification running (`night-research/run_first_moves_9x9.py`, memo=28, 4 parallel)
- Loop job `b7a5158c` every 10m

## H4 k=5 anomaly — representation, not geometry

At k=5, LOSS enrichment ranks `{13,91}` first (3.17×) while its witness-count `w=24` is low.
Spearman(w, enrichment) ≈ **−0.25** (static w is slightly anti-correlated at this depth).
Stone 91 appears in **11/11** LOSS 5-subsets of R, but also in 24/45 WIN — necessary, not sufficient.

Prior research-properties F-B/H2 already showed these “cores” dissolve under D4 canonicalization.
So the k=5 “core” is an **input-embedding artifact** of R, not a board-invariant pair law.
H4’s failure at k=5 is provenance evidence, not a new geometric structure.

Artifacts: `night-research/h4-k5-anomaly.json`

## Background still running

- 9×9 first-move class `(1,1)` solver process alive (memo=30, ~13GB, ~0.4 M/s)
- Do not start more concurrent 9×9 roots; RAM is the bottleneck

## Next highest-value experiments

1. Harvest `(1,1)` when done; continue remaining D4 classes one-at-a-time (memo=30)
2. Test 5×5 even-lattice-minus-corners against 9×9 actual wins when table is ready
3. H2 mobility-vs-redundancy on unique-max 4-stone disagreements (child solves)
4. Do **not** promote O1-only or I=0

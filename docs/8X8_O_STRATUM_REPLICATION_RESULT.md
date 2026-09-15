# 8×8 O-stratum independent replication — result

Status: COMPLETE (full D4-orbit census)
Branch: `replicate-8x8-o-stratum`
Base: `5af0bf2f6b30124eec37e64d16b8ca90643931ae`
Freeze commit: `020f0f119d499a5b48f2b17740345bd38832744c`
Solver validation commit: `a8b5b943f1a826311e4211a8058a718c871404cf`

## Freeze discipline

No 8×8 production child outcome was read before the freeze commit.
Primary hypothesis, stratum definitions, and the +0.05 gap threshold were frozen in
`docs/8X8_O_STRATUM_REPLICATION_PREREG.md` / `docs/8X8_O_STRATUM_REPLICATION_FREEZE.md`.

## Geometry and population (outcome-free)

| quantity | value |
|---|---|
| board | N=8, V=64 |
| all 4-stone sets | 635376 |
| forbidden 4-stone sets | 14564 |
| safe 4-stone parents | 620812 |
| all4_unique_raw | 395592 |
| any_score_diff_raw | 18712 |
| eligible D4 orbits (population) | **2340** |

Exporter geometry validation: PASS (orbit sizes ∈ {1,2,4,8}, canonical D4-invariant,
top moves covariant, moves in 0..63, parent+move legal 5-stone).

## Strata (outcome-free)

| stratum | n |
|---|---|
| O0-only | **165** |
| O-overlap | **155** |
| O1-only | **102** |

## Required unique roots and solve

| quantity | value |
|---|---|
| raw root instances | 1154 |
| unique (canonical_parent, move) roots | **848** |
| dedup rate | 0.265 |
| solve completion | **848 / 848 (100%)** |
| failed shards | 0 |
| retries | 0 |
| memo-over | 0 |
| wall time (12 shards, 8 workers, memo_power=26) | 3.74 s |

Shared-child dependence audit (frozen pre-outcome):

| quantity | value |
|---|---|
| unique parent,move instances | 848 |
| unique canonical 5-stone children | 840 |
| shared child states | 7 |
| max shared degree | 3 |
| connected components | 414 |
| max component size | 3 |

Full finite-population census; shared children reported, not hidden.

## Primary finite-population effects (LOSS=1, WIN=0)

### O0-only (n=165)

| cell | count |
|---|---|
| both LOSS | 3 |
| both WIN | 145 |
| baseline-only LOSS | 12 |
| O-added-only LOSS | 5 |
| discordant | 17 |
| baseline LOSS rate | 0.0909 |
| added LOSS rate | 0.0485 |
| **Δ_O** | **−0.0424** |
| change rate | 0.1030 |
| net count | −7 |

### O-overlap (n=155)

| cell | count |
|---|---|
| both LOSS | 2 |
| both WIN | 137 |
| baseline-only LOSS | 9 |
| O-added-only LOSS | 7 |
| discordant | 16 |
| baseline LOSS rate | 0.0710 |
| added LOSS rate | 0.0581 |
| **Δ_O** | **−0.0129** |
| change rate | 0.1032 |
| net count | −2 |

### Primary contrast

```
G = Δ_O(O0-only) − Δ_O(O-overlap)
  = (−0.0424) − (−0.0129)
  = −0.0295
```

Frozen success criterion:

1. Δ_O(O0-only) > 0 → **false** (−0.0424 ≤ 0)
2. G ≥ +0.05 → **false** (−0.0295 < 0.05)

**Verdict: FAIL** — the 9×9 O0-only structural hypothesis does not replicate on 8×8.

## Secondary

### O1-only (n=102)

| cell | count |
|---|---|
| both LOSS | 2 |
| both WIN | 83 |
| baseline-only LOSS | 4 |
| O-added-only LOSS | 13 |
| discordant | 17 |
| baseline LOSS rate | 0.0588 |
| added LOSS rate | 0.1471 |
| **Δ_O_E1** | **+0.0882** |
| change rate | 0.1667 |
| net count | +9 |

Descriptive only; not part of the primary criterion.

### Shared-parent interaction (O-overlap)

I = (y11 − y10) − (y01 − y00)

| I | count |
|---|---|
| −2 | 0 |
| −1 | 0 |
| 0 | **155** |
| +1 | 0 |
| +2 | 0 |

mean I = 0, median I = 0, |I|=2 = 0.

This reproduces the 9×9 finding that E×O interaction on shared parents is essentially zero
(here: exactly zero on the full O-overlap census).

## 9×9 comparison

| board | O0-only n | O-overlap n | O0-only Δ | O-overlap Δ | gap | interaction mean |
|---|---|---|---|---|---|---|
| 8×8 (this census) | 165 | 155 | −0.0424 | −0.0129 | −0.0295 | 0.0 |
| 9×9 (exploratory holdout ref) | — | — | +0.0912 | −0.0143 | +0.1055 | ~0 |

The 9×9 O0-only positive Δ did **not** replicate. O-overlap Δ is similarly slightly
negative on both boards. Interaction ≈ 0 replicates.

## Interpretation (frozen rules)

Under the preregistered rules:

> If Δ_O(O0-only) <= 0, the main 9×9 structural hypothesis fails to replicate on 8×8.

That condition holds. The 9×9 claim that “O’s usefulness is strongly conditioned by
outcome-free top-move membership structure (O0-only ≫ O-overlap)” is **not** supported
by this independent 8×8 full census.

Secondary observation (not a new primary): O1-only shows a positive Δ_O_E1 (+0.088),
while both O0-only and O-overlap E0 contrasts are non-positive. Any new hypothesis built
on that pattern requires another independent dataset.

## Failed / retry / memo-over

- failed roots: 0
- retries: 0
- memo-over errors: 0

## Artifacts

- `docs/8X8_O_STRATUM_REPLICATION_PREREG.md`
- `docs/8X8_O_STRATUM_REPLICATION_FREEZE.md`
- `docs/8X8_SOLVER_VALIDATION.md`
- `scripts/export-8x8-factorial-population.cpp`
- `scripts/build-8x8-o-strata-roots.py`
- `scripts/run-8x8-o-census-solve.py`
- `scripts/analyze-8x8-o-stratum-replication.py`
- `cpp/solvers/kyouen_solver_8_root.cpp`
- `artifacts/8x8-factorial-population.csv`
- `artifacts/8x8-o-strata.csv`
- `artifacts/8x8-o-required-roots.csv`
- `artifacts/8x8-o-shared-child-audit.json`
- `artifacts/8x8-o-census-outcomes.csv`
- `artifacts/8x8-o-solve-manifest.json`
- `artifacts/8x8-o-parent-outcomes.csv`
- `artifacts/8x8-o-primary-summary.json`
- `artifacts/8x8-o-9x9-comparison.csv`
- `artifacts/8x8-o-analysis-summary.json`
- `artifacts/SHA256SUMS-8x8-freeze.txt`
- `artifacts/SHA256SUMS-8x8-result.txt` (written at result commit)

# 10x10 cache-aware loss-first-only ablation — endpoint result

Prereg: `docs/10X10_CACHE_AWARE_LOSS_FIRST_ONLY_PREREG.md`
Branch: `preregister-10x10-loss-first-only`
Head SHA: `378d86ed9fa0de593f8da9c293eb41b686c38d3a` (`378d86e`)
Workflow run: `35545436757` (loss-first blinded endpoint, success)
Safety-gate run: `35545436769` (loss-first ordering safety gate, success)
Artifact source: Actions artifact `loss-first-only-endpoint` (expires 2026-12-19)

Status: **PRIMARY SUCCESS** — frozen criterion Recovery ≥ 0.80 and L < B on ≥10/12 parents.

## Frozen primary endpoint

| quantity | value |
|---|---|
| B total visited | 265,470,110 |
| L total visited | 225,422,484 |
| F total visited | 225,422,484 |
| Recovery `(sum B − sum L) / (sum B − sum F)` | **1.000** |
| L = F (exact visited) | **12 / 12** parents |
| L < B (strict improvement) | **12 / 12** parents |
| outcome parity (B/L/F) | PASS (all WIN) |
| safety gate | **4225 / 4225 PASS** |
| primary_success | **true** |

Mechanistic reading (prereg §Mechanistic interpretation): on this frozen 12-parent cohort,
promoting a single B-earliest cached-LOSS child recovers **100%** of the previously observed
full-aware aggregate search reduction. Cached-WIN demotion and full cached-class sorting do
not contribute additional `visited` reduction here.

## Secondary aggregates (from `endpoint_result.json`)

| metric | value |
|---|---|
| median L/B | 0.8605781106881454 |
| geomean L/B | 0.8580463598417525 |
| median L/F | 1.0 |
| geomean L/F | 1.0 |
| n_parents | 12 |
| cohort_complete | true |

## Raw paths

- Per-run raw: `results/10x10/cache-aware-loss-first-only/endpoint_raw.json`
- Aggregate JSON: `results/10x10/cache-aware-loss-first-only/endpoint_result.json`
- Flat CSV (this commit): `results/loss_first_only_endpoint.csv`
- Collector: `scripts/run_loss_first_only_endpoint.py`
- Safety harness: `scripts/loss_first_order_test.cpp` → `LOSS-FIRST SAFETY PASS cases=4225`

## Conditions

- **B** — cache-blind below-root order `(legal_move_count, canonical key)`
- **L** — loss-first-only: promote one B-earliest cached-LOSS child to index 0; all others keep B relative order
- **F** — full cache-aware order `cached LOSS < unknown < cached WIN < legal_move_count < canonical key`

Cohort: frozen C1 original 12 parents. Fresh serial processes, 3×3 cyclic counterbalance.
Primary metric is exact `visited`; timing is secondary.

## Interpretation note

Recovery = 1.000 with L ≡ F on every parent means this cohort has **no residual benefit**
from cached-WIN demotion or multi-LOSS ordering beyond single-child promotion. Follow-up
should target depth 7/8 parent→child multi-parent measurement (canonical child key distinct
parent counts; later reuse as cached LOSS/WIN) rather than new root-order probes.

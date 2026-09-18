# Cycle 10 — why K=14 occupancy on n=7 is only types A and B

Evidence mix (explicit):
- **COMPLETE enum**: 16 max sets realize exactly 2 occupancy vectors.
- **COMPLETE constrained first/count** via `night-research/cycle8_b_maxsafe.exe`
  (complete=true ⇒ exhaustive for that constraint at the stated size).
- Theoretical count of sum=14 vectors within orbit-size caps: **304,752**
  (combinatorial only — not a search).

## Realized vectors (COMPLETE)

Orbit order: `(0,0)(0,1)(0,2)(0,3)(1,1)(1,2)(1,3)(2,2)(2,3)(3,3)`

| type | vector | ids | corners | center |
|---|---|---|---:|---:|
| **A** | (2,3,2,0,1,3,2,0,0,1) | 0,2,5,9,10,11,12,15 | 2 | 1 |
| **B** | (3,1,2,1,1,3,1,0,2,0) | 1,3,4,6,7,8,13,14 | 3 | 0 |

Always-used on all 16 (count>0 in both A and B): `(0,0),(0,1),(0,2),(1,1),(1,2),(1,3)`.
Never-used on all 16: `(2,2)`.
Phase-exclusive: center / `(0,3)` / `(2,3)`.

## COMPLETE constraint table (first/count @ K=14)

| constraint | result | complete? |
|---|---:|---|
| force center | 8 (= all A) | yes |
| force one `(0,3)` cell | 2 | yes |
| force one `(2,3)` cell | 4 | yes |
| force one `(2,2)` cell | **0** | yes |
| require orbit center | 8 | yes |
| center ∧ require `(0,3)` | **0** | yes |
| center ∧ require `(2,3)` | **0** | yes |
| center ∧ require `(2,2)` | **0** | yes |
| center ∧ corners=3 | **0** | yes |
| no-center ∧ forbid `(0,3)`∧`(2,3)` | **0** | yes |
| force 3 specific `(1,3)` | **0** | yes |
| force 3 specific `(0,1)` | **0** | yes |
| force 3 specific `(2,3)` | **0** | yes |
| force 4 `(2,3)` | unsafe (−1) | yes |
| force two specific `(1,3)` | 2 | yes |
| forbid orbit `(2,2)` | still possible (16 exist) | enum |
| corners=4 @14 | **0** | yes (Package B) |

Incomplete-but-informative (node cap): require `(1,1)/(1,2)/(0,2)` ≥10 hits
(consistent with always-used); require `(0,3)` or `(2,3)` ≥6 (B side);
no-center∧corners=2 incomplete 0 (B uses 3 corners);
no-center∧require(0,3)∧require(2,3) count≥7 incomplete (expect 8=all B).

### Phase characterization (COMPLETE)

| phase | COMPLETE defining constraints @K=14 | count |
|---|---|---:|
| **A** | center ∧ corners=2 | **8** complete |
| **B** | ¬center ∧ corners=3 | **8** complete |
| A excluded from B-orbits | center ∧ require(0,3) or require(2,3) or require(2,2) | **0** complete |
| B needs its orbits | ¬center ∧ forbid(0,3)∧forbid(2,3) | **0** complete |

> **Phase lemma.** The 16 n=7 max safe sets are exactly
> `{center ∧ corners=2}` ⊔ `{¬center ∧ corners=3}` (8+8 COMPLETE),
> and the no-center branch cannot omit the `(0,3)/(2,3)` orbits.

## Selection lemma (compressed)

> On 7×7, a size-14 safe set’s D4-orbit occupancy vector must satisfy:
> 1. `(2,2)=0` (COMPLETE).
> 2. corners ∈ {2,3} only; corners=4 impossible at 14 (COMPLETE).
> 3. center ∈ {0,1}; if center=1 then `(0,3)=(2,3)=0` (COMPLETE exclusivity).
> 4. if center=0 then the set **must** use both orbits `(0,3)` and `(2,3)`
>    — forbidding them together with no center leaves **zero** K=14 sets (COMPLETE).
> 5. Local caps: `(1,3)≤2`, `(2,3)≤2`, and the specific-cell force tests above.
> 6. Under (1)–(5) and orbit-size caps, the census realizes **exactly two**
>    full vectors A and B (COMPLETE enum of 16).
>
> Among 304,752 theoretical sum=14 vectors respecting only orbit *sizes*,
> only these two survive the geometry.

This is the strongest available compression of “why only two phases at K=14”:
not an average trend, but a **finite COMPLETE selection rule** on occupancy,
with the no-center branch *forcing* the B-side orbits on.

## Relation to K7=14 / n=7 anomaly

- K7=14=2n is still inherited (not re-proved).
- Cycle 10 explains the **shape** of the maximizing family, not yet a
  board-size criterion for why n=7 reaches 2n.
- n=8 SAMPLE shows many occupancy patterns — the two-phase selection is
  not a generic max-safe phenomenon.

## Artifacts

- `results/cycle10_occupancy_probes.json`
- `night-research/cycle10_occupancy_probes.py`
- Solver: `night-research/cycle8_b_maxsafe.exe`

## Geometric side of center exclusivity (COMPLETE local lists)

Forbidden quads through center `(3,3)` **and**:
- some `(0,3)` cell: **180**
- some `(2,3)` cell: **244**
- some `(2,2)` cell: **216**

On phase A0, each empty `(0,3)` cell has **5–8** blocker triples already
inside A0 (examples listed in the probe run: e.g. `(3,0)` blocked by
`(0,0),(1,0),(5,0)` etc.). On phase B0, the empty center has **7** blockers,
several using `(0,3)`/`(2,3)` stones — so B’s exclusive orbits are exactly
what pin the center out.

## Orbit necessity at K=14 (COMPLETE forbid-orbit tests)

`first 7 14 --forbid-orbit X,Y` with complete=true and count=0 means **no**
K=14 safe set omits that entire orbit.

| orbit | forbid-orbit @14 | verdict |
|---|---:|---|
| `(0,0)` corners | **0** complete | **mandatory** |
| `(0,1)` | **0** complete | **mandatory** |
| `(0,2)` | **0** complete | **mandatory** |
| `(1,1)` | **0** complete | **mandatory** |
| `(1,2)` | **0** complete | **mandatory** |
| `(1,3)` | 0 incomplete (4M nodes) | used by both phases; likely mandatory |
| `(2,2)` | n/a (force=0) | **forbidden** (cannot be used) |
| `(0,3)` | possible (phase A omits) | phase-B exclusive |
| `(2,3)` | possible (phase A omits) | phase-B exclusive |
| `(3,3)` center | possible (phase B omits) | phase-A exclusive |

> **Necessity lemma (COMPLETE).** Every n=7 14-stone safe set meets each of
> the five orbits `(0,0),(0,1),(0,2),(1,1),(1,2)`. None may use `(2,2)`.
> The remaining three orbits `(3,3),(0,3),(2,3)` implement the A/B split:
> center XOR (B-orbits), with ¬center forcing B-orbits on.

Combined with corner strata and phase counts, occupancy is fully selected.

### B-phase uniqueness (COMPLETE)

`first 7 14 --forbid center --require-orbit 0,3 --require-orbit 2,3`
→ **count=8, complete=true** (all B sets; first `1106400a29843`).

So the 16 sets are **exactly**
`{center ∧ corners=2}` ⊔ `{¬center ∧ require(0,3)∧require(2,3) ∧ corners=3}`
with both branches COMPLETE-counted at 8.

## n=8 contrast (SAMPLE, incomplete forbid-orbit first@15)

| forbid orbit on n=8 K=15 | first-found count (cap 1.5M nodes) |
|---|---:|
| `(0,0)` corners | 0 incomplete |
| `(0,1)` | **1** (orbit optional) |
| `(0,2)` | 0 incomplete |
| `(0,3)` | **3** |
| `(1,1)` | **4** |
| `(1,2)` | **6** |
| `(1,3)` | **30** |
| `(2,2)` | **5** — (2,2) is **usable** on n=8 |
| `(2,3)` | **11** |
| `(3,3)` 2×2 center block | **45** |

**SAMPLE contrast:** n=7 forbidding five orbits or using (2,2) is COMPLETE
impossible at K=14; n=8 already exhibits witnesses that omit most orbits and
that use (2,2). The n=7 “crystal selection rule” does not transfer.

## Next probes

1. COMPLETE count @14 under `no-center ∧ require (0,3) ∧ require (2,3)`
   (expect 8 = all B) — require both orbits without center.
2. COMPLETE max under forcing the *counts* of A vs B via enough forced cells
   from each orbit bundle.
3. Independent Python recompute of the COMPLETE zeros in the table.

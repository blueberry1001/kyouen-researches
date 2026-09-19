# Cycle 41 — proof dependency map for the n=7 selection theorem

Target statement:

\[
|S|=14,\ \mathrm{Safe}(S)\ \Longrightarrow\ S\in\mathcal{M}_A\cup\mathcal{M}_B.
\]

Minimal dependency chain (what each step uses). COMPLETE / first-principles marked.

```
[D0] Forbidden 4-sets: det[x²+y²,x,y,1]=0  (definition; COMPLETE)
        │
[D1] Orbit–circle lemma: each D4-orbit ⊂ center-circle
        ⇒ x_i ≤ 3 on every orbit with |O|≥4   (COMPLETE, elementary)
        │
[D2] (2,2) empty at |S|=14
        solver force@14 max=13 COMPLETE
        + structured lattice SAMPLE consistent
        │
[D3] Skeleton M = six mandatory orbits (forbid-orbit@14=0 COMPLETE)
        α(M) ≤ 13 via compressed occupancy certificate:
          D1 + proper-subset COMPLETE maxima (kill 113/120)
          + 7 joint residual lemmas (COMPLETE decision)
        witness max(M)=13 COMPLETE
        │
[D4] Phase extensions of M (cells outside M):
        max(M∪{center})=14 = A  (COMPLETE)
        max(M∪B-bundle)=14 = B  (COMPLETE)
        partial B-bundle max=13; center XOR B (COMPLETE zeros)
        occupancy-lattice: A/B occ Σ=14 realizable; mixed not (COMPLETE)
        │
[D5] Census of the 16: A ≡ center∧corners=2 (8);
        B ≡ ¬center∧corners=3∧require(0,3)∧(2,3) (8)
        → characterization of the two phases
```

**Conclusion.** Any safe 14-set cannot live on M alone (D3). It must use
phase orbits (D4). Those lifts are exactly A or B; mixed occupancy is
unrealizable. D5 identifies A/B with explicit orbit predicates.

## What is first-principles vs computer-assisted

| step | type |
|---|---|
| D0 | definition |
| D1 | elementary geometry (D4 preserves radius) |
| D2 | COMPLETE solver (+ lattice SAMPLE) |
| D3 local ceilings | from D1 |
| D3 subset maxima | COMPLETE constrained solver |
| D3 seven joint lemmas | COMPLETE exact-occupancy decision |
| D4 capacities / exclusivity | COMPLETE solver + occupancy decision |
| D5 characterization | COMPLETE census / require-count |

The theorem is **computer-assisted but dependency-minimal**: no full
σ₇, no re-enumeration of all 14-sets beyond inherited K₇=14, no n=8/K9.

## Corridor width 11 vs static selection

Restricted widest A–B path on union-19 has **width 11 COMPLETE**
(`CYCLE39C`). The path oracle is `is_safe` — the **same** forbidden 4-sets
as D0. So static selection and dynamic width share one local geometry.

Still open: a **static** inequality that forces every single-stone
A↔B path to dip to ≤11 without searching the path graph — i.e. deriving
the barrier from the same occupancy inequalities as D3–D4.

## Rejected dependency shortcuts

- Density-only or center-only explanations (prior cycles).
- Universal inequalities taken from max-13 patterns without solver max
  on that subset (Cycle 40 rejected example).
- Circular use of α(M)=13 as a “subset” inequality when proving α(M)≤13.

## Artifacts

- `CYCLE40_COMPRESSED_CERTIFICATE.md`
- `CYCLE34_OCCUPANCY_LATTICE_CERTIFICATE.md`
- `CYCLE35_PHASE_LIFT_CONTRAST.md`
- `CYCLE39C_WIDEST_PATH_FAST.md`
- `FINAL_SELECTION_THEOREM.md`

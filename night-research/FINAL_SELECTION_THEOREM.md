# n=7 K=14 Selection Theorem — final compressed statement

**Branch** `cycle8-n7-structure` · **Base** `2d3855a` · evidence checklist:
`night-research/SELECTION_THEOREM_CHECKLIST.md`

Throughout: **COMPLETE** = exhaustive for the stated finite family/constraint
(census of all max sets, or C++ target/count finished with `complete=true`).
**SAMPLE** = node-capped partial.

---

## Theorem (computer-assisted, COMPLETE core)

Let Safe(S) mean the occupied set S on the n×n grid contains no forbidden
4-subset (collinear or concyclic; integer det test). Let K_n be the maximum
|S| with Safe(S). Then **K_7 = 14** (inherited; re-counted 16 times).

Let \(\mathcal{M}_7\) be the family of safe 14-sets on 7×7. Then:

1. \(|\mathcal{M}_7| = 16\), in two D4-orbits of size 8 (COMPLETE enum).

2. **Occupancy selection.** Order the ten D4 cell-orbits
   `(0,0)(0,1)(0,2)(0,3)(1,1)(1,2)(1,3)(2,2)(2,3)(3,3)`.
   Exactly two occupancy vectors occur:
   - **A** = (2,3,2,0,1,3,2,0,0,1) — center occupied, corners=2
   - **B** = (3,1,2,1,1,3,1,0,2,0) — no center, corners=3, uses both (0,3) and (2,3)
   Corner count at K=14 is **only** 2 or 3 (corners=4 → 0 COMPLETE; corners=1 census 0).

3. **Phase characterization (COMPLETE counts).**
   - \(\mathcal{M}_A = \{S : \#\text{corners}=2,\ (3,3)\in S\}\), \(|\mathcal{M}_A|=8\) COMPLETE.
     Equivalently: corners=2 ∧ forbid(0,3) → 8; corners=2 ∧ forbid(2,3) → 8.
   - \(\mathcal{M}_B = \{S : \#\text{corners}=3,\ (3,3)\notin S\}\), \(|\mathcal{M}_B|=8\) COMPLETE.
     Further, every such S uses both (0,3) and (2,3) (require both → 8 COMPLETE).
   - forbid center∪(2,2) @14 → 8 COMPLETE (=B).
   - forbid B∪(2,2) @14 → 8 COMPLETE (=A).
   - center ∧ (0,3) or (2,3) or (2,2) @14 = 0 COMPLETE.
   - no-center ∧ forbid(0,3)∧forbid(2,3) @14 = 0 COMPLETE.
   - A cannot require (0,3)/(2,3)/(2,2) — all **0 COMPLETE**.
   - A ∧ forbid (0,3) alone → 8 COMPLETE; A ∧ forbid (2,3) alone → 8 COMPLETE.
   - B cannot require center or (2,2) (COMPLETE 0).
   - B **cannot omit** (0,3) or (2,3) (forbid → 0 COMPLETE).
   - B **must** use both (0,3) and (2,3) (each require → 8 COMPLETE).
   - Every B uses all six mandatory orbits (require each → 8 COMPLETE).

4. **Mandatory / forbidden orbits (COMPLETE forbid-orbit).**
   Every S∈ℳ7 meets orbits `(0,0),(0,1),(0,2),(1,1),(1,2),(1,3)` @14.
   No S uses orbit `(2,2)`.
   Phase-level COMPLETE zeros: **neither** A nor B may omit **any** of
   `(0,0),(0,1),(0,2),(1,1),(1,2),(1,3)`.
   Deeper: `(0,2)` **and** `(1,2)` are already mandatory at **size 13** COMPLETE.

5. **Capacity decomposition (COMPLETE).** Let M be the six mandatory orbits.
   - max Safe on M only = **13**
   - max on M∪{center} = **14** (= phase A)
   - max on M∪{(0,3)} only = **13**; on M∪{(2,3)} only = **13**
   - max on M∪{(0,3),(2,3)} = **14** (= phase B; both orbits required)
   - max with any (2,2) occupied = **13**
   - center+(2,3) = **12**; forbid(0,2) = **12**; corners=4 ≤ **12**

6. **Exchange / pinning (COMPLETE on the 16).**
   - Unique D4-class of 5→5 exchange A↔B; d*=5; no 1-swap; no pair with d≤4.
   - min_det(S)=2 for every S∈ℳ7 (two stones determine S among ℳ7).
   - All 224 thirteen-subsets of members of ℳ7 uniquely complete inside ℳ7
     → single-stone paths between distinct max sets visit size ≤12.

7. **Corridor (COMPLETE on union / path-witness).**
   On A0∪B0 (19 cells): safe 14-sets = {A0,B0} only; restricted path width ≤11.
   Explicit full-board A–B path dips to 12; path-witness bottlenecks use (2,2)
   and drop center (not claimed for all min-width paths).

---

## What is *not* claimed

- A first-principles derivation of K_7=2n from board geometry alone.
- That orbit-quad density explains the crystal (**rejected**: n=6 has higher
  (0,2)/(1,2) incidence yet diffuse maxima).
- That a unique center cell produces phases (**rejected**: n=5 center split
  44/56 COMPLETE without crystal collapse).
- Complete n=8 classification (**SAMPLE** only: flexible orbits, d=4 pairs).
- K_9 or full σ_7.

## Branch status (research, not pushed)

- Workspace: active checkout (worktree add blocked by shared-registry guard).
- Branch: `cycle8-n7-structure` from base `2d3855a`.
- Independent verifies PASS; C++ regression 16/464/8/0 PASS.
- Closing action (merge/PR/push/keep) left to orchestrator/user.

---

## Sharp contrasts (COMPLETE censuses)

| n | K_n | #max | mandatory orbits | empty orbit @max | occ vectors | min_det min |
|---:|---:|---:|---:|---|---:|---:|
| 4 | 7=2n−1 | 64 | 3/3 | none | 4 | 3–4 |
| 5 | 9=2n−1 | 100 | 4 | none | 9 | 3 |
| 6 | 11=2n−1 | 464 | 4 | none | 22 | 3 |
| 7 | **14=2n** | **16** | **6** | **(2,2)** | **2** | **2** |

n=6 independent: 296/464 sets have a d=1 partner (304 undirected pairs).
n=8 SAMPLE: (2,2) usable; center-block usable; 67–45 occ patterns in capped dumps.

---

---

## Appendix — representative boards (COMPLETE census ids 0 and 8)

Phase A0 (center), occupancy A:
```
XX...X.
.XX....
.....XX
...X.X.
X......
...XX.X
X......
```

Phase B0 (no center), occupancy B (`c` marks empty center):
```
XX....X
....XX.
.X.X...
X.Xc...
......X
..XX...
..X...X
```

Also COMPLETE complementary counts @14:
- forbid `(2,2)∪(0,3)∪(2,3)` → **8** (phase A)
- forbid `(2,2)∪center` → **8** (phase B)

---

## One-sentence summary

> On 7×7 the +1 maximum family is a **two-phase crystal**: a six-orbit
> mandatory skeleton that only reaches 2n−1=13 is lifted to 2n=14 solely by
> a **mutually exclusive** commitment to the center (phase A: corners=2) or
> to the full (0,3)+(2,3) bundle (phase B: corners=3, no center), never by
> (2,2); the phases meet only through a unique 5→5 exchange and are locally
> pinned by 2-stones yet globally isolated — a selection pattern that fails
> on n=4,5,6 censuses and in n=8 samples.

---

## Reproduce (Windows)

```powershell
& $env:MIMO_PYTHON night-research/cycle8_verify_lemmas.py
& $env:MIMO_PYTHON night-research/cycle11_verify.py
night-research/maxsafe_enum.exe count 7 14
night-research/maxsafe_enum.exe count 6 11
night-research/cycle8_b_maxsafe.exe count 7 14 --force 24 --max-nodes 4000000
night-research/cycle8_b_maxsafe.exe first 7 14 --force 16 --max-nodes 3000000
# capacity decomposition cases — see CYCLE15_CAPACITY_DECOMPOSITION.md
```

## File index
- `CYCLE8_11_MAIN_RESULT.md` — rolling consolidated notes
- `CYCLE15_CAPACITY_DECOMPOSITION.md` — capacity table + geometry
- `SELECTION_THEOREM_CHECKLIST.md` — evidence matrix
- `CYCLE10_OCCUPANCY_SELECTION.md`, `CYCLE11_ORBIT_NECESSITY.md`
- `CYCLE12_K13_LAYER.md`, `CYCLE12_OMIT_MANDATORY.md`
- `CYCLE16_CENTER_NOT_SUFFICIENT.md`
- `CYCLE9_G1_NOTES.md`, `CYCLE9_G2_NOTES.md`
- `CYCLE9H_K9_128BIT_DESIGN.md` — K9 design only

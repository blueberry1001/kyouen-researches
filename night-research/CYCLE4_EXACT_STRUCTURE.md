# Cycle 4 — Exact small-board structure toward a non-trivial conclusion

## Checked

- Active checkout: `replicate-8x8-o-stratum` @ `db50e40`
  (`Complete 9x9 first-move classification: all 81 moves WIN`)
- GitHub `origin` as of this cycle:
  - `origin/main` @ `4152c1a` (factorial Holm documentation, 2026-09-05)
  - `origin/replicate-8x8-o-stratum` is **one commit behind** local (missing Cycle 3)
  - Open PR #15 `probe-two-stone-subsets` still DRAFT (medium 10×10 LOSS root)
  - Release `v1.0.0` unchanged; no newer classification release
- Spec: `docs/compose/spec/night-cycle4-exact-structure.md`
- New exact enumerator: `night-research/exact_structure_cycle4.py`
- Independent cross-check: `rust/independent-verifier` `classify-first` for n=3,4,5
- `git worktree add` for a fresh linked worktree was blocked by the session
  shared-registry guard; work proceeded additively under `night-research/`
  on the active research branch (see spec S2 workspace note).

## Exact new results

Forbidden-quadruple counts reproduce the published values (1, 14, 194, 826 for
n=2..5). Empty-board outcomes reproduce the certificate winners.

| n | winner | forbidden | reachable safe sets | first-move density | parity-locked outcomes? |
|--:|:---:|---:|---:|---:|:---|
| 2 | F | 1 | 15 | 1.00 | **yes** |
| 3 | F | 14 | 298 | 1.00 | **yes** |
| 4 | S | 194 | 5,811 | 0.00 | no |
| 5 | F | 826 | 151,394 | 0.36 | no |

**Parity locking (exact).** On n∈{2,3}, every reachable safe set with odd
cardinality is LOSS and every reachable safe set with even cardinality is WIN
(terminal layers included). On n=3 this means the entire game graph is a
complete outcome-grading by `k mod 2`; combined with Cycle 1 maximal sets
(all size 5), play is forced toward an odd terminal length. Locking **fails**
on n=4 and n=5 — so it is not a general law and not an F/S separator.

**Exact depth profiles (LOSS rate among safe k-sets).**

n=3 (locked): `k=1..5` LOSS rates `1,0,1,0,1`.

n=4 (S-board): interior LOSS peak at **k=2 (0.70)**; k=3 collapses to 0.029;
k=6 rises again to 0.647; terminal k=7 all LOSS.

n=5 (F-board): outcomes are labeled for the **player to move**, so a first
move is a **win** for the first player iff the resulting 1-stone position is
**LOSS** for the opponent. Hence k=1 `loss_rate=0.36` is exactly the
**winning** first-move density (9/25), not the losing one. Losing first moves
are the 16/25 = 0.64 k=1 positions that are WIN for the player to move. Shallow
k=2 LOSS rate is 0.067; LOSS concentrates near saturation (k=8: 0.839,
k=9: 1.000). Full-population profiles do **not** support a naive reading of
sample-based P9b as “a single mid-depth LOSS peak at k=4 on S-boards / k=5 on
F-boards”; the exact shape is multi-modal (especially n=4).

**First-move reply mobility (exact, n≤5).** After any first move on n=2..5,
**every** remaining cell is still legal (1 stone never completes a 4-set), so
reply mobility is constantly `n²−1`. Mobility does **not** distinguish winning
from losing first moves.

What *does* distinguish them is the opponent’s **winning-reply multiplicity**:

| n | first-move class | opponent winning replies |
|--:|---|---|
| 4 | all 16 first moves are LOSS | **9** or **12** (orbit-dependent; 8 cells each) |
| 5 | 9 WIN first moves | **0** |
| 5 | 4 corner LOSS first moves | **4** |
| 5 | 12 other LOSS first moves | **2** |

On the unique exceptional F-board n=5:

> A first move wins **iff** the opponent has zero winning replies.
> Losing first moves always give the opponent 2 or 4 winning replies, never 1.

Winning cells match the closed form `{(x,y): x+y even} \ {corners}`.
Rust `classify-first --size 5` agrees cell-for-cell with the Python enumerator
(same WIN set; winning replies e.g. corner `(0,0) → (3,0)`).

## Invariant audit (F-boards vs S-boards)

| candidate | separates F={1,2,3,5,6,9} vs S={4,7,8,10}? |
|---|---|
| empty-board winner | yes, but definitional |
| winning-first-move density | density 0 on S is definitional; non-trivial content is density=1 on every F n≤9 except n=5 |
| parity-locking of all safe-set outcomes by k | **no** (holds on F n=2,3; fails on F n=5 and S n=4) |
| legal reply count after first move | **no** (always n²−1 on measured boards) |
| forbidden-quadruple count | **no** (monotone in n) |
| H-dense | characterizes the exceptional F-board n=5, not S-boards |
| local/embedding rules (H3-abs, H-embed, H4 static w, local geometry) | already rejected in Cycles 1–3 |

Artifacts: `night-research/cycle4-density-table.json`,
`cycle4-exact-n{2,3,4,5}.json` (**authoritative per-board evidence**),
`cycle4-exact-structure.json` (regenerated aggregate n=2..5),
`cycle4-invariant-audit.json`, `cycle4-n5-orbit-mobility.json`,
`cycle4-n5-two-stone-loss.json`, `H_DENSE_PREREG.md`.

Note: `winning_reply_ids` in per-board mobility JSON may be capped at 8 ids
for n=4 (counts in `second_player_winning_reply_count` are complete).

## Non-trivial conclusion

**What the combined exact data now forces.**

1. **Winner sequence and first-move structure for n≤10 are complete enough to
   state a sharp classification of first-move rigidity:**
   - second-player boards `{4,7,8,10}`: no winning first move;
   - first-player boards `{1,2,3,6,9}`: **every** cell is a winning first move;
   - the sole exceptional first-player board in this range is **n=5**, with
     density `9/25` and winning set = even sublattice minus corners.

2. **Stone-count parity locking is a true theorem-shaped fact only for the
   tiny boards n∈{2,3}**, where the full reachable safe-set complex is graded
   by `k mod 2`. It dies immediately at n=4. Therefore no argument of the form
   “outcome = parity of some board invariant that locks play length” can
   survive contact with the certified sequence.

3. **Local reply mobility is the wrong invariant.** On n=5, winning and losing
   first moves are mobility-indistinguishable (always 24 replies). The exact
   discriminator is whether the induced position is a true LOSS for the player
   to move — i.e. whether *any* reply exists that is winning — not how many
   safe replies exist. On n=4, even universally losing first moves split into
   orbits with 9 vs 12 winning replies for the second player.
   Reminder: enumerator outcome is **player-to-move**. At k=1, LOSS count =
   winning-first-move count (n=5: 9 = density 0.36), not losing first moves.

4. **Any successful general law for kyouen outcomes must be global.**
   Embedding transfer, absolute-coordinate even-sum rules, static pair-witness
   counts, and 1-ply local geometry predictors are all empirically dead. The
   only standing cross-size regularity on first-move data is **H-dense**
   (among F-win n≤10, only n=5 has a losing first move) — and that statement
   is about an exceptional board, not about separating F from S.

5. **Evidence boundary vs GitHub.** The complete 9×9 first-move classification
   that upgrades density to 1.0 on n=9 exists locally at `db50e40` on
   `replicate-8x8-o-stratum` but has **not** been pushed to `origin`. Remote
   readers of GitHub still see center-witness wording in older snapshots and
   the factorial-Holm tip on `main`. Conclusions above that cite n=9 all-win
   rest on local Cycle 3 artifacts (`night-research/first-moves-9x9.csv`).

**One-sentence non-trivial conclusion.**

> For kyouen on n×n with 1≤n≤10, optimal-play outcomes are certified; first-move
> outcomes are completely classified and are **universal (all-win or all-loss)
> on every board except n=5**, where the winning set is exactly the even
> sublattice minus the corners; full safe-set outcome grading by stone-count
> parity holds only for n≤3; and because mobility/embedding/local-geometry
> invariants all fail, any further general law must explain the **global**
> position of n=5 as the unique partial board, not a local cell rule.

## Official-doc lag (unchanged from Cycle 3 list, partially already fixed)

- `README.md` now mentions all 81 first moves win (line ~80) — good.
- `docs/RESULTS_AND_IMPLICATIONS.md` §4 already lists 9×9 81/81 — good.
- `night-research/cycle2-density-table.json` still had n=9 status `partial`
  until Cycle 4 wrote `cycle4-density-table.json` with status `complete`.
- Push/land of `db50e40` remains an orchestrator/user decision.

## Next cycle candidates

1. Attempt **exact n=6** full safe-set profile only if memory/time allow; else
   exact n=6 first-move mobility via rust/C++ per-orbit (already known all-win).
2. Pre-register an **independent H-dense test** that does not peek at n≤10
   outcomes (structural rule freeze) — still open from Cycle 3.
3. Deepen n=5 LOSS-reply multiplicity: why only {2,4} and how it sits on D4
   orbits; compare to n=4’s {9,12}.
4. Do **not** re-solve 9×9 or 10×10 roots.
5. When authorized, push `replicate-8x8-o-stratum` / open PR so GitHub matches
   local complete 9×9 first-move classification.

## Deepening — n=5 two-stone LOSS geometry (Cycle 4 night follow-up)

Exact re-enumeration (`deepen_cycle4_geometry.py`, artifact
`cycle4-n5-two-stone-geometry.json`):

- Safe 2-stone positions: 300 = C(25,2); LOSS for player to move: **20**.
- The 20 undirected LOSS pairs are **exactly** the 20 directed
  “losing first move → winning second-player reply” edges
  (`equal=true`, no residual either side).
- **Endpoint typing:** all 20 pairs have **both** endpoints on losing
  first-move cells; 0 pairs touch a winning first-move cell; 0 mixed.
  Among C(16,2)=120 pairs of losing-first cells, only 20 are LOSS —
  co-location on losing cells is necessary but not sufficient.
- **Cell-class composition of the 20:** corner–odd-sum 8, odd-sum–odd-sum 8,
  corner–corner 4. Winning-cell geometry (center / edge-centers / interior
  diagonal) never appears.
- Chebyshev distance: 16 pairs at ℓ∞=3, 4 pairs at ℓ∞=4 — distance alone is
  not the rule.

**Refined structural reading on n=5.** The first-move dichotomy extends one
ply downward in a sharp way: the shallow LOSS layer at k=2 lives entirely on
the 16 losing-first cells, and coincides with the opponent’s winning-reply
graph from those cells. Winning first-move cells are “safe partners” at k=2
in the sense that no 2-stone LOSS contains them. This still does **not**
transfer via H-embed (already rejected).

## Cross-board exact snapshot

| n | winner | density | k1 LOSS rate (= winning first-move density) | mid-depth LOSS peak (k≥2, mixed) |
|--:|:---:|---:|---:|---|
| 2 | F | 1.0 | 1.0 | none (parity-locked) |
| 3 | F | 1.0 | 1.0 | none (parity-locked) |
| 4 | S | 0.0 | 0.0 | k=2 rate 0.70 |
| 5 | F | 0.36 | 0.36 | k=8 rate 0.839 |

Identity `k1_loss_rate == winning-first-move density` holds on all exact boards.

## Journey log (this cycle)

- `git worktree add` blocked → continued on active research branch with
  additive `night-research/` + compose spec (documented in spec).
- First-pass peak metric `argmax loss_rate` was dominated by trivial layers
  (k=0 on S-boards, terminal all-LOSS); fixed reporting to use interior peaks
  and full profiles.
- Sample-based P9b mid-depth peak did **not** reappear as a single exact peak
  on n=4/n=5 full populations — recorded as a nuance/correction, not as a
  refutation of the 8×8/9×9 *sample* finding on those larger boards.
- Rust `classify-first` matched Python exactly on n=3,4,5; strengthens trust
  in the new enumerator beyond certificate root labels.
- Review catch (C1): prose inverted k=1 loss_rate on n=5 — player-to-move
  labeling means LOSS@k=1 = **winning** first moves (9/25), not losing ones.
- Review catch (N1): first aggregate `cycle4-exact-structure.json` was stale
  (only n=5) because a later single-size run overwrote it; regenerated for
  n=2..5. Prefer per-n JSON when in doubt.
- Night follow-up: n=5 k=2 LOSS pairs ≡ winning-reply edges from losing first
  moves; both endpoints always losing-first cells; geometry split
  corner/odd-sum only.
- Re-review (general-2): C1 and N1 closed; identity safe to cite.

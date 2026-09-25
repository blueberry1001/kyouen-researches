# Killer-response diagnostic preregistration

Status: pre-data analysis plan. This file fixes the diagnostic before reading true response values for the five still-uninspected confirmatory LOSS parents. The two previously inspected maximum counterexamples remain calibration-only examples.

Provenance:

- branch: `probe-two-stone-subsets`
- blind-replication baseline: `b5172a4`
- preregistration parent HEAD: `a367b5764029de0b1838298b3306e7ace253fcab`
- semantic correction (pre-data): the blind fixed rule is the frozen **probe-score rule**, not immediate unique gain; the response-side gain ordering below is a separate diagnostic ordering
- sample-count correction (pre-data): seven blind LOSS parents exist, but only five are fresh for this killer hypothesis because the two maximum counterexamples were inspected before preregistration
- tie-semantics correction (pre-data): confirmatory thresholds use **distinct gain tiers**, not competition ranks, because a large top-gain tie must not make the second-best gain value look artificially weak
- blind LOSS parents: `2,9,33`, `4,9,33`, `9,12,33`, `9,19,33`, `9,23,33`, `0,31,36`, `0,36,44`
- calibration-only parents: `4,9,33`, `9,19,33`
- fresh confirmatory parents: `2,9,33`, `9,12,33`, `9,23,33`, `0,31,36`, `0,36,44`

The two previously inspected maximum counterexamples (`4,9,33`, `9,19,33`) are calibration examples only. They must not be counted as fresh confirmation of any hypothesis below. Their response rows may be reported descriptively, but all confirmatory counts and the predeclared interpretation use only the five fresh parents.

## Question

The frozen blind fixed rule ranks children by its preregistered probe score (for three-stone parents: final memo used at the 1,000,000-visited probe budget, descending, with the frozen tie-break). Some moves selected by that rule are nevertheless losing. The diagnostic tests a narrower downstream mechanism:

> after the frozen probe rule has selected a losing move, is that loss caused by one or a few opponent responses that look locally weak under an independent immediate-unique-gain ordering but are true minimax killers?

This is deliberately different from an average-response-strength hypothesis, and it does **not** claim that immediate unique gain is the original fixed rule. A parent may have many weak-looking responses while only one of them matters to minimax value.

## State/value convention

For each blind LOSS parent `S`:

1. Let `v_fixed` be the move selected by the already frozen blind probe rule, including its existing deterministic tie-break and original batch concatenation semantics.
2. Let `S1 = S + v_fixed`. It is now the opponent's turn.
3. Enumerate every legal opponent response `r` from `S1`.
4. Let `S2 = S1 + r`. It is now the original player's turn.
5. Solve `S2` exactly with the existing certified solver semantics.
6. `r` is a **killer response** iff `S2` is `LOSS` for the player to move. Thus the opponent can choose `r` and leave the original player in a losing state.

No probe estimate, memo size, timeout label, or heuristic value may substitute for the exact/certified outcome in the primary diagnostic.

## Frozen response-side diagnostic ranking

The opponent responses are **not** rerun through the blind probe rule. For every legal response `r`, compute its exact immediate unique gain at `S1`: the number of currently safe next candidates made unsafe by playing `r`.

Primary diagnostic order is `(unique_gain descending, move index ascending)`. This ordering is frozen here solely to ask whether minimax killers are hidden below locally attractive opponent replies; it is not described as production fixed-rule order.

Record three different notions of rank; they answer different questions and must not be substituted for one another:

- `move_rank(r)`: 1-based position under `(unique_gain descending, move index ascending)`. This is the operational rank for a deterministic top-k move search.
- `gain_competition_rank(r) = 1 + count{q : gain(q) > gain(r)}`. This is invariant to ordering inside an equal-gain tie, but it can skip integers when a higher tier contains multiple moves.
- `gain_tier_rank(r) = 1 + count{g : g is a distinct response gain and g > gain(r)}`. This is the ordinal rank of the distinct gain value itself and is the primary rank for the phrase "locally weak".

Example: if five responses tie at gain 10 and the next response has gain 9, that gain-9 response has `move_rank=6`, `gain_competition_rank=6`, but `gain_tier_rank=2`. It is second-best by the local score, not sixth-best. The earlier preregistration threshold on competition rank would therefore have produced a false positive whenever the top tiers were wide; this correction is made before reading any of the five fresh response-value datasets.

## Per-parent outputs

Record:

- `response_count`
- `killer_count`
- `killer_fraction = killer_count / response_count`
- `best_killer_move_rank = min move_rank among killers`
- `best_killer_gain_competition_rank = min gain_competition_rank among killers`
- `best_killer_gain_tier_rank = min gain_tier_rank among killers`
- `top1_has_killer`, `top3_has_killer`, `top5_has_killer` under deterministic move order
- `top1_gain_tier_has_killer`, `top3_gain_tiers_has_killer`, `top5_gain_tiers_has_killer`
- gain distribution for killers and non-killers separately
- for every response: state, move, gain, move rank, competition rank, tier rank, exact outcome

If `killer_count == 0`, the parent/value convention or upstream selected-move reconstruction is inconsistent with the claim that `v_fixed` loses; treat this as a hard audit failure, not as a zero-valued observation.

## Predeclared interpretation

The "locally weak killer" hypothesis is supported only if killers systematically appear below the top **distinct gain tiers**. There are only five fresh confirmatory parents, so do not fit a threshold post hoc. Report all five fresh raw `best_killer_gain_tier_rank` values, plus the move and competition ranks for transparency. Report the two calibration parents separately and never include them in confirmatory counts.

Strong falsification: all five fresh parents have `best_killer_gain_tier_rank <= 3`. In that case every failure has a killer among the three locally strongest distinct gain levels; the failure is not hidden in locally weak responses, and shallow adversarial checking of obvious high-gain replies is the better next hypothesis.

Positive signal: at least two of the five fresh parents have `best_killer_gain_tier_rank > 5` while still having at least one exact killer. Then the immediate-gain score itself is specifically hiding minimax-critical replies, motivating adversarial-width experiments. This `>=2/5` rule is fixed before inspecting any of the five fresh response-value datasets.

Operational top-k cost must be reported separately using `best_killer_move_rank`. A wide high-gain tie can make a locally strong killer expensive for deterministic top-k search without supporting the "locally weak" hypothesis; that is a different mechanism (tie width / strategy width).

Do not use the two already inspected maximum counterexamples to choose a new cutoff after seeing these results.

## Audit guards

Before accepting results:

- reproduce `v_fixed` from the frozen blind probe rule and its original stored probe rows for every parent; do not substitute unique gain for this reconstruction;
- verify every enumerated response is legal and the response set has no duplicates;
- verify exact outcomes are invariant under D4 canonicalization for a deterministic sample plus every killer state used in the summary;
- rerun at least one killer and one non-killer child per parent through the certified path independently of any shared memo process;
- verify `gain_tier_rank` is contiguous over distinct observed gain values starting at 1, while `gain_competition_rank` is allowed to skip integers;
- retain raw per-response rows so summary statistics are reconstructible.

This diagnostic is observational within already selected losing moves. It identifies where minimax-critical responses sit in a deliberately separate local ranking; it does not by itself prove that changing response order improves the full solver or game-playing policy.
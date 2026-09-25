# 9x9 fixed-rule provenance audit

Date: 2026-09-23

## Finding

Do not use the historical `b5172a4` first-LOSS positions as evidence about the
geometric immediate-gain / candidate-conflict-degree heuristic.

Two different objects are currently adjacent in the research trail:

1. `docs/10X10_PROBE_BLIND_VALIDATION.md` defines the historical 3-stone fixed
   rule as **final memo used, descending, after a 1,000,000-visited probe**.
2. `docs/9X9_TWO_STONE_PROBE_RESEARCH_NOTES.md` develops a geometric heuristic
   where, for a 3-stone parent, immediate gain equals candidate-conflict degree
   exactly, and analyzes the large historical counterexamples `4,9,33` and
   `9,19,33` through that geometry.

Those analyses can describe the geometry of the same parents, but they do not
by themselves explain why the historical *memo-probe* ordering put the first
LOSS at positions 16 and 13.

There is a second, stronger provenance problem already recorded in
`docs/BLIND_PROBE_FRESHNESS_AUDIT.md`: the historical probe runner reused one
solver across children. Its absolute memo count therefore accumulated roughly
1M per row, so sorting memo descending mostly reversed input order. That audit
explicitly says `b5172a4` is not a valid blind validation of an independently
measured `memo desc @ 1M` rule.

## Consequence

The following quantities remain valid as an audit trail for the historical
batch0 run, but should not be used as predictive evidence for either a fresh
memo probe or the geometric gain heuristic:

- fixed first-LOSS median 3.0;
- random median 6.0;
- solver-default median 3.0;
- the 16 / 13 historical positions for `4,9,33` / `9,19,33`;
- verdict C attached to that historical ordering.

The exact child WIN/LOSS outcomes themselves remain useful; the confound is in
the probe-derived ordering.

## Frozen separation for future work

Keep three labels distinct in every later table:

- `historical_cumulative_memo_order`: the `b5172a4` ordering, audit only;
- `fresh_memo_order`: one fresh solver process per child, as required by
  `BLIND_PROBE_FRESHNESS_AUDIT.md`;
- `geometric_gain_order`: exact 3->4 immediate unique-gain / conflict-degree
  ordering, with its own tie rule fixed before evaluating outcomes.

Do not transfer a success/failure position from one label to another.

## Corrective rerun is already complete

A repository audit after the provenance note found that the frozen fresh-solver
rerun had already been executed, frozen, revealed, and committed. Therefore it
must be used instead of proposing another rerun.

`results/10x10/blind-probe-fresh-revealed-analysis.json` reports, over the same
seven parents:

- fresh `memo desc @ 1M` median first LOSS: **15**;
- solver/input-order median first LOSS: **3**;
- exact random parentwise median-of-medians: **6**;
- fresh memo ordering worse than solver order on **7/7** parents;
- fresh memo ordering worse than the exact random median on **7/7** parents;
- first-LOSS rank sums: fresh memo **90**, solver **41**, random medians **38**.

This reverses the historical interpretation. The independently measured
absolute-memo rule is not merely weaker than the cumulative historical result;
on this frozen seven-parent cohort it is systematically bad at putting a LOSS
early.

The two historical large examples also remain bad under the corrected rule, but
with newly defined positions: `4,9,33` moves from historical 16 to fresh **19**
(two LOSS children), while `9,19,33` moves from historical 13 to fresh **16**
(one LOSS child). Their geometric structure is therefore still worth studying,
but now as possible structure behind a genuine fresh-memo failure rather than
as an explanation of the old cumulative ordering.

The strongest corrected example is `4,9,33`: its two LOSS children occupy the
last two positions under fresh memo order (first LOSS 19), giving LOSS-early AUC
0.0, while solver/input order finds a LOSS at position 3. `9,12,33` is also
extreme: its sole LOSS is ranked last (position 20), although solver/input order
places it at 18. This suggests that high final memo occupancy at a fixed visited
budget may be anti-correlated with the target LOSS label in the sparse-LOSS
parents, rather than merely noisy.

## Priority change

Do **not** rerun the same corrected seven-parent experiment. The next clean
question is why `memo desc` fails so consistently. Preserve the revealed cohort
as diagnostic data and test hypotheses that were not used to choose the rule.
A particularly cheap first diagnostic is the sign question: evaluate the
already-recorded fresh memo values with `memo asc` descriptively, clearly marked
post-hoc and without treating it as a validated replacement rule. If the sign
nearly reverses the ordering on sparse-LOSS parents, preregister any subsequent
validation on new parents before claiming predictive value.

This audit introduces no new success threshold. It separates historical,
corrected, and geometric orderings and records the already-completed corrective
result so future work does not repeat it.

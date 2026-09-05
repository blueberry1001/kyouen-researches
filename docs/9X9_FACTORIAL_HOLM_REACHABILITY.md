# 9×9 factorial: Holm reachability monitor

## Purpose

The pre-registered factorial analysis has four exact two-sided binomial tests followed by Holm correction at family-wise alpha 0.05.

During a long exact-solver run, raw remaining-parent counts are not enough to tell whether a comparison can still become significant. A safe early-stopping diagnostic is therefore useful.

## Optimistic lower bound

For each comparison, let

- `a` = currently observed baseline-only LOSS discordances,
- `b` = currently observed component-added-only LOSS discordances,
- `R` = unresolved parents remaining in that comparison.

Construct the most favorable possible completion by assuming all `R` unresolved parents become discordant and all fall on whichever side is currently larger. This maximizes the final imbalance and therefore minimizes the attainable two-sided exact binomial p-value.

This assumption is intentionally over-optimistic: in reality some unresolved parents will be concordant, and outcomes across the four comparisons are not freely assignable. Therefore the resulting p-values are lower bounds on what is attainable, not forecasts.

After constructing this optimistic raw p-value independently for all four comparisons, apply the same Holm adjustment as in `scripts/analyze-9x9-factorial-outcomes.py`.

If a comparison's optimistic Holm-adjusted p-value is already >= 0.05, that comparison cannot possibly reject at the end of the run. If all four are >= 0.05, then no rejection in the pre-registered family is mathematically reachable and further solving cannot change the family-level null result.

This is stronger than checking only whether each raw p-value can get below 0.0125. The 0.0125 threshold is necessary for the smallest p-value to start Holm's step-down procedure, but later comparisons may reject at the looser 0.05/3, 0.05/2, and 0.05 thresholds after earlier hypotheses reject. Applying Holm to the entire vector of optimistic lower bounds captures those later-stage possibilities as well.

## Script

Use `scripts/check-9x9-factorial-holm-reachability.py`.

Example:

```bash
python scripts/check-9x9-factorial-holm-reachability.py \
  E_at_O0:12:7:100 \
  O_at_E0:5:8:60 \
  E_at_O1:11:9:100 \
  O_at_E1:3:4:50
```

Each argument is:

`LABEL:baseline_only:added_only:remaining`

The script reports the optimistic final discordant counts, optimistic raw exact p-value, optimistic Holm-adjusted p-value, and whether rejection is still mathematically reachable.

## Interpretation constraint

This diagnostic must not be used to change the hypothesis, score definition, direction, alpha, or allocation after seeing outcomes. It is only a reachability calculation under the already pre-registered family of tests.

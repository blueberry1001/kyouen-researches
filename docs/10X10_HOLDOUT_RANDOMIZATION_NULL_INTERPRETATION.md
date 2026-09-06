# 10x10 holdout: interpretation of the exact random-order null

Date: 2026-09-06

This note is committed before any holdout probe outcome is analyzed. It does not change the preregistered ranking rule, primary 1M budget, frozen parent set, or endpoint. It only fixes the interpretation of the exact null calculation added in `scripts/analyze_probe_holdout_exact_null.py`.

## What the exact convolution tests

For a fixed parent with `m` children and `l` exact LOSS children, if the children are placed in a uniformly random order, the first-LOSS rank has

```text
P(R=r) = C(m-r, l-1) / C(m,l).
```

The script convolves these parent-specific distributions and uses

```text
T = sum_i R_i
```

as the statistic. The lower-tail probability

```text
P(T <= T_observed)
```

therefore answers this precise question:

> Conditional on the frozen parents and their exact LOSS/WIN labels, how often would independently random candidate orders across those parents obtain a summed first-LOSS rank at least this small?

This is an exact random-order benchmark. It correctly handles different `(m,l)` values, discreteness, and ties without Monte Carlo error.

## What it does not test

The 11 holdout parents were not sampled uniformly at random from a formally specified population of all 10x10 LOSS parents. They were selected deterministically from the available eligible pool under the frozen selection rule.

Therefore the convolution p-value must **not** be described as:

- a population-level p-value for all 10x10 LOSS parents;
- a probability that the heuristic will generalize to an arbitrary future parent;
- evidence that parent-to-parent effects are independent samples from a broad population distribution.

Its randomization is over **candidate order within each fixed parent**, not over the choice of parents.

## Consequence for reporting

The primary result should be reported in two layers.

1. **Conditional random-order result**
   - observed summed first-LOSS rank;
   - exact random-order expected sum;
   - exact lower-tail p-value from the convolution.

2. **Holdout replication effect size**
   - all 11 parent-level first-LOSS ranks;
   - better/tie/worse versus each parent's exact random median;
   - mean and median parent AUC;
   - number of parents in which the preregistered rule improves over random.

The second layer is what supports or weakens the claim that the previously discovered direction replicates across new parents. The first layer quantifies how unusual the observed rank performance is relative to random candidate ordering on this *specific frozen holdout set*.

## Why this matters here

The ranking rule can use probe outcomes that sometimes prove LOSS or WIN within the 1M budget. Consequently, the algorithm is not a score statistically independent of the exact label: proving LOSS is itself useful computational evidence. That is allowed—the research question is whether the whole preregistered probing procedure finds LOSS children early—but it reinforces that the exact-null p-value is a **procedure-vs-random-order benchmark**, not a generic no-association test between an externally fixed feature and LOSS labels.

No change to the preregistered decision rule follows from this note. The holdout outcome must still be accepted without changing score direction, parent set, budget, or primary endpoint after inspection.

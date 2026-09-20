# 10x10 holdout: exact random-rank null correction

Date: 2026-09-06

This correction is committed **before any holdout probe output exists**. It does not change the frozen parent set, 1M budget, fresh-Solver isolation, ranking rule, or first-LOSS endpoint.

## Problem found in the preregistered analyzer

The analyzer classifies each parent as `better / tie / worse` according to whether the corrected first-LOSS rank is below / equal to / above the exact random median, then applies a sign test with null probability 0.5 after discarding ties.

That sign test is not generally exact here. The first-LOSS rank under a random permutation is discrete and asymmetric. For a parent with `m` candidates and `l` LOSS children,

```text
P(R = r) = C(m-r, l-1) / C(m, l),   r = 1,...,m-l+1.
```

Because of discreteness, `P(R < median)` and `P(R > median)` need not be equal, and conditioning on `R != median` need not produce probability 0.5. Therefore the binomial sign-test p-value is retained only as the originally planned descriptive quantity, not as the calibrated primary random-order p-value.

## Correct exact null

Keep the already frozen endpoint: smaller first-LOSS rank is better.

For parent `i`, let `R_i` have the exact random-permutation distribution above, conditional on that parent's observed `(m_i, l_i)`. Define

```text
T = sum_i R_i.
```

The observed statistic is the sum of the preregistered corrected-rule first-LOSS ranks over all frozen holdout parents. Under the random-order comparator, convolve the exact parent-specific PMFs and report

```text
p_exact = P(T <= T_observed).
```

This uses all rank information, automatically accounts for different LOSS densities, handles ties/discreteness correctly, and requires no simulation.

The expected null sum is

```text
E[T] = sum_i (m_i + 1)/(l_i + 1).
```

## Interpretation

- `p_exact` is the primary calibrated comparison against uniformly random candidate order.
- The preregistered `better/tie/worse` counts and median-based sign test remain in the output for transparency, but are secondary/descriptive because their nominal binomial null is not exact.
- Parent-level AUC remains secondary.
- No score direction, parent membership, budget, or outcome-dependent rule may be changed after holdout results are observed.

Implementation is frozen in `scripts/analyze_probe_holdout_exact_null.py`.
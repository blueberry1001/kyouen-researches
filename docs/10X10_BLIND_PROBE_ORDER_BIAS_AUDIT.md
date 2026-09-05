# 10x10 blind probe order-bias audit

This note audits the 3-stone blind validation at commit `b5172a4` without rewriting any historical result files.

## Confirmed implementation behavior

`run_blind_probe_batch.py` invokes one `probe_cert_solver` process for an entire child batch. In `kyouen_solver_10_kyoenc4_resume_4.inc`, one `Solver solver(shrink, load)` is constructed outside the loop over input states. After each state, the CSV `memo` field is written as `solver.memo_used()`.

The blind analyzer fixes the 3-stone rule as:

```python
3: ('memo', 'desc', 1_000_000)
```

and sorts the emitted `memo` value descending.

Therefore `memo` is not a child-local probe feature. It is the amount of memo occupied by the shared solver after all previously processed children plus the current child. Candidate evaluation order is part of the feature.

## Observed consequence in the historical CSV

For the 3-stone rows in `results/10x10/blind-probe-rankings.csv`, `probe_memo` rises with solver-default/input order. The resulting `fixed_rank` is the reverse of `solver_default_rank` (`20,19,...,1` versus `1,2,...,20` for each 20-child parent shown in the historical validation).

A read-only checker was added as `scripts/audit_blind_probe_order_bias.py`. It verifies per parent:

- strict monotonicity of `probe_memo` in solver-default order;
- whether `fixed_rank == n + 1 - solver_default_rank` for every row;
- first-LOSS positions under fixed/reverse and solver-default orders.

## Interpretation correction

The historical facts that remain useful are the exact child outcomes and the discovery/classification of new LOSS parents. The reported 3-stone fixed-rule first-LOSS statistics, however, must not be interpreted as evidence that 1M memo probing predicts promising children: on this data the rule is confounded with candidate order.

In particular, the reported median fixed first-LOSS rank 3.0 versus random median 6.0 is also the performance of reversing the input order. It cannot be attributed to the intended probe signal without a corrected rerun.

The `C` success label should therefore be treated as **not established for the probe heuristic** until an order-independent measurement reproduces it. This does not invalidate exact WIN/LOSS classifications.

## Corrected rerun design

The cleanest primary rerun is candidate-independent probing:

1. construct/reset a fresh `Solver` for every child (or provide an explicit full memo reset proven equivalent);
2. apply the same per-child visited budget;
3. record child-local `visited`, `maxdepth`, and final memo occupancy;
4. rank only after all probes are complete;
5. keep the already-revealed exact outcomes frozen and evaluate the corrected ranking on exactly the same parents/children.

As a separate diagnostic, preserve the shared-memo solver but repeat each parent in forward, reverse, and several deterministic shuffled child orders. If rank changes strongly with input order, that directly measures the contamination.

Always include two cheap baselines in the corrected report: solver-default order and **reverse solver-default order**. The latter is essential because it is what the historical 3-stone fixed rule effectively measured.

## Priority

Before spending more exact-solver time on new 10x10 parents, rerun the existing blind children with independent probe state. Exact labels are already available, so this isolates the heuristic question at much lower cost than discovering more LOSS parents.

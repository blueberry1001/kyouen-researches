# Cache-aware bucket-order equivalence proof

Preregistered experiment: `10x10-cache-aware-bucket-order-optimization`

Frozen baseline order for a child `c` is the lexicographic key

`(cache_priority(c.cached), c.count, c.key)`

with priorities `cached LOSS = 0`, `unknown = 1`, `cached WIN = 2`.

The proposed bucket implementation first partitions children by the first component of that key, in priority order 0,1,2, then sorts each bucket by the remaining key `(count,key)`, and concatenates the buckets in priority order.

For any two distinct children `a,b`:

- If `cache_priority(a) != cache_priority(b)`, both implementations order them solely by that priority, so their relative order is identical.
- If `cache_priority(a) == cache_priority(b)`, both implementations compare exactly `(count,key)`, so their relative order is identical.

Therefore every pair has the same strict ordering relation in both implementations. Since canonical child keys are deduplicated before `order_children`, the solver domain has no duplicate-key ambiguity. Hence both procedures produce exactly the same total child-key sequence for every solver-valid input.

The deterministic executable check in `scripts/test_cache_aware_bucket_order_equivalence.py` was also evaluated with frozen seed `0xCACEA11E`: all 10 explicit edge cases plus 20,000 random unique-key fixtures passed, for 20,010/20,010 cases.

This establishes only the pure ordering transform. It does **not** replace the preregistered integration hard gate: after the C++ bucket implementation is introduced, the frozen C1 12-parent cohort must still match the single-sort implementation exactly on outcome, visited, memo, maxdepth, all depth-visited values, root diagnostics, and memo instrumentation before any timing result may be interpreted.

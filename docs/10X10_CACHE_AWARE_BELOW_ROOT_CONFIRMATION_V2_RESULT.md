# 10x10 cache-aware below-root ordering confirmation V2 — result: INCOMPLETE

Prereg: `docs/10X10_CACHE_AWARE_BELOW_ROOT_CONFIRMATION_V2_PREREG.md`
(prereg commits `cd151c3` text + `6a9bbab` machine manifest)
Branch: `preregister-10x10-cache-aware-below-root-confirmation-v2`
Base: `d9b9a0f` (C1 end). Freeze commit: `7caa7e9` (tooling + execution manifest).
End SHA: `d87b1e8aaff31628016f8ad89925bd7825cc1b57` (report commit; push receipt follows).

## 1. Headline

The confirmatory endpoint is **INCOMPLETE**, per frozen prereg §7:
rank 7 parent `1,12,80` exceeds the frozen memo capacity
(shrink=0/load=90) under **both** conditions, so no primary ratio exists
for 1 of 12 parents. No PASS/FAIL judgment is made; no R statistics are
computed on the reduced denominator.

C1 (`d9b9a0f`: median R 1.162, 12/12, criterion PASS) is retained as a
fixed-cohort causal finding. No generalization claim is made.

## 2. Attempt log (all 24 parent-conditions attempted, rank order)

| rank | parent | A | B |
|---|---|---|---|
| 1 | 12,21,58 | WIN 41253019 | WIN 48565266 |
| 2 | 0,19,95 | WIN 40334044 | WIN 48122261 |
| 3 | 2,11,61 | WIN 27789159 | WIN 32749276 |
| 4 | 1,27,61 | WIN 16020139 | WIN 18775664 |
| 5 | 1,68,74 | WIN 14174908 | WIN 16534371 |
| 6 | 0,7,67 | WIN 33663004 | WIN 39772866 |
| 7 | 1,12,80 | **TableFull** | **TableFull** |
| 8 | 2,43,60 | WIN 10890815 | WIN 12698786 |
| 9 | 23,37,45 | WIN 11864773 | WIN 13822908 |
| 10 | 1,6,51 | WIN 10931142 | WIN 12786596 |
| 11 | 12,13,67 | WIN 6524427 | WIN 7563460 |
| 12 | 12,25,71 | WIN 13528345 | WIN 15785216 |

22/24 runs complete (all WIN, 0 timeouts); 2/24 solver-capacity failures.
Counterbalancing followed the frozen rank rule throughout
(odd rank A-first, even rank B-first). No parent added/dropped/replaced.
No early stopping: after the rank 7 A failure, B was attempted, then
ranks 8–12 were completed in order.

NOTE: visited numbers above are raw completion facts from committed
CSVs/runner logs. Per the frozen incomplete-endpoint rule, **no R ratios,
medians, means, counts, sign tests, or secondary mechanism statistics are
computed or judged here**.

## 3. Failure evidence (rank 7, `1,12,80`)

- A (`cache-aware`): rc=3, `table_full=1`, memo high-water 477425788,
  ~1834 solver seconds, maxdepth 19.
- B (`cache-blind`): rc=3, `table_full=1`, memo high-water 512338741,
  ~1780 solver seconds, maxdepth 19.
- Failure stdout/stderr preserved in
  `results/10x10/cache-aware-below-root-confirmation-v2/raw/1_12_80_cache_{aware,blind}/`
  (no `depth_raw.csv`: the solver threw before the instrumentation flush).
- Both conditions failed deterministically at the same capacity wall, so
  this is not a flake or a machine interruption (no rerun permitted beyond
  the completed fresh attempts). B's higher high-water mark is consistent
  with blind ordering visiting more nodes, but no inference is drawn.

For scale: the heaviest C1 parent needed ~85M memo entries; `1,12,80`
needs >512M under identical settings — roughly 6x heavier. The
SHA256-ranked confirmation cohort simply contains a parent outside the
frozen solver's capacity envelope.
## 4. Verifier

`scripts/verify_10x10_cache_aware_confirm_v2.py`: **FAIL** (exit 1) at the
cohort-completeness gate:

`cache-aware parent set differs from frozen cohort: missing=['1,12,80']`

Full output saved as `verifier.log` next to the raw outputs. Per protocol,
no primary analysis was run (analyzer never executed). Manifest provenance
is untouched: no solver/runner/verifier/analyzer file changed since the
freeze commit (only result files were added).

## 5. Checklist answers

1. branch/final SHA: confirmation-v2 branch / (see End SHA above).
2. prereg/freeze SHAs: `cd151c3` + `6a9bbab`; freeze `7caa7e9`.
3. binary SHA256: `55fa84a1b9c68073f9690b25e1e10b487f8070f8a028aa7e14926b2ef63cd7a5`
   — byte-identical rebuild of the C1 binary (matches C1 manifest).
4. 24/24完了数: 22 complete + 2 TableFull; 24/24 attempted.
5. failures/timeouts: 2 TableFull (rank 7 A+B); 0 timeouts; 0 crashes.
6. verifier: FAIL (completeness gate; see §4).
7. A/B outcome一致: 11/11 completed pairs agree (all WIN); rank 7 unknown.
8–14. parent別R / median / gmean / aggregate / improved-tie-worse /
   success / sign-test: **N/A — endpoint incomplete, not computed.**
15–17. secondary timing / memo reuse / depth deltas: **N/A — not analyzed.**
18–19. C1 effect-size比較 / pooled 24: **not performed.**
20. generalization claim: **NO.** C1 stands alone.
21. next: see §6.
22. push: yes (this branch only).
23. main: untouched (refs verified).

## 6. Next steps (requires a NEW prereg; nothing starts inside C2)

Most direct: same frozen 12-parent cohort, larger memo capacity sized
from the failure high-water marks (>512M entries + margin), identical
A/B protocol, all 24 runs fresh (current 22 raws must NOT be mixed in).
Capacity sizing uses failure evidence only — no A/B ratio is touched.

Alternative: a fresh frozen cohort with a preregistered feasibility rule.

Note the trap: screening candidates by exact difficulty after seeing
these results would be outcome-based selection. Any screen must be
defined before A/B results exist for the new cohort.

Also worth preregistering alongside: the heavy-tail observation (one
SHA256-random parent 6x heavier than the C1 max) matters for capacity
planning of any future exact-solve campaign.

## 7. Upstream audits (added by repo owner during the campaign)

* `scripts/preflight_cache_aware_confirm_v2.py` (`090c9a3`): post-campaign
  run fails ONLY on its clean-start clause (outputs exist, as designed);
  every seal check ahead of it passed — cohort 12/12 order, binary SHA,
  all include SHAs, all 4 tool SHAs, regression.log SHA, 12-entry
  counterbalanced run order. The frozen seal held end to end.
* `scripts/audit_cache_aware_confirm_v2_outputs.py` (`0c8afd4`): fails
  exactly on `missing=[('1,12,80','cache-aware'),('1,12,80','cache-blind')]`,
  i.e. the same TableFull pair — no other bookkeeping complaint.

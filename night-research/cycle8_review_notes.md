# Cycle 8 critical review notes

Reviewer pass: re-ran `cycle8_verify_lemmas.py` (all PASS), independent `cycle8_lib` recompute of claims 1–6, cross-checked report vs `results/cycle8_*.json` / `night-research/cycle8_cd_result.json` / `night-research/cycle8_a_result.json`.
Did **not** re-run force_2_2@K=14 UNSAT, n=7/n=6 full enum, or any git worktree/rebase/merge/push.

## Verdict

**Status: success.** Main claims hold against bins and JSON artifacts. No critical error (wrong counts, sample-as-complete, circular verify, hardcoded answers).

## Claims checked

| Claim | Result |
|---|---|
| 8 d=5 pairs; 9/5/5 on (0,8); center XOR phase | PASS — pairs match `D5_PAIRS`; all inter-orbit; perfect matching on 16 |
| Unique 5→5 exchange under D4 | PASS **with orientation** — center-first directed exchange key = 1 (`0x801000424`↔`0x920009`); pair/symdiff keys = 1; unoriented exchange keys = 2 |
| 224/224 unique 13-completion among the 16 | PASS |
| min_det=2 all 16 n=7; n=6 0/464 unique pair; hist 3:160,4:240,5:40,6:24 | PASS |
| (2,2) unused on the 16; conditional max = 13 via enum upper + K=13 witness | PASS — B JSON search for K=14 unfinished; report correctly cites complete enum |
| Occupancy exactly 2 types among 16 | PASS — matches Lemma 4 table |
| n=6: no empty orbit; (2,2) analog 360/464; d*_inter=1; ~64% ρ=1 (296/464) | PASS |
| Verify script recomputes, not hardcoded | PASS |

## Non-critical findings (fixed in report where prose was wrong)

1. Lemma 3 table said「304 本の集合が ρ=1」— **304 is pair/edge count** (`n_pairs_d1`); set count is **296/464**. Fixed in report.
2. Oriented vs unoriented exchange uniqueness should state center-phase orientation (a_verify asserts EX=1; verify_lemmas allows ≤2).
3. Lemma 2 “no 13-corridor / full-board width 12” uses **single-stone add/remove** move graph + inherited completeness of the 16 K=14 sets. Unique completion alone does not discuss size-13 1-swaps outside max cones. Clarified in report.
4. `cycle8_a_verify.py` hardcodes `th_full=12` (existence lives in template JSON explicit path). Acceptable but weak independence.
5. Verify `k13_witness_with_22` checks only one (2,2) cell; B package claims all four.
6. Verify n=6 min_det only proves no unique *pair*; full hist is package C.
7. `cycle8_b_conditional_max.json` field `conditional_max.force_2_2=13` mixes witness lower bound with enum upper bound; search for K=14 not finished.
8. Cosmetic: 「弃却」→「棄却」; verify.json `pass: 1` int for k13 check.

## Residual risk

All Cycle 8 lemmas inherit completeness of `maxsafe_n7_K14.bin` (16) and `maxsafe_n6_K11.bin` (464). Not re-verified this cycle (spec forbids).

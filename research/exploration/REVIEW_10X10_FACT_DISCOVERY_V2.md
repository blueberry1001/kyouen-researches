# REVIEW V2: 10×10 fact discovery (post f09bfb2)

Scope: re-review after safety fix f09bfb2. Heavy enumerations not re-run. Witnesses re-checked with independent exact determinants (collinear + 4×4 circle det over ℚ). Point index convention `i → (i mod n, i div n)` confirmed against F-BA coordinates.

## 1. Spec compliance

- T1/T3/T7 PASS (as before).
- T2 nits remain: `status: in-progress` (acceptance wants `designed`); `commits:` placeholder unfilled.
- **T4/T5 unmet, checkbox overclaim.** Acceptance requires the minimum size to be *確定* via integer enumeration with a complete flag. 10×10 is only bracketed **6 ≤ K_min ≤ 11**; `fact_10x10_k6.json` is `complete:false` (789M nodes). Both boxes are `[x]`. The gap *is* honestly stated in findings (F-AK: 「6..11 の間で未確定」, F-AZ, DISCOVERY_SUMMARY 未解決 #1) — but not in the spec task list.
- T6 PASS now. n=9 degrees (`fact_9x9_point_degrees.json`, 81 values) and n=10 degrees (`fact_10x10_two_stone_orbits.json` `point_degrees`, 100 values) are comparable full arrays; circle spectra n=8/9/10 exist. F-BB does the comparison. Shared-edge structure (S2 「など」) still absent; not in T6 acceptance.
- T8 checked `[x]` before this review cleared — premature.

## 2. Correctness

Independent re-check (all PASS):

| Witness | Safe | Maximal |
|---|---|---|
| F-BA n=7 `[1,9,22,23,27,44,45]` | yes (C(7,4)=35 clean) | yes (42 outside blocked) |
| F-AK 10×10 size-11 `[11,20,23,32,43,50,59,63,68,81,98]` | yes (330 subsets) | yes (89 outside blocked) |
| F-AK size-12, F-AM n=3..6, F-AS 8×8/9×9 | yes | yes |

K_min(7)=7 is sound: k=4,5,6 non-existence stays valid even under the old unsound enumerator (it searched a *superset* of maximal-safe sets; zero found a fortiori applies). F-BA's independence argument is correct.

F-AE matches `fact_10x10_geometry.json`: corner min 1515, max 2499 at r²=4.5 (not center 2401 @0.5), non-monotone pairs 2409>2401 and 2395>2359, bin 12.5 spread 2301..2325. F-BB matches `fact_9x9_point_degrees.json`: min 978, max 1728 at exact center (idx 40), mean 1439.60, Σd = 4×29152 = 116608.

No positive existence claim is unsafe/false. F-AT size-10, F-AL second size-11, F-AR old n=7 witness, F-AU border bias are retracted by F-AZ + the block at findings.md:913-918.

Nit: `fact_verify_claims.py` 20/20 PASS, but `check("AK size11 still listed", True)` is vacuous and no check re-tests witness safety.

## 3. Consistency

- **Residual:** F-AL/AR/AT/AU bodies still read as live claims (F-AT title 「サイズ 10 の極大安全配置が存在する」, 確信度 高) with no inline pointer to F-AZ. A reader stopping inside those sections can still take an invalid witness as true. Corpus-level truth state is corrected; per-finding text is not.
- `fact_kmin_n7_safe.json` `complete:true` with `found:true` means "not timed out" (search stops at first hit) — fine for existence, misleading label vs spec's complete-flag contract.
- Empty `fact_10x10_minmaximal.json` (0 bytes) still committed. `experiments.jsonl` still has no entries. DISCOVERY_SUMMARY is now accurate (gap 6..11 stated).

## Conclusions

- **Spec compliance:** partial — T6 fixed; T4/T5 acceptance still unmet for 10×10 and are checked off anyway; T2/T8 bookkeeping stale.
- **Correctness:** pass — both key witnesses independently safe+maximal; no false positive existence claim survives.
- **Consistency:** minor residuals — inline retraction pointers missing on F-AL/AR/AT/AU; `complete` flag semantics; empty artifact.

**No critical.** K_min(10) ∈ 6..11 remains the real open gap and is honest in findings, dishonest only in the T4/T5 checkboxes.

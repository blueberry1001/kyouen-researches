# REVIEW: 10×10 fact discovery (155a143..9ac53bd)

Scope: spec T1–T8, findings F-AD..F-AW (plus F-AX), artifacts under `research/exploration/`, scripts under `scripts/analysis/`. Heavy enumerations not re-run; claims cross-checked against committed JSON and cheap local recomputation (4-point determinant, maximality of published examples).

## 1. Spec compliance (T1–T8)

- T1 PASS — gpcc 9×9 results committed (fd91c28); base 155a143 equals origin/main; S2 documents the upstream premise.
- T2 PASS (nits) — spec exists at the required path. Status field is `in-progress` (sibling delivered specs use `delivered`); T1–T7 checkbox flips are uncommitted working-tree edits; frontmatter `commits:` placeholder unfilled.
- T3 PASS — `fact_10x10_two_stone_orbits.{json,csv}`: 120 orbits, representatives, Σd 3030–4998; member sum recomputed = 4950.
- T4 CRITICAL unmet — acceptance requires the minimum size to be *settled* by integer enumeration. Only k=4,5 are complete (empty, tool sound); k=6..10 incomplete. The "size-10 exists ⇒ K_min≤10" evidence is invalid (see §2), so the minimum is not determined.
- T5 CRITICAL unmet — same object as T4; "合法手 0 の最小石数" is only bracketed. One valid size-11 example exists (F-AK); the exact minimum is unknown.
- T6 CRITICAL unmet — circle-size spectra for n=9 and n=10 exist and are comparable; point-degree distribution exists only for 10×10 (`fact_10x10_geometry.json`, two-stone JSON). No n=9 point degrees, so the required n=9,10 comparable JSON is missing. Shared-edge structure (S2 target T-F) is absent entirely.
- T7 PASS (nits) — F-AD..F-AX use the standard 8-field format with reproduce commands; some evidence is ephemeral (§3).
- T8 open — this review; criticals below must clear before delivery.

## 2. Correctness

Recomputed and OK: 120 orbits / Σd range / corr 0.27; F-AF ranks 5 and 26 ({73,66} is rank 28 = max); circle split 12,170 with Σ C(k,4)=48,513 and hist {4:10868,5:400,6:600,7:16,8:261,10:16,12:9}; 12-point circles 1/4/9/21 with r²-family decomposition; 16 primitive collinear dirs summing 5,928; run-hist Σ C(L,4)=5,928 (n=10) and 10,428 (n=11); triple completion hist sums to 4×54,441; F-AX inequality.

**CRITICAL — "found" sets are never checked for safety.**
`fact_10x10_triple_cover.cpp` and `fact_kmin_general.cpp` only test that every outside point is blocked; they never verify that S itself contains no forbidden quad. `Engine.is_maximal` in `fact_10x10_maximal_sample.py` has the same hole. (`fact_10x10_maximal_fast.cpp` builds via `safe_add` and is sound.) Consequences:

- F-AT: all three size-10 examples in `fact_10x10_size10_geometry.json` contain collinear quads, e.g. (1,2,3,4) = (1,0)..(4,0). "サイズ 10 の極大安全配置が存在する / K_min ≤ 10" is false as delivered. Correct bracket: **6 ≤ K_min(10) ≤ 11**.
- F-AL: the second size-11 witness `[0,1,2,3,4,5,6,10,11,20,27]` has seven collinear points on y=0. The "structurally distinct types" claim collapses to one valid type (F-AK).
- F-AR: K_min(7)=7 witness `[0,2,4,9,20,26,44]` contains concyclic quad {(2,0),(4,0),(6,2),(2,6)} (center (3,3), r²=10). Claim unsupported (k=4,5,6 non-existence remains valid).
- F-AU: "small maximal sets hug the border" is built on those invalid size-10 examples (border 8/10). The one valid size-11 (F-AK `[11,20,23,32,43,50,59,63,68,81,98]`) is only 4/11 border. Overclaimed.
- Survives: F-AK size-11/12 examples (re-checked safe + maximal), F-AJ k=4,5 non-existence, F-AM n=3..6 examples, F-AS greedy examples.

**CRITICAL — F-AE contradicts its own artifact.**
"中心からコーナーへ向かうほど単調に減る" is false (2401@r²=0.5 → 2409@2.5 → 2499@4.5, then 2359@6.5 < 2395@8.5). "半径ビンごとに min=max" is false (r²=12.5 bin: min 2301, max 2325). Max is at r²=4.5, not the exact center; the gradient story is only qualitative.

## 3. Codebase consistency

Format, paths (`scripts/analysis`, `research/exploration`), and C++ reproduce CLIs (`exact_k 5`, `tc 11 60`, `kg 7 4 10 300`) all match conventions.

Nits:
- `DISCOVERY_SUMMARY_10X10.md` stale: cites "F-AD..F-AQ" (actual F-AX), and its 未解決 list ("6..11、サイズ 10 が存在するか") contradicts its own body ("サイズ 10 が存在、6≤K_min≤10").
- F-AV/F-AT/F-AS cite "本セッション/本コミットの実行ログ" that are not committed; F-AV has a script but no JSON artifact despite the raw-data contract.
- Empty artifact committed: `fact_10x10_minmaximal.json` (0 bytes).
- `research/experiments.jsonl` (used by earlier research cycles) has no entries for this work.
- Spec working tree: T1–T7 marks uncommitted; status left `in-progress`.
- F-AD's midpoint 27/24 counts leave 69 mixed-parity orbits unmentioned (not wrong, just incomplete).

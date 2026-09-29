# df-pn 回帰・交差検証・追い出し試験の記録（2026-09-29 夜）

commit: `cabece2`（本ファイルは次 commit で追加）.
solver: `cpp/solvers/kyouen_dfpn_root.cpp`（unified logging + mask hygiene + --roots-csv）.
machine: 19 GB RAM / 16 core WSL.

## 1. 空盤回帰 n=4〜7（全て既知勝敗と一致）

| n | 結果 | expansions | wall |
|---|------|-----------|------|
| 4 | LOSS | 239 | 0s |
| 5 | WIN | 847 | 0s |
| 6 | WIN | 55,561 | 0s |
| 7 | LOSS | 2,123,417 | 18s |

## 2. DFS との途中局面照合（n=6, n=7）

同一 CSV（`canonical_parent,move` 形式、20+21 行）を DFS solver
（`kyouen_solver_6/7_root.cpp`）と df-pn（`--roots-csv`）の両方に与え、
行ごとに勝敗を比較。

**約束の違いに注意**: DFS の `child_outcome` はその局面で手番側の勝敗、
df-pn の outcome は「ライン最初に置いた側が最終的に勝つか」。
石数 k の局面では手番側＝初手側 iff k が偶数なので、
k 偶数では一致、k 奇数では反転して一致すべき。

結果: **n=6 は 14 共通根、n=7 は 15 共通根、すべて一致（MISMATCHES=0）**。
比較器: `research/verification/scripts/dfpn_xcheck_compare.py`
（parity 換算を明示）。

含まれるもの: OR/AND parity 両方、終局局面、D4 canonical 経由、
TT 再利用（同一プロセス・同一 TT で連続 root 解決）。
df-pn 側でのみ解けた 3 根（DFS が unsafe で停止）は比較対象外。

## 3. 追い出し試験（memo 縮小）

memo=2^20（1M 枠）では全根が 2. の結果と同一。
memo=2^16（65k 枠）では n=6 の最初の 3 根が 300/600/900 秒かけても
TIMEOUT（pn/dn は動いているが証明未完）。**結果が変わったのではなく、
時間内に終わらなくなった**。これは正しさの問題ではなく速度の問題。

所見（`evict6-p16.log` の hb 行より）:
- evict_open は 2.7 億回規模で発生、evict_solved は 0
- memo=59055/65536 で頭打ち、open=33508・solved=25547 で停滞
- avgprobe は 10.9→17.8 に悪化（追い出しで probe が伸びる）
- exprate は ~19〜31 万/s を維持（計算自体は止まらない）
- root eviction は起きていない（`acquire` が root を保護）
- solved entry の eviction はこの run では 0

**結論**: 追い出しは正しさを壊さない（p20 で全一致）。
ただし 65k 枠では再計算地獄で 11×11 級の証明は現実的でない。
11×11 は memo=26（67M 枠）で evict ほぼゼロのまま走っているため、
現状の容量で十分。power 拡大の優先度は低い。

## 4. マスク衛生バグ（修正済み）

`--roots-csv` 導入時に n=6 で Gen overflow（ASan: 6344 B 領域直後への
128 B 書き込み）。原因は `legal` の hi 残りビット: V<64 の盤で hi に
ゴミが残ると `take_lsb` が v>=V を返し、`bitof(v)` のシフト UB で
move loop が V を超える子を生成。`gen_into` 入口でマスクし直し、
v 範囲検査と子 overflow の loud throw を追加。再発時は即座に分かる。

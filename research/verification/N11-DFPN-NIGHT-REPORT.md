# 朝の最終報告（2026-09-30）: 11×11 df-pn 自律作業

基準: `8168cbf` → 最新 `14e1f4b`。全て main へ push 済み。
**11×11 の勝敗は UNKNOWN のまま。** 断定なし。

## 何を修正したか

1. **ログ経路の統一** (`7d3e9cc`): solver 内部 `log_/csv_` と run 側 `L/C` の
   二重管理を解消。`attach_log/attach_csv` で単一 stream 化。
   heartbeat が `--log` に残らなかった原因はこれ。
2. **時間基準 heartbeat**: 2^16 反復ごとに時計を見て 10 秒ごとに発火。
   t=0 点を即時出力。記録項目: wall・visited・expansions・exprate・
   root pn/dn・pn/dn 比（参考値）・memo・open・solved・evict open/solved・
   maxdepth・TT hit/miss・avgprobe。
3. **second minimum の標準化**（前夜 `8168cbf` の継続）: 同値込み真の
   second minimum、depth guard を `>V+8 throw` 化。
4. **`--roots-csv`**: 任意多石根の cross-check 用。DFS と同一 CSV 方言。
5. **マスク衛生**: V<64 盤で hi 残りビットが `take_lsb`→`bitof` UB で
   Gen overflow（ASan で特定）。`gen_into` 入口でマスク＋loud throw。

## 回帰試験結果

- n=4 LOSS（239）、n=5 WIN（847）、n=6 WIN（55,561）、
  n=7 LOSS（2,123,417、18秒）。全て既知勝敗と一致
- DFS との途中局面照合: n=6 は 14 根、n=7 は 15 根で **100% 一致**
  （parity 換算を明示: DFS=手番側、df-pn=ライン初手側）
- 追い出し試験: memo=2^20 で全一致。2^16 では遅くなるが結果不変。
  root 保護・solved ゼロ追い出しを確認

詳細: `N11-DFPN-VALIDATION.md`。

## 21初手の結果（各5分・fresh TT・memo=26）

全21軌道が TIMEOUT（未証明）。pn 85,796〜95,332、dn 10,761〜14,672。
差は最大11〜36%、桁の差なし。中央60が pn 最小・dn 最大。
詳細: `N11-DFPN-21ORBITS.md`。

## 長時間走（各1時間）

| 初手 | expansions | pn | dn | pn/dn |
|---|---:|---:|---:|---:|
| v=60 中央 | 49.8M | 202,718 | 110,924 | 1.83 |
| v=27 | 47.2M | 444,609 | 34,369 | 12.94 |
| v=12 対角 | 50.2M | 456,651 | 35,734 | 12.78 |

v=60 のみ pn/dn が 5.85→1.83 と単調減少。ただし参考値であり証明ではない。
詳細: `N11-DFPN-LONGRUN.md`。

## solvedかunsolvedか

**全て unsolved。** 1石局面の P 証明なし、21軌道の N 証明なし。
README の winner 欄は UNKNOWN を維持。

## 最も有望な方向

1. **v=60 の継続**（2〜4時間）: pn/dn 1.8 を割るかを見る
2. **tie-break 改善の A/B 比較**: 現状は合法手数のみ。DFS ordering・
   終局距離等の導入を1つずつ
3. memo 拡大は不要（TT 監査で容量は十分と判明）

## 新しい問題/バグ

なし（既知の未解決は証明未完のみ）。全バグは修正・回帰済み。

## commit hash一覧

- `7d3e9cc` ログ統一＋時間 heartbeat
- `cabece2` roots-csv・マスク衛生・cross-check
- `3692fad` 検証記録
- `eeaf33f` スクリーニング script
- `f303f92` 4点時系列
- `1213b28` 21軌道記録
- `23e1f72` longrun script
- `975277f` longrun 結果
- `59b8c34` TT 監査

## 人間が判断すべき点

- v=60 の長時間継続 vs tie-break 改善の優先順位
- 証明完成時の独立検証方針（証明 DAG 出力は未実装）
- 21軌道の D4 被覆の機械的確認（未実施、次走で追加予定）

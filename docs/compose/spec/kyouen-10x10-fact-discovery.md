---
feature: kyouen-10x10-fact-discovery
status: in-progress
updated: 2026-09-26
branch: research/kyouen-fact-discovery-20260926
commits: 155a143..HEAD # filled at delivery
---

# 共円ゲーム 10×10 非自明事実の発見

## Report

## [S1] Problem

1×1〜9×9 の最適勝敗は証明済みで、`research/findings.md` に F-A〜F-AC の非自明事実が積み上がっている。一方 10×10 は「空盤は後手必勝」「medium LOSS ルート R の部分集合」「プローブ戦略の方法論」が中心で、**盤そのものの幾何・組合せ・ゲーム構造に関する新しい確定事実**が不足している。

上流（origin/main）同期後の状態で、10×10 について再現可能な非自明な事実を発見し、`research/findings.md` に正本として記録する。

## [S2] Design

### Workspace override

`git worktree add` は共有 ref store ガードでブロックされる（Cycle 4/8 と同じ）。カレントチェックアウト上で `research/kyouen-fact-discovery-20260926` を切り出し、加算的なファイルのみ変更する。他ブランチの rebase/merge/cherry-pick はしない。

### 上流取り込み（完了前提）

- origin/main と同期済み（155a143）。
- 未追跡の `results/gpcc2026-9x9-center-*.txt` を取り込み済み（fd91c28）。9×9 中央初手の再確認であり、新分類ではない。

### 継承事実（再探索禁止）

- 10×10 空盤 = 後手必勝。初手分類は完了。**空盤・全初手を再 solve しない**。
- forbidden(10) = 54,441。共線 5,928 / 共円 48,513（F-W）。
- medium LOSS ルート `R = 90,61,2,73,69,66,13,91` とその 2〜6 石部分集合は分類済み。
- F-E / F-F: 4 石では Σd 高いほど LOSS（R 内・R 外 holdout で再現）。2–3 石の R 外は未検証。
- F-K: M(10)=12（円上最大格子点）。
- 9×9 は全 81 初手が勝ち。再 solve しない。

### 発見対象（本セッション）

各タスクは「観測可能な結果」で受け入れ判定する。証拠は整数演算または再現スクリプトで残す。

1. **10×10 二石 D4 軌道の完全幾何**（T-G）
   全 C(100,2) ペアを D4 正規化し、軌道代表・安定化群・危険 4 点組への露出度 d(p) の和・相対ベクトル分類を完全表にする。
   期待事実の例: 軌道数、Σd 分布、R 内 2 石 LOSS 2 個の幾何的位置づけ。

2. **10×10 極小極大安全配置**（T-M）
   「どの 1 点も加えられない安全集合」のうちサイズ最小のものの完全列挙（DFS / バックトラック）。サイズ・D4 軌道・幾何形状を記録。
   5×5 ではサイズ 5 が棒状 4 個（F-S）。10×10 で何石か。

3. **10×10 飽和（終端）構造**（T-S）
   合法手 0 となる安全配置（= ゲーム終端）の最小石数を探索し、その構造を記録する。9×9 では証明書末端に 17 石完全飽和（F-A）。10×10 の最小飽和は未知。

4. **禁止 4 点組の局所構造**（T-F）
   10×10 危険 4 点組 54,441 の、円サイズ分布・点次数分布・共有辺構造などを列挙し、9×9 (29,152) と対比した非自明な差分を見つける。

5. **R 外 2–3 石サンプルの勝敗と Σd**（T-P、時間余裕があれば）
   D4 層化した 2–3 石を exact solve し、序盤の「低 Σd = LOSS」傾向を外部検証する。1 インスタンス上限とし、TABLE_FULL/timeout は欠測として扱う。

### 事実の記録契約

- 各発見は `research/findings.md` に `F-AD` 以降の連番で追加する。
- 項目形式は既存と同じ: 発見内容 / なぜ非自明なのか / 証拠 / 再現方法 / 試した反証 / 成立範囲 / 確信度 / 今後の検証方法。
- 生データは `research/exploration/` または `results/10x10/fact-discovery/` に JSON/CSV で置く。
- スクリプトは `scripts/analysis/` に置き、`python scripts/analysis/<name>.py` で再現できるようにする。

### 検証境界

- 幾何・組合せ列挙は完全性フラグ（DFS 打切りなら complete=false）を必ず残す。
- ゲーム solve は exact のみ。近似・タイムアウト結果を勝敗の根拠にしない。
- 既存 10×10 CSV の state 列が非正規形である点（F-B）に注意し、比較は D4 正規形で行う。

## [S3] Out of Scope

- 10×10 空盤・全初手の再分類
- 9×9 の再 solve
- 11×11 への一般化（ただし10×10で確認した法則の「11×11 で試す」提案は findings の「今後」に書いてよい）
- プローブ戦略の盲検追試（方法論研究。既に大量の docs がある）
- 証明書形式の変更、Rust 検証器の拡張
- GitHub への push / PR 作成（ユーザーの finish 指示まで）

## Tasks
- [x] T1: 上流成果の取り込み — acceptance: gpcc 結果がブランチに commit され、origin/main との差分が発見作業の前提として文書化される (covers: S2)
- [x] T2: 仕様書作成 — acceptance: この文書が `docs/compose/spec/kyouen-10x10-fact-discovery.md` に存在し status=designed (covers: S2)
- [x] T3: 二石 D4 軌道完全幾何 — acceptance: 軌道数・代表・Σd を含む JSON/CSV が `research/exploration/` にあり、再現スクリプトが走る (covers: S2)
- [x] T4: 極小極大安全配置 — acceptance: 最小サイズと代表配置が整数列挙で確定し、complete フラグ付きで保存される (covers: S2)
- [x] T5: 最小飽和配置 — acceptance: 合法手 0 の最小石数と 1 例以上の構造が検証可能な形式で残る (covers: S2)
- [x] T6: 禁止 4 点組の局所構造 — acceptance: 円サイズ・点次数分布が n=9,10 で比較可能な JSON になる (covers: S2)
- [x] T7: findings.md への記録 — acceptance: F-AD 以降に各発見が既存形式で入り、再現コマンドが書かれている (covers: S2)
- [ ] T8: 検証とレビュー — acceptance: 主要スクリプトを再実行して数値一致を確認し、独立レビューで critical が残らない (covers: S2)

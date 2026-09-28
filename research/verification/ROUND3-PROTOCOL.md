# Round3 検証共通指示書（第3回・未解決368件の決着）

作成: 2026-09-27。対象: `PROTOCOL.md` の判定ラベルが `PARTIAL` / `INCONCLUSIVE` /
`NOT-CHECKED` のまま残っている仮説。

## あなたの仕事

割り当てられた **特定の ID だけ** について判定を一段前に進め、
`research/verification/round3-batch-<範囲>.md` に個票を書く。

他の ID には触らない。他のエージェントが並列で同じファイルを編集している。
**書き込みは自分の担当ファイルと `research/verification/scripts/round3_<id>*.py` のみ。**

## 判定ラベル（必ず1つ）

| ラベル | 意味 |
|---|---|
| **REFUTED** | 反例を具体的に発見した（盤・配置・数値を書く） |
| **SUPPORTED** | 検証可能な範囲で成立を確認（**範囲を必ず明記**） |
| **PARTIAL** | 一部範囲のみ成立（成立部分と未確認部分を分けて書く） |
| **INCONCLUSIVE** | 計算・考察したが判定不能（**なぜ判定できないかを書く**） |
| **NOT-CHECKED** | 着手できなかった（**理由を具体的に書く**） |

前回と同じラベルでも、内容が強化されていればよい。
**前文書と同じ定型文を機械的に繰り返すだけの再掲は禁止。**
必ず「今回どこまで前進させたか」を書く。

## 検証の手段（優先順）

1. **既存データ照合** — `research/verification/*.json`, `night-research/*.json`,
   `research/exploration/*.json`, `research/findings.md`, `docs/` にある確定結果。
2. **小盤厳密計算** — Python。コアは `research/verification/scripts/kyouen_core.py`
   を import して使う（整数行列式、点 id = `y*n+x`、bitmask 安全集合、
   `board_square(n)`, `board_rect(w,h)`, `board_square_minus(n, deleted)`,
   `solve_outcomes()`, `solve_grundy()`, `is_maximal()`, `max_safe_size()`）。
3. **反例探索** — [全称] は最小の n から反例を探す。[存在] は小 n で証人を探す。
   [存在] の非発見は**反証にならない**ので、INCONCLUSIVE にせず「何の n まで見たか」を書く。
4. **理論的考察** — 証明できるなら短証明書として SUPPORTED。
   「効くはずだが証明できていない」は INCONCLUSIVE で、その障碍を具体的に書く。

## 計算の指針

- **整数演算のみ。浮動小数禁止。**
- 盤サイズ: n≤4 は完全列挙可能。n=5 は 151,394 状態（Grundy 全計算は重い）。
  n=6 は極大 349,596。n≥7 の全探索は既存の確定結果を読む。
- **この環境には C++ コンパイラが無い**（g++/cl/clang++ すべて無い、`cmake` のみ）。
  重い計算は numpy を使うか、状態をビット集合で詰める形で Python を書く。
- 利用可能な python パッケージは **numpy のみ**（scipy/pulp/networkx/sympy は無い）。
  LP/ILP が要る場合（例: 最小被覆 B431–B434）は scipy の `linprog`/`milp`、
  pulp は使わない。simple-simplex / 分岐限界を **pure-Python で自前実装**する。
  参考: B432 の前回メモ「scipy 不在のため LP 未解」— 今回こそこの障害を解消すること。
- 実行: `python research/verification/scripts/<name>.py`（作業ディレクトリはリポジトリ根）。
- **スクリプトは `research/verification/round3_<担当ID>.json` に結果を JSON で吐かせる。**
  md には結論と要点だけ書く。

## 禁止事項

- 既存の確定事実（`PROTOCOL.md` の表）の再発見を SUPPORTED として報告しない。
- 小盤の不発見を、無界の存在命題の反証として書かない。
- 有限列のフィットや短い周期の一致を漸近定理として書かない。
- 次数列の一致とスペクトルの一致、群の位数と群同型、最大集合と極大集合を混ぜない。
- 反証された相関を、条件を変えずに逆符号で再提出しない。
- 既存ファイル（`hypothesis-bank-*.md`, `SUMMARY.md`, `PROTOCOL.md`）を**編集しない**。
- 有料モデルに切り替えない。作業はすべて既定モデルで完結させる。

## 個票フォーマット

```markdown
# Round3: Baaa-Bbbb

対象: research/hypothesis-bank-*.md の Baaa〜Bbbb。
スクリプト: scripts/round3_<name>.py
データ: research/verification/round3_<name>.json

## Baaa [種別] 原文の要約
- 判定: **LABEL**（前回: PARTIAL → 今回: LABEL に変化、等）
- 前回の一手: （前回文書に書かれていた「次の一手」を引用）
- 今回の範囲: 何の n / 何状態まで実際に計算したか
- 証拠: 具体的な数値・配置・座標
- 判定の根拠 / 残った障害: （why it is not decided, concretely）

（以降 B ごとに繰り返し）

## バッチ総括
| ラベル | 件数 | ID |
|---|---|---|
- 今回決着（SUPPORTED/REFUTED に動いたもの）
- 残る未解決とその一言理由
- 最も有望な次の一手（1つだけ）
```

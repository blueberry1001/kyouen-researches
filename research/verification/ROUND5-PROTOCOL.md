# Round5 検証共通指示書（第5回・残り316件の決着）

作成: 2026-09-28。対象: HANDOVER.md の未解決 316 件（PARTIAL / INCONCLUSIVE / NOT-CHECKED）。

## 環境（第4回で解消済み・重要）

**WSL2 Ubuntu に C++ がある。** Windows 側には無い。

```bash
wsl -d Ubuntu -- bash -c "g++ --version"   # g++ 13.3.0
# 16 コア / 19 GB RAM
```

長いコマンドは必ず `.sh` ファイルに書いてから
`wsl -d Ubuntu -- bash <パス>` で実行すること。
PowerShell のインラインはクォートで壊れる。

共有 C++ コア: `research/verification/scripts/kc_core.h`
- 禁止4点組は整数行列式 `det[x²+y², x, y, 1] == 0`
- 盤は `uint64_t`（n≤8 で 64 点）
- 点 id = `y*n + x`（`kyouen_core.py` と一致）
- **自己検査済み**: n=2..9 の F_n が既知値と完全一致

Python コア: `research/verification/scripts/kyouen_core.py`
（`board_square(n)`, `solve_outcomes()`, `solve_grundy()`, `is_maximal()`, `max_safe_size()` 等）

## メモリの共有ルール（最重要）

WSL の 19 GB は**全エージェントで共有**。
重い計算（数 GB 級）を並行すると exit 137（OOM）になる。

- **n=8 の p_rand 列挙は専任エージェントが単独で走らせる**
- 他のエージェントの「重い」= n≤6 の完全 Grundy（数秒〜1分、数百 MB）までは可
- n=7 以上の列挙・p_rand 全計算は**自分がやらない**（専任に任せる）
- 終了前に `free -h` で空きを確認し、available < 4 GB なら重い計算を控える

## 判定ラベル（必ず1つ）

| ラベル | 意味 |
|---|---|
| **REFUTED** | 反例を具体的に発見した（盤・配置・数値を書く） |
| **SUPPORTED** | 検証可能な範囲で成立を確認（**範囲を必ず明記**） |
| **PARTIAL** | 一部範囲のみ成立 |
| **INCONCLUSIVE** | 計算・考察したが判定不能（理由を書く） |
| **NOT-CHECKED** | 着手できなかった（理由を書く） |

前回と同じでも内容が強化されていればよい。
**定型文の機械的再掲は禁止。** 「今回どこまで前進させたか」を書く。

## 検証の手段（優先順）

1. **既存データ照合** — `research/verification/*.json`, `night-research/`,
   `research/exploration/`, `research/findings.md`, `docs/`
2. **小盤厳密計算** — Python (`kyouen_core.py`) または WSL C++ (`kc_core.h`)
3. **反例探索** — [全称] は最小 n から。[存在] は小 n で証人探し。
   [存在] の非発見は反証にならない。
4. **理論的考察** — 証明できるなら短証明書として SUPPORTED。
   無界命題は**弱化**（n≤6 で検証可能な形）を検討すること。

## 無界命題の扱い（B231–B290 に集中）

大半は [存在]・[漸近]・[大胆] の無界命題。
有限計算では原理的に決着しない。次の順で攻めること:

1. **弱化して SUPPORTED/REFUTED** — 「任意の r 点グラフは粗視化で
   高々 1 点を失って実現できる」のように n≤6 で検証可能な形に直す。
   弱化が成功したら「弱化版 SUPPORTED / 原命題 INCONCLUSIVE」の両方を書く。
2. **短い理論証明** — 補題が書けるなら SUPPORTED。
3. **それでも無理なら INCONCLUSIVE** — 「なぜ決着しないか」を具体的に。
   NOT-CHECKED のまま放置しないこと。

## 計算の指針

- 整数演算のみ。浮動小数は比較に使わない。
- n≤4 は完全列挙が軽い。n=5 は 151,394 状態。n=6 は極大 349,132。
- n≥7 の全探索・p_rand は**専任エージェントの n=8 ジョブを待つか既存結果を読む**。
- スクリプトは `research/verification/scripts/round5_<name>.py`（または `.cpp`）。
- 結果 JSON は `research/verification/round5_<name>.json`。
- **ASan を使うこと**: `g++ -O1 -g -fsanitize=address,undefined`
- 新ソルバは n=4,5,6 の既知値と**必ず**突き合わせてから使う。

## 書き出し（絶対）

1. **100 ターンで強制終了される。** 「全部読み終わってから書く」は成果ゼロ。
2. **最初に自分の担当 md を空で作り、ID ごとに逐次追記する。**
3. **既存ファイルの上書き禁止。** 自分の担当 `round5-batch-*.md` だけ書く。
4. `hypothesis-bank-*.md`, `SUMMARY.md`, `PROTOCOL.md`, `HANDOVER.md` は編集しない。

### 個票フォーマット（census が拾える形）

```markdown
## Bxxx [種別] 原文の要約
- 判定: **LABEL**（前回: X → 今回: LABEL）
- 前回の一手: （前回個票の「次の一手」を1行で）
- 今回の範囲: 何の n / 何状態まで実際に計算したか
- 証拠: 具体的な数値・配置・座標
- 残った障害: なぜ完全に決着しないか（決着したら「なし」）
```

ファイル先頭:
```markdown
# Round5: Baaa-Bbbb

対象: research/hypothesis-bank-*.md の Baaa〜Bbbb。
スクリプト: scripts/round5_<name>.py
データ: research/verification/round5_<name>.json
```

**`判定: **LABEL**` の行は census (`full_census.py`) が拾う。省略禁止。**

## 禁止事項

- 既存の確定事実（`PROTOCOL.md` の表）の再発見を SUPPORTED と報告しない
- 小盤の不発見を無界存在命題の反証と書かない
- 有限列のフィットを漸近定理と書かない
- 次数列の一致とスペクトルの一致を混ぜない
- 反証された相関を逆符号で再提出しない
- 有料モデルに切り替えない

## 既知の確定事実（再発見禁止・PROTOCOL.md より）

- F_n（禁止4点組を含まない n 点配置の最大数）: n=2..9 確定
- 最大 nimber n=2..6 = 1, 1, 5, 6, 8
- 7×7 は後手勝ち。8×8 は先手勝ち
- 8×8 の 8石極大は 408 個、6石極大は 0 個
- 最小被覆数 = 21（B431 証明済み）
- D_n（共線四点組数）= 7ζ(2)/(60ζ(3)) n^5 − 3/(4ζ(2)) n^4 log n + O(n^4)
- p_rand 最大: n=4: 76/135, n=5: 2383/3360, n=6: 5162/6615, n=7: 3709/4620
- B141 は SUPPORTED（第1回の REFUTED は誤読。HANDOVER §2 参照）

## 詳細

- 引き継ぎ: [`HANDOVER.md`](HANDOVER.md)
- WSL: [`WSL-BUILD.md`](WSL-BUILD.md)
- 第4回: [`round4-SUMMARY.md`](round4-SUMMARY.md)

# Round4 検証指示書 — C++（WSL）による決着

作成: 2026-09-27。第3回（`ROUND3-PROTOCOL.md` / `round3-SUMMARY.md`）の残り
未解決 359 件を、**WSL の C++ で再做する**。

## 壊れた根本障碍は既に解消した

第3回の未解決の多くは「Windows に C++ が無く pure-Python では間に合わない」ためだった。
**WSL2 Ubuntu に g++ 13.3.0 / 16 コア / 19 GB がある。** 詳細は `WSL-BUILD.md`。

- 共有コア: `research/verification/scripts/kc_core.h`（**必ず #include して使う**）
- 自己検査済み: n=2..9 の禁止4点組数 F_n が既知の確定値と**完全一致**。
  K_n / 極大集合も既存記録と一致（n=5 の 8石極大 = 16,760、n=6 の 10石 = 349,132）。
  **(core は既に検証済み。書き直すな。)**

## ビルドと実行

```bash
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
wsl -d Ubuntu -- bash -c "cd $REPO/research/verification/scripts && \
  g++ -O2 -march=native -std=c++20 -o /tmp/x your.cpp && /tmp/x"
```

並列化するなら `-fopenmp` を付ける。16 コアある。

**Shell 工具の呼び出し方**: `wsl -d Ubuntu -- bash -c "コマンド"`。
`**` や `$` のエスケープで壊れることがあるので、
**長いスクリプトは `.sh` ファイルに書き出して `wsl -d Ubuntu -- bash <パス>` で実行する。**
インラインで書くと PowerShell のクォートで壊れる（実際に壊れた経験がある）。

**重い計算は 1 回の呼び出しで走らせ、待つな。** 100 ターンで強制終了されるので、
`run_in_background` で始めて、**先に md ファイルを空で作成してから**計算結果を待つ。
最初に空ファイルを Write し、ID ごとに即時追記すること。最後にまとめて書くと成果ゼロになる。

## 整数演算のみ

- **浮動小数禁止。** 比率や確率は有理数として正確に持ち、`p/q` 形式で報告する。
- 禁止4点組は整数行列式 `det[x^2+y^2, x, y, 1]` が 0（共円または共線）。
- 点 id = `y*n + x`（`kyouen_core.py` と一致）。
- 盤は 1 つの `uint64_t` に入る（n ≤ 8、64 点）。

## 判定ラベル

`ROUND3-PROTOCOL.md` のラベル表に従う: SUPPORTED / REFUTED / PARTIAL / INCONCLUSIVE / NOT-CHECKED。

- 前回と同じラベルでも、内容が進んでいればよい。
- **前回と同じ定型文の繰り返しは禁止。** 何をどこまで前進させたかを書く。
- 数値が無いのに推測で SUPPORTED/REFUTED を書いてはいけない。

## 禁止事項

- 既存の確定事実（`PROTOCOL.md` の表、README）の再発見を SUPPORTED として報告しない。
- 小盤の不発見を無界の存在命題の反証にしない。
- 有限列のフィットや短い周期の一致を漸近定理にしない。
- 既存ファイル（`hypothesis-bank-*.md`, `SUMMARY.md`, `round2-SUMMARY.md`,
  `round3-SUMMARY.md`, `PROTOCOL.md`）を**編集しない**。
  他の round3 個票も上書きしない（他エージェントが並行で書いている）。
- 有料モデルを使わない。すべて既定モデルで完結させる。

## 成果物

- スクリプト: `research/verification/scripts/round4_<担当>.cpp`（または .py / .sh）
- データ: `research/verification/round4_<担当>.json`（数値はここに。md は結論だけ）
- 個票: `research/verification/round4-batch-<範囲>.md`
  書式は `ROUND3-WRITEOUT.md` の「判定の書き方」に従う。

## 最終回答（400字以内）

1. SUPPORTED/REFUTED に動いた ID 一覧
2. 各 ID の実行時間・状態数（具体的な数字）
3. 未解決で残った ID と一言理由
4. 書き出したファイルのパス

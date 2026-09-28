# Round3 書出し専用指示（既存データから md を作る）

あなたは共円ゲーム(kyouen)検証の**記録担当**です。作業ディレクトリ:
`D:\ghq\github.com\yuubinnkyoku\kyouen-researches`

## 絶対の原則

1. **新しい重い計算をしない。既存スクリプト/JSON/既存資料を読むだけ。**
   特に既存のスクリプトを `python` で走らせ直さないこと。
   先に計算した人が既に走らせている・走らせて失敗している。**読むだけ。**

2. **100 ターンで強制終了される。全部読み終わると書けなくなる。**
   読む → 書く を ID ごとに即座に行うこと。
   最初に担当 ID 全部の「原文1行 + 前回判定」だけを grep で集める（軽い）。
   続いて ID を1つずつ、既存データを1つ読む → すぐ md に追記する。
   件数は多いが、1 件あたり必要なのは Write 数行だけ。

3. **md は最初に Write ツールで空ファイルとして作成し、逐次追記する。**
   最後にまとめて書くと、途中で上限に達して成果ゼロになる（これが前回の失敗）。

4. **既存ファイルの上書き禁止。自分の担当ファイルだけを書く。**

## 使うもの

- `research/verification/ROUND3-PROTOCOL.md` — 判定ラベルと禁止事項
- `research/verification/PROTOCOL.md` — 既存の確定事実（再発見を SUPPORTED にするな）
- `research/verification/round2-batch-*.md` / `batch-*.md` — 前回個票
- `research/hypothesis-bank-*.md` — 原文（grep で引く）
- `research/verification/scripts/round3_*.py` — 先行計算スクリプト（docstring を読む）
- `research/verification/round3_*.json` — 先行計算データ

## 大きな JSON の読み方

32MB の census のようなものは Read ツールで開かない。必ず python で：
```
python -c "import json;d=json.load(open('research/verification/round3_b451_census.json',encoding='utf-8'));print(list(d.keys()))"
```
`d['B451']` など当該 ID のキーのみ取り出す。キーを知ったら针对性アクセス。

## 判定の書き方（各 ID）

```markdown
## Bxxx [種別] 原文の要約
- 判定: **LABEL**（前回: X → 今回: LABEL）
- 前回の一手: （前回個票の「次の一手」を1行で）
- 今回の範囲: （何の n / 何状態か。既存データならデータファイル名）
- 証拠: （具体的な数値。JSON から取った実際の値）
- 残った障害: （なぜ完全には決着しないか。具体的）
```

- 既存データで決着した場合: PARTIAL/INCONCLUSIVE/NOT-CHECKED から SUPPORTED/REFUTED に。
- 既存データが足りない場合: そのまま NOT-CHECKED / INCONCLUSIVE。
  前回とラベルと理由が完全に同一なら、そのまま転記してよい
  （この場合は「既存データに情報がなく前回と状況が変わらない」と一行書く）。
- **推測で SUPPORTED / REFUTED を書いてはいけない。**
  数値が Reverence 写得ないなら INCONCLUSIVE / NOT-CHECKED が正解。

# 10×10 probe `memo` 累積値監査

固定日: 2026-09-09

## 結論

`b5172a4` の盲検追試で3-stone固定則に使った `memo` 列は、childごとの独立な探索特徴量ではなく、同一process内で前のchildから引き継がれた **累積memo使用量** だった。

そのため

```text
3-stone: memo descending, budget=1,000,000
```

は実データ上、ほぼ「後に実行したchildを先に並べる」規則になる。今回の主評価160 childでは、固定順位は solver既定順の**完全な逆順**だった。

したがって `b5172a4` の判定Cは「memo descendingという探索特徴量の有効性検証」としては解釈できない。観測された first LOSS / total cost 自体は実測値だが、検証した実体は **solver既定順の逆順** に近い。

## 機械監査

追加:

```text
scripts/audit_probe_memo_cumulative.py
.github/workflows/probe-memo-cumulative-audit.yml
```

GitHub Actions:

```text
run 34358326856: SUCCESS
```

結果:

```text
1,000,000-node probe files          95
cumulative signature files          95 / 95 = 100%
blind 3-stone ranked child rows     160
exact reverse-order rank matches    160 / 160 = 100%
```

各probeファイルでは `memo` が全行で単調増加し、隣接行差

```text
delta_memo[i] = memo[i] - memo[i-1]
```

（先頭は `memo[0]`）が、ほぼその行の `visited` に対応した。典型的な20-child batchでは各childの `visited=1,000,000` に対し、`delta_memo` は概ね0.99M台である。一方、生の `memo` は約1M, 2M, 3M, ... 20Mと増える。

これは `memo` が「このchildが何件memoを使ったか」ではなく「process開始からここまでにmemoに何件入ったか」を表していることと整合する。

## 最大反例の再解釈

### `4,9,33`

batch0のLOSS childは solver既定順3位と5位だった。

```text
solver default first LOSS = 3
fixed first LOSS          = 16
```

fixed順は20件の完全逆順なので、solver 5位のLOSSが逆順では16位になる。したがってこの最大反例は、memo特徴が親依存で符号反転した証拠というより、**逆順化そのものが不利だった例**として説明できる。

### `9,19,33`

唯一のbatch0 LOSSは solver既定順8位だった。

20件の逆順では `20 + 1 - 8 = 13` 位となり、観測された

```text
fixed first LOSS = 13
```

と完全一致する。

この2件については反例の位置が累積memo由来の逆順化だけで説明できる。

## 既存結果の扱い

保持してよいもの:

- exact child WIN/LOSS
- exact visited
- solver既定順での first LOSS / total cost
- random baseline
- 「solver既定順を逆転した順序」の first LOSS / total cost

memo heuristic の証拠として扱ってはいけないもの:

- raw `memo` descending の性能
- raw `memo` とLOSS/WINの関連
- raw `memo` の親間・child間比較

## 次の優先実験

11×11へ進む前に、3-stoneだけを対象として probe特徴量の測定方法を直す。

優先順位:

1. **fresh-process probe**
   - childごとに新しいsolver process / fresh memoで同じbudgetを実行する。
   - `memo` がchild固有値として比較可能になる。
   - 既存の新規LOSS親を再利用してよいが、これは今回のoutcomeを既に見た後なので探索的再解析と明記する。

2. **既存rawから `delta_memo` を作るpost-hoc解析**
   - `memo[i]-memo[i-1]` は追加memo件数の近似になる。
   - ただし前childのmemo再利用の影響があるため、fresh-process版の代替ではなく低コストな仮説生成用途に限定する。

3. **順序不変性テスト**
   - 同じchildrenを正順・逆順・固定乱数順でprobeし、fresh-processなら同じchildの特徴量が一致することを確認する。
   - shared-process測定値が順序で変わることも対照として記録する。

次の正式な固定則を作るなら、特徴量ごとに「processを跨いでもchild固有である」ことを先に検証し、その後に別holdoutを凍結する。

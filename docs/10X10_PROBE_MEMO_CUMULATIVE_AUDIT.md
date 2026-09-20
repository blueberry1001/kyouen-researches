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

## fresh-process 測定の順序不変性

累積値問題を除くため、既存 `run_blind_probe_batch_isolated.py` をWindows/WSLだけでなくLinux上でも同じ意味で動くようにし、childごとに完全に別processを起動する経路をGitHub Actionsで検証した。

追加:

```text
scripts/test_fresh_probe_order_invariance.py
.github/workflows/probe-fresh-process-order-invariance.yml
```

GitHub Actions:

```text
run 34366319306: SUCCESS
commit ae88f95c89f8a0ee7270f6e9cde16566ece3799e
```

同じ3 childを20,000-node budgetで

```text
forward
reverse
fixed shuffle (seed 20260909)
```

の3順序に並べ、各childを毎回fresh solver processで測定した。壁時計時間 `seconds` を除くsolver CSVの全項目が、同一childについて3順序で完全一致した。

```text
0,1,10,13  visited=20000 maxdepth=17 memo=19940
0,2,10,13  visited=20000 maxdepth=16 memo=19959
0,4,10,13  visited=20000 maxdepth=17 memo=19940
```

したがって少なくともこの検査範囲では、fresh-process版の `memo` / depth profile は**前にどのchildを測ったかに依存しないchild固有測定値**として扱える。一方で20,000-node時点のmemo差は最大19件と小さく、順位特徴として十分な信号量があるかはまだ未確認である。

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

11×11へ進む前に、3-stoneだけを対象としてprobe特徴量を測り直す。

優先順位:

1. **既知7 LOSS親でfresh-process 1,000,000-node probeを探索的に再測定**
   - childごとに新しいsolver process / fresh memoで測る。
   - 既にoutcomeを見た親なので、ここでは `memo`、`maxdepth`、depth profile の候補規則を作るだけに限定し、成功判定には使わない。
   - raw `memo descending` だけでなく、`memo/visited`、深さ別memo比率、深さ別visited比率も候補にする。

2. **候補規則を結果非依存の形へ固定**
   - 方向（ascending/descending）を既知7親だけで選ぶ。
   - tie-breakまで完全に固定する。
   - solver既定順、固定乱数順、旧「逆順」baselineを同時に残す。

3. **新しいholdout parentで再盲検**
   - fresh-process probeを先に完了・hash固定する。
   - その後だけexact child outcomeを開く。
   - first LOSS順位とtotal exact costを主評価にする。

4. **既存rawの `delta_memo` は補助解析に限定**
   - `memo[i]-memo[i-1]` は追加memo件数の近似になるが、前childからのmemo再利用を含むためfresh-process版の代替にはしない。

fresh-process順序不変性は確認できたので、次に未解決なのは「**正しく測ったchild固有特徴に、LOSSを早く見つけるだけの信号が本当にあるか**」である。

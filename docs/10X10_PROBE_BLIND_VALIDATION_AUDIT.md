# 10×10 固定プローブ盲検追試 — memo特徴量の事後監査

最終更新: 2026-09-06

## 結論

3-stone の固定ルール

```text
memo, budget=1,000,000, descending
```

は、意図していた「各 child の probe 後の memo 使用量」ではなかった。

`probe_cert_solver` は task ごとに Solver を作り直さず、1個の Solver を全 child で共有する。そのうえ CSV の `memo` 列には各 task 終了時点の

```cpp
solver.memo_used()
```

を出力している。したがって `memo` は child 固有値ではなく、前に処理した child の状態を含む**累積 memo 使用量**である。

実際、例 `P={4,9,33}` の batch0 では

```text
child 1 :    998,355
child 2 :  1,997,116
child 3 :  2,994,540
...
child 20: 19,959,989
```

と入力順に厳密増加する。このため `memo desc` はこの batch では solver default/input order の**完全な逆順**になる。

よって、既報の

```text
fixed first LOSS median = 3
random median           = 6
solver default median   = 3
```

は「memo probe が LOSS child を上位に寄せた」証拠としては扱えない。比較されていた fixed rule は、実質的には reverse-input ordering だった。

## 実装上の原因

probe 実行部は概略として次の構造になっている。

```cpp
Solver solver(shrink, load);
solver.set_probe_budget(max_visited, max_seconds);

for (auto &pts : tasks) {
    Solver::Stats st;
    solver.solve(pts, st);
    // ...
    std::cout << solver.memo_used();
}
```

`Solver` が loop 外にあるため、memo table は task 間で共有される。

これは exact solve の transposition reuse としては合理的だが、**各 child を比較する特徴量の測定方法としては不適切**である。

## 既報結果の統計的な再解釈

batch0 で LOSS child が観測された7親について、各親の

- `m = child_count`
- `l = loss_child_count`

を条件として、無作為順で最初のLOSSが位置 `R` に来る厳密分布

```text
P(R=r) = C(m-r, l-1) / C(m,l)
```

を使う。

7親の fixed first-LOSS position の和は

```text
1 + 16 + 3 + 13 + 1 + 1 + 3 = 38
```

である。無作為順での期待値の和は

```text
43.5125
```

で、独立な条件付き分布を畳み込んだ片側確率

```text
P(sum R <= 38) = 0.3349816851667474
```

となる。

したがって、中央値 `3 vs 6` だけを見ると大きく見えるが、この7親の LOSS 密度差を条件付けると、無作為順より良いという証拠は強くない。

なお、この検定は「累積memo問題」を直すものではない。あくまで、実際に使われた reverse-input ordering の成績が、条件付き無作為順に対してどの程度珍しいかを見る事後診断である。

## 盲検性について

この問題は親選定や outcome reveal の盲検手順そのものを否定しない。

壊れていたのは、事前固定された特徴量 `memo` の**計測単位**である。したがって追試の価値は残るが、結論は

```text
「3-stone memo-desc に弱い再現効果」
```

ではなく

```text
「盲検手順は実施できたが、3-stone memo特徴量は累積値だったため
 intended rule の追試としては不成立」
```

へ修正するのが妥当。

## 修正版の最小設計

3-stone の再追試では、各 child を独立条件で測る。

候補は次のどちらか。

1. child ごとに新しい `Solver` を構築する。
2. memo と探索統計を完全に reset する専用 `solve_probe_isolated()` を追加する。

重要なのは

```text
feature(child_i)
```

が `child_0 ... child_{i-1}` の実行履歴に依存しないこと。

さらに、1M visited の固定budgetでは `memo_used` 自体がほぼbudgetに張り付く可能性が高い。再測定時は少なくとも

- local memo_used
- maxdepth
- depthごとのvisited分布
- memo_used / visited

を保存し、outcomeを見る前にどの特徴量を主評価にするか固定する。

## 自動監査

`scripts/audit_blind_probe_memo_feature.py` を追加した。

このスクリプトは

- 各3-stone probe CSVで `memo` が入力順に厳密増加するか
- `fixed_rank + solver_default_rank = n+1` が全childで成立するか
- 7親の first-LOSS rank 和に対する正確な条件付き無作為確率

を機械的に検査する。

## 研究上の優先順位

この発見により、10×10 blind probe の追加batchをそのまま延長する優先度は下がる。累積memoのままデータを増やしても intended heuristic の検証にはならない。

優先順位は次の通り。

1. **probe計測をchild独立に修正する**。
2. outcome未参照の未実行親に対し、修正版featureを先に生成して固定する。
3. その後に exact child classification を進める。
4. 既にoutcomeを見た7親は修正版ruleの主検定には再利用せず、探索的な診断用に限定する。

これなら、既存の盲検追試で得た教訓を捨てずに、次の追試を本当に独立なものにできる。

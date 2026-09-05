# 9×9 pair-sum vs true mobility: confirmatory implementation audit

最終更新: 2026-09-05

事前登録済みの確認試験について、outcome を見る前に実装経路を監査した。主検定の定義・標本・seed・有意水準は変更しない。

## 1. 層別副解析の metadata が solver 出力から落ちる

標本作成器 `select-9x9-pair-mobility-confirmatory.py` は、solver 用CSVを意図的に

```text
canonical_parent,pair_top,true_unique_top
```

の3列へ縮め、`cause_class` や `pair_T/E/O` などの事前特徴量は別の

```text
*.meta.csv
```

へ保存する。

一方、`kyouen_solver_9_compare` の出力は入力3列と exact outcome / 探索統計だけなので、`cause_class` は自動では戻らない。従来の集計器は結果CSVに `cause_class` がある場合だけ層別表示するため、そのままでは事前登録文書に書いた `E-only / O-only / both / synergy` の探索的副解析が実行できなかった。

outcome を見ずに直せる配線上の問題なので、metadata を `canonical_parent` で再結合する補助スクリプトを追加した。

```bash
python3 scripts/join-9x9-confirmatory-metadata.py \
  /tmp/9x9-confirmatory-1024-results.csv \
  /tmp/9x9-confirmatory-1024.meta.csv \
  /tmp/9x9-confirmatory-1024-results-with-meta.csv

python3 scripts/analyze-9x9-pair-mobility-confirmatory.py \
  /tmp/9x9-confirmatory-1024-results-with-meta.csv
```

主検定は outcome 2列だけで決まるため、この修正は主p値に影響しない。

## 2. `visited` / `seconds` は局面固有の難度ではない

`kyouen_solver_9_compare` は1つの `Solver9` インスタンスをCSV全行で再利用し、transposition memo も共有する。

これは exact outcome の再利用としては正しい。しかし、後ろの行ほど前のsolveで得た状態をmemoから利用できる。そのため出力される

```text
pair_visited
other_visited
pair_seconds
other_seconds
memo_used
```

は入力順序と、それ以前に解いた局面に依存する。

特に同じ親の中でも pair child を先に解き、true child を後に解くため、

> `pair_seconds` と `other_seconds` の差を「pair手とtrue手の本質的な探索難度差」と解釈してはいけない。

同様に、これらを outcome 方向の説明変数として扱わない。

局面固有の探索難度を別研究で測る必要が出た場合は、各rootをfresh memoで独立solveするか、順序を入れ替えたcold-memo benchmarkを別途設計する。確認試験本体では不要。

## 3. 主解析への影響

確認試験の主解析は

```text
pair-only  vs  true-only
```

の個数だけを使う matched exact binomial test である。

- metadata欠落: 主解析に影響なし
- shared memo: exact outcomeに影響なし
- 探索統計の順序依存: 主解析に影響なし

したがって事前登録済み主判定はそのまま維持できる。

今回の監査で変わったのは、**副解析の再現経路を修復したこと**と、**探索コスト列の解釈範囲を明確にしたこと**だけである。

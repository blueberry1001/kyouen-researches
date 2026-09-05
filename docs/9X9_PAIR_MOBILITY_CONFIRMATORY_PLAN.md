# 9×9 pair-sum vs true mobility: confirmatory holdout plan

最終更新: 2026-09-05

予備解析では canonical key の小さい順64件を exact solve し、discordant 29件中 `true_unique` 側だけが LOSS child になる例19件、`pair` 側だけが LOSS child になる例10件だった。この64件はすでに outcome を見ているため、確認試験には再利用しない。

## 母集団

対象は9×9 safe 4-stone parentのうち、

- `raw pair-sum` の首位が一意
- `true one-ply safe-response reduction T` の首位も一意
- その2手が異なる

D4 canonical 11,378 orbits。

`raw_pair = T + E + O` の逆転原因により、既報の4層に分ける。

```text
E-only   6,350
O-only     706
both       337
synergy  3,985
```

全母集団CSVは次で再生成する。

```bash
g++ -O3 -std=c++20 scripts/analyze-9x9-pair-gap-decomposition.cpp -o /tmp/pair-gap
/tmp/pair-gap --csv /tmp/9x9-pair-gap-population.csv
```

## outcomeを見ない固定標本

予備64件

```text
results/9x9/pair-vs-true-unique-pilot-64-input.csv
```

を除外した後、各層の残数に比例して合計1,024件を抽出する。層内順位は疑似乱数ライブラリではなく

```text
SHA256(seed || NUL || canonical_parent)
```

の辞書順で固定する。

seedは outcome を見る前に以下へ固定する。

```text
kyouen-9x9-pair-vs-true-mobility-confirmatory-v1-2026-09-05
```

抽出コード:

```bash
python3 scripts/select-9x9-pair-mobility-confirmatory.py \
  /tmp/9x9-pair-gap-population.csv \
  results/9x9/pair-vs-true-unique-pilot-64-input.csv \
  /tmp/9x9-confirmatory-1024.csv
```

`/tmp/9x9-confirmatory-1024.csv` は既存比較solverへ直接渡せる3列CSV。事前特徴量は `/tmp/9x9-confirmatory-1024.meta.csv` に別保存される。

## exact solve

```bash
cmake -S . -B build -DBUILD_RESEARCH_SOLVERS=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build --target kyouen-solver-9-compare -j
./build/kyouen-solver-9-compare /tmp/9x9-confirmatory-1024.csv 29 \
  > /tmp/9x9-confirmatory-1024-results.csv
```

必要ならmemo powerは増やしてよいが、標本・判定規則は変更しない。

各parentについて、手を置いた後の相手手番のexact outcomeを比較する。`LOSS child`を作る手が親側から見た成功。

## 主判定

4分類する。

```text
pair-only: pair child=LOSS, true child=WIN
true-only: pair child=WIN,  true child=LOSS
both-loss
both-win
```

主解析はdiscordant (`pair-only + true-only`) のみを使うmatched comparison。

帰無仮説:

```text
P(true-only | discordant) = 1/2
```

予備64件から方向仮説はすでに `true_unique` 優勢と置いたため、確認試験の主p値は

```text
H1: P(true-only | discordant) > 1/2
```

に対する片側 exact binomial とする。二側p値も併記する。

```bash
python3 scripts/analyze-9x9-pair-mobility-confirmatory.py \
  /tmp/9x9-confirmatory-1024-results.csv
```

有意水準は `0.05`。標本サイズ、seed、除外集合、主判定を結果確認後に変更しない。

## 副解析

`E-only / O-only / both / synergy` 別のdiscordant方向、`pair_T/E/O` と `true_T/E/O` の差との関連は探索的解析とする。層ごとの多重比較を主結論へ使わない。

この設計で答えたい問いは単純な「どちらが常に正しいか」ではない。予備解析ですでに両方向の反例があるため、確認するのは

> strict-disagreement局面全体で、raw pair-sumよりtrue one-ply mobilityの方が winning child を拾う確率が高いか

である。

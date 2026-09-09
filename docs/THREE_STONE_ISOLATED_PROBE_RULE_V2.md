# 3-stone blind probe rule v2: fresh-process memo ascending

固定日: 2026-09-10

## 背景

旧 `memo desc` 規則は、複数childを同一solver processで順番にprobeした結果の累積 `memo` をchild特徴量として扱っていたため無効である。`run_blind_probe_batch_isolated.py` により、各childをfresh process / fresh memoで測る方式へ修正した。

この文書は、既にoutcomeが開いている7 parentのbatch0だけを探索集合として使った後、**新しいholdout outcomeを見る前**に次の規則を固定する。

## 探索集合

既知LOSSを含むbatch0 parent 7件:

```text
2,9,33
4,9,33
9,12,33
9,19,33
9,23,33
0,31,36
0,36,44
```

各parentについて20 childを、childごとに独立processで 1,000,000 visited-node 上限までprobeした。

既知ラベルに対して、結果を見る前に候補特徴を次の4系統×2方向へ限定した。

- child-local `memo`
- `maxdepth`
- visited depthの平均 (`mean_depth`)
- depth >= 15 のvisited比率 (`deep_fraction`)

比較用baselineはsolver既定順。無作為baselineは、20 child中k個がLOSSならfirst LOSS位置の期待値 `(20+1)/(k+1)` を用いた。

## 探索結果

GitHub Actions run `34372371918` で7 parentすべてのfresh-process probeと集計が成功した。

| 規則 | first LOSS位置（7親） | 中央値 | solver既定順に対する勝-分-敗 |
|---|---|---:|---:|
| `memo asc` | 1, 1, 1, 5, 5, 2, 1 | **1** | **5-0-2** |
| `mean_depth asc` | 1, 1, 1, 9, 4, 2, 1 | **1** | 4-0-3 |
| `deep_fraction asc` | 2, 1, 1, 7, 3, 2, 1 | 2 | 4-2-1 |
| `maxdepth asc` | 2, 1, 3, 4, 5, 1, 10 | 3 | 3-2-2 |
| `maxdepth desc` | 1, 3, 20, 19, 5, 1, 6 | 5 | 1-3-3 |
| `mean_depth desc` | 11, 19, 20, 12, 15, 1, 5 | 12 | 1-1-5 |
| `deep_fraction desc` | 10, 18, 20, 14, 15, 1, 5 | 14 | 1-1-5 |
| `memo desc` | 9, 19, 20, 16, 15, 2, 9 | 15 | **0-0-7** |

solver既定順の中央値は3、無作為first LOSS期待値の親間中央値は7.0だった。

重要なのは、旧shared-process結果で使われていた `memo desc` と**方向が反転した**ことである。fresh processでは `memo asc` が最良であり、`memo desc` は7親すべてでsolver既定順より悪い。

### 解釈仮説

固定node budgetに達した未完了childでは、`visited` は同じ1,000,000である。それに対して `memo` が小さいことは、探索中に同一または対称同値状態へ再到達し、memo lookupで再利用できた割合が相対的に高いことを示す可能性がある。LOSS探索では勝ち手を早期発見して枝刈りするWIN探索より広く複数分岐を検査するため、transposition / symmetry reuseが増える、という仮説と整合する。

これはまだ説明仮説であり、既知7親への適合だけでは確証としない。

## 1M以内のexact completion

fresh-process probeでは、すべてのchildが必ず `PROBE` で打ち切られるとは限らない。少なくとも `0,31,36` の1 childは1M未満でexactに完了し、既存exactラベルと一致した（このケースはWIN）。

したがってholdout評価では `PROBE` 以外を異常値として捨てない。

- probe中に `LOSS` がexact確定したchildがあれば、そのparentについてLOSS childは既に発見済みと記録する。
- probe中に `WIN` がexact確定したchildは、後段のLOSS探索候補から除外できる。
- 未完了 (`PROBE`) childだけを `memo asc` で順位付けする。
- exact completionの有無とprobe費用を別途記録し、順位だけを都合よく比較しない。

## 新holdoutへ持ち出す固定規則

3-stone parentについて、次を **v2 primary rule** とする。

1. 各candidate childを独立fresh process / fresh memoで最大1,000,000 visited nodes probeする。
2. probe中のexact `LOSS` は直接発見として扱う。
3. exact `WIN` は後段候補から除外する。
4. 残る `PROBE` childを **`memo` 昇順**に並べる。
5. `memo` tieは元のsolver既定順（child input order）が早いものを先にする。
6. この順序でexact solveし、最初のLOSS位置・visited costを記録する。

`mean_depth asc` などをholdout結果確認後にprimaryへ差し替えない。

## 判定

新holdoutでは最低限、以下を同時に報告する。

- v2 first LOSS位置の中央値
- solver既定順の中央値
- 無作為baseline（同じLOSS個数条件）
- parent-wise v2 vs solver既定順の勝/分/敗
- probe中exact completion数（WIN/LOSS別）
- probe費用 + exact solve費用を含む総visited cost
- 最大反例

既知7親の結果は仮説生成用であり、v2の成功判定には含めない。

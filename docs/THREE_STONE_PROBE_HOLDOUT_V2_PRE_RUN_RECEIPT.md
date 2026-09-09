# 10x10 three-stone isolated-probe v2 holdout: pre-run receipt

固定日: 2026-09-10

このreceiptは新しい3-stone holdoutのprobeを開始する前に固定する。選抜元CSVには既知 `loss_child` が含まれるが、holdout選抜工程では `index` と `state` 以外を候補記録へ取り込まず、選抜後もラベル結合を実行していない。

## 固定済み仮説・順位規則

規則commit:

```text
eff2b36ca01d98842af8adad80cd19d4bd3cf186
```

各parentの合法childを、childごとに fresh process / fresh memo、node budget 1,000,000 でprobeする。

順位は以下で固定する。

1. probe中に exact `LOSS` まで完了したchildは最優先（発見時点でparentのLOSS child探索は成功扱い）。
2. exact `WIN` まで完了したchildはLOSS候補から除外する。
3. node budgetで未完了の `PROBE` childは `memo` 昇順。
4. `memo` 同値はsolver既定入力順でtie-breakする。

既知7 LOSS親はこの規則の仮説生成にのみ使い、新holdoutの評価には含めない。

## Holdout選抜

selector commit:

```text
beb44948a9db3ce2d9f0dfe7953029d20bb7c66a
```

seed:

```text
kyouen-three-stone-isolated-probe-v2-holdout-2026-09-10
```

source blobs:

```text
4dd8d1e2869b55406f0df06ffee2366f90ce50ef  results/10x10/two-stone-90-61-child-proof.csv
ee53f63ca1d8c8bcc360144e0601f4c801057ee4  results/10x10/two-stone-90-66-child-proof.csv
3ee4e2b2867c757eac79909a79cac29c8b42d95a  results/10x10/blind-probe-parent-selection.csv
```

各sourceから6 parent、計12 parentをSHA-256順で選ぶ。過去の3-stone blind-probe parent 19件を除外し、source間もparentで重複排除する。

設計確認中に `two-stone-90-66-child-proof.csv` の先頭側（source index 0–38）のラベルが一部見える状態になったため、盲検性を保守的に守る目的で**両sourceとも index < 39 を候補集合から丸ごと除外した後に再抽選**した。この除外規則はholdout probe開始前に固定した。

最終選抜:

```text
selected parents                  12
eligible after quarantine/source  59 / 59
historical overlap                 0
quarantined rows selected          0
selection SHA256                   80168e938d2dcd3a4f7f7d538f3ff9123d12722d221c30e7e7e43b38194aa625
```

固定ファイル:

```text
results/10x10/three-stone-probe-holdout-v2.csv
```

選抜再現CI run `34378337405` は、同じ選抜を2回生成してbyte一致、12 parentの一意性、ラベル/search-data列を含まないことを確認してSUCCESS。

## 評価順序

ラベル漏洩を避けるため、次の順序を変更しない。

1. 12 parentについてchild集合をsolver既定順で固定する。
2. 全childを上記fresh-process probe条件で測定する。
3. `LOSS / WIN / PROBE` と `memo` からv2順位を作り、順位ファイルのSHA256を固定する。
4. **ここまで完了するまでsource proofの `loss_child` をholdoutへjoinしない。**
5. 順位固定後にだけ既知exact LOSS childラベルをjoinし、first LOSS rankを算出する。

## 事前固定する主要評価

各parentで v2順位・solver既定順について first exact LOSS rankを比較する。主報告値は次の4つとする。

- v2 first LOSS rank の中央値
- solver既定順 first LOSS rank の中央値
- parent-wise `v2 better / tie / worse` の件数
- v2とsolver既定順それぞれがfirst LOSSへ到達するまでの総探索順位（12 parent合計）

主要な成功判定は、**(A) v2の中央値がsolver既定順より小さく、かつ (B) parent-wise better件数がworse件数を上回る**ことの両方を満たすこととする。差が小さい場合も値をそのまま報告し、結果確認後に別特徴量へ主要評価を変更しない。

補助的に、各parentの合法child数から一様ランダム順のfirst LOSS rank期待値を計算し、probe中のexact completion数、visited総量、最大反例も報告する。ただし主要成功判定は上記(A)(B)から変更しない。

## pre-run state

```text
holdout selection:      FROZEN
holdout probe:          NOT RUN
holdout ranking:        NOT CREATED
holdout label join:     NOT RUN
holdout evaluation:     NOT RUN
```

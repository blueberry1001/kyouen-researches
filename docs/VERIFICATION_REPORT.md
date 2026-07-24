# 検証報告

## 結論

共通独立検査器 `kyouen-certcheck` は、1×1～9×9の全9証明書を受理しました。

```text
1  FIRST
2  FIRST
3  FIRST
4  SECOND
5  FIRST
6  FIRST
7  SECOND
8  SECOND
9  FIRST
```

完全な標準出力は `results/all-certificates-check.txt` にあります。

## 最大証明書

- 8×8：8,744,406ノード、約134 MiB（生）、約32 MiB（圧縮）
- 9×9：13,457,134ノード、約206 MiB（生）、約60 MiB（圧縮）

## 検査器が再計算するもの

- 整数行列式による危険な4点組
- 回転・反転8種類による正規形
- 各証明書局面の合法性
- 各局面の全合法手
- winning証人とlosing全分岐
- rankの厳密な減少

## 生成経路

- 1～8：`kyouen-certgen-1-to-8`
- 9：既存の中央初手後のKYOENC2証明書へ、空盤面winningノードと中央証人手を加えてKYOENC3へ変換

9×9の元証明書は、中央を置いた後の相手番をlosingとして独立検査済みです。変換器はそのDAGを変更せず、空盤面の1ノードだけを追加します。

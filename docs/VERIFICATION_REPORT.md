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


## 10×10との境界

上記の「全9証明書」は **1×1〜9×9** の共通KYOENC3証明書を指します。10×10の勝敗は別経路で確定しています。

- 100初手をD4対称性で15代表に縮約
- 15代表すべてを厳密探索して先手初手 `LOSS`
- よって100/100初手が先手負け、空盤面は後手必勝
- 証拠表: `rust/independent-verifier/evidence-sample/10x10-first-move-classification-complete.csv`
- Rust参照実装で証拠CSVの構造・対称性・分枝網羅性を監査
- KYOENC4形式で一部10×10実局面の証明DAGを独立Rust検査済み

ただし、10×10全分類を空盤面から1本のKYOENC4証明書へ統合する作業は未完了です。このため、1〜9の「単一証明書を共通検査器で全件検査」と10×10の「完全初手分類＋証拠監査＋部分KYOENC4検査」は区別して記載します。

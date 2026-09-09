# 10x10 three-stone isolated-probe v2: evaluation audit

固定日: 2026-09-10

この監査は holdout v2 の probe 実行前、かつ source proof の `loss_child` を holdout に結合する前に行った。

## 発見した評価上の偏り

固定済み v2 順位規則は次の通りである。

1. probe 中に exact `LOSS` まで完了した child を最優先する。
2. exact `WIN` まで完了した child は順位表から除外する。
3. 未完了 `PROBE` child を `memo` 昇順に並べる。
4. 同値は solver 既定順で tie-break する。

この規則自体は実行方針として合理的だが、従来の事前評価案である

```text
v2 first LOSS rank vs solver-default first LOSS rank
```

をそのまま主要な heuristic 評価に使うと、同じ母集団の順位を比較していない。

- v2 側は exact `WIN` が消えた候補列で順位を数える。
- solver-default 側は全合法 child を含む元の列で順位を数える。
- probe が exact `LOSS` を解いた場合、v2 rank は定義上ほぼ自動的に 1 になる。

したがって、probe が LOSS/WIN を exact に分類できた効果と、`memo` 昇順という未完了 child の順序付け能力が混ざる。特に exact WIN が loss child より前に多い parent では、`memo` に予測信号がなくても v2 rank が機械的に小さくなり得る。

これは盲検性の破れではないが、**heuristic の予測性能を測る評価としては比較対象が非対称**である。

## 修正版の評価分解

holdout の標本、probe 条件、順位規則は変更しない。評価だけを probe 前に次の2層へ分ける。

### 1. ordering-signal evaluation（主要）

`memo` 昇順そのものの信号を測る。

各 parent について、probe 後に `outcome=PROBE` のまま残った child だけを同一候補集合として取り出す。

- v2-unresolved: その集合を `memo` 昇順、同値は solver-default 順で並べる。
- default-unresolved: 同じ集合を solver-default 順で並べる。

source proof の exact LOSS child がこの unresolved 集合に含まれる parent だけで first LOSS rank を比較する。

主要報告値:

- v2-unresolved first LOSS rank 中央値
- default-unresolved first LOSS rank 中央値
- parent-wise better / tie / worse
- 両順序の first LOSS までの順位和

主要成功判定:

```text
(A) median(v2-unresolved) < median(default-unresolved)
AND
(B) better > worse
```

これなら両者が同じ child 集合を並べ替えるため、exact WIN 除外による rank 圧縮は生じない。

### 2. probe-completion / operational evaluation（補助）

probe 自体が exact に解いた価値は別に報告する。

各 parent について:

- exact LOSS completion の有無と visited
- exact WIN completion 数と visited
- unresolved child 数
- 固定済み実行方針（exact LOSS first / exact WIN drop / unresolved memo ascending）の first LOSS rank

ただし、この operational rank を solver-default の raw rank と直接比較して `memo` heuristic の証拠とはしない。必要なら probe に費やした visited も含めた総探索量で比較する。

## exact LOSS を probe が解いた parent の扱い

probe が loss child を exact `LOSS` まで解いた parent は、ordering-signal evaluation から除外する。

理由は、その parent では「未完了 child のどれを先に解くべきか」という順位問題自体が probe 中に終了しており、`memo` ordering の正否を観測できないためである。

これは失敗として捨てるのではなく、probe-completion 成功として別集計する。

## 既存の pre-run receipt との関係

`THREE_STONE_PROBE_HOLDOUT_V2_PRE_RUN_RECEIPT.md` に固定した以下は維持する。

- holdout 12 parent
- child 1161件と solver-default 順
- 60 batch
- fresh process / fresh memo
- node budget 1,000,000
- ranking rule
- raw seal -> ranking SHA -> label join の順序

変更するのは **主要評価で何を同じ母集団として比較するか**だけである。この監査は holdout probe 実行前・label join 前に固定したため、結果を見て評価を差し替える post-hoc 変更ではない。

## 次の実行時に必須の検証

label join 後の評価器は、parent ごとに次を機械的に確認する。

1. source proof の `loss_child` が frozen 1161-child universe に存在する。
2. probe outcome が `LOSS` なら source `loss_child` と一致することを確認する。
3. ordering-signal evaluation では `outcome=PROBE` の child だけを両 baseline で同じ集合として使う。
4. exact WIN / exact LOSS の child を unresolved rank の分母へ混ぜない。
5. ordering 対象 parent 数と probe-completion parent 数を別々に報告する。

未解決なのは、正しく fresh-process で測った `memo` 昇順が、この対称な unresolved-only 比較でも LOSS を早めるかどうかである。

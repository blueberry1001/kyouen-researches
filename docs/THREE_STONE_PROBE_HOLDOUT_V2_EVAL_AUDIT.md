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
- default-unresolved: 同じ集合を solver-default 順に並べる。

source proof の exact LOSS child がこの unresolved 集合に含まれる parent だけで、**その固定済み certified LOSS witness の順位**を比較する。

主要報告値:

- v2-unresolved certified-witness rank 中央値
- default-unresolved certified-witness rank 中央値
- parent-wise better / tie / worse
- 両順序の certified-witness までの順位和

主要成功判定:

```text
(A) median(v2-unresolved certified-witness rank)
    < median(default-unresolved certified-witness rank)
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
- 固定済み実行方針（exact LOSS first / exact WIN drop / unresolved memo ascending）における、probe が実際に証明した LOSS の最小順位

ただし、この operational rank を solver-default の raw rank と直接比較して `memo` heuristic の証拠とはしない。必要なら probe に費やした visited も含めた総探索量で比較する。

## 追加監査: source `loss_child` は「first LOSS」ではなく1個の certified witness

source proof CSV は各 WIN parent に対して `HAS_EXACT_LOSS_CHILD` と1個の `loss_child` を与える。しかし、これは「その child だけが LOSS」「solver-default 順で最初の LOSS」を意味しない。

既存の盲検追試データには、同じ parent に複数の exact LOSS child が存在する具体例がある。

`parent = 4,9,33` の batch0 exact 20件では少なくとも次の2件が `LOSS` である。

```text
2-4-9-33  LOSS
4-5-9-33  LOSS
```

したがって、source `loss_child` 1件だけを label join して得た順位を **first LOSS rank** と呼ぶのは不正確である。未知の別 LOSS child が、それより前に並ぶ可能性を排除できない。

このため holdout v2 の主要評価では、source `loss_child` を次のように扱う。

- source `loss_child` は **固定済み certified LOSS witness** と呼ぶ。
- 主要比較は同一 unresolved 集合上での **certified-witness rank** とする。
- `better / tie / worse` は同じ witness を2順序で比較するので有効であり、heuristic が「少なくとも1つの証明済み LOSS を前へ寄せるか」を測る。
- certified-witness rank は真の first LOSS rank の上界にはなるが、first LOSS rank そのものとは主張しない。
- 真の first LOSS rank を報告したい場合は、順位 SHA 固定・label join 後に必要範囲を追加 exact 証明するか、全 child の完全分類を行う。その追加探索は v2 の主要盲検判定とは分離する。

この修正は child 集合、probe 条件、順位規則、holdout 選択を一切変更せず、source label を見る前に評価語義を厳密化するものである。

## exact LOSS を probe が解いた parent の扱い

probe が source certified LOSS witness 自体を exact `LOSS` まで解いた parent は、ordering-signal evaluation から除外する。

理由は、その parent では「未完了 child のどれを先に解くべきか」という source witness に対する順位問題が probe 中に終了しており、`memo` ordering の正否を同じ形では観測できないためである。

これは失敗として捨てるのではなく、probe-completion 成功として別集計する。probe が source witness 以外の exact LOSS を発見した場合も、それは probe-completion の独立な成功として保存するが、source witness rank と混同しない。

## 既存の pre-run receipt との関係

`THREE_STONE_PROBE_HOLDOUT_V2_PRE_RUN_RECEIPT.md` に固定した以下は維持する。

- holdout 12 parent
- child 1161件と solver-default 順
- 60 batch
- fresh process / fresh memo
- node budget 1,000,000
- ranking rule
- raw seal -> ranking SHA -> label join の順序

変更するのは **主要評価で何を同じ母集団として比較するか**と、source `loss_child` の順位を **first LOSS rank ではなく certified-witness rank と呼ぶ**点だけである。この監査は holdout probe 実行前・label join 前に固定したため、結果を見て評価を差し替える post-hoc 変更ではない。

## 次の実行時に必須の検証

label join 後の評価器は、parent ごとに次を機械的に確認する。

1. source proof の `loss_child` が frozen 1161-child universe に存在する。
2. probe outcome が `LOSS` なら source `loss_child` と一致する、という強すぎる仮定は置かない。probe が source witness 以外の LOSS を発見することを許容し、全 exact LOSS を別記録する。
3. ordering-signal evaluation では `outcome=PROBE` の child だけを両 baseline で同じ集合として使う。
4. source certified LOSS witness が unresolved 集合に含まれる parent だけを主要順位比較へ入れる。
5. exact WIN / exact LOSS の child を unresolved rank の分母へ混ぜない。
6. ordering 対象 parent 数と probe-completion parent 数を別々に報告する。
7. `first LOSS` という語は、必要範囲の LOSS/WIN が完全に証明されて真に最小と分かる場合だけ使う。

未解決なのは、正しく fresh-process で測った `memo` 昇順が、この対称な unresolved-only 比較でも **固定済み certified LOSS witness** を solver-default 順より前へ寄せるかどうかである。

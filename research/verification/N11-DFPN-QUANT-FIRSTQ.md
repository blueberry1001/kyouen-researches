# 量化 solver: 最初の oracle query の実測

**11x11 の勝敗は UNKNOWN のまま。**
本ファイルは**途中経過**であり、勝敗の断定ではない。

- base commit: `98338d8`
- script: `dfpn_capture_first_query.sh`
- 機械: WSL / g++ -O3 -march=native、16 cores / 19 GB RAM
- memo 2^24、swap 使用 0

## 前回の結論は撤回する

前回は「予算が 2〜3 桁不足」で停止したとする記録を書いた。
**それはコードと一致していなかった。** 二つの誤り:

1. **`--quant-budget` は query ごと**に与えられる（20M/query）。
   前回は「三手目全体で共有する 20M」と読んで
   `20M / 13,572 = 1,473 nodes/query` と計算したが、これは誤り。
2. **`queries=0` は「query が始まっていない」ではない。**
   進捗行が oracle 呼び出しの**前**に出され、次の行が
   **最初の query が戻るまで**出ないため、
   止まった `queries=0` は「1 つ目の query がまだ終わっていない」
   という意味に過ぎなかった。

いずれもテレメトリの不足から生まれた解釈であり、
**測ってから判断すべきだった。**

## 計測: 最初の query を捕まえる

`s5_oracle()` の exact 呼び出しの直前に `[q-start]`、
直後に `[q-done]` を出した。両方に query 番号・canonical key・
legal count・nodes・ms を含む。

```
[quant] r2=0 m3=1 (1/119) queries=0 hits=0 nodes=0
[q-start] q=1 key=1152921504606849031,0 legal=93 budget=20000000
[q-done]  q=1 key=1152921504606849031,0 result=2 nodes=3932058 ms=16803
[q-start] q=2 key=1152921504606851079,0 legal=86 budget=20000000
[q-done]  q=2 key=1152921504606851079,0 result=2 nodes=4920863 ms=22134
[q-start] q=3 key=1152921504606855175,0 legal=95 budget=20000000
[q-done]  q=3 key=1152921504606855175,0 result=2 nodes=3320924 ms=15355
[q-start] q=4 key=1152921504606863367,0 legal=84 budget=20000000
[q-done]  q=4 key=1152921504606863367,0 result=2 nodes=4384707 ms=21064
[q-start] q=5 key=1152921504606879751,0 legal=93 budget=20000000
[q-done]  q=5 key=1152921504606879751,0 result=2 nodes=3733015 ms=18855
```

**query は正常に完了していた。** 1 個あたり 330 万〜490 万 nodes、
15〜22 秒。全件 LOSS。

## 単独 replay との比較

捕まえた key を `--exact-replay` で単独実行した:

| budget | result | nodes | wall |
|---:|---:|---:|---:|
| 2,000,000 | UNKNOWN | 2,000,000 | 7 s |
| 5,000,000 | **LOSS** | 3,935,197 | 16 s |
| 10,000,000 | LOSS | 3,935,197 | 16 s |
| 20,000,000 | LOSS | 3,935,197 | 16 s |
| 50,000,000 | LOSS | 3,935,197 | 16 s |

**単独 replay でも 393 万 nodes で閉じる。** 20M budget なら十分で、
budget をいくら上げても同じ結果になる（3,935,197 で打ち切られる）。

## 二択の答え: 前半（有利なケース）

「単独 replay で数百万 nodes で解ける → quant 側に
cache/TT 状態・ordering・実装上の性能問題がある」

→ **前者。** この query は 393 万 nodes whereas
既存の 23 s5 benchmark の中央値（~240 万）と同程度であり、
**「quant がはるかに難しい s5 を引いた」わけではない。**
23 個の benchmark が df-pn 選択で偏っていたという仮説は
**支持されない**。

したがって、停止の原因は「重い局面」ではなく
**クエリ数そのもの**にある。

## ただし新しい問題が明確になった

cost  =

```
（三手目の数）×（四手目の数）×（五手目の数）×（1 query の nodes）
```

1 query = 393 万 nodes、16 秒。1 送信あたり
最悪 117 × 116 = 13,572 query = **2.2e10 nodes / 16 時間**。
20 送信は到底間に合わない。

ただし実測の最初の 6 query がすべて LOSS だった事実は、
**その m4 の残りの五手目も LOSS である可能性**を示唆する。
もしそうなら m3 を少数の query で反証でき、
13,572 query/m3 という最悪値は関係しなくなる。

**ただし断定はできない**: m4 は OR ノードなので、
その m4 を反証するには**合法な m5 を全て LOSS と証明する必要がある**。
最初の数個が LOSS だっただけでは m4 は反証されていない。
（この点を最初に誤って記載していたので訂正する）

**cache の実効が鍵**であり、`hits` が `queries` に
近づけば重複が効くことを示す。現時点で capture した範囲では
まだ `hits` hue 確認できていない（6 query すべて異なる key）。

## 実装上の 2 つの修正

1. **`--quant-timeout` が機能していなかった。**
   `run_quant()` は timeout を 1 返信が返った後にしか見ず、
   oracle 内部では `set_deadline(0)` にして，所以
   **最初の 1 query が 12 分走っても止まらない**。
   `set_quant_deadline()` を追加し，**query ごと**に
   期限切れを確認するようにした。sentinel `-1` を返し，
   quant_solve はそれを「時間切れ」として扱う。

2. **quant_solve は one-sided prover だった。**
   最後が `return 0`（UNKNOWN）であり，
   全 m3 について「ある m4 で全 m5 が LOSS」を完全に反証できた場合でも
   LOSS を返さなかった。
   `saw_unknown` を導入し，
   **全 query が確定的に解決した場合のみ LOSS を返す**ようにした
   （UNKNOWN が 1 つでもあれば UNKNOWN のまま）。

## 次の手への示唆

1. **cache の実効を長い測定する。** 数百 query 回して
   `hits/queries` を見る。これが「20 返信すべて回れるか」を
   決める。
2. **五手目の順序を考える。** 最初の m4 で五手目が順に LOSS に
   なっていくなら、LOSS になる五手目の並びが分かれば先に試して
   query 数が減る。
3. **三手目の順序。** 1 つ目の三手目は全 query LOSS だった。
   cache hit が多い三手目から試す。

## 記録

- 1 返信（r2=0）は 300 秒で時間切れ。
  1 個目の三手目の 1 個目の四手目の反証には成功しているが，
  三手目 119 個を全て試算是終わっていない。
- 二石 root は 1 個も閉じられていない。
- **11x11 は UNKNOWN のまま。**
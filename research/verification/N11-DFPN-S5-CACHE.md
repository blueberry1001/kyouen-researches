# s5 verdict 永続 cache: 三手目 m3=1 の完全反証

**11×11: UNKNOWN**

- base commit: `2c28436`
- script: `dfpn_s5_cache.py`, `dfpn_s5_cache_test.sh`
- 対象局面: first=60, r2=0, **m3=1**, **m4=2**
- 機械: WSL / g++ -O3 -march=native、memo 2^24、swap 使用 0

## 論理的な帰結

`s4 = {60,0,1,2}` の合法な五手目 **103 個すべて**について、
到達する 5 石局面が **exact LOSS** であることが cold replay で証明済み
（`N11-DFPN-S5-CHILD-DISTRIBUTION.md`）。

したがって:

```
{60,0,1,2} は LOSS
  （合法な五手目が全て LOSS なので、四石局面は反証される）

よって {60,0,1} も LOSS
  （後手が m4=2 を選べば先手勝ち命題を潰せる）
```

つまり **reply r2=0 に対する先手の三手目 m3=1 は完全に反証された。**
未完探索や時間切れではなく、**証明済みの積み上げ**である。

## 実装: 永続 s5 verdict cache

PnTT（67M entry）を保持する代わりに、
`canonical s5 key -> WIN/LOSS` だけをファイルに保存する。

- `--s5-cache=P`   : 起動時に読む
- `--s5-cache-out=P`: 起動時に追記する（append-only）
- **UNKNOWN は絶対に保存しない。** budget 切れは
  後でより豊かな query が引き継いでしまうため。

.cache フォーマット: `s5verdict,key_lo,key_hi,stones,result,nodes`

## 実測: cache 103 件投入、query 0 で反証

```
quant,0,UNKNOWN,-1,0,216,206,49115136,240,3,2,0,0,0,2,0,...
# SUMMARY ... oracle_queries=216 oracle_hits=206
            cache_loaded=103 cache_size=112
```

| 指標 | 値 |
|---|---:|
| cache 読込 | 103 |
| oracle hits | **206** |
| 実際の oracle query | **9** |
| m3 を refuted にした数 | **3** |
| m3 を UNKNOWN にした数 | 2 |

`[quant]` 行が示す進行:

```
[quant] r2=0 m3=1 (1/119) queries=0   hits=0   nodes=0
[quant] r2=0 m3=2 (2/119) queries=103 hits=103 nodes=0
[quant] r2=0 m3=3 (3/119) queries=206 hits=206 nodes=0
```

**m3=1 は nodes=0 で refuted された。** 103 個の cache hit のみで、
exact 探索を 1 ノードも使わずに終わった。
さらに m3=2, m3=3 も同様に refuted（cache に既にある s5 を流用）。

残り 9 回の実 query は、cache に無い m4 の s5 を解いたもので、
1 回の cost は 3.5M〜11.5M nodes。

## 独立検証

`dfpn_s5_cache.py` の verify は、solver の計数に依存せず
**cache と局面列挙だけ**から反証を再計算する:

```
cache entries        : 103
children of s4       : 103
children NOT in cache: 0
cached LOSS          : 103
cached WIN           : 0
REFUTATION VERIFIED
```

## 今回の範囲の限定

- **ordering 問題でないことが確定したのは s4={60,0,1,2} についてのみ。**
  103 個全部 LOSS なので、この局面には探すべき WIN child 自体がない。
  他の s4 に cheap WIN が存在する可能性は残る。
- reply r2=0 全体が LOSS とは**まだ言っていない。**
  三手目 119 個のうち refuted は 3 個、UNKNOWN が 2 個で、
  240 秒の制限で終わっただけである。
- 二石 root は 1 個も閉じていない。

## 次の手

1. **他の m3 を同じ方法で refuted にする。** cache 方式和なら
   並列 worker で未知の s5 を，解けた順で cache に積む。
2. **s5 verdict cache を git 管理するか**を判断する。
   103 件は小さいが、今後数万〜数十万件になると Git には重い。
3. **他の s4 でも WIN ゼロか**を確認する（ordering 問題の
   範囲を一般化できるか）。

## 記録
- UNKNOWN を LOSS に昇格させる変更はしていない。
- 回帰: hybrid n=4 LOSS / n=5 WIN / n=6 WIN / n=7 LOSS、
  adaptive 全条件 pass。
- **11×11: UNKNOWN**

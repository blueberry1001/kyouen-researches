# LOSS-edge cover: 1 つの s4 証明が 4 つの三手目を反証する

**11×11: UNKNOWN**

- base commit: `8ee5eef`
- script: `dfpn_cover_probe.sh`, `dfpn_cache_robustness.sh`,
  `dfpn_s5_cache.py`
- 対象: first=60, r2=0（119 頂点、7021 辺）

## 構造: s4 を辺として見る

二石局面 {60,0} に対して、合法な三手目 119 個を頂点とし、
相異なる 2 頂点 {a,b} の組を**辺**とする。
{60,0,a,b} は m3=a,m4=b でも m3=b,m4=a でも同じ s4 局面である。

```
E(a,b) = WIN   ... ∃m5: s5 が WIN
       = LOSS  ... ∀m5: s5 が LOSS

m3=a が反証される  <=>  a に接続する LOSS 辺が 1 本でもある
reply r2=0 が LOSS <=>  ∀a ∃b: E(a,b)=LOSS
```

すなわち **LOSS と証明された s4 辺の集合で 119 頂点を覆えばよい。**
これは 119 x 117 x 116 の入れ子ループではなく、集合被覆（set cover）型の問題である。

## 実測: cache だけで 2 本の LOSS 辺

```
# LOSS-edge cover: first=60 r2=0 vertices=119 cache_loaded=103
# edges total=7021 LOSS=2 WIN=0 UNKNOWN=7019
cover,1,2,LOSS
cover,11,22,LOSS
# COVER covered=4/119 edges_used=2
```

**1 本の s4 証明が 4 つの三手目インデックスを反証した。**

### なぜ {1,2} と {11,22} が同じ証明なのか

点番号は `v = y*11 + x` なので、

- 点 2  = (x=2, y=0)
- 点 22 = (x=0, y=2)

であり、これは主対角線についての鏡像（D4 群の元）である。
したがって **{60,0,1,2} と {60,0,11,22} は D4 で同一の局面**であり、
8 個の D4 像が完全に一致する（独立に検証した）。

結果として 1 本の proved LOSS 辺が、辺のラベルとしては 2 本、
覆われる三手目としては **4 つ**を反証する。

これは単なる cache hit より強い構造的再利用である。

## cache の堅牢化（証明材料として）

cache は証明材料になったので、以下を実装した:

| 項目 | 挙動 |
|---|---|
| 同一 key に WIN と LOSS | **throw**（後勝ち黙示的上書きをしない） |
| ヘッダに n=11 / schema=1 が無い | **throw** |
| UNKNOWN verdict | ロードも保存も**しない** |
| 再保存 | 新規確定分のみ append（`touched` で判定） |

`dfpn_cache_robustness.sh` で 5 ケースを検証した:
正常読込 / 矛盾 verdict 拒否 / 外部ヘッダ拒否 / UNKNOWN 無視 /
再保存で行数が増えない（215 -> 215）。

## 独立検証の境界

`dfpn_s5_cache.py` の verify は **構造を独立に検証している**:
103 個の合法 s5 子を正しく列挙し、その全 key が cache で LOSS に
なっていることを、solver 本体の counter に依存せず確認する。

ただし **cache に書かれた各 LOSS 判定そのものを再証明しているわけではない**。
各 103 局面は cold replay で解いており実質かなり強いが、
最終 certificate では

- 「cache のラベルを信用する verifier」
- 「各 s5 proof まで独立に再検証する verifier」

を分けるのが望ましい。

## ゼロ探索だった m3 の厳密な範囲

ログのクエリ累積:

```
m3=1 start: queries=0   hits=0
m3=2 start: queries=103 hits=103
m3=3 start: queries=206 hits=206
```

したがって **m3=1 と m3=2 は 103 cache hit のみでゼロ探索**と断定できる。
**m3=3 はそうでない**: その後に新規 query が発生しており、
cache hit だけのゼロ探索ではない。

## 現状

- 119 頂点のうち **4 のみ**が cache で覆われている。
  残り 115 は s4 辺の証明が必要であり、そこが次の作業である。
- reply r2=0 が LOSS とは**まだ言っていない。**
- 二石 root は 1 個も閉じていない。

## 次の一手

1. **LOSS 辺を 1 本ずつ積む並列 driver**。辺 1 本で 2 頂点
   （D4 で縮約するなら 4 頂点）覆えるので、119 頂点なら理論上
   数十本の s4 LOSS 証明で足り得る。
2. **s4 verdict の永続化**。s4 LOSS 証明には
   「全合法 s5 子 LOSS」の子リスト参照だけあればよく、
   WIN なら s5 WIN の witness 1 個で済む。cache を s4 層にも
   持たせれば毎回 103 key をなめる必要がなくなる。

## 記録
- 回帰: hybrid n=4 LOSS / n=5 WIN / n=6 WIN / n=7 LOSS、
  adaptive 全条件 pass。
- **11×11: UNKNOWN**

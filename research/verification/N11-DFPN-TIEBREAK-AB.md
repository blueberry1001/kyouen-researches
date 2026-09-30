# 11x11 中央 v=60 tie-break A/B（asc vs desc, 各 15 分）

**11x11 の勝敗は UNKNOWN のまま。** どちらの arm も 900 秒で
**TIMEOUT（未証明）**。20 返信のどれも WIN/LOSS として確定していない。

- solver: `cpp/solvers/kyouen_dfpn_root.cpp`、commit `478f366`
- 機械: WSL / g++ -O3 -march=native、**16 cores / 19 GB RAM**
- memo power: 2^26 = 67,108,864 entry（両 arm 同一）
- budget: 900 s、`--only=60`、`--children`
- **並列 2 本**（asc / desc を同時実行）。コア数 16 に対し 2 本なので
  物理コア競合なし。RSS 各 ~1.9 GB、合計 ~3.8 GB < 18 GB available。
  **swap 使用 0**（swap-tainted な結果は使っていない）。
- **fresh process / fresh TT / TT 再利用なし**（両 arm 同一条件）

## 変更内容

df-pn の b1 選択は「proof number が等しい子」に対する tie-break だけを
pn/dn 比較の後に適用していた。これを `tie_better()` に hoist し、
実行時選択できるようにした。

- `--tiebreak=asc`（baseline）: legal count **ASC**, then canonical key **ASC**
- `--tiebreak=desc`（challenger）: legal count **DESC**, then canonical key **DESC**

`desc` は DFS ソルバー側の事前登録済み実験
（`cpp/solvers/kyouen_solver_10_depth5_max_first.cpp`）で効いたルール。

**重要: tie-break は pn/dn が既に等しい子にのみ作用するため、
証明結果の正しさに影響しない。** n=4,5,6,7 の全 root で
両 mode の勝敗が完全一致することを確認済み
（`research/verification/scripts/dfpn_regress_tiebreak.sh`）:

| n | asc expansions | desc expansions | 勝敗 |
|---|---|---|---|
| 4 | 239 | 235 | LOSS / LOSS |
| 5 | 847 | 1,026 | WIN / WIN |
| 6 | 55,561 | 82,424 | WIN / WIN |
| 7 | 2,123,417 | 2,025,919 | LOSS / LOSS |

## 結果

| 指標 | asc | desc |
|---|---:|---:|
| outcome | TIMEOUT | TIMEOUT |
| expansions | 12,106,467 | 11,818,025 |
| visited | 25,165,824 | 25,165,824 |
| root_pn | 100,229 | 99,903 |
| root_dn | 24,477 | 24,691 |
| pn/dn | 4.076 | 4.051 |
| **solved（TT 全体）** | **24** | **35** |
| root 直下の solved 子 | 0 個 | 0 個 |
| maxdepth | 12 | 12 |
| evict_open / evict_solved | 0 / 0 | 0 / 0 |

depth-exp:
- asc: `d5=940,628 d6=5,682,478 d7=5,034,521`（d5-d7 で 96.3%）
- desc: `d5=939,955 d6=5,516,876 d7=4,898,156`（d5-d7 で 96.1%）

## 20 返信の分布（15 分後）

| 指標 | asc | desc |
|---|---:|---:|
| Σ pn（= root_pn） | 100,229 | 99,903 |
| pn 最小 / 最大 | 3,091 / 6,400 | 2,947 / 6,235 |
| Σ work（root 降下回数） | 103,801 | 99,985 |
| work 最大 / 最小 | 7,840 / 1,643 | 6,538 / 1,864 |
| 上位 10 子が root_pn に占める割合 | 59.7% | 59.5% |

全 20 子 `st=1`(OPEN)、`legal=119`。**どちらの arm も solved な子は 0 個。**

## 判定

**明確な勝者なし。差分は 1〜4% 程度，而且 方向が混在している。**

- `expansions`: desc が 2.38% 少ない
- `root_pn`: desc が 0.33% 小さい
- `root_dn`: **asc が 0.87% 小さい**（desc が不利）
- `solved`: desc が 35 vs 24 で多い（+46%）
- `Σ work`: desc が 3.7% 少ない

つまり **`desc` は「より多くの solved エントリを作り」「より少ない降下
回数で済ませる」方向に動くが、rootの勝ち証明に直接必要な改善は見えていない。**
中央1石局面は AND node なので、中央初手の勝ち（元の先手勝ち）を証明する側は
`root_pn = Σ(20返信のpn)` である。したがって中央を証明するには
**20返信すべてで `pn=0` が必要**。一方 `root_dn = min(20返信のdn)` は
中央初手を反証する側で、どれか1返信が `dn=0` になれば中央はLOSSになる。
以前ここを逆に「root_dnが証明側のbottleneck」と読んでいたのは誤り。

さらに 900 秒時点でも **20 返信すべて OPEN**。60 秒時点で見られた
`pn=118` の 10 個同値クラスタは解消し、全員が `pn` 3,000〜6,400 に
散らばった。`pn/dn` も 4.08 / 4.05 で 1 には遠く、
**どちらの arm も 15 分では形になるような進展は見られない。**

## 20 返信の内訳（asc / desc, work 降順）

asc:
```
move= 0 pn=4542 work=7840    move=12 pn=4329 work=7057
move=16 pn=4429 work=6790    move= 5 pn=4073 work=6141
move=27 pn=4312 work=5837    move= 4 pn=6099 work=5646
move=15 pn=6167 work=5638    move=26 pn=5775 work=5602
move= 2 pn=6257 work=5575    move=13 pn=5898 work=5567
move=25 pn=6038 work=5516    move=14 pn=5575 work=5429
move= 3 pn=6071 work=5350    move= 1 pn=6400 work=5066
move=38 pn=4419 work=4811    move=24 pn=3949 work=4488
move=37 pn=5543 work=4229    move=36 pn=3945 work=3761
move=49 pn=3317 work=1815    move=48 pn=3091 work=1643
```

desc:
```
move= 5 pn=4281 work=6538    move=16 pn=4528 work=6481
move=26 pn=5770 work=6403    move=38 pn=4274 work=6077
move=37 pn=5480 work=5766    move=25 pn=6041 work=5720
move=15 pn=5963 work=5706    move=12 pn=4255 work=5619
move=36 pn=3948 work=5397    move=13 pn=5879 work=5293
move=14 pn=5622 work=5268    move= 0 pn=4599 work=5179
move= 4 pn=6103 work=4878    move=24 pn=4137 work=4421
move= 3 pn=6223 work=4275    move= 2 pn=6132 work=4229
move=49 pn=3750 work=4078    move= 1 pn=6235 work=3591
move=27 pn=3918 work=3202    move=48 pn=2947 work=1864
```

両 arm とも **`move=48` が最下位、`move=0` / `move=5` / `move=16` が上位**
というおおむね共通の結果。`desc` は順位の上位を小幅にずらすだけで、
構造的には同じ探索をしている。

## 次の手への示唆（測定であり結論ではない）

1. **tie-break の変更は現状ほぼ無効**。desc を採用する根拠は薄い。
   baseline の asc を維持し、時間を長い走に回すのが妥当。
2. **`solved` だけが改善している（24 → 35）**点が唯一の差。
   これは「より多くの末端局面が解けている」ことを意味するが、
   それらは root の証明にはまだ寄与していない
   （20 返信すべて OPEN）。
3. **どちらの arm も 20 返信が全部 OPEN**。15 分では1つも解けていない。
   tie-break差もroot境界では小さいため、descをさらに追う優先度は低い。
4. 次は中央の20返信を `{60, reply}` の2石rootとして**独立に**
   fresh process / fresh TTでスクリーニングする。20個すべてWINなら中央初手の
   P証明へ直結し、1個でもLOSSなら中央候補を反証できる。これにより
   「中央の証明が20-wayで均一に難しい」のか「数個だけが真のボトルネック」
   なのかを直接測る。

## 記録上の注意

- 本ファイルは **途中経過**であり、勝敗の断定ではない。
- 両 arm とも `done=0 timeout=1`。**1 つも証明完了していない。**
- 15 分の run で `maxdepth=12` に留まる。depth-exp でも
  `d10=837, d11=14, d12=5`（asc）でしか展開されていない。

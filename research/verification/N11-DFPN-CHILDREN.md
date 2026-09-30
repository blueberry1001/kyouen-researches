# 11x11 中央初手 v=60: root 直下 20 返信の診断

**11x11 の勝敗は UNKNOWN のまま。** 20 返信のいずれも証明は完了していない。

- solver: `cpp/solvers/kyouen_dfpn_root.cpp`（`--children` モード、本ファイルと同時 commit）
- 機械: WSL / g++ -O3 -march=native
- memo power: 2^26 = 67,108,864 entry
- budget: 60 s / `--budget=60`、fresh process、fresh TT、TT 再利用なし
- 結果: **TIMEOUT（未証明）**

## この診断が答える問い

1 時間走った後の root 値 `(pn=202718, dn=110924)` だけでは、
次に何を集中すべきか分からない。root は AND node なので

```
root_pn = Σ (20 返信の pn)
root_dn = min(20 返信の dn)
```

であり、**どの返信が root pn を支配しているのか** を分解する必要がある。

- 20 返信が均一なら → 「中央の証明そのものが広い」
- 1〜2 個が突出なら → 「その 1 個が明確なボトルネック」で tie-break 改善の矛先が決まる

## 出力形式

```
[children] t=<s>s n=<root の子数> updates=<root 子の観測回数>
  move=<盤面 index> pn=<pn> dn=<dn> st=<状態> work=<root からの降下回数> legal=<合法手数>
```

- `st` は `enum { FREE=0, OPEN=1, WIN=2, LOSS=3 }`。本測定は全 20 行 `st=1`(OPEN)
- `work` = その返信に root から **降下した回数**（root 集約時に b1 として選ばれた回数）
- ソート: `work` 降順、同値なら `pn` 昇順
- `updates` は `gen_into` が root 子を更新した総回数（77,180）。
  これは `work` の総和（3,859）よりはるかに大きい = root が
  3,859 回降下され、そのたびに 20 子すべての pn/dn が読み直された。

## 実測（v=60, 60 s, memo 2^26）

```
# [v=60] TIMEOUT reason=TIME_BUDGET expansions=813959 visited=1701441
#   root_pn=16453 root_dn=5934 memo=813959/67108864 solved=0 solved_disc=0

[children] t=60s n=20 updates=77180
  move=24 pn=1997 dn=5935 st=1 work=427 legal=119
  move= 5 pn=1878 dn=5935 st=1 work=416 legal=119
  move=48 pn=1967 dn=5938 st=1 work=382 legal=119
  move= 0 pn=1819 dn=5934 st=1 work=368 legal=119
  move=27 pn=1637 dn=5934 st=1 work=339 legal=119
  move=49 pn=1867 dn=5935 st=1 work=312 legal=119
  move=12 pn=1292 dn=5936 st=1 work=299 legal=119
  move=36 pn=1163 dn=5940 st=1 work=288 legal=119
  move=16 pn= 822 dn=5935 st=1 work=255 legal=119
  move=38 pn= 831 dn=5937 st=1 work=219 legal=119
  move=26 pn= 118 dn=5960 st=1 work= 72 legal=119
  move=15 pn= 118 dn=6025 st=1 work= 68 legal=119
  move=14 pn= 118 dn=6150 st=1 work= 65 legal=119
  move=25 pn= 118 dn=5999 st=1 work= 58 legal=119
  move=37 pn= 118 dn=5989 st=1 work= 57 legal=119
  move= 3 pn= 118 dn=6179 st=1 work= 55 legal=119
  move= 2 pn= 118 dn=5959 st=1 work= 53 legal=119
  move= 1 pn= 118 dn=6143 st=1 work= 49 legal=119
  move= 4 pn= 118 dn=6002 st=1 work= 40 legal=119
  move=13 pn= 118 dn=5987 st=1 work= 37 legal=119

[depth-exp] total=813959 d1=1 d2=20 d3=950 d4=31869 d5=384413 d6=355782 d7=38077 d8=2847
```

**整合性チェック（両方とも一致）**:
- `Σ pn = 16453` = `root_pn` → 診断は root 集約と矛盾しない
- `min dn = 5934` = `root_dn` → 同上
- `n=20` = root の実際の fan-out と一致

## 観察

- **20 返信は 10 + 10 に明確に二極化した。**
  - 上位 10 子: `pn = 822 … 1997`、`work = 219…427`
  - 下位 10 子: **`pn = 118` で完全に同値**、`work = 37…72`
- **下位 10 子の `pn=118` は proof number がまだ同値という意味**で、
  易しいことを意味しない。`dn` だけが 5959〜6179 とばらついている。
  `pn` は「元の先手勝ち」を証明する側、`dn` はそれを反証する側の数なので、
  pn が揃ったまま dn だけが動いているのは **disproof 側だけに差が付いている**
  という読み方が正しい。
- **work は上位 10 子が下位 10 子の 3〜11 倍。** 探索は上位 10 子に偏っている。
  ただしこれは df-pn の「最も proving な子を先に掘る」性質の反映であり、
  下位 10 子が易しいという推論はできない。
- **legal は全 20 子とも 119**（= 121 − 1 着手 − 1 禁止）で**完全に同値**。
  したがって現在の tie-break である「合法手数（`count`）小さい順」は
  **root 直下では一切効いていない**（全子 count 同値 → 次のキー `key` で決まる）。
  これは tie-break 改善の重要な制約になる。
- **depth-exp は d5-d6 が 91%**（384,413 + 355,782 = 740,195 / 813,959）。
  展開の 9 割が 5〜6 手目に集中。`d1=1`（root 自身）、`d2=20`（20 返信ちょうど）と
  構造も整合している。

## 次の手への示唆（測定であり結論ではない）

中央1石局面は AND node なので、**中央初手が勝ちであることを証明するには
20返信すべてを WIN（各子の `pn=0`）にする必要がある**。逆に20返信の
どれか1つでも LOSS（`dn=0`）になれば中央初手は反証される。
したがって、中央を1つのAND rootとしてだけ回し続けるより、
20個の2石局面 `{60, reply}` を独立rootとして fresh TT でスクリーニングする
価値が高い。

1. **`legal` tie-break は root 直下で無効**（全 119）。key 順の偶然に依存している。
   DFS 側で効いた ordering を入れるなら、`count` 以外の軸が必要。
2. **上位 10 子が root_pn を支配**（92.8%: 15,273 / 16,453）。
   ただし中央の勝ち証明には最終的に20子すべての `pn=0` が必要。
3. 次の実験は20返信それぞれを5分程度、fresh process / fresh TTで解く。
   完全WINになった返信数、TIMEOUT時のpn/dn、expansions、solved descendants、
   maxdepthを比較し、本当に難しい返信を特定する。
4. `pn/dn` 比が1へ近づくこと自体は「証明完成へ近づいている」ことを意味しない。
   主要指標は:
   - root 直下で WIN（pn=0）の子が現れるか
   - LOSS（dn=0）の子が1つでも現れるか
   - 未解決子の難度が均一か、一部だけ突出するか
   - work が1本に固定されるか分散するか

## 正当性の確認

本診断は観測のみを追加し、探索結果の数値には一切影響しない
（`track_children_` が false のとき `gen_into`/`mid_iter` は
従来と同じ命令列）。以下は再確認済み:

- n=4 LOSS / n=5 WIN / n=6 WIN / n=7 LOSS（`dfpn_regress2.sh`、全一致）
- DFS 交差検証 n=6 14 roots + n=7 15 roots、`MISMATCHES=0`

## 実装上の注意点（開発中に踏んだ罠）

1. **ハッシュ衝突**: 当初 `lo*1000000007+hi` をキーにしたら
   20 子の root に対して **n=970 の phantom 子**が出た。
   `std::map<Bits,ChildStat>` に変更して解消。
2. **`stones_` フィールドでの root 判定は不可**: `expand()` の
   throwaway `Gen` や深い frame が `stones_` を上書きし、
   20 個の root 子以外が混入した（同じく n=970）。
   `gen_into(..., bool is_root)` を**明示引数**で渡すように変更。
   この 2 点を直さないと診断値そのものが信頼できない。

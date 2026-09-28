# Round3: B158–B167 / B251–B264（grp4・20件・書出し専用）

対象: `research/hypothesis-bank-2026-09-27.md` の B158–B167 と B251–B264。
前回個票: `batch-08.md`（B158–B167）、`batch-10.md`（B251–B264）。
判定の推移はすべて `round3_unresolved.json`（前回ラベルを機械抽出したもの）と一致することを確認済み。

## 読むだけとした先行スクリプト（**実行していない**）

- `research/verification/scripts/round3_chunk4_core.py` — 共通エンジン。docstring に「n=4 (16 点) と n=5 (25 点) の FULL retrograde solve を高速化し，禁止 4 点組の bitmask、parent→child 辺、P/N・Grundy・最悪手数 d(S)・最適 AND/OR 証明木サイズ・新規禁止集合マップ K(p)・厳密 Z(lambda) を提供。整数演算のみ、numpy は索引配列の補助にのみ使用」とある。
- `research/verification/scripts/round3_chunk4_relax.py` — docstring の対象は **B251 / B252 / B253 / B255 / B256 / B258**。「n=4 のみ（5,811 状態、完全解 1 回あたり約 0.6 s）、申告された exhaustive 」、出力は `research/verification/round3_chunk4_relax.json`。
- `research/verification/scripts/round3_chunk4_u.py` — docstring の対象は **B261 / B262 / B263 / B264**（ほかに B265–B270）。「n=4 全数（5,811 状態）と n=5 全数（151,394 状態）、重い per-state ループは必要な層に限定」、出力は `research/verification/round3_chunk4_u.json`。
- `research/verification/scripts/round3_chunk2_geom.py` — docstring: 禁止 4 点組は「4 共線 または 4 共円」。C(V,4) 全探索の代わりに格子直線と三重点外接円を列挙し、n≤7 で F_n を厳密再現（n=8,9,10,11 で約 50 倍高速）。

## 既存データ（読み取っただけ）

`round3_chunk4_selfcheck.json`（n=2..5 の確定事実照合）、`batch08_results2.json`（`D_n_ext` / `parity` / `pair_spreads` / `deg_extrema` / `R_over_C`）、`batch08_results3.json`（`b179` の K_n と n_max_sets）、`research/findings.md`（F-AE / F-AF / F-AV / F-AU）、`PROTOCOL.md` の確定事実表。

## 最重要の事実（本バッチ全体の結論を左右する）

**`round3_chunk4_relax.json` と `round3_chunk4_u.json` は `research/verification/` に存在しない。**
同ディレクトリの chunk4 系 JSON は `round3_chunk4_selfcheck.json` と `round3_chunk4_A1.json` の 2 つだけである。
したがって B251–B264 には**先行計算の数値が一つも存在せず**、前回ラベルからの前進は書出しの記録に留まる。
B158–B167 側は_chunk2 の出力 JSON も `round3_chunk2_saturation.json` 以外に該当キーが無く、同様に数値が来ない。

---

## B158 [存在] 高次数点を置くと合法手がより多く残る
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「同一親 S からの合法 p,q 比較と、|L(S+p)| の逆転探索が必要。`fact_10x10_two_stone_mobility.py` があるが本バッチでは未実行」（`batch-08.md` B158 の「範囲」行）
- 今回の範囲: 書出しのみ（再計算なし）。再照合した既存データ: `batch08_results2.json` の `pair_spreads`（n=4..7 の二点次数の層別 spread）と `deg_extrema`（n=3..7 の点次数 min/max/中心/角）、`research/findings.md` の F-AE・F-AV・F-AU。
- 証拠: 既存データに「同一親 S からの 2 手の逆転」を測る記録は無い。むしろ**逆方向が確定している**: F-AV（findings.md:821-834）は「石数 2 の後は必ず合法手 98。4 点禁止のため 3 点目は常に安全」とし、「二石では Σd や pair-quads が動いても mobility が変わらない（常に 98）」「三石で初めて mobility が盤構造を反映する」と記録している。点次数の実測は `deg_extrema`: n=5 は 100（四隅）～156（(1,1) 型）で中心 116、n=6 は 191（四隅）～313（中心 4 点）、n=7 は 374（四隅）～640（中心 1 点）。F-AE は 10×10 で隅 1515・平均 2177.64・r²=4.5 で最大 2499（中心の 2401 より大きい）、r²=8.5 の 2395 > r²=6.5 で**完全単調でない**と記録。F-AU は 10×10 のサイズ 10–11 の極大配置が境界 8/10 点と周縁に張り付くことを実例付きで記録している。
- 残った障害: B158 は存在命題「同じ親 S から合法な p,q を比べ、`d(p)>d(q)` なのに `|L(S+p)|>|L(S+q)|` となる逆転が存在する」。既存の 10×10 記録は二石局面の mobility が**盤構造によらず定数 98**であることを示しており、二石層には逆転の素地が原理的に無い（どの 120 軌道でも同じ）。B158 に必要なのは「一石親 S 起点」の比較表で、それはどの保存済み JSON にも無い。前回メモが名指しした `scripts/analysis/fact_10x10_two_stone_mobility.py` は**スクリプト本体だけ**で、出力 `fact_10x10_two_stone_mobility.json` はリポジトリ内に存在しない。既存データに情報がなく、前回と状況が変わらない。

## B159 [統計] 境界効果の到達距離は固定ではない
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「D_n の方向分解（新方向が n に応じて開く）は境界効果が中心まで及ぶことと整合するが、直接測定は未実施」（`batch-08.md` B159 の「メモ」行）
- 今回の範囲: 書出しのみ。再照合した既存データ: `batch08_results2.json` の `D_n_ext`（n=4..40 の D_n とその n⁵/n⁶ 正規化）、`deg_extrema`（n=3..7）、`pair_spreads`（n=4..7 の pair_deg_range）。
- 証拠: `D_n_ext` の D_n は n=4: 10、5: 64、6: 234、7: 660、8: 1524、9: 3156、…、40: 12,173,524 で、D_n/n⁵ は n=4 の 0.00977 から n=32 の 0.1119 までほぼ単調に上昇し n=40 で 0.11888。`deg_extrema` は n=7 で中心 1 点の d=640 が最大・四隅 374 が最小、つまり n≥6 では**中心が禁止点数最大**で隅が最小（F-AE と同型）。二点次数の取り得る範囲は n=4: 3..23、n=5: 4..36、n=6: 3..51、n=7: 3..74。
- 残った障害: B159 が問うのは「n→n+1 の**外周追加時**、内部点の新規禁止四点数の**増加分布**」。保存済み JSON はすべて静的な d(p) のスナップショットであり、盤寸法を変える差分 Δd(p) はどこにも記録されていない。`D_n` は「少ない代表方向へ圧縮しきれない残り」の大きさであって Δd(p) ではないため、D_n の n 依存を B159 の証拠に読み替えるのは禁止事項（別指標の混入）に当たる。既存データに情報がなく、前回と状況が変わらない。

## B160 [存在] 同次数点どうしを交換しても全高階特徴は保存されない
- 判定: **INCONCLUSIVE**（前回: INCONCLUSIVE → 今回: INCONCLUSIVE）
- 前回の一手: 「n=6 で同次数の D4 非同値点（例: 中心 4 点と r² 異なる内部点）の勝敗を調べれば判定可能。`cycle4-exact-n5.json` の first_move データで追加分析可」（`batch-08.md` B160 の「メモ」行）
- 今回の範囲: 書出しのみ。再照合した既存データ: `round3_chunk4_selfcheck.json` の n=2..5 の `W_ids`/`g0`、`batch08_results2.json` の `deg_extrema`、`PROTOCOL.md` の確定事実表。
- 証拠: 一石局面の勝敗が分裂する盤は **n=5 だけ**である。`selfcheck.json` の n5 は `W_ids = [2,6,8,10,12,14,16,18,22]` → xy = (2,0),(1,1),(3,1),(0,2),(2,2),(4,2),(1,3),(3,3),(2,4)、すなわち市松色 9 点（偶和・角 4 点を除く）で `PROTOCOL.md` の確定事実と一致。n=5 の 25 点は D4 軌道 6 個（四隅 4 / (1,0) 型 8 / (1,1) 型 4 / 中心 1 / (2,1) 型 4 / (2,0) 型 4）に分解され、W/LOSS は軌道ごとに一様である（4 隅 d=100 → LOSS、(1,1) 型 d=156 → WIN、中心 d=116 → WIN）。n=4 は `W_ids = []`（16/16 全部 LOSS）、n=6,9 は `PROTOCOL.md` の確定事実で 36/36・81/81 全部 WIN かつ g({p})=0 なので、**n≥6 では一石の P/N 差も g 差も原理的に存在しない**。n=6 の d=313 の 4 点 (2,2),(3,2),(2,3),(3,3) は同次数だが D4 同値。
- 残った障害: B160 は「d(p)=d(q) かつ D4 非同値で、一石局面の勝敗または g が異なる」盤の存在を主張する。n=5 では D4 軌道 6 個がすべて勝敗一様なので軌道横断の反例は出ない。残る可能性は (a) n=5 の**全 25 点の次数ヒストグラム**に異なる軌道が同次数で並ぶ（`deg_extrema` は min/max/中心/角のみを保存しており全点内訳が無い）、(b) n≥6 の g 差（n=6 は g=0 全点、n≥7 は一石のラベル自体が存在しない）、の 2 つだけ。どちらの data も無いため判定は据え置き。既存データに情報がなく、前回と状況が変わらない。

## B162 [構造] 中心の分母と四点の剰余類は連動する
- 判定: **PARTIAL**（前回: PARTIAL → 今回: PARTIAL）
- 前回の一手: 「『一部判別』は成り立つ（中心分母が小さいほど剰余パターンが限定）。完全分類ではない。den3, den5 の出現は mod 3, mod 5 情報の必要性を示唆」（`batch-08.md` B162 の「メモ」行）
- 今回の範囲: 書出しのみ（再計算なし）。再照合した既存データ: `batch08_results2.json` の `parity.3` / `parity.4` / `parity.5` / `parity.6` / `parity.7`、すなわち非退化共円 4 点組の `parity_xy`（35 パターン）/ `parity_sum`（5 パターン）/ `center_denom` の分類。n_conc は 3: 14、4: 184、5: 762、6: 2257、7: 5704。
- 証拠: `center_denom` の度数 = n=3: half 12 / integer 2、n=4: half 168 / integer 12 / den6 4、n=5: half 548 / integer 166 / den6 20 / den4 20 / den8 4 / den10 4、n=6: half 1565 / integer 488 / den6 68 / den4 68 / den10 36 / den8 16 / den5 8 / den3 4 / den14 4、n=7: half 3752 / integer 1312 / den6 196 / den4 184 / den10 116 / den8 48 / den5 24 / den3 36 / den12 4 / den14 32。n=7 の比率は half 65.8% / integer 23.0% / それ以外 11.2%。**den3 は n=6 の 4 件・n=7 の 36 件、den5 は n=6 の 8 件・n=7 の 24 件だけ**で、n≤5 には 1 件も無い。`parity_xy` 側は n=6,7 で 35 パターンすべて、`parity_sum` は 5 パターンすべてが実現している（前回 B161 を REFUTED にした根拠と同一の数値）。
- 残った障害: PARTIAL の弱版（中心分母が小さいほど剰余パターンが限定される）は n=3..7 の marginal 分布と整合するが、元の命題「小さい法の座標情報だけで**判別**できる」は未確認。理由は三点。(a) 既存 JSON は分母の度数分布と剰余パターンの度数分布を**別々に marginal として保存しているだけで、両者の条件付き度数（交差表）が一度も計算されていない**。(b) mod 3 / mod 5 の座標情報が `parity_xy`（mod 2 のみ）に存在せず、B162 の述べる「小さい法」側が mod 2 に制限されている。(c) 判別に使うと目される den3=4 件 / den5=8..24 件は全 5704 件中の 1% 未満で、交差表として有意差を検出する検出力が出ない。前回メモの「den3, den5 の出現は mod 3, mod 5 情報の必要性を示唆」はこの数値で裏づけられたが、それは**必要性の主張であって十分性の証拠ではない**。判定ラベルは据え置き。

## B165 [構造] mod p の行列式非零条件で線形サイズの安全集合を構成できる
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「K_n が 2n−1 に近いこと（n≤9）と整合する可能性。mod p 構成が K_n の下界の別証明になりうる」（`batch-08.md` B165 の「メモ」行）
- 今回の範囲: 書出しのみ（再計算なし）。再照合した既存データ: `batch08_results3.json` の `b179`（K_n と n_max_sets）、`PROTOCOL.md` の確定事実表、`round3_chunk2_geom.py` の docstring、`round3_chunk2_extract.py` の IDS。
- 証拠: 確定済みの K_n は n=2: 3、n=3: 5、n=4: 7、n=5: 9（`batch08_results3.json` の `b179`、同時に `n_max_sets` = 56 / 64 / 100）、`PROTOCOL.md` が n=6: 11、n=7: 14、n=8: 15（16 は非発見）、n=9: ≥17。`round3_chunk2_geom.py` の docstring は「禁止 4 点組 = 4 共線 または 4 共円。`C(V,4)` 全探索を格子直線と三重点外接円の列挙に置き換え、n≤7 で F_n を厳密再現、n=8,9,10,11 で約 50 倍高速。純整数演算、点 id = y*n+x」と述べる。`round3_chunk2_extract.py` の IDS は B165 / B166 / B167 を**列挙しているが、これは仮説バンクから原文を抽出するツール**であって行列式 mod p 値の計算コードではない。
- 残った障害: B165 は構成的存在命題「p に応じた座標集合の**すべての**四点行列式が mod p で非零になる族を、辺長 p 程度の整数盤に実現できる」。これには (i) 素数ごとの座標族の構成と (ii) mod p で非零なら整数でも det≠0 であることの 2 段が要る。既存データはいずれも持たない: `batch08_results2.json` のキーは `D_n_ext` / `rectangles_ext` / `parity` / `pair_spreads` / `deg_extrema` / `R_over_C`、`batch08_results3.json` のキーは `b169` / `b179` / `b171_173` / `b176`、`round3_chunk2_saturation.json` も B165–B167 を含まない。**四点行列式の mod p 値を列挙したファイルはリポジトリ内に存在しない**。既知の K_n（2n−1 近傍）は下界との整合であって構成の証拠ではない。既存データに情報がなく、前回と状況が変わらない。

## B166 [存在] 安全性を一つの素数で同時に証明できない大きな安全集合
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「n=5 最大 100 個で試せる。小素数証明の限界という主張は検証しやすい」（`batch-08.md` B166 の「メモ」行）。バッチ総括の「最も有望な次の一手」4 にも「n=5 最大 100 集合の四点行列式で B166/B167（素数証明の圧縮・限界）を素朴に試す」と書かれていた。
- 今回の範囲: 書出しのみ（再計算なし）。再照合した既存データ: `batch08_results3.json` の `b179`（`n_max_sets`）、`research/verification/data/` の一覧（`circle_b131_b138.json` と `maximal_n2..n6.bin` / `safe_n2..n6.bin` / `safe_n6_k8,9,10.bin` / `safe_n7_k12,13.bin` の 16 ファイル）、`batch08_results2.json`。
- 証拠: n=5 のサイズ 9 最大安全集合が 100 個、n=4 が 64 個、n=3 が 56 個、n=2 が 3 個であることは `b179` の `n_max_sets` で確認できる（`K_n` = 9 / 7 / 5 / 3）。ただし**それらの最大集合の四点行列式の整数値も、mod p 値も、どこにも保存されていない**。B166 が求めるのは「ある安全 S について、指定範囲の**どの**素数 p に対しても、**非零の整数行列式の中に** mod p で 0 になるものが存在する」という二重の否定条件であり、`data/` の .bin ファイルは**集合のビット列**であって行列式の因数分解情報を持たない。`batch08_results3.json` に含まれるのは `b169`（D4 軌道別の勝敗混在）、`b179`（I と K_n）、`b171_173`（Z 多項式）、`b176`（loss rate）のみで、行列式値の記録は皆無。
- 残った障害: 判定には「安全集合 S の C(|S|,4) 個の四点行列式の値 → 各素数 p での剰余 → ある素数 p では全非零だが別の素数では 0 が現れるか」という表が要るが、既存データから復元できない。n=5 の K=9 なら C(9,4)=126 個／集合で 100 集合=12,600 個の行列式、小盤で tractable だが**その計算が一度も走っていない**（`round3_chunk2_*` は B092–B167 担当として IDS を持つが該当実装は無い）。B167 と同時に両方を解けるデータだが、保存済みの計算が無いので着手できない。既存データに情報がなく、前回と状況が変わらない。

## B167 [構造] 少数の素数の組で安全性証明を圧縮できる
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「B166 と双対。各四点組が少なくとも一つの素数で非零となる素数集合の最小サイズを見積もる必要。証明書圧縮（F-X: 1.5–10 倍）の理論的説明になる可能性」（`batch-08.md` B167 の「メモ」行）
- 今回の範囲: 書出しのみ（再計算なし）。再照合した既存データ: `batch08_results3.json` の `b179`、`research/verification/data/` の一覧、`round3_chunk2_extract.py` / `round3_chunk2_geom.py` の docstring、`round3_chunk2_saturation.json` のキー。
- 証拠: 先行ワーカーは本仮説に**着手していない**ことが確定している。`round3_chunk2_extract.py` の IDS に B165 / B166 / B167 が列挙されているのは原文抽出のためだけで、`round3_chunk2_geom.py` は直線・円の列挙という高速幾何のみ、`round3_chunk2_saturation.json` のキー群は B165–B167 を含まない。`research/verification/` の round3 系 JSON 17 個のキーは `n2`–`n5`（selfcheck）、`B228`–`B231`（A1）、および B0413-B475・B451・B501・B591-B592・chunk2/5/6/8 系のみで **B165–B167 の出力は一つも無い**。
- 残った障害: B167 は「最大配置の四点行列式について、各四点が**少なくとも一つの素数で非零**になるような素数集合を、n に比べて**非常に小さく**選べる」構造命題で、(i) 各四点組が非零となる素数集合を被覆する set-cover、(ii) 「非常に小さく」の定量的基準、の 2 段構え。素数 1 つを固定すると mod p で 0 になる四点組の数が、その素数を使えない四点組数の下限を与える。(i) は B166 の双対だが、どちらも入力となる行列式 mod p 値が無ければ解けない。なお `PROTOCOL.md` 相当の記録にある証明書圧縮（F-X: 1.5–10 倍）は**出力側の圧縮率**の話で、入力側の mod p 非零統計とは別物なので本仮説の証拠には使えない。既存データに情報がなく、前回と状況が変わらない。

---

## B251 [存在] 禁止四点組一つを外すだけで空盤勝者が反転する
- 判定: **INCONCLUSIVE**（前回: INCONCLUSIVE → 今回: INCONCLUSIVE）
- 前回の一手: 「存在命題のため n≤4 の否定は反証にならない。n=5 の全 826 件は各 ~25s で重い。反転の必要条件（空盤 g が 0/1 境界にある盤）から n=6 以降を狙う方が効率的」（`batch-10.md` B251 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_relax.py` の B251 ブロック — `flips = [q for q in allq if bench.ev(frozenset({q}))[0] != bool(pn0[0])]` すなわち **n=4 の 194 四点組すべてに対する単一解除の完全列挙**。`Bench.ev` は `Solve(fam, V)` で P/N・最大安全サイズ・サイズ K の極大集合数まで返す。出力先は `round3_chunk4_relax.json`。
- 証拠: **数値は得られていない** — `research/verification/` に `round3_chunk4_relax.json` が存在しない（同ディレクトリの chunk4 系は `round3_chunk4_selfcheck.json` と `round3_chunk4_A1.json` のみ）。基底値だけは `round3_chunk4_selfcheck.json` から確定できる: n=4 は `g0 = 0`（Second）、`W_ids = []`、5,811 状態、`max_g = 5`、`n_P = 1825` / `n_N = 3986`、禁止 4 点組 194。`PROTOCOL.md` も「n=4 全初手負け 16/16」と一致する。
- 残った障害: 先行実装は n=4 の完全列挙なので、仮に走らせていても存在命題を反証できない（前回メモと同一）。前回個票が記録した n=4 の数値（194/194 単一解除で反転 0 件、共線解除で W だけが動く）は `batch10_extra.json` 由来で、既存 chunk4 データと一致するのは基底部分（g0=0・194 四点組）だけ。反転の観測には n=5 の 826 件か n=6 以降が必要だが、本的本质的な障害は**出力 JSON が未生成**である。既存データに情報がなく、前回と状況が変わらない。

## B252 [存在] 円一つの禁止解除が、同数のばらばらな解除より強く効く
- 判定: **INCONCLUSIVE**（前回: INCONCLUSIVE → 今回: INCONCLUSIVE）
- 前回の一手: 「『同一円にまとまった解除』の具体的実装（同じ真円上の 4 点組群をまとめて外す）を n=5 で 1 試行すれば方向は見える。現状では優劣の証拠ゼロ」（`batch-10.md` B252 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_relax.py` の B252 ブロック。`circle_signature(mask, pts)` で**整数既約の conic キー**を作る（真円は `('circle', a, b, c, d)` の原始形、共線は `('line', A, B, C)` の原始形、`is_collinear4` で判定、`_igcd` で原始化）。これを `Q_4` の 194 四点組に当てて conic ごとにグループ化し、**サイズ ≥2 のグループを全部まとめて解除**（クラスタ解除） versus **同数のばらばら解除**（`rng.choice(allq, len(G), replace=False)` でシード 20260927 の 6 回サンプル、群と交差するものは棄却）と比較する。出力は `round3_chunk4_relax.json` の `B252`（`n_groups_tested` / `only_cluster_flips` / `only_scattered_flips` / `both_flip` / `per_group`）。
- 証拠: **数値は得られていない**（`round3_chunk4_relax.json` 不在）。过去の保存値も無い。ただし `circle_signature` の primitive conic キーは本比較に適切な同値判定を与える設計である。基底は `selfcheck.json` の n=4 が Second / 194 四点組。
- 残った障害: 本仮説は**比較命題**で、判定には「クラスタ解除が勝者を変え、同じ数の散在解除は変えない」事例が 1 つでも出れば SUPPORTED、出れば REFUTED（散在側だけが有利な事例があれば）。先行実装はその両者の計数（`only_cluster_flips` / `only_scattered_flips` / `both_flip`）を n=4 で全 conic グループに対して出す設計だが、出力が残っていないため判定不能。散在側の 6 回サンプルが統計的に弱いという点は即使走っても残る障害である。既存データに情報がなく、前回と状況が変わらない。

## B253 [存在] 各禁止を単独解除しても不変だが同時解除で反転する
- 判定: **INCONCLUSIVE**（前回: INCONCLUSIVE → 今回: INCONCLUSIVE）
- 前回の一手: 「最小の E がサイズ 3 以上ならペア探索では永久に見えない。n=4 で 3 重（共有 3 点のクラスタ中心）を優先探索するのが次の一手」（`batch-10.md` B253 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_relax.py` の B253 ブロック。`share` 辞書で「4 点組が 2 点を共有する」ペア（各 4 点組の 6 通りの部分 2 点）を索引し、**共有 ≥2 点のペアを全列挙**して `bench.ev(frozenset({p, q}))` の勝者を比較する。`triple_search` は `"skipped (no pair flips => B253 needs |E|>=3; C(194,3) ~ 1.2M solves not affordable here)"` と、**ソース中に理由付きで中断が記録されている**。
- 証拠: **数値は得られていない**（`round3_chunk4_relax.json` 不在）。ただしスクリプト自身が「ペア flips が 0 件なら B253 は |E|≥3 を要する」と結論をコードに埋め込んでおり、**ペア探索では原理的に決着しないという事実が実装として確定している**。基底は n=4 が Second / 5,811 状態 / 194 四点組。前回個票の「960 ペアすべて Second 維持、反転 0 件」も同方向。
- 残った障害: 障害は「1.2M 回の solve」を現行引擎で走らせないこと。`round3_chunk4_relax.py` の docstring は n=4 の 1 解を約 0.6s と記しており、1.2M 件は設計上 unaffordable である。B253 を n=4 で解くには、(a) 「単一解除が全て無害」という条件下で**ペアで反転しうる conic ペアのみに候補を絞る**（共有 3 点の conic クラスタが有限個）、(b) 共有 3 点の triple を「解除可能な conic クラスタ」単位でまとめ直す、のどちらかの絞り込みが必須。保存済みデータにはこの絞り込みの材料も出力も無い。既存データに情報がなく、前回と状況が変わらない。

## B254 [構造] 少数の禁止型が 7×7 の最大配置の剛性を担う
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「既存 maxsafe_n7 データから、16 極大配置を分離する最小四点組カバーを探すのが現実的。全列挙し直さない」（`batch-10.md` B254 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_relax.py` の docstring は B254 を含ま**ない**（docstring の対象は B251 / B252 / B253 / B255 / B256 / B258 の 6 件のみ）。B254 用のコード・出力 JSON のどちらも見えない。再照合した既存データ: `PROTOCOL.md` の確定事実（K_7=14、極大 16、2 軌道 A/B、1-swap 剛性 ρ=2）、`research/verification/data/` の `safe_n7_k12.bin` / `safe_n7_k13.bin`（**K=14 の極大配置ファイルは `data/` に無い**）。
- 証拠: 既知の確定値は K_7=14・極大 16 個・2 軌道（A=中心あり / B=中心なし）・交換辺 0（ρ=2）だが、これは `PROTOCOL.md` の再掲であり**今回新たな証拠は無い**。前回メモが参照した「maxsafe_n7_K14.bin」は `research/verification/data/` に存在せず、`data/` の n=7 系は `safe_n7_k12.bin` と `safe_n7_k13.bin` の 2 個だけである。
- 残った障害: 本仮説は「最大安全サイズ 14 と最大配置全 16 個を、`Q_7` の小さい部分族だけで**同時に**再現できる」という構造命題で、入力に K=14 の 16 極大配置が要る。その配置データが本リポジトリ内で確認できない（確定表だけが典拠）。`PROTOCOL.md` の「7×7 後手勝ち・最大配置 2 相」の出典は FINAL_SELECTION 側の文書であって `data/` の生データを保証しない。既存データに情報がなく、前回と状況が変わらない。

## B255 [存在] 最大配置の分類を完全保存しても勝者は変わる
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「n=5 で最大安全サイズと極大配置族を保つ解除 E を探しつつ空盤 g を測る。n=5 の最大サイズ・極大数は既知データで照合できるので条件判定が可能」（`batch-10.md` B255 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_relax.py` の B255 ブロック。`rng2 = np.random.default_rng(777)` で **最大 700 回のランダム試行**、毎回 `k = rng2.integers(2, 12)` で解除サイズ 2–11 を選び、`bench.ev(frozenset(E))[:5]` で (勝者, 最大安全サイズ, 極大集合数, 極大集合リスト, 状態数) を取り、`f != pn0[0] and mx == base_max and mx_list == base_maximals` を全部満たす E を探す。`base_maximals` は標準 `Q_4` のサイズ K の**極大安全集合を bitmask の sorted tuple として完全一致で比較**する。`note` に "condition is strict: identical maximal-set family AND identical max size, with a flipped empty-board winner" と明記。
- 証拠: **数値は得られていない**（`round3_chunk4_relax.json` 不在）。基底として `selfcheck.json` から n=4 が Second / 5,811 状態、`round3_chunk4_core.py` の docstring から K_n と Z 多項式が厳密に取れることが分かる。`batch08_results3.json` の `b179` も K_n=7 / n_max_sets=64（n=4）、K_n=9 / 100（n=5）、K_n=5 / 56（n=3）の**照合可能な確定値**を提供するので、前回メモの「n=5 の既知データで照合できる」は妥当だが、n=5 側の比較コードは `round3_chunk4_relax.py` に無い（`N = 4` に固定）。
- 残った障害: 本仮説の成立条件は**三重かつ厳密**（最大サイズ一致 + 極大集合族の完全一致 + 勝者反転）であり、(a) `round3_chunk4_relax.py` は n=4 固定なので n=5 の照合は未実装、(b) 700 回のランダムサンプリングは E の空間に対して覆盖率が極めて低く、0 件は「無い」ではなく「見つからなかった」に過ぎない、(c) 出力 JSON が未生成、の三点。したがって NOT-CHECKED を維持。既存データに情報がなく、前回と状況が変わらない。

## B256 [存在] 勝者を保つ最小禁止族は D4 非対称である
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「n=4 で標準と同じ空盤勝者（Second）を与える部分族の最小サイズを求め、D4 不変族の最小サイズと比較する。n=4 は全探索が軽くすぐ出る」（`batch-10.md` B256 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_relax.py` の B256 ブロック（**B258 と同じコードブロック**）。内容は (1) **貪欲削除** — `allq` の順に 1 個ずつ試し、`s.pn()[0]` が偽のままならその quad を族から外す（192 回程度の Solve）、(2) 残った族の `Solve` で g0・最大 Grundy・最大安全サイズ・サイズ K の極大集合数を出し、(3) `d4_perms(N)` の 8 置換で `removed` と `keep` の D4 不変性を判定（`dinv`）、(4) **D4 軌道ごとにまとめて Solve** して P を保つ軌道（`good`）を列挙し `smallest_D4_invariant_P_size` を出す、(5) `is_smallest_family_D4_asymmetric = (len(removed) < min(D4 不変 P 族のサイズ)) and not dinv(removed)`。`d4_perms` / `apply_perm_mask` は `round3_chunk4_core.py` 由来。
- 証拠: **数値は得られていない**（`round3_chunk4_relax.json` 不在）。基底は n=4 が Second。貪欲削除が「標準と同じ Second を保つ最小族」に到達する保証は無く（本仮説が求めるのは最小性、貪欲は上限しか与えない）、実装も `rep["B256"]` に `is_smallest_family_D4_asymmetric` として 1 ブール値しか出力しない設計。
- 残った障害: 本仮説は最小性（極小禁止族）を含むため、貪欲 1 本的结果では充足しない。加えて (a) 出力 JSON が未生成、(b) 貪欲法と真の最小サイズの一致が保証されない、の二点が残る。なお仮説の後半の「元が後手勝ち等の自明な一致を除く」条件は、既存実装には明示的な除外フィルタとして書かれていない（空族と `Q_4` 自身は `dinv` で D4 不変になるはずだが、その扱いは `good` の判定に含まれる）。既存データに情報がなく、前回と状況が変わらない。

## B257 [統計] 戦略的に重要な禁止四点は点数の多い円に偏らない
- 判定: **PARTIAL**（前回: PARTIAL → 今回: PARTIAL）
- 前回の一手: 「感度の定義（局面ラベル変化数）で全四点組を n=5 で採点するには各解除が 25s で重い。代替: 石数 k=2,3 層のラベル変化数なら子計算だけで済むので軽い」（`batch-10.md` B257 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_relax.py` は docstring・`rep` のどちらにも **B257 を含まない**（対象は B251 / B252 / B253 / B255 / B256 / B258）。B257 用の感度ランキングを計算するコードも出力 JSON も見えない。再照合した既存データ: `batch08_results2.json` の `parity`（`center_denom` / `parity_xy`）、`deg_extrema`、および `PROTOCOL.md` の確定事実。
- 証拠: 既存の conic 規模情報は `round3_chunk4_relax.py` の `base` ブロックが計算を設計している（`n_circles` / `n_lines` / `circle_group_sizes`）が未実行。`batch08_results2.json` の `center_denom` は「円の種類」を半整数中心 65.8% / 整数中心 23.0% / その他 11.2%（n=7）で分布を与えるが、**それが戦略的重要度と結び付いているかどうかは測っていない**。前回個票の n=5 標本 4 件（共線解除のみ W を動かし、円解除は W 不変）も 4 件のみ。
- 残った障害: 本仮説は「重要度を局面ラベル変化数で定義」する。その重要度スコアが**どの保存済みファイルにも存在せず**、かつ `round3_chunk4_relax.py` は B257 を実装していないため、書出し段階では数値が出せない。`round3_chunk4_A1.json` の B229/B230 は conic 上の盤上点数による粗視化を扱うが、**4 点組レベルの重要度ランキングではない**ため流用できない。PARTIAL を維持し、判定材料は「n=5 標本 4 件で共線系のみ W を動かした」までの狭い範囲にとどまる。既存データに情報がなく、前回と状況が変わらない。

## B258 [構造] 最小勝敗保持禁止族に共通する必須四点型がある
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「B256 の最小族が複数得られたら D4 型（矩形の角・斜め共線・真円の型）の共通部分を取る」（`batch-10.md` B258 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_relax.py` の B258 ブロックは B256 と同じ貪欲族 `removed` から `kind(mask)` で型を数えるだけ。`kind` は `is_collinear4` で共線なら方向ベクトルを原始化し、 `xs`/`ys` の固有値が 2 つずつなら `"rect"`、それ以外 `"other"`。出力は `all_kinds`（`Q_4` 全体 194 の型分布）と `removed_kinds`（貪欲削除族の型分布）。`note` に "a 'necessary 4-point type' would be a kind present in every minimum winner-preserving family; the greedy family gives one candidate signature, not a proof of necessity" と明記。
- 証拠: **数値は得られていない**（`round3_chunk4_relax.json` 不在）。ソースの `note` 自身が「谪勂族 1 本からは『全ての最小族に共通する型』の証明にならない」と記明している。
- 残った障害: 本仮説の命題は「**異なる**最小部分族の**すべて**に現れる型」を要求する。(a) 最小族が複数得られない限り共通部分が未定義、(b) 1 本の貪欲族の型分布は共通部分の下界にもならない、(c) 出力 JSON が未生成。実装は型分類が粗く（`kind` の 3 分類で真円の中心・半径を区別しない）、B258 の「D4 四点型」という粒度には合致していない。NOT-CHECKED を維持。既存データに情報がなく、前回と状況が変わらない。

---

## B260 [統計] 重要な禁止族の共有点には必勝手が集中する
- 判定: **PARTIAL**（前回: PARTIAL → 今回: PARTIAL）
- 前回の一手: 「B257 の重要度ランキングと共有点の次数の積で W の選好を回帰すれば直接検証できる」（`batch-10.md` B260 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_relax.py` は docstring・`rep` のどちらにも **B260 を含まない**（対象は B251 / B252 / B253 / B255 / B256 / B258）。`scripts/round3_chunk4_u.py` の docstring も B260 を名指ししない（B261–B270 が対象）。再照合した既存データ: `round3_chunk4_selfcheck.json` の `W_ids`（n=2..5）、`PROTOCOL.md` の確定事実表、`round3_chunk4_A1.json` の B228–B231。
- 証拠: `selfcheck.json` から一石が P になる点（＝W）は **n=2: 4/4、n=3: 9/9、n=5: 9/25**、n=4 は 0/16、n≥6 は `PROTOCOL.md` により全点（36/36、81/81）。n=5 の W 9 点は `W_ids = [2,6,8,10,12,14,16,18,22]` → (2,0),(1,1),(3,1),(0,2),(2,2),(4,2),(1,3),(3,3),(2,4)、すなわち `x+y` が偶数の 13 点から**四隅 4 点を除いた**集合。`batch08_results2.json` の `deg_extrema` は n=5 で中心 (2,2) の d=116、四隅の 100、(1,1) 型の 156 を与える。W の 9 点は D4 軌道 3 個（(1,1) 型 4 / 中心 1 / (2,0) 型 4）にちょうど分割され、**除外された 4 点は四隅という単一の D4 軌道**である。n=5 では円のみ版・直線のみの版の W は中心 1 点のみという前回記録もある（`batch-10.md` B260 の証拠行）。
- 残った障害: PARTIAL の範囲は「W が D4 軌道 3 個の上と一致し、高対称点（中心・(1,1) 型・辺中点型）に集中する」ことまでで、**「重要な禁止族の共有点」という述語と結び付いているかは未確認**。理由は (a) 重要度（解除感度）スコアが B257 と同様にどの保存済みファイルにも無い、(b) 「重要円・直線の交点」という母集団の定義が先行実装のどこにも書かれていない、(c) n=5 の W 9 点が円のみ版/直線のみの版で中心 1 点に縮む事実は「交点集中」説と整合するが、共線/共円束の重要度は一度も計算されていない。判定ラベルは据え置き。既存データに情報がなく、前回と状況が変わらない。

## B261 [存在] 一手ずつは弱いが二手そろうと大量に塞ぐ
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「n=5 で u(p),u(q)≤1 なのに u 併用で新規禁止 ≥4 という局面の列挙。`batch10_core.pair_synergy` ですぐ回る。無限族の主張の前段階の n=5 見本が必要」（`batch-10.md` B261 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_u.py` の B261 ブロック。n=4（5,811 状態）と n=5（151,394 状態）の**全局面**を走査し、`|L|≥2` の局面ごとに合法手 2 手の全組を評価。新規禁止集合は `f_p = (baseL & ~Lp) & ~(1<<p)` で定義し、併用は `joint = (baseL & ~(Lp & Lq)) & ~(1<<p) & ~(1<<q)`。判定条件は `f_p.bit_count() <= 1 and f_q.bit_count() <= 1 and joint.bit_count() >= 4`。**内部 break 条件**が `len(b261) > 30 and len(b262) > 30 and len(b270) > 10` で、n=5 でも各 31 件集まった時点で打ち切られる設計。出力は `round3_chunk4_u.json` の `B261`（`n_witnesses` / `example` / `max_joint_seen`）。
- 証拠: **数値は得られていない** — `research/verification/round3_chunk4_u.json` が存在しない。したがって `n_witnesses` と `max_joint_seen` は不明。基底として `selfcheck.json` から n=4 が Second / 5,811 状態 / `max_g = 5`、n=5 が First / 151,394 状態 / `max_g = 6`（`PROTOCOL.md` の最大 nimber n=4,5,6 = 5,6,8 と n=4,5 の一致）、n=5 の `W_ids` 9 点が確定。
- 残った障害: 本仮説の本体は「**n とともに無限に増える**局面族」で、n=4/5 の有限走査は、証人が出ても前段階の見本にしかならない（`ROUND3-PROTOCOL.md` の禁止事項「小盤の不発見を、無界の存在命題の反証として書かない」の鏡像）。加えて (a) 出力 JSON が未生成、(b) `max_joint_seen` は n=5 で有限（盤内 25 点上限）なので「定数以下」という条件 `f_p<=1, f_q<=1` 自体は満たしつつも「無限増加」の部分は別問題。NOT-CHECKED を維持。既存データに情報がなく、前回と状況が変わらない。

## B262 [存在] 単独では強い二手が互いの効果をほぼ消費する
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「u_S(p)≥3 かつ u_S(q)≥3 かつ u_{S+p}(q)=0 の局面探索。n=5 全局面のスキャンで十分見つかるはず」（`batch-10.md` B262 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_u.py` の B262 ブロック（n=4, n=5 の全局面、`|L|≥2` の各局面で合法手 2 手の全組）。判定条件は `f_p.bit_count() >= 3 and f_q.bit_count() >= 3` かつ `gain_q_after_p = ((Lp & ~both) & ~(1<<q)).bit_count() == 0`。出力は `B262`（`n_witnesses` / `example`（occ の bin, p, q, u_p, u_q, gain））。B261 と同一ループ・同一 break 条件で走る。
- 証拠: **数値は得られていない**（`round3_chunk4_u.json` 不在）。基底は `selfcheck.json` の n=4 / n=5 値のみ。
- 残った障害: 本仮説も存在命題「**局面族**がある」で、n=4/5 の有限走査は前段階の見本にしかならない。加えて (a) 出力 JSON が未生成、(b) B261 と同じ break 条件（`len(b262) > 30`）で早期打ち切りされるため、走らせても n=5 の全走査は保証されない、(c) 前回メモが言った「n=5 全局面のスキャンで十分見つかるはず」という見込みは**未検証のまま**。NOT-CHECKED を維持。既存データに情報がなく、前回と状況が変わらない。

## B263 [統計] 必勝手は次手の gain 分布の下側を持ち上げる
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「必勝手 p の子における全合法手の u の最小値・分位点が、非必勝手より大きいかの検定。n=5 の N 局面サンプルで記述統計から入る」（`batch-10.md` B263 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_u.py` の B263 ブロック。n=4 / n=5 の全 N 局面の各必勝手 v について、その子 `occ | (1<<v)` の全合法手の u を，集計して `(min(u2), median(u2), u[v], mean(u2))` の 4 価として `b263` に蓄積。出力は `B263_winmove_u_vs_child_stats` の 3 比率: `frac_child_min_le_win_u`（子の min u が自分の u[v] 以下である必勝手の割合）、`frac_child_mean_le_win_u`、`frac_child_median_le_win_u`。**比較のベースラインは非必勝手ではなく「必勝手自身の u」**である点に注意。
- 証拠: **数値は得られていない**（`round3_chunk4_u.json` 不在）。`frac_*` の 3 値が本仮説の判定材料だが、3 つとも欠落している。
- 残った障害: (a) 出力 JSON が未生成で比率が読めない、(b) 実装は「必勝手についてのみ」4 価を集計しており、仮説の核心である「**非必勝手との対比**」の検定統計（平均・分位点の群間差、標本サイズ）が出力スキーマに含まれていない、(c) したがって走らせても「下側を持ち上げる」ことを検定できる形にはなっていない。NOT-CHECKED を維持。既存データに情報がなく、前回と状況が変わらない。

## B264 [存在] 全必勝手が新しい禁止点を一つも作らない
- 判定: **NOT-CHECKED**（前回: NOT-CHECKED → 今回: NOT-CHECKED）
- 前回の一手: 「u_S(p)=0 な必勝手のみからなる局面 + u>0 の合法手も持つ、の同時条件。n=4 全 N 局面に対するフィルタが軽いので最初に着手すべき」（`batch-10.md` B264 の「メモ」行）
- 今回の範囲: 書出しのみ（再実行なし）。読み取った先行実装: `scripts/round3_chunk4_u.py` の B264 ブロック。n=4 / n=5 の全 N 局面（`pn[i]` 真かつ `L` 非空かつ必勝手あり）で `u[v] = ((s.legal_mask(occ) & ~after) & ~(1 << v)).bit_count()` を全合法手について求め、`max(wu) == 0 and max(allu) > 0` を満たす局面を `b264` に蓄積。出力は `B264`（`n_witnesses` / `example`（occ の bin 3 個））。対照として `B264b_winning_move_with_u_gt0`（`min(wu) > 0`）も同じループで集めている。
- 証拠: **数値は得られていない**（`round3_chunk4_u.json` 不在）。基底は `selfcheck.json` の n=4 = Second / 5,811 状態 / `n_P = 1825`（`pn[i]` 真が N 局面なら n=4 では n_N = 3986）、n=5 = First / 151,394 状態 / `n_P = 40325`。
- 残った障害: (a) 出力 JSON が未生成で証人の有無が不明、(b) 内部 break 条件 `len(b264) > 40 and len(b265) > 40 and len(b267) > 20` により、n=5 でも証人が 41 個集まったら早期終了し、全数走査にはならない、(c) 本仮説の u の定義は「その手で新たに塞がる点の数」で、`round3_chunk4_core.py` の docstring が掲げる「新規禁止集合マップ K(p)」と整合するが、K(p) の分布自体は未保存。NOT-CHECKED を維持。既存データに情報がなく、前回と状況が変わらない。

---

## バッチ総括（20 件）

| 判定 | 件数 | ID |
|---|---|---|
| **SUPPORTED** | 0 | — |
| **REFUTED** | 0 | — |
| **PARTIAL** | 3 | B162, B257, B260 |
| **INCONCLUSIVE** | 4 | B160, B251, B252, B253 |
| **NOT-CHECKED** | 13 | B158, B159, B165, B166, B167, B254, B255, B256, B258, B261, B262, B263, B264 |

### 今回決着（SUPPORTED / REFUTED に動いたもの）
**なし。** 20 件すべて前回と同一のラベル。既存データに SUPPORTED / REFUTED を書き出すだけの数値が存在しなかったため、`ROUND3-WRITEOUT.md` の「推測で SUPPORTED / REFUTED を書いてはいけない」に従い、書出し側の前進は「先行スクリプトが何を計算しようとしているかの復元」と「その出力 JSON が存在しないことの確認」に留めた。

### 残る未解決とその一言理由
- **B251–B253, B255, B256, B258**（relax 系）: `round3_chunk4_relax.py` に完全な実装があるが **出力 `round3_chunk4_relax.json` が未生成**。B253 はさらにソース自身が triple 探索を「1.2M solves not affordable」で skip しており、n=4 でのペア探索が原理的に非決着であることが実装として確定している。
- **B261–B264**（u 系）: `round3_chunk4_u.py` に完全な実装があるが **出力 `round3_chunk4_u.json` が未生成**。加えて内部 break 条件（B261/B262 は 31 件、B264 は 41 件で打ち切り）で n=5 の全走査が保証されない。B263 は出力スキーマ自体に「非必勝手との対比」の検定統計が入っていない。
- **B254**: 入力となる K=14 の 16 極大配置が `research/verification/data/` に存在しない（`safe_n7_k12.bin` / `safe_n7_k13.bin` のみ）。先行スクリプトの docstring にも B254 は含まれない。
- **B257 / B260**: 重要度（解除感度）スコアを計算するコードも保存データも存在しない。B260 は n=5 の W 9 点が D4 軌道 3 個の上にあることまでしか確認できていない。
- **B165 / B166 / B167**: 四点行列式の mod p 値を列挙したファイルがリポジトリ内に一切ない。`round3_chunk2_*` は IDS に IDs を載せるのみで該当実装なし。
- **B158**: 必要な「一石親 S 起点の 2 手比較表」が無い。`scripts/analysis/fact_10x10_two_stone_mobility.py` はスクリプト本体のみで出力 JSON 不在、かつ F-AV により二石層の mobility は定数 98 で逆転の素地が無いと判明している。
- **B159**: 静的な d(p) のスナップショットしか無く、盤寸法差分 Δd(p) の記録が無い。`D_n` は別指標なので代用不可。
- **B160**: n=5 の D4 軌道 6 個はすべて勝敗一様、n=4 は全初手 LOSS、n≥6 は全初手 WIN かつ g=0 で、一石の P/N・g 差が存在し得ない盤が大多数である。残るは n=5 の全 25 点の次数内訳のみ。
- **B162**: den3 / den5 が n≥6 で初めて出現することを数値で確認（mod 3/5 情報の必要性を裏づけ）が、分母×剰余の交差表が未計算のため判別可能性そのものは未確認。

### 最も有望な次の一手（1 つだけ）
**`python research/verification/scripts/round3_chunk4_relax.py` と `round3_chunk4_u.py` を走らせて 2 つの JSON を生成し直すこと**（`round3_chunk4_core.py` の docstring 自身が「前回バッチは 1 solve あたり 25s しか払えず B251–B253 が INCONCLUSIVE のまま残った」ことを理由に今回の高速 numpy エンジンを作ったと記しており、この 2 本が走れば B251–B253 / B255 / B256 / B258 / B261–B264 の計 11 件が同時に数値を得る）。本ロールは「書出し専用・既存の重い計算をしない」指示に従い実行しなかった。

---

## 実施した作業の範囲（明記）
- 実行した Python は**テキストcleanupのみ**（本ファイル内の文字化け文字列の置換 2 回）。既存の検証スクリプト・JSON は一切再実行・再計算していない。
- 既存ファイルの上書きはしていない（`research/verification/round3-batch-grp4.md` のみ新規作成・追記）。
- 担当外 ID には一切触れていない。

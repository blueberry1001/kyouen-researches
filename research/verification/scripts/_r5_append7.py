from pathlib import Path
p = Path(r'D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5-batch-b020-b090.md')
summary = r'''
---

## バッチ総括（B020–B090 未解決追加・35 件）

| ラベル | 件数 | ID |
|---|---:|---|
| **SUPPORTED** | **4** | B040, B050, B072, B077 |
| **REFUTED** | **1** | B081 |
| PARTIAL | 14 | B020, B021, B024, B034, B039, B043, B045, B054, B059, B066, B079, B082, B088, B090 |
| INCONCLUSIVE | 14 | B029, B032, B037, B047, B058, B060, B063, B069, B070, B074, B083, B084, B085, B089 |
| NOT-CHECKED | 2 | B022, B023 |

**決着（SUPPORTED/REFUTED）: 5 件 / 前進（PARTIAL へ昇格 or 内容強化）: 14 件**

### 今回決着
1. **B040 SUPPORTED** — n=4,5 の WFT を完全再計算し `{6}`, `{7}`（n=6 は `{9}`）。round4 の「n=5 で WFT=∅」は g_empty の誤分類に起因する誤りで訂正。
2. **B050 SUPPORTED** — 5×5 の負け初手 16 点の g が全て 3。D4 軌道をまたいで nimber 一致。
3. **B072 SUPPORTED** — F_p の線形性を安全集合の構造（直線・円に 3 点まで）から短証明。`b_S(p) ≤ floor(k(k−1)/6)` が全称で成立。計算は n=4,5 全数・k≤6 で違反 0。
4. **B077 SUPPORTED** — 4×4 で 104 件・5×5 で 940 件の証人（batch-04 の具体例 S={0,1,2,4,10,15}）。
5. **B081 REFUTED** — 既知の確定事実 K_9=18 が K_9=17 の反例。

### 今回前進
- **B043 PARTIAL** — 180° 回転対合が「対称局面から常に合法応手」である短証明（回転不変性）。
- **B088 PARTIAL** — 放物線 y=x² (x≥0) が安全である短証明（4 点共円は根の和=0 が必要で非負 x では不可能）。点数 O(√n) のため多曲線が必須と確定。
- **B090 PARTIAL** — 8×8 の 408 集合/309 軌道を第 3 点として交絡を一部解消（n=6 と n=8 は規模近いが型数が大きく異なる）。
- **B034 PARTIAL** — n=6 の T*(∅)={6..11} に K=11 が含まれる事を確定。n≤6 で証人なし。
- **B039 PARTIAL** — n=4,5 の**全数**反転率。主張 A（終局直前より中盤）成立、主張 B（中間層が最大）は n=5 で不成立。
- **B021/B024/B045/B054/B059/B066/B079/B082** — 内容強化。

### 新規計算・データ
- `scripts/round5_b020_b090.py` → `round5_b020_b090.json`（n=4,5 完全 Grundy, T*, WFT, 全数 flip rate, b_S(p) 境界）
- `scripts/round5_b020_resid.py` → `round5_b020_b090_resid.json`（n=3,4,5 の R(S) 多成分率・高階制約率・P(S) 型数）

### 訂正（既存記録の誤り）
1. **round4_tstar_n45.json** の n=5 `WFT_empty=[]` は誤り。正しい値は **{7}**（g_empty=1 が既知の先手勝ちと一致）。
2. **round4_tstar_n67.json** の `g_empty=0, winner=second` は n=6 では誤り（既知: 先手勝ち 36/36）。per_firstmove の WFT={9} は正しい。
3. **round4** の「放物線は四次式なので 4 点共円になり得ない」は誤り（四次は 4 根持ちうる）。正しくは **x≥0 で根の和=0 が必要**なため 4 点共円が起きない。
4. **n=4 の T*(∅)** は round4 の {5,6,7} ではなく **{6}**（P 空盤では勝敗維持軌跡の終局は偶数石に固定される）。

### 最も有望な次の一手
1. **B082/B084/B085 の 10×10 証人探索**（K_10≥19 で 3 件同時に前進）。100 点で uint64 収容。
2. **B022 の M_7(1)** — n=7 一石層の g が σ_7 の下限を決める（禁止枠なら専任へ）。
3. **B090 の n=8 1-swap 辺数全数** — 型数と剛性の 3 点相関を閉じる。
'''
p.write_text(p.read_text(encoding='utf-8') + summary, encoding='utf-8')
print('final len', len(p.read_text(encoding='utf-8')))

# 9×9 Pair Mobility Confirmatory Audit & Manifest

## 1. 実行環境
- OS: Windows 11 Home (win32 10.0.26200, x64)
- CPU: AMD Ryzen 7 5800HS with Radeon Graphics
- Compiler: GNU g++.exe 15.2.0 (MSYS2 UCRT64)
- Build flags: `-O3 -DNDEBUG -std=gnu++20` (CMake Release build)
- Target: `kyouen-solver-9-compare`
- Solver source commit: `4152c1a0a74f17ecd89a3085cfdf9afc19fabaa8`
- Solver source file: `cpp/solvers/kyouen_solver_9_compare.cpp` (SHA-256: `32a23e06442cc905170ff1a8680a18b789a44705b51184d47375be773feab508`)
- Memo power: `28` (FlatMemo81)
- Batch size: 64 roots per shard, total 16 batches, deterministic checkpoint/resume runner (`scripts/run-9x9-confirmatory-batches.py`)

## 2. 実験入力および結果の完全性
- Seed: `kyouen-9x9-pair-vs-true-mobility-confirmatory-v1-2026-09-05`
- Population Reps: 11,378
- Pilot 64 Excluded: 64
- Eligible Population: 11,314
- Sample Size: 1,024
- 開始行: 1 (ヘッダ除く先頭行)
- 終了行: 1024
- 欠損数 (missing): 0
- 重複数 (duplicate): 0
- 出力整合性: 1,024行すべてが入力行と1対1で完全一致

### SHA-256 Hashes
- `input.csv`: `07e60d22eac16834726a5972967e2ae426f2a75f89401f9d4508d1ce033fc840`
- `input.meta.csv`: `9b221b61817a5d6792f3faae07e8f3d492c21e23007bdeda375924df6946d053`
- `results_raw.csv`: `93020f2516b779b2a44b3e4525d6ed7d7ab10cab539c5b11c253231680d16917`
- `results_with_meta.csv`: `bc00572605a0844e3c368dfbd84b55352f7f3715076accdb745b196083905986`

## 3. 独立再現性・順序不変性監査 (Spot-check Audit)
- 1,024件から疑似乱数 (seed 42) で無作為に10件の親局面を抽出。
- fresh な `kyouen-solver-9-compare` インスタンスを用いて順方向および逆方向の2通りの順序で独立 solve を実施。
- 結果: 全10件について、初回収集時の exact outcome (`pair_child_outcome`, `other_child_outcome`) と完全に同一の `WIN`/`LOSS` が得られ、探索順序や memo 共有に依存しない完全な不変性が確認された。

## 4. 解析結果要約

### 主検定 (Primary Endpoint)
- 総サンプル数 $N = 1,024$
- Both LOSS: 317 (30.96%)
- Both WIN: 265 (25.88%)
- Pair-only (pair=LOSS, true=WIN): 225 (21.97%)
- True-only (pair=WIN, true=LOSS): 217 (21.19%)
- Discordant 数: 442 (43.16%)
- Discordant 中 True-only 比率: $217 / 442 = 0.490950$ (49.10%)
- 効果量: $\text{true-only} - \text{pair-only} = 217 - 225 = -8$
- 帰無仮説: $H_0: P(\text{true-only} \mid \text{discordant}) = 0.5$
- 対立仮説 (事前登録): $H_1: P(\text{true-only} \mid \text{discordant}) > 0.5$ (True 優勢)
- **片側 exact binomial p値**: $p = 0.665682$
- **二側 exact binomial p値**: $p = 0.739210$
- **結論**: 有意水準 $\alpha = 0.05$ において帰無仮説は棄却されず、事前仮説「true one-ply mobility は raw pair-sum より優勢である」は**非支持 (not supported)** となった。

### 探索的副解析 (Exploratory Cause Class Breakdown)
| Cause Class | Eligible | Sampled | Discordant | Pair-only | True-only | True% | 片側 p値 | 二側 p値 | Both LOSS | Both WIN |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **E-only** | 6,334 | 573 | 249 | 132 | 117 | 46.99% | 0.8447 | 0.3750 | 172 | 152 |
| **O-only** | 690 | 63 | 34 | 20 | 14 | 41.18% | 0.8853 | 0.3915 | 15 | 14 |
| **both** | 321 | 29 | 16 | 8 | 8 | 50.00% | 0.5982 | 1.0000 | 5 | 8 |
| **synergy** | 3,969 | 359 | 143 | 65 | 78 | 54.55% | 0.1578 | 0.3156 | 125 | 91 |

※ 事前登録どおり、副解析は探索的位置づけであり主結論を変更するものではない。

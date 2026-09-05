# 共円ゲーム 1×1～9×9 完全分類

**Kyouen: a computer-assisted optimal-play classification for square boards of sizes 1 through 9**

本リポジトリは、完全指摘ルールの共円ゲームについて、`n × n` 格子点盤の最適プレイ時の勝者を **`1 ≤ n ≤ 9` の全サイズで分類**した計算機援用証明を収録します。

## 主結果

| 盤面 | 1×1 | 2×2 | 3×3 | 4×4 | 5×5 | 6×6 | 7×7 | 8×8 | 9×9 |
|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 最適プレイ時の勝者 | 先手 | 先手 | 先手 | 後手 | 先手 | 先手 | 後手 | 後手 | **先手** |

したがって、先手必勝となるのは

```text
n ∈ {1, 2, 3, 5, 6, 9}
```

後手必勝となるのは

```text
n ∈ {4, 7, 8}
```

です。

この列は、少なくとも小盤面では勝敗が次の単純則で決まらないことを示します。

- **盤面サイズの奇偶では決まらない**：6×6は先手必勝、7×7は後手必勝
- **盤面拡大に対して単調ではない**：6→7で先手から後手、8→9で後手から先手へ変わる
- **すぐに見える短周期でもない**：4～9は `後・先・先・後・後・先`
- **最大安全配置数の偶奇だけでは決まらない**：勝敗は、相手をどの飽和配置へ誘導できるかに依存する

より詳しい考察は [`docs/RESULTS_AND_IMPLICATIONS.md`](docs/RESULTS_AND_IMPLICATIONS.md) にあります。

## ルール

- 盤面は `n × n` 個の格子点
- 2人が交互に未使用の点へ石を置く
- 新しく置いた石を含む4石が、同一円周上または同一直線上になれば、その手を打った側が負け
- 共円・共線は必ず即座に発見される

この条件では、「安全な手だけを合法手とし、合法手がなくなった側が負ける」という有限の通常プレイゲームとして扱えます。

4点の共円・共線判定には浮動小数点数を使わず、次の整数行列式が0かどうかを用います。

```text
| x²+y²  x  y  1 |
```

## 証明の構成

各サイズについて、空盤面を根とする順位付きAND/OR証明書を収録しています。

- **winning局面**：証明書中のlosing局面へ進む合法手を1つ持つ
- **losing局面**：すべての合法手が、証明書中のwinning局面へ進む
- 各辺で順位が必ず減るため、証明DAGに循環はない
- 根のラベルが、その盤面の先手必勝／後手必勝を与える

探索器とは別の `kyouen-certcheck` が、格子点から危険な4点組と全合法手を再生成し、証明書の局所条件を検査します。

| n | 危険な4点組 | 証明書局面数 | 結論 |
|---:|---:|---:|:---|
| 1 | 0 | 2 | 先手必勝 |
| 2 | 1 | 5 | 先手必勝 |
| 3 | 14 | 28 | 先手必勝 |
| 4 | 194 | 135 | 後手必勝 |
| 5 | 826 | 1,217 | 先手必勝 |
| 6 | 2,491 | 21,712 | 先手必勝 |
| 7 | 6,364 | 393,550 | 後手必勝 |
| 8 | 14,564 | 8,744,406 | 後手必勝 |
| 9 | 29,152 | 13,457,134 | 先手必勝 |

全証明書を展開・検査した記録は [`results/all-certificates-check.txt`](results/all-certificates-check.txt)、ハッシュとサイズは [`results/certificates.csv`](results/certificates.csv) にあります。

## 9×9について

9×9では、先手が中央 `(4,4)` に置くと、相手番がlosing局面になります。v3証明書は空盤面をwinningとし、中央を証人手として、その後の13,457,133局面の証明DAGへ接続しています。

現時点では、中央以外の初手が勝ちかどうかをすべて分類したとは主張していません。

fixed rule / two-stone subset probe の盲検追試後に行った反例解析・訂正・棄却済み仮説・次の実験は [`docs/9X9_TWO_STONE_PROBE_RESEARCH_NOTES.md`](docs/9X9_TWO_STONE_PROBE_RESEARCH_NOTES.md) にまとめています。

## リポジトリ構成

```text
.
├── Kyouen/                    Lean形式化
├── cpp/
│   ├── certificate/           1～9共通証明書の生成・変換・検査
│   ├── generator/             9×9旧形式の生成器
│   ├── checker/               旧9×9検査器（比較用）
│   └── solvers/               完全探索器と独立検証用実装
├── docs/                      証明形式・結果の含意・検証報告
├── results/                   結果表、ハッシュ、実行記録
├── release-assets/            圧縮証明書（GitHub Release向け）
├── scripts/                   Linux/macOS・Windows用検証手順
├── CMakeLists.txt
├── lakefile.lean
└── lean-toolchain
```

## 最短の検証方法

完全版ZIPを展開した場合、圧縮証明書は `release-assets/` にあります。

### Linux / macOS

必要なもの：C++20コンパイラ、CMake、zstd。

```bash
./scripts/check-all-certificates.sh
```

Leanの健全性層もビルドする場合：

```bash
./scripts/verify.sh
```

### Windows PowerShell

```powershell
./scripts/check-all-certificates.ps1
./scripts/verify.ps1
```

### 手動ビルド

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
./build/kyouen-certcheck certificates/raw/kyouen-5x5.cert
```

研究用探索器もビルドする場合：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_RESEARCH_SOLVERS=ON
cmake --build build --parallel
```

## 証明書の配布

証明書の圧縮版は合計約92 MiBです。GitHubリポジトリ本体を重くしないため、通常は `release-assets/*.zst` をGitHub Releaseへ添付してください。

```text
kyouen-1x1.cert.zst
...
kyouen-9x9.cert.zst
```

ハッシュは [`release-assets/SHA256SUMS.txt`](release-assets/SHA256SUMS.txt) にあります。

## Lean形式化の位置づけ

[`Kyouen/CertificateSoundness.lean`](Kyouen/CertificateSoundness.lean) は、順位付きAND/OR証明書の局所条件から通常プレイの勝敗が従う一般健全性定理を形式化します。

[`Kyouen/Rules.lean`](Kyouen/Rules.lean) は、任意の `n × n` 格子点盤について、整数行列式による禁止4点組と合法手を定義します。

ただし、巨大なバイナリ証明書の読み込みと全局所条件の実検査は、現時点では独立C++検査器が担当します。したがって信頼境界は、

```text
独立C++証明書検査
＋
Leanによる証明書方式の一般健全性定理
```

です。具体証明書をLeanの核だけで最後まで検査する実装は今後の課題です。

## English summary

This repository gives a computer-assisted complete classification of optimal-play outcomes for Kyouen on `n × n` lattice-point boards for `1 ≤ n ≤ 9`.

The first player wins for `n ∈ {1,2,3,5,6,9}`, while the second player wins for `n ∈ {4,7,8}`. Every result is accompanied by a ranked AND/OR certificate checked by a common independent verifier. A Lean development formalizes the general soundness argument for such certificates.

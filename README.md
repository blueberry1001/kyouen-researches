# 共円ゲーム 1×1～10×10 最適勝敗分類

**Kyouen: a computer-assisted optimal-play classification for square boards of sizes 1 through 10**

本リポジトリは、完全指摘ルールの共円ゲームについて、`n × n` 格子点盤の最適プレイ時の勝者を **`1 ≤ n ≤ 10` の全サイズで分類**した計算機援用研究を収録します。  
`1 ≤ n ≤ 9` は空盤面を根とする共通形式の順位付きAND/OR証明書まで整備済みです。10×10は、100通りの初手をD4対称性で15代表に縮約して厳密探索した完全初手分類により後手必勝を確定しており、検証形式の違いは後述します。

**11×11 は探索を層5まで進めていますが、勝者は未確定です**（第3節参照）。

## 主結果

| 盤面 | 1×1 | 2×2 | 3×3 | 4×4 | 5×5 | 6×6 | 7×7 | 8×8 | 9×9 | 10×10 |
|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 最適プレイ時の勝者 | 先手 | 先手 | 先手 | 後手 | 先手 | 先手 | 後手 | 後手 | **先手** | **後手** |

したがって、先手必勝となるのは

```text
n ∈ {1, 2, 3, 5, 6, 9}
```

後手必勝となるのは

```text
n ∈ {4, 7, 8, 10}
```

です。

この列は、少なくとも小盤面では勝敗が次の単純則で決まらないことを示します。

- **盤面サイズの奇偶では決まらない**：6×6は先手必勝、7×7は後手必勝
- **盤面拡大に対して単調ではない**：6→7で先手から後手、8→9で後手から先手へ変わる
- **すぐに見える短周期でもない**：4～10は `後・先・先・後・後・先・後`
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

## 1×1〜9×9の証明書検証

1×1〜9×9の各サイズについて、空盤面を根とする順位付きAND/OR証明書を収録しています。

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

D4軌道14クラス（中心を除く）を独立に逐次探索した結果、**すべての初手が勝ち**であることも確認しました（`night-research/first-moves-9x9.csv`）。したがって9×9の勝ち初手は81点すべてです。

fixed rule / two-stone subset probe の盲検追試後に行った反例解析・訂正・棄却済み仮説・次の実験は [`docs/9X9_TWO_STONE_PROBE_RESEARCH_NOTES.md`](docs/9X9_TWO_STONE_PROBE_RESEARCH_NOTES.md) にまとめています。

## 10×10について

10×10では、100通りの初手を回転・反転（D4）で **15代表**に縮約し、15代表すべてについて先手のその初手が `LOSS` であることを厳密探索で確認しました。したがって、**100通りすべての初手が先手負けで、空盤面は後手必勝**です。

完全表は [`rust/independent-verifier/evidence-sample/10x10-first-move-classification-complete.csv`](rust/independent-verifier/evidence-sample/10x10-first-move-classification-complete.csv) にあります。各代表について後手の勝ち応手を記録し、必要なケースではその後の第3手98通り（転置対称な場合は53代表で98通りを包含）を完全探索しています。

10×10用には128-bit状態を扱う `KYOENC4` 証明書形式と独立Rust検査器も実装済みで、4〜8石などの実局面について最大180万ノード級の証明DAGを生成・独立検査しています。ただし、**10×10の空盤面分類全体を1本のKYOENC4証明書として統合したものはまだありません**。したがって検証境界は次のとおりです。

- 1×1〜9×9：空盤面からの共通AND/OR証明書を独立検査
- 10×10：15初手代表の厳密探索による完全分類＋証拠CSV監査＋一部局面のKYOENC4独立検査
- 11×11：**勝敗未確定**。層0〜5の安全局面数は厳密確定済みだが、層5を終端扱いしたP/N分割は打ち切りゲームの値にすぎない。現在は全層列挙ではなく128-bit AND/OR証明探索へ移行中

詳細は [`docs/PROOF_STATUS.md`](docs/PROOF_STATUS.md)、[`docs/10X10_KYOENC4_EXPORT.md`](docs/10X10_KYOENC4_EXPORT.md)、[`rust/independent-verifier/README.md`](rust/independent-verifier/README.md) を参照してください。

## 11×11について（**勝敗は未確定**）

11×11（121点）は **128ビット**の状態表現が必要です。`uint64_t` 前提のコードは
`1ULL << v` を v ≥ 64 で使った瞬間に黙ってビットを落とすため使えません。

D4対称性（11×11の121点は21個の点軌道に分解、一般位置では軌道サイズ8）で
状態数を **1/8** に削減した上で、Grundy探索を**層5まで**行いました。

### 現時点で言えること（断定できる範囲）

- 11×11 の安全局面数は **層0〜5まで厳密に列挙済み**
- D4軌道数も層0〜5まで確定
- 禁止4点組数 **F₁₁ = 95,670**（n=6〜11の6値で独立に数え直し既知値と完全一致）
- 同じソルバが n=6, 7 で既知値と**完全一致**（g(∅)=1 / 0、P/N局面数とも一致）

層サイズは `[1, 121, 7260, 287980, 8399740, 187879156]`（最長層は
D4軌道 2,349万 = 3.0 GB）。

### なぜ 11×11 の勝者は出ていないか

**層6以降の生成がメモリ的に破綻した**ためです。層5の1.879億状態に対して
層6は成長率（22.37倍が直近値）から数十億〜50億状態に達し、
19 GB の箱には収まりません。

このため層5には未計算の合法手が **2,439,393,194 個** 残っており、
DPは層5を「終局」として g=0 を割り当てて逆算しています（打ち切りゲーム）。
**その P/N パターン（層0〜5の交互）は真の値ではありません。**
ソルバー自身も `"complete": false`, `"g_empty": null`, `"winner": "UNKNOWN"` を
出力しており、実装がコメントでも明記しています。

> The resulting g(empty) is therefore NOT the true Grundy value: it is the
> value of a truncated game.

**したがって 11×11 の勝者は未確定です。**（本節は初版で「先手必勝」と
記載しましたが撤回しました。訂正の記録は
[`research/verification/N11-RESULT.md`](research/verification/N11-RESULT.md) を参照。）

### この作業の成果

失敗ではなく、**11×11 における計算壁の位置を正確に突き止めた**ことです。
128ビット化とD4対称化（1/8削減）により層5までは到達できましたが、
層6の生成に必要なメモリが 19 GB を超えて破綻する、という境界が判明しました。

詳細は [`research/verification/N11-RESULT.md`](research/verification/N11-RESULT.md)、
[`research/verification/N11-WORKLOG.md`](research/verification/N11-WORKLOG.md) を参照してください。
再現: `wsl -d Ubuntu -- bash research/verification/scripts/n11_reproduce.sh --with-n11`

## 関連研究

先行研究を広く調査した結果、3×3〜6×6の完全探索、最大安全配置数 k(1)〜k(9)、一般の必勝判定の計算量研究などは既知であることを確認しました。一方、2026-09-23までに確認できた公開資料では、完全指摘・2人制の7×7〜9×9の厳密な最適勝敗分類と独立検査可能な証明書の先行公開例は確認できていません。10×10の勝敗も本リポジトリでは確定していますが、同日の先行研究調査は7×7〜9×9の優先権確認を主眼としていたため、**10×10については同じ強さの新規性主張を現時点では行いません**。調査範囲、既知結果との境界、留保事項は [docs/RELATED_WORK.md](docs/RELATED_WORK.md) に記録しています。

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
├── rust/independent-verifier/ 10×10証拠監査・KYOENC4独立検査
├── release-assets/            1～9圧縮証明書（GitHub Release向け）
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

This repository gives a computer-assisted complete classification of optimal-play outcomes for Kyouen on `n × n` lattice-point boards for `1 ≤ n ≤ 10`.

The first player wins for `n ∈ {1,2,3,5,6,9}`, while the second player wins for `n ∈ {4,7,8,10}`. Boards 1×1 through 9×9 have ranked AND/OR certificates checked by a common independent verifier. The 10×10 outcome is established by an exact classification of all 15 D4 first-move representatives (covering all 100 first moves); its evidence is structurally audited by an independent Rust implementation, and selected 10×10 roots have independently checked KYOENC4 proof DAGs. A single empty-board KYOENC4 certificate for the full 10×10 classification has not yet been produced. A Lean development formalizes the general soundness argument for ranked certificates.

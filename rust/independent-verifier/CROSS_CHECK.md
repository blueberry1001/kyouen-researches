# C++・Rust差分検査

高速探索器とRust参照実装が、盤面規則を同じように解釈しているかを局面単位で検査します。

## 構成

- `cpp/tools/kyouen_query.cpp`
  - C++20
  - 最大128点の盤面を扱う
  - 共円・共線判定には4×4行列式を使用
  - JSON出力と、Rustから読みやすい`key=value`出力に対応
  - `--serve`では盤面表を一度だけ構築し、標準入力から複数局面を処理
  - `--solve`を付けると小盤面のWIN・LOSSと勝ち手を完全探索
- `src/bin/kyouen-cross-check.rs`
  - 合法手だけを選ぶ決定的なランダムウォークで有効局面を生成
  - Rustの3×3行列式・盤面再構成方式とC++の結果を比較

## C++照会器のビルド

リポジトリのルートで実行します。

```bash
g++ -std=c++20 -O2 -Wall -Wextra -pedantic \
  cpp/tools/kyouen_query.cpp -o /tmp/kyouen-query
```

単一局面をJSONで照会する例です。

```bash
/tmp/kyouen-query --size 10 --ids 0,44,72
```

主な出力項目：

- `valid`: 既に禁止四つ組を含んでいないか
- `legal_ids`: 合法手
- `forbidden_ids`: 空点のうち禁止される点
- `canonical_ids`: 8つの回転・反転で最小の盤面
- `transforms`: 8つの回転・反転後の盤面
- `forbidden_quadruples`: 盤全体の禁止四つ組数
- `outcome`: `--solve`使用時の手番側の勝敗
- `winning_move`: `WIN`なら勝ち手の一例

## 差分検査の実行

Rustプロジェクトへ移動します。

```bash
cd rust/independent-verifier
```

### 小盤面：勝敗まで比較

```bash
cargo run --release --bin kyouen-cross-check -- \
  --cpp /tmp/kyouen-query \
  --size 4 \
  --samples 40 \
  --seed 20260801 \
  --max-stones 8 \
  --solve-max-size 4
```

比較内容：

- 局面の有効・無効
- 合法手集合
- 禁止点集合
- 8つの回転・反転
- 正規形
- 禁止四つ組数
- WIN・LOSS
- C++が返した勝ち手がRustでLOSSへ移ること
- Rustが返した勝ち手がC++でLOSSへ移ること

勝ち手が複数ある場合があるため、勝ち手の点番号そのものの一致は要求しません。互いの勝ち手が本当に相手のLOSS局面へ移るかを確認します。

### 10×10：幾何と合法手を比較

```bash
cargo run --release --bin kyouen-cross-check -- \
  --cpp /tmp/kyouen-query \
  --size 10 \
  --samples 100 \
  --seed 20260802 \
  --max-stones 12 \
  --solve-max-size 0
```

10×10では巨大な勝敗探索を繰り返さず、次を比較します。

- 有効局面100個
- 意図的に作った禁止四つ組を含む無効局面1個
- 合法手と禁止点
- 8対称と正規形
- 禁止四つ組数54,441

サンプルは乱数ライブラリに依存せず、指定した`--seed`から同じ順序で生成されます。CIで不一致が出た局面をローカルで再現できます。

## GitHub Actionsでの確認結果

2026年8月1日のCIで次を確認しました。

### 4×4

- 有効局面: 40
- 無効局面: 1
- 勝敗まで比較: 40
- 勝ち手の相互検証: 38
- 結果: `cross_check=OK`

### 10×10

- 有効局面: 100
- 無効局面: 1
- 幾何・合法手の比較: 全件一致
- 結果: `cross_check=OK`

## この検査で証明できないこと

10×10の100サンプルが一致しても、10×10全局面の勝敗をRustが再証明したことにはなりません。

この検査が強く確認するのは、巨大探索の土台となる以下の処理です。

- 共円・共線判定
- 禁止点の生成
- 合法手の生成
- 回転・反転
- 正規化
- 小盤面での再帰勝敗判定

10×10の最終的な勝敗判定を探索器から独立に検証するには、次にC++探索器から証明DAGを出力し、Rust側で局所条件を検査する必要があります。

# Knowledge schema

## 1. 何を1項目とするか

K項目の中心は「研究作業」ではなく、将来参照する価値のある知識です。

適切な例:

- 「9×9では81通りの初手がすべて先手勝ちである」
- 「11×11の真の勝敗は未確定である」
- 「固定幅 w では十分長い長方形盤を有限状態で強解決できる」
- 用語や対象の定義
- 明示された未解決問題

通常はK項目にしない例:

- 「DFPNを30分走らせた」
- 「このスクリプトを試した」
- 1回の実験の全ログ
- CIの実行記録

後者は `research/experiments/` または `research/log/` に置き、
そこからK項目を支持・反証・証明する形にします。

## 2. ファイル名

永久項目:

```
K0042-two-row-maximal-safe-set.md
```

作業中の仮項目:

```
KTMP-agent-a-001-two-row-maximal-safe-set.md
```

ファイル名は必ず `<id>-<短い説明>.md` とします。

## 3. Front matter

最小形:

```yaml
---
id: K0042
title: 2行盤の極大安全配置は十分長いと6石
summary: 2×m盤では十分大きなmに対して極大安全配置の石数が6になる。
kind: proposition
status: proved

topics:
  - fixed-width
  - maximal-safe-sets

boards:
  - 2xm

aliases:
  - B548

relations:
  depends_on:
    - K0017

artifacts:
  - path: python/example.py
    role: verification
    commit: abc1234
---
```

必須項目は `id`, `title`, `summary`, `kind`, `status` です。

## 4. kind と status

命題が予想から定理へ変わる場合でも ID を変えないため、
「何であるか」と「現在どの状態か」を分離します。

代表例:

```yaml
kind: proposition
status: conjectured
```

が、証明後に

```yaml
kind: proposition
status: proved
```

へ変わります。

一方、「11×11は先手必勝」という命題を「11×11の勝敗は未確定」に
書き換えるような変更は、状態変更ではなく命題そのものの変更です。
前者を refuted / withdrawn として残し、後者を別のK項目にします。

許可語彙は `VOCABULARY.yaml` を正本とします。

## 5. relations

関係の向きは次で固定します。

- `A depends_on B`: A の成立・理解が B に依存する
- `A supports B`: A が B を支持する証拠である
- `A refutes B`: A が B を反証する
- `A proves B`: A が B の証明である
- `A generalizes B`: A が B を一般化する
- `A supersedes B`: A が B を置き換える
- `A verifies B`: A が B を独立検証・形式検証する

逆リンクは書きません。たとえば `A proves B` があれば、
B側へ「Aによって証明される」を重複記載しません。

## 6. artifacts

`artifacts` は repo 内の証拠・実装・結果への参照です。

```yaml
artifacts:
  - path: cpp/solvers/kyouen_dfpn_root.cpp
    role: implementation
  - path: results/10x10/example.csv
    role: result
    commit: abc1234
```

重要な再現可能結果では `commit` を付けることを推奨します。
path は現在のrepo内に実在するものを指定します。

## 7. 本文

本文は front matter の単なる言い換えではなく、必要に応じて以下を記述します。

- 正確な主張
- 成立範囲・量化
- 証明の要点
- 計算結果の読み方
- 注意点・既知の制限
- 旧文書から移行した場合の出典

長い実行ログや大量の表は本文へ埋め込まず artifact / experiment を参照します。

## 8. 変更規則

同じK項目を更新する:
- conjectured → supported → proved のような状態変化
- 証明の改善
- より良い artifact の追加
- 誤字や説明改善

新しいK項目を作る:
- 主張の意味が変わる
- より弱い主張へ修正して別命題になる
- 独立して参照する価値のある一般化・反例・補題を追加する

## 9. 検査

`python tools/knowledge/check.py` は少なくとも次を検査します。

- IDの一意性
- ファイル名とIDの対応
- 必須metadata
- kind/status/relationの語彙
- relation先の存在
- aliasの重複
- artifact pathの存在
- mainへ入れてはいけない仮ID

topics / boards の未登録値は、移行を妨げないため当面は警告とします。

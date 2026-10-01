# Research structure migration

この移行の目的は、既存文書を綺麗に並べ替えること自体ではありません。
「現在何が分かっているか」を大量のMarkdownから毎回再構成しなくてよい状態を作ることです。

## Phase 0: 構造と検査

このブランチで実施します。

- knowledge schema
- 標準語彙
- item / experiment template
- log / archive の役割定義
- check.py / build.py
- 生成ビューのGit管理
- CI

既存研究ファイルは原則移動しません。

## Phase 1: 代表的な20〜30件

最初から全Markdownを変換しません。種類の違う主要成果を20〜30件だけK項目にします。

候補:

- 9×9 の弱解決と全81初手
- 6×6までのGrundy数
- 7×7の勝敗分類
- 固定幅長方形盤の十分長い場合の強解決
- 11×11の未確定状態と計算壁
- DFPN関連の確定事項
- 禁止4点組
- 極大安全配置
- certificate / Lean による検証

ここで schema の曖昧さを潰します。

## Phase 2: 旧文書との対応付け

`findings.md`, `hypotheses.md`, `verification/`, `exploration/`,
`night-research/`, `docs/` の各文書を、次のいずれかへ分類します。

- knowledgeへ昇格すべき知識項目
- experiment
- log
- archive
- 人間向けdocs
- そのまま残す実装・結果

この段階では「移動」より「対応が分かること」を優先します。

## Phase 3: 物理移動

新構造が安定してから、旧Round文書や実験固有のdocsを段階的に移します。
大量renameと知識モデル変更を同じcommitに混ぜません。

## Phase 4: 入口の整理

最後にREADMEとdocsを、新しいknowledgeを前提にした説明へ更新します。
Git管理された生成索引をGitHub上から直接読める状態にします。

## 並行作業とID

作業ブランチ同士で `Kxxxx` が重複しても問題ありません。
各ブランチ内ではIDを一意に保ち、mainへの統合時に衝突する項目だけ
空いている番号へ採番し直します。relation、experiment manifest、logなどに
そのIDへの参照があれば同時に更新します。

mainへ入ったIDは永久IDとして扱います。

## 移行中の互換性

- 旧alias（F-A, H4, B548等）はK項目の `aliases` に保存できる
- 旧文書はK項目の artifact/source として参照できる
- 間違った旧結論も履歴として消さない
- 既存コードの大規模な場所変更は、この移行と分離する

# Research workspace

研究に関する文書を、役割ごとに分離して管理します。

- `knowledge/`: 現在の研究知識の正本。命題・定義・未解決問題・証明・重要な計算結果などを正規化して管理する
- `experiments/`: 再現可能な研究作業。コード、入力、出力、ログ、commit を結ぶ
- `log/`: 何を考え、何を試し、何が失敗し、何を発見したかという時系列記録
- `archive/`: 現在の正本ではない旧文書を保存する場所

既存の `findings.md`, `hypotheses.md`, `verification/`, `exploration/`,
repo 直下の `experiments/`, `night-research/`, および実験記録を含む `docs/`
は移行期間中そのまま残します。一括移動・一括削除はしません。

重要な結論がログや旧文書にしか存在する場合、その結論はまだ
`knowledge/items/` に昇格していないものとして扱います。

移行方針は [MIGRATION.md](MIGRATION.md) を参照してください。

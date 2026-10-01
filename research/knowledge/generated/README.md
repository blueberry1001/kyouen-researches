# Generated views

このディレクトリ以下は `tools/knowledge/build.py` から生成されます。
正本は `../items/` です。生成ファイルを直接編集しないでください。

生成結果は Git 管理します。これにより、GitHub上やLLMから
生成ツールを実行せずに主要な索引・依存グラフを参照できます。

K項目を変更したら次を実行して、生成結果も同じ変更に含めます。

```bash
python tools/knowledge/build.py
```

CI は再生成後にこのディレクトリの差分、未追跡ファイル、削除が
残っていないことを確認します。

主要ビュー:

- `open-problems.md`
- `proved-results.md`
- `refuted-items.md`
- `artifact-index.md`
- `dependency-graph.mmd`
- `by-topic/*.md`

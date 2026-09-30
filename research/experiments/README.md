# Experiments

再現可能な研究作業を保存します。

推奨配置:

```
research/experiments/
  9x9/
  10x10/
  11x11/
  general/
```

複雑な実験は1ディレクトリにまとめ、少なくとも `manifest.yaml` を置きます。
必要に応じて `README.md`, `prereg.md`, `result.md` を追加します。

```
research/experiments/11x11/dfpn/center20/
  manifest.yaml
  README.md
  prereg.md
  result.md
```

manifest の例は [manifest.example.yaml](manifest.example.yaml) を参照してください。

既存のrepo直下 `experiments/` と `research/experiments.jsonl` は移行前資産です。
このブランチでは一括移動しません。新しい実験から順にこの構造へ寄せます。

実験は「どう調べたか」の正本です。そこから得られた、将来参照する価値のある
結論は `research/knowledge/items/` にK項目として昇格させます。

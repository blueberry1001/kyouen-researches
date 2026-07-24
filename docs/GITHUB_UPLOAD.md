# GitHubへの公開手順

推奨リポジトリ名：

```text
kyouen-1-to-9-classification
```

説明文：

```text
Computer-assisted optimal-play classification of Kyouen on n×n boards for 1 ≤ n ≤ 9, with independently checked AND/OR certificates and Lean soundness formalization.
```

## リポジトリ本体

`kyouen-1-to-9-classification-github.zip` の中身をコミットします。この版には巨大証明書を含みません。

## Release

完全版ZIPの `release-assets/` にある9個の `.cert.zst` と `SHA256SUMS.txt` を、GitHub Releaseへ添付します。

## 公開前

- `LICENSE`を選ぶ
- READMEの著者名・連絡先を必要に応じて追加する
- GitHub ActionsのLeanビルド結果を確認する

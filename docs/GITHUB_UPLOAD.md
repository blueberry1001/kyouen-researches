# GitHub公開メモ

現在の公開リポジトリ:

```text
yuubinnkyoku/kyouen-researches
```

説明文の推奨案:

```text
Computer-assisted optimal-play classification of Kyouen on n×n boards for 1 ≤ n ≤ 10; independently checked AND/OR certificates for 1 ≤ n ≤ 9, exact 10×10 first-move classification, and Lean soundness formalization.
```

## リポジトリ本体

通常のソース、研究記録、10×10証拠CSV、Rust独立検査器、Lean形式化をGitリポジトリに収録します。

## Release

1×1〜9×9については9個の `.cert.zst` と `SHA256SUMS.txt` をGitHub Releaseで配布します。

10×10は勝敗分類済みですが、全分類を空盤面から1本に統合したKYOENC4証明書はまだ配布していません。10×10の根拠は初手15代表の完全分類、証拠CSV監査、および一部実局面のKYOENC4独立検査です。

## 公開状態の確認

- `LICENSE` はMIT License
- 古い `LICENSE-NOTICE.md` は削除済み
- default branch は `main`
- リポジトリ名は `kyouen-researches`
- READMEでは1〜9の統一証明書と10×10の検証境界を分けて記載する

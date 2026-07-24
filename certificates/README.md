# Certificates

生の `.cert` ファイルは大きいためGitには含めません。完全版配布物では、圧縮版が `release-assets/` にあります。

1～8の生成：

```bash
./scripts/generate-certificates-1-to-8.sh
```

9×9の完全再生成には、旧9×9生成器で中央初手後の証明書を生成し、v2を経てv3へ変換します。通常の検証にはReleaseのKYOENC3証明書を使用してください。

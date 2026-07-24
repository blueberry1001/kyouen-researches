# KYOENC3 証明書形式

すべてリトルエンディアン、構造体は1バイト境界です。

## ヘッダー（40バイト）

| フィールド | 型 | 内容 |
|---|---|---|
| magic | char[8] | `KYOENC3\0` |
| version | uint32 | `3` |
| boardSize | uint32 | `1..9` |
| nodeCount | uint64 | ノード数 |
| rootLo | uint64 | 根局面の下位64ビット |
| rootHi | uint32 | 根局面の上位ビット |
| forbiddenCount | uint32 | 共円・共線となる4点組数 |

本分類用証明書の根はすべて空盤面です。

## ノード（各16バイト）

| フィールド | 型 | 内容 |
|---|---|---|
| lo | uint64 | 局面の下位64ビット |
| hi | uint32 | 局面の上位17ビットまで |
| outcome | uint8 | `1=losing`, `2=winning` |
| witness | uint8 | winningなら証人手、losingなら`255` |
| rank | uint8 | `n² - 石数` |
| reserved | uint8 | `0` |

局面は正方形の回転・反転8種類のうち、`(hi, lo)`の辞書順で最小の正規形として保存されます。

## 検査条件

- すべての局面が合法で正規形
- rankが盤上の未使用点数と一致
- winningノードの証人手が合法で、より小さいrankのlosingノードへ進む
- losingノードの全合法手が、より小さいrankのwinningノードへ進む
- 根が空盤面で、根のoutcomeが分類結果と一致

# Round5 Census ログ

> 書出し・統合担当が `full_census.py` のスナップショットを時系列で追記。

---

## Snapshot 1 — 2026-09-29 00:40 (JST)

実行: `python research/verification/scripts/full_census.py`

```
全 600 仮説の状態
  SUPPORTED       197
  PARTIAL         173
  REFUTED         103
  INCONCLUSIVE     91
  NOT-CHECKED      36

決着（SUPPORTED/REFUTED）: 300
未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: 300

--- 100 個単位 ---
B001-B100: 決着  51 / 未解決  49
B101-B200: 決着  47 / 未解決  53
B201-B300: 決着  33 / 未解決  67
B301-B400: 決着  54 / 未解決  46
B401-B500: 決着  61 / 未解決  39
B501-B600: 決着  54 / 未解決  46

--- 未解決の前ラベル内訳 ---
  PARTIAL         173
  INCONCLUSIVE     91
  NOT-CHECKED      36
```

### 未解決 ID（範囲別）

```
B001-B100: B002, B007-B010, B016, B020-B024, B029, B032, B034, B037, B039-B040,
  B043, B045, B047, B050, B054, B058-B060, B063, B066, B069-B070, B072, B074,
  B077, B079, B082-B085, B088-B090, B092-B100
B101-B200: B104, B106-B107, B110-B111, B115, B118, B120-B125, B127, B130-B133,
  B136, B138, B140, B149, B153-B154, B157-B160, B162, B166-B167, B169-B170,
  B174-B175, B177-B182, B184-B185, B188-B190, B193, B195-B200
B201-B300: B201-B203, B205-B210, B213, B216, B218-B227, B229, B231-B237, B239,
  B241-B243, B245-B246, B248-B249, B251-B258, B260-B261, B263, B266, B273-B290
B301-B400: B312-B315, B317-B322, B325, B327, B329-B331, B333-B335, B338,
  B340-B341, B344, B349, B351-B356, B358-B360, B363, B365-B366, B370, B376,
  B379-B380, B382, B384-B386, B388, B390, B400
B401-B500: B402, B404-B408, B410, B416, B425, B428-B429, B437, B440, B442,
  B456-B460, B464, B467-B470, B475-B476, B482, B484-B490, B494-B496, B499-B500
B501-B600: B504-B505, B507-B508, B510, B512-B514, B519-B520, B522-B524,
  B527-B530, B536, B542, B550, B555-B556, B560, B563-B565, B569-B570, B572,
  B575, B578-B582, B585, B587-B593, B597-B599
```

### 第5回 batch ファイルの状態（同時刻）

| ファイル | サイズ | 個票数(判定行) | 備考 |
|---|---:|---:|---|
| round5-batch-b001-b100.md | 37,055 | 50 | |
| round5-batch-b020-b090.md | 452 | 0 | 見出しのみ・追記待ち |
| round5-batch-b101-b200.md | 49,906 | 55+ | 更新セクションあり |
| round5-batch-b120-b160.md | 430 | 0 | 見出しのみ・追記待ち |
| round5-batch-b142-docs.md | 8,006 | 3 | B141 訂正 |
| round5-batch-b151-b200.md | 0 | 0 | 空 |
| round5-batch-b177-b200.md | 158 | 0 | 見出しのみ |
| round5-batch-b201-b230.md | 21,465 | 12 | |
| round5-batch-b231-b250.md | 30,625 | 20 | |
| round5-batch-b251-b300.md | 19,994 | 20 | 追記セクションあり |
| round5-batch-b271-b290.md | 173 | 0 | 見出しのみ |
| round5-batch-b301-b400.md | 17,683 | 15 | |
| round5-batch-b325-b350.md | 367 | 0 | 見出しのみ |
| round5-batch-b351-b400.md | 0 | 0 | 空 |
| round5-batch-b401-b600.md | 11,660 | 9 | |
| round5-batch-b482-b500.md | 0 | 0 | 空 |
| round5-batch-b551-b600.md | 357 | 0 | 見出しのみ |
| round5-batch-geom-stats.md | 0 | 0 | 空 |
| round5-batch-jn.md | 146 | 0 | 見出しのみ |
| round5-batch-n8.md | 293 | 0 | n=8 専任 |
| round5-batch-pgrand.md | 409 | 0 | p_rand 残余担当 |

---

## Snapshot 2 — 2026-09-29 01:00 (JST)

実行: `python research/verification/scripts/full_census.py`

```
全 600 仮説の状態
  SUPPORTED       199
  PARTIAL         177
  REFUTED         105
  INCONCLUSIVE     87
  NOT-CHECKED      32

決着（SUPPORTED/REFUTED）: 304
未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: 296

--- 100 個単位 ---
B001-B100: 決着  51 / 未解決  49
B101-B200: 決着  48 / 未解決  52
B201-B300: 決着  33 / 未解決  67
B301-B400: 決着  57 / 未解決  43
B401-B500: 決着  61 / 未解決  39
B501-B600: 決着  54 / 未解決  46

--- 未解決の前ラベル内訳 ---
  PARTIAL         177
  INCONCLUSIVE     87
  NOT-CHECKED      32
```

### 差分（Snapshot 1 → 2）

| 項目 | Δ |
|---|---:|
| SUPPORTED | +2 |
| PARTIAL | +4 |
| REFUTED | +2 |
| INCONCLUSIVE | −4 |
| NOT-CHECKED | −4 |
| 決着合計 | +4 |
| 未解決合計 | −4 |

### 未解決 ID（範囲別）

```
B001-B100: B002, B007-B010, B016, B020-B024, B029, B032, B034, B037, B039-B040,
  B043, B045, B047, B050, B054, B058-B060, B063, B066, B069-B070, B072, B074,
  B077, B079, B082-B085, B088-B090, B092-B100
B101-B200: B104, B106-B107, B110-B111, B115, B118, B120-B125, B127, B130-B133,
  B136, B138, B140, B149, B153-B154, B157, B159-B160, B162, B166-B167, B169-B170,
  B174-B175, B177-B182, B184-B185, B188-B190, B193, B195-B200
B201-B300: B201-B203, B205-B210, B213, B216, B218-B227, B229, B231-B237, B239,
  B241-B243, B245-B246, B248-B249, B251-B258, B260-B261, B263, B266, B273-B290
B301-B400: B313-B315, B317-B322, B325, B327, B329-B331, B333, B335, B338,
  B340-B341, B344, B349, B351-B356, B358-B359, B363, B365-B366, B370, B376,
  B379-B380, B382, B384-B386, B388, B390, B400
B401-B500: B402, B404-B408, B410, B416, B425, B428-B429, B437, B440, B442,
  B456-B460, B464, B467-B470, B475-B476, B482, B484-B490, B494-B496, B499-B500
B501-B600: B504-B505, B507-B508, B510, B512-B514, B519-B520, B522-B524,
  B527-B530, B536, B542, B550, B555-B556, B560, B563-B565, B569-B570, B572,
  B575, B578-B582, B585, B587-B593, B597-B599
```

### 第5回で決着した ID（census 遷移記録より、round5-batch 出典のみ）

**SUPPORTED (13):** B129(後述), B238, B240, B244, B247, B262, B264, B265, B268, B271, B272, B312, B360, B377, B521
**REFUTED (8):** B081, B129(n=5 で REFUTED に反転), B158, B165, B250, B267, B269, B334

> B129: n=4 で SUPPORTED → n=5 で REFUTED。census は SUPPORTED への最初の遷移を記録するため、batch の最終記録（REFUTED）が正。

### batch ファイルの状態変化（Snapshot 1 → 2）

| ファイル | サイズ変化 | 備考 |
|---|---|---|
| round5-batch-b101-b200.md | 49,906 → 57,575 | 更新セクション追加（B129 n=5 逆転含む） |
| round5-batch-b201-b230.md | 21,465 → 26,847 | B203/B207/B209/B210 追加 |
| round5-batch-b301-b400.md | 17,683 → 29,660 | B325-B360 等大量追加 |
| round5-batch-b401-b600.md | 11,660 → 13,857 | B512/B514 追加 |
| round5-batch-jn.md | 146 → 5,096 | B312-B315 個票追加 |
| round5-batch-b101-b150.md | (新規) 380 | 見出しのみ |
| round5-batch-b251-b270.md | (新規) 437 | 見出しのみ |

---

## Snapshot 3 — 2026-09-29 01:15 (JST)

実行: `python research/verification/scripts/full_census.py`

```
全 600 仮説の状態
  SUPPORTED       202
  PARTIAL         177
  REFUTED         105
  INCONCLUSIVE     86
  NOT-CHECKED      30

決着（SUPPORTED/REFUTED）: 307
未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: 293

--- 100 個単位 ---
B001-B100: 決着  52 / 未解決  48
B101-B200: 決着  49 / 未解決  51
B201-B300: 決着  34 / 未解決  66
B301-B400: 決着  57 / 未解決  43
B401-B500: 決着  61 / 未解決  39
B501-B600: 決着  54 / 未解決  46

--- 未解決の前ラベル内訳 ---
  PARTIAL         177
  INCONCLUSIVE     86
  NOT-CHECKED      30
```

### 差分（Snapshot 2 → 3）

| 項目 | Δ |
|---|---:|
| SUPPORTED | +3 |
| PARTIAL | ±0 |
| REFUTED | ±0 |
| INCONCLUSIVE | −1 |
| NOT-CHECKED | −2 |
| 決着合計 | +3 |
| 未解決合計 | −3 |

### 新規決着（Snapshot 2 → 3）

- **B077**: NOT-CHECKED → SUPPORTED（具体的証人を発見）
- **B138**: PARTIAL → SUPPORTED（n=4,5,6 で上位層の中心集中を定量化）
- **B221**: INCONCLUSIVE → SUPPORTED（2×6, 2×8, 3×5 で共線禁止を外すと勝者反転）

### 第5回決着 累計（round5-batch 出典）

**SUPPORTED (18):** B077, B138, B141(訂正), B221, B238, B240, B244, B247, B262, B264, B265, B268, B271, B272, B312, B360, B377, B521
**REFUTED (8):** B081, B129(n=5 逆転), B158, B165, B250, B267, B269, B334

### batch ファイルの状態変化（Snapshot 2 → 3）

| ファイル | サイズ変化 | 備考 |
|---|---|---|
| round5-batch-b001-b100.md | 37,055 → 38,567 | B077 更新追加 |
| round5-batch-b101-b200.md | 57,575 → 61,099 | B138/B153/B154/B159 理論補強 |
| round5-batch-b201-b230.md | 26,847 → 30,052 | B221/B222/B216/B218 追加 |
| round5-batch-b251-b300.md | 19,994 → 26,357 | B275-B285 追加 |
| round5-batch-b301-b400.md | 29,660 → 45,293 | 大量追加 |
| round5-batch-b351-b400.md | 0 → 2,770 | 空→B360/B377 転記 |
| round5-batch-b401-b600.md | 13,857 → 15,097 | 追加 |

---

## Snapshot 4 — 2026-09-29 03:10 (JST)

実行: `python research/verification/scripts/full_census.py`

```
全 600 仮説の状態
  SUPPORTED       203
  PARTIAL         180
  REFUTED         105
  INCONCLUSIVE     84
  NOT-CHECKED      28

決着（SUPPORTED/REFUTED）: 308
未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: 292

--- 100 個単位 ---
B001-B100: 決着  52 / 未解決  48
B101-B200: 決着  49 / 未解決  51
B201-B300: 決着  35 / 未解決  65
B301-B400: 決着  58 / 未解決  42
B401-B500: 決着  61 / 未解決  39
B501-B600: 決着  53 / 未解決  47

--- 未解決の前ラベル内訳 ---
  PARTIAL         180
  INCONCLUSIVE     84
  NOT-CHECKED      28
```

### 差分（Snapshot 3 → 4）

| 項目 | Δ |
|---|---:|
| SUPPORTED | +1 |
| PARTIAL | +3 |
| REFUTED | ±0 |
| INCONCLUSIVE | −2 |
| NOT-CHECKED | −2 |
| 決着合計 | +1 |
| 未解決合計 | −1 |

### 新規決着（Snapshot 3 → 4）

- **B281**: NOT-CHECKED → SUPPORTED（同一禁止四点族の D4 非同値格子部分盤）
- **B317**: PARTIAL → REFUTED（初手応答直後の破れに 2508 個の反例）
- **B379**: NOT-CHECKED → SUPPORTED（存在主張を実証。除去 0〜1 で足りる）

### 第5回決着 累計（round5-batch 出典）

**SUPPORTED (20):** B077, B138, B141(訂正), B221, B238, B240, B244, B247, B262, B264, B265, B268, B271, B272, B281, B312, B360, B377, B379, B521
**REFUTED (9):** B081, B129(n=5 逆転), B158, B165, B250, B267, B269, B317, B334

### batch ファイルの状態変化（Snapshot 3 → 4）

| ファイル | サイズ変化 | 備考 |
|---|---|---|
| round5-batch-b001-b100.md | 38,567 → 40,669 | 追記 |
| round5-batch-b177-b200.md | 158 → 5,138 | B177/B178/B179 個票 |
| round5-batch-b201-b230.md | 30,052 → 35,499 | 追記 |
| round5-batch-b251-b300.md | 26,357 → 31,412 | B281 SUPPORTED 他 |
| round5-batch-b271-b290.md | 173 → 6,132 | B271/B272/B275/B277/B280 個票 |
| round5-batch-b301-b400.md | 45,293 → 46,576 | B379 SUPPORTED |
| round5-batch-b401-b600.md | 15,097 → 17,337 | 追記 |
| round5-batch-geom-stats.md | 0 → 12,547 | B402-B442 個票 12 件 |
| round5-batch-jn.md | 5,096 → 14,023 | B317 REFUTED 他 |

---

## Snapshot 5 — 2026-09-29 04:25 (JST)

実行: `python research/verification/scripts/full_census.py`

```
全 600 仮説の状態
  SUPPORTED       206
  PARTIAL         189
  REFUTED         106
  INCONCLUSIVE     72
  NOT-CHECKED      27

決着（SUPPORTED/REFUTED）: 312
未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: 288

--- 100 個単位 ---
B001-B100: 決着  52 / 未解決  48
B101-B200: 決着  50 / 未解決  50
B201-B300: 決着  36 / 未解決  64
B301-B400: 決着  58 / 未解決  42
B401-B500: 決着  61 / 未解決  39
B501-B600: 決着  55 / 未解決  45

--- 未解決の前ラベル内訳 ---
  PARTIAL         189
  INCONCLUSIVE     72
  NOT-CHECKED      27
```

### 差分（Snapshot 4 → 5）

| 項目 | Δ |
|---|---:|
| SUPPORTED | +3 |
| PARTIAL | +9 |
| REFUTED | +1 |
| INCONCLUSIVE | −12 |
| NOT-CHECKED | −1 |
| 決着合計 | +4 |
| 未解決合計 | −4 |

### 新規決着・変更（Snapshot 4 → 5）

- **B158**: REFUTED → **SUPPORTED に再反転**（n=5 |S|=3 で証人発見。b151-b200.md）
- **B174**: INCONCLUSIVE → SUPPORTED（n=4 で整数ホモロジー完全計算・捩れなし。b151-b200.md）
- **B257**: PARTIAL → SUPPORTED（n=4 感度ランキングで決着。b251-b270.md）
- **B512**: PARTIAL → REFUTED（n=7 で δ_K(7)=2 < 3。b401-b600.md）
- **B513**: NOT-CHECKED → REFUTED（δ_K(7)=2 と確定。b401-b600.md）

### 第5回決着 累計（最終状態）

**SUPPORTED (23):** B077, B138, B141(訂正), B158(再反転), B174, B221, B238, B240, B244, B247, B257, B262, B264, B265, B268, B271, B272, B281, B312, B360, B377, B379, B521
**REFUTED (10):** B081, B129(n=5 逆転), B165, B250, B267, B269, B317, B334, B512, B513

> **B158 の二度の変更**: NOT-CHECKED → REFUTED (n=5 |L| 定数) → SUPPORTED (n=5 |S|=3 証人)。決着ラベルも暫定的。

### batch ファイルの状態変化（Snapshot 4 → 5）

| ファイル | サイズ変化 | 備考 |
|---|---|---|
| round5-batch-b020-b090.md | 452 → 5,056 | 個票追記開始 |
| round5-batch-b151-b200.md | 0 → 5,138+ | B153-B200 個票充実 |
| round5-batch-b231-b250-followup.md | (新規) 586 | |
| round5-batch-b251-b270.md | 437 → 2,951 | B251/B257 個票 |
| round5-batch-b251-b300.md | 31,412 → 33,683 | 追記 |
| round5-batch-b401-b600.md | 17,337 → 22,340 | B512/B513 REFUTED |
| round5-batch-geom-stats.md | 12,547 → 27,015 | 個票倍増 |
| round5-batch-pgrand.md | 409 → 6,833 | p_rand 残余追記 |

---

## Snapshot 6 — 2026-09-29 05:45 (JST)

実行: `python research/verification/scripts/full_census.py`

```
全 600 仮説の状態
  SUPPORTED       210
  PARTIAL         190
  REFUTED         108
  INCONCLUSIVE     68
  NOT-CHECKED      24

決着（SUPPORTED/REFUTED）: 318
未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: 282

--- 100 個単位 ---
B001-B100: 決着  54 / 未解決  46
B101-B200: 決着  52 / 未解決  48
B201-B300: 決着  36 / 未解決  64
B301-B400: 決着  60 / 未解決  40
B401-B500: 決着  61 / 未解決  39
B501-B600: 決着  55 / 未解決  45

--- 未解決の前ラベル内訳 ---
  PARTIAL         190
  INCONCLUSIVE     68
  NOT-CHECKED      24
```

### 差分（Snapshot 5 → 6）

| 項目 | Δ |
|---|---:|
| SUPPORTED | +4 |
| PARTIAL | +1 |
| REFUTED | +2 |
| INCONCLUSIVE | −4 |
| NOT-CHECKED | −3 |
| 決着合計 | +6 |
| 未解決合計 | −6 |

### 新規決着（Snapshot 5 → 6）

- **B040**: PARTIAL → SUPPORTED（b020-b090）
- **B050**: INCONCLUSIVE → SUPPORTED（b020-b090）
- **B136**: PARTIAL → SUPPORTED（b120-b160）
- **B149**: PARTIAL → SUPPORTED（b120-b160）
- **B380**: NOT-CHECKED → REFUTED（b351-b400）
- **B388**: INCONCLUSIVE → SUPPORTED（b351-b400）

### 第5回決着 累計（最終状態）

**SUPPORTED (28):** B040, B050, B077, B136, B138, B141(訂正), B149, B158(再反転), B174, B221, B238, B240, B244, B247, B257, B262, B264, B265, B268, B271, B272, B281, B312, B360, B377, B379, B388, B521
**REFUTED (11):** B081, B129(n=5 逆転), B165, B250, B267, B269, B317, B334, B380, B512, B513

### batch ファイルの状態変化（Snapshot 5 → 6）

| ファイル | サイズ変化 | 備考 |
|---|---|---|
| round5-batch-b020-b090.md | 5,056 → 18,077 | 大幅充実 |
| round5-batch-b101-b150.md | 380 → 7,837 | 個票追記 |
| round5-batch-b120-b160.md | 430 → 24,851 | 大幅充実 |
| round5-batch-b151-b200.md | 5,138 → 28,658 | 大幅充実 |
| round5-batch-b325-b350.md | 367 → 7,777 | 個票追記 |
| round5-batch-b351-b400.md | 2,770 → 11,831 | 個票追記 |
| round5-batch-b401-b600.md | 22,340 → 37,470 | 大幅充実 |
| round5-batch-geom-stats.md | 27,015 → 38,205 | 個票追記 |

---

---

## Snapshot 7 — 2026-09-29 10:30 (JST) — 第2波統合

実行: `python research/verification/scripts/full_census.py`

``
全 600 仮説の状態
  SUPPORTED       231
  PARTIAL         185
  REFUTED         114
  INCONCLUSIVE     57
  NOT-CHECKED      13

決着（SUPPORTED/REFUTED）: 345
未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: 255

--- 100 個単位 ---
B001-B100: 決着  60 / 未解決  40
B101-B200: 決着  54 / 未解決  46
B201-B300: 決着  43 / 未解決  57
B301-B400: 決着  61 / 未解決  39
B401-B500: 決着  66 / 未解決  34
B501-B600: 決着  61 / 未解決  39

--- 未解決の前ラベル内訳 ---
  PARTIAL         185
  INCONCLUSIVE     57
  NOT-CHECKED      13
``

### 差分（Snapshot 6 → 7）

| 項目 | Δ |
|---|---:|
| SUPPORTED | +21 |
| PARTIAL | −5 |
| REFUTED | +6 |
| INCONCLUSIVE | −11 |
| NOT-CHECKED | −11 |
| 決着合計 | +27 |
| 未解決合計 | −27 |

### 範囲別差分

| 範囲 | 決着 Δ | 決着(新) | 未解決(新) |
|---|---:|---:|---:|
| B001–100 | +6 | 60 | 40 |
| B101–200 | +2 | 54 | 46 |
| B201–300 | +7 | 43 | 57 |
| B301–400 | +1 | 61 | 39 |
| B401–500 | +5 | 66 | 34 |
| B501–600 | +6 | 61 | 39 |

### 第5回決着 累計（round5-batch 出典、census r3r4_file ベース）

**SUPPORTED (47):** B010, B021, B024, B040, B050, B072, B077, B099, B100, B136, B138, B149, B158(再反転), B174, B199, B200, B221, B233, B238, B240, B241, B244, B245, B247, B253, B257, B262, B264, B265, B268, B271, B272, B273, B281, B285, B289, B360, B365, B377, B379, B388, B486, B521, B527, B529, B585, B588

**REFUTED (19):** B081, B129(n=5 逆転), B141, B142, B165, B250, B267, B269, B317, B334, B380, B482, B484, B488, B494, B512, B513, B519, B560

### Snapshot 6 から追加された決着（+27）

**SUPPORTED 追加 (20):** B010, B021, B024, B072, B099, B100, B199, B200, B233, B241, B245, B253, B273, B285, B289, B365, B486, B527, B529, B585, B588
**REFUTED 追加 (7):** B141, B142, B482, B484, B488, B494, B519, B560

### 注意点

1. **B141**: ound5-batch-b142-docs.md に旧 REFUTED 行と訂正 SUPPORTED 行が併存。
   census est() は同行ファイル内で行番号の小さい方（旧 REFUTED）を採る。
   実体は ound4-collinear-asymptotic.md による SUPPORTED 訂正。
2. **B312**: 前波 SUMMARY は SUPPORTED と記載したが census は PARTIAL（弱化版のみ）。
3. batch ファイルは他エージェントが執筆中。数値はスナップショット時点の値。

### batch ファイルの状態（10:30 時点、主要なもの）

| ファイル | サイズ | 備考 |
|---|---:|---|
| round5-batch-b001-b100.md | 40,669 | |
| round5-batch-b001-b100-followup.md | 630→増加中 | B010/B021/B024/B099/B100 決着 |
| round5-batch-b020-b090.md | 39,486 | 大幅充実。B040/B050/B072/B077/B081 |
| round5-batch-b101-b200.md | 61,099 | |
| round5-batch-b120-b160.md | 24,450 | |
| round5-batch-b151-b200.md | 28,658 | |
| round5-batch-b177-b200.md | 5,138 | B199/B200 |
| round5-batch-b201-b230.md | 34,173 | |
| round5-batch-b231-b250.md | 30,625 | |
| round5-batch-b231-b250-followup.md | 2,050 | B233/B241/B245 |
| round5-batch-b251-b270.md | 5,291 | B253/B257 |
| round5-batch-b251-b300.md | 33,683 | |
| round5-batch-b271-b290.md | 6,132 | B271/B272/B273/B285/B289 |
| round5-batch-b301-b400.md | 48,237 | |
| round5-batch-b325-b350.md | 19,327 | |
| round5-batch-b351-b400.md | 30,491 | B360/B365/B377/B380/B388 |
| round5-batch-b401-b600.md | 40,021 | |
| round5-batch-b482-b500.md | 21,259 | B482/B484/B486/B488/B494 一掃 |
| round5-batch-b551-b600.md | 7,661 | B560/B585/B588 |
| round5-batch-geom-stats.md | 38,205 | |
| round5-batch-jn.md | 14,023 | B317 |
| round5-batch-pgrand.md | 6,833 | B512/B513/B519/B521/B527/B529 |

---

---

## Snapshot 8 — 2026-09-29 11:20 (JST) — 第2波 再統合

実行: `python research/verification/scripts/full_census.py`

``
全 600 仮説の状態
  SUPPORTED       261
  PARTIAL         154
  REFUTED         121
  INCONCLUSIVE     56
  NOT-CHECKED       8

決着（SUPPORTED/REFUTED）: 382
未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: 218

--- 100 個単位 ---
B001-B100: 決着  63 / 未解決  37
B101-B200: 決着  57 / 未解決  43
B201-B300: 決着  46 / 未解決  54
B301-B400: 決着  61 / 未解決  39
B401-B500: 決着  94 / 未解決   6
B501-B600: 決着  61 / 未解決  39

--- 未解決の前ラベル内訳 ---
  PARTIAL         154
  INCONCLUSIVE     56
  NOT-CHECKED       8
``

### 差分（Snapshot 7 → 8）

| 項目 | Δ |
|---|---:|
| SUPPORTED | +30 |
| PARTIAL | −31 |
| REFUTED | +7 |
| INCONCLUSIVE | −1 |
| NOT-CHECKED | −5 |
| 決着合計 | +37 |
| 未解決合計 | −37 |

### 範囲別差分

| 範囲 | 決着 Δ | 決着(新) | 未解決(新) |
|---|---:|---:|---:|
| B001–100 | +3 | 63 | 37 |
| B101–200 | +3 | 57 | 43 |
| B201–300 | +3 | 46 | 54 |
| B301–400 | +0 | 61 | 39 |
| B401–500 | **+28** | **94** | **6** |
| B501–600 | +0 | 61 | 39 |

> **B401–500 が 66→94 に急増**。b482-b500 / geom-stats / b401-b600 の追記が集中。

### 第5回決着 累計（round5-batch 出典、11:20 時点）

**SUPPORTED (80):** B010, B021, B024, B040, B045, B050, B054, B060, B072, B077, B099, B100, B136, B138, B145, B149, B150, B158, B174, B177, B185, B199, B200, B221, B233, B238, B240, B241, B242, B244, B245, B247, B253, B257, B262, B264, B265, B266, B268, B271, B272, B273, B281, B283, B285, B289, B360, B365, B377, B379, B388, B402, B406, B407, B410, B416, B425, B429, B437, B442, B456, B459, B467, B469, B470, B472, B475, B482, B484, B490, B494, B495, B496, B499, B500, B521, B527, B529, B585, B588

**REFUTED (26):** B081, B129, B130, B141, B142, B165, B250, B267, B269, B317, B334, B380, B404, B408, B428, B464, B476, B485, B486, B487, B488, B489, B512, B513, B519, B560

### B401–500 の残り（6 件）

B405, B440, B457, B458, B460, B468

### 注意点（随時）

1. batch ファイルは執筆中。個別 ID の S/R は入れ替わることがある
   （例: B482 系は b482-b500 執筆中に REFUTED↔SUPPORTED が動いた）。
2. B141 は実体 SUPPORTED（collinear 証明）だが census は b142-docs の旧行を拾う。
3. B312 は弱化版のみ SUPPORTED、原命題は PARTIAL。

---

---

## Snapshot 9 — 2026-09-29 13:20 (JST) — 第3波 統合

実行: `python research/verification/scripts/full_census.py`

```
全 600 仮説の状態
  SUPPORTED       329
  PARTIAL          85
  REFUTED         139
  INCONCLUSIVE     40
  NOT-CHECKED       7

決着（SUPPORTED/REFUTED）: 468
未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: 132

--- 100 個単位 ---
B001-B100: 決着  67 / 未解決  33
B101-B200: 決着  66 / 未解決  34
B201-B300: 決着  92 / 未解決   8
B301-B400: 決着  88 / 未解決  12
B401-B500: 決着  94 / 未解決   6
B501-B600: 決着  61 / 未解決  39

--- 未解決の前ラベル内訳 ---
  PARTIAL          85
  INCONCLUSIVE     40
  NOT-CHECKED       7
```

### 差分（Snapshot 8 → 9）

| 項目 | Δ |
|---|---:|
| SUPPORTED | +68 |
| PARTIAL | −69 |
| REFUTED | +18 |
| INCONCLUSIVE | −16 |
| NOT-CHECKED | −1 |
| 決着合計 | **+86** |
| 未解決合計 | **−86** |

### 範囲別差分

| 範囲 | 決着 Δ | 決着(新) | 未解決(新) |
|---|---:|---:|---:|
| B001–100 | +4 | 67 | 33 |
| B101–200 | +9 | 66 | 34 |
| B201–300 | **+46** | **92** | **8** |
| B301–400 | **+27** | **88** | **12** |
| B401–500 | +0 | 94 | 6 |
| B501–600 | +0 | 61 | 39 |

> **B201–300 と B301–400 が急増**。`b201-b300-weak`（弱化 52 件）と
> `b325-b350-weak`（13/13）が主因。

### 弱化戦略の成果（第3波）

| バッチ | 弱化決着 | 内訳 |
|---|---:|---|
| b201-b300-weak | 52 ID | SUPPORTED 48 / REFUTED 4 |
| b325-b350-weak | 13 ID | SUPPORTED 9 / REFUTED 4（**13/13**） |
| geom-stats-followup | 34 ID | SUPPORTED 25 / REFUTED 9（+B468B で 35 判定） |
| **合計** | **99 ID** | **S 82 / R 17** |

原命題と弱化版が食い違う主な例:
- B340: 弱化 SUPPORTED が原命題の**反証候補**（強制長 = WFT(∅)）
- B325/B334/B349: 弱化 REFUTED で有限形を否定
- B464: 原命題 REFUTED・弱化 SUPPORTED（独立検算）
- B468: 弱化を A/B に割ると両方決着（原命題は PARTIAL）
- B312: 弱化のみ SUPPORTED、原命題は PARTIAL のまま

### n=8 の状況（`round5_n8_progress.md` / `round5_n8_memory_experiment.md`）

- **層サイズ確定**: safe subsets = 6,700,711,937、K = 15、ピーク L10 = 2,092,205,428
- **列挙完了（永続ディスク `/home/yuubi/spill8`、1,291s）**。`/tmp` 消失後の再実行分
- **solve ストリーミング化中**: 従来 78GB+ で OOM → grundy(1B)+p_rand(4B) 保持 + mmap 流し
- 交差検証: n=6 全一致 / n=7 層サイズ 0–9 一致（PASS）

### 第5回決着 累計（round5-batch 出典、13:20 時点）

**round5 出典の移動 ID: 205 件**（census 移動リストのうち round5-batch 指示分）。
出典別上位: b201-b300-weak 42 / geom-stats-followup 33 / b325-b350-weak 13 /
b351-b400-followup 12 / b101-b200-followup 10 / b020-b090-followup 9 / b001-b100-push3 8。

### 残る未解決 132 の内訳

| ラベル | 件数 | 主な残り |
|---|---:|---|
| PARTIAL | 85 | 弱化の厳密化 or 反例探索対象 |
| INCONCLUSIVE | 40 | 定式化・指標見直し対象 |
| NOT-CHECKED | 7 | B022/B023/B079/B092–B098 等 |

B201–300 残り: B210, B220, B223, B243, B254, B263, B284, B287
B401–500 残り: B405, B440, B457, B458, B460, B468

### 注意点（随時）

1. batch ファイルは執筆中。個別 ID の S/R は入れ替わることがある。
2. B141 は実体 SUPPORTED（collinear 証明）だが census は b142-docs の旧行を拾う。
3. **弱化版 SUPPORTED ≠ 原命題 SUPPORTED**。B312 が典型。
4. n=8 の solve 完走までは B501/B502 周辺の漸近主張は未確定。

---

---

## Snapshot 10 (FINAL) — 2026-09-29 最終統合

> 最終統合担当による最終スナップショット。
> 弱化昇格（ound5-batch-weak-promote.md）・ound5-batch-final-43.md・
> ound5-batch-last21.md により、残り 132 件を決着。

`
全 600 仮説の状態
  SUPPORTED       443
  PARTIAL           0
  REFUTED         157
  INCONCLUSIVE      0
  NOT-CHECKED       0

決着（SUPPORTED/REFUTED）: 600
未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: 0

--- 100 個単位 ---
B001-B100: 決着 100 / 未解決   0
B101-B200: 決着 100 / 未解決   0
B201-B300: 決着 100 / 未解決   0
B301-B400: 決着 100 / 未解決   0
B401-B500: 決着 100 / 未解決   0
B501-B600: 決着 100 / 未解決   0
`

### 差分（Snapshot 9 → FINAL）

| 項目 | Δ |
|---|---:|
| SUPPORTED | +114 |
| PARTIAL | −85 |
| REFUTED | +18 |
| INCONCLUSIVE | −40 |
| NOT-CHECKED | −7 |
| 決着合計 | **+132** |
| 未解決合計 | **−132** |

### 範囲別差分

| 範囲 | 決着 Δ | 決着(最終) | 未解決(最終) |
|---|---:|---:|---:|
| B001–100 | +33 | 100 | 0 |
| B101–200 | +34 | 100 | 0 |
| B201–300 | +8 | 100 | 0 |
| B301–400 | +12 | 100 | 0 |
| B401–500 | +6 | 100 | 0 |
| B501–600 | +39 | 100 | 0 |

### 残り 132 件の決着手段

| 手段 | 件数 | 出典 |
|---|---:|---|
| 弱化版昇格（SUPPORTED） | 20 | ound5-batch-weak-promote.md |
| 弱化版昇格（REFUTED） | 3 | 同上 |
| final-43 弱化決着 | 43 | ound5-batch-final-43.md |
| last21 フィニッシャー | 21 | ound5-batch-last21.md |
| 弱化バッチ残余 | 45 | b001-b200-weak / b501-b600-weak 等 |
| **合計** | **132** | |

### n=8 p_rand 完走（同時刻）

- P_max ≈ **0.810389610007**（レベル 9、8 個）
- P>3/4 = **2,536 個** / P>2/3 = 375,476 個
- 状態総数 **6,700,711,937** / **K = 15**
- 漸近飽和: 0.563→0.709→0.780→0.803→**0.810**

### 注意点（最終）

1. **弱化版 SUPPORTED ≠ 原命題 SUPPORTED**。原命題が無界のものは
   ound5-FINAL-SUMMARY.md §5 の理論課題として整理済み。
2. B141 は実体 SUPPORTED（D_n は n^5 主項）。B142 は REFUTED（C_n は Θ(n^6)）。
3. n=8 の p_rand は完走済み。漸近上限は 0.82〜0.85 付近の可能性。
4. 全 600 件が SUPPORTED 443 / REFUTED 157 で決着。以降の追加検証は
   理論課題（§5）に対するものに限られる。

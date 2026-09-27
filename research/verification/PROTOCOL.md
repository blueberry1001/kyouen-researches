# 共円ゲーム仮説バンク 検証プロトコル

対象: `research/hypothesis-bank-2026-09-27.md` の B001〜B300。
目的: 各仮説について、既存データ・小規模計算・理論的考察で**可能な限り**判定を付ける。

## ルール（標準）

- 盤 `B_n = {0,…,n−1}²`、点 id = `y*n+x`
- 禁止4点組: 整数行列式 `det[x²+y², x, y, 1]` の4行が0（共円または共線）
- 安全集合: 禁止4点組を部分集合に含まない占有集合
- 手番側の勝敗は通常プレイ（合法手なしの側が負け）
- `g(S)` = Grundy数、`g=0` が P 局面（手番側負け）
- 勝ち初手 `W_n = {p : g({p})=0}`（初手後に相手が P）

## 既知の確定事実（検証済み。再発見扱いしない）

| 事実 | 値・内容 | 出典 |
|---|---|---|
| 空盤勝者 n=1..9 | 先,先,先,後,先,先,後,後,先 | README / 証明書 |
| 禁止4点組数 F_n n=2..9 | 1, 14, 194, 826, 2491, 6364, 14564, 29152 | README |
| 空盤 g n=2..6 | 1, 1, 0, 1, 1 | CYCLE5 |
| 最大 nimber n=2..6 | 1, 1, 5, 6, 8 | CYCLE5 |
| n=2,3 の parity locking | g∈{0,1}、偶奇で P/N 決定 | CYCLE4/5 |
| n=5 勝ち初手 | 9/25 = 市松色（角除く） `{(x,y): x+y even} \ corners` | CYCLE4 |
| n=5 負け初手の g | すべて 3 | CYCLE5 F2 |
| n=4 全初手負け | 16/16 | CYCLE4 |
| n=6,9 全初手勝ち | 36/36, 81/81 | README / first-moves |
| K_6=11（極大464） | maxsafe_n6_K11.bin | CYCLE6 |
| K_7=14（極大16, 2軌道A/B） | maxsafe_n7_K14.bin, enum7 | CYCLE6 |
| K_7 は 1-swap 剛性 ρ=2 | 交換辺0 | CYCLE6 |
| K_8=15（15は存在、16は非発見） | cycle6-maxsafeset-n8-*.json | CYCLE6 |
| K_9 ≥ 17（証明書末端17石飽和） | cert terminal | F-A |
| 7×7 後手勝ち・最大配置2相 | A=中心あり, B=中心なし | FINAL_SELECTION |
| 9×9 中央初手は勝ち、全81勝ち | first-moves-9x9.csv | README |
| 5×5 J_5: 負け初手16点 | Pペア20本等 | cycle4-n5-two-stone-*.json |

## 判定ラベル（各仮説に必ず1つ）

| ラベル | 意味 |
|---|---|
| **REFUTED** | 反例を具体的に発見した（盤・配置を書く） |
| **SUPPORTED** | 検証可能な範囲で成立を確認（範囲を明記） |
| **PARTIAL** | 一部範囲で成立、一部未確認／弱い版のみ確認 |
| **INCONCLUSIVE** | 計算・考察したが判定不能 |
| **NOT-CHECKED** | 時間・計算資源で着手できなかった（理由を書く） |

## 検証の優先順位

1. **既存データ照合**: `night-research/*.json`, `cycle*-*.json`, `research/findings.md` にある確定結果と矛盾しないか
2. **小盤厳密計算**: n≤5 は完全列挙可能。n=6 は Grundy/極大集合の既存データあり。Python で追加計算する
3. **反例探索**: [全称] は最小の n から反例を探す。[存在] は小 n で証人を探す
4. **理論的整合**: 競合する仮説の対（B001/B002 など）の両立・排他を整理
5. **大胆な漸近予想**: 小 n の数値と整合するかだけ確認し、INCONCLUSIVE でよい

## 計算の指針

- 整数演算のみ（浮動小数禁止）。`det4` は `exact_structure_cycle4.py` を参照
- 点 id = `y*n+x`、bitmask で安全集合を表すと速い
- 既存モジュール: `night-research/exact_structure_cycle4.py`, `grundy_cycle5.py`, `cycle8_lib.py`
- 重い計算は n≤6 に限定。n≥7 の全探索は避ける（既存結果を読む）
- スクリプトは `research/verification/scripts/` に置く
- 各バッチの結果は `research/verification/batch-XX.md` に書く

## バッチ結果フォーマット

```markdown
# Batch XX: Baaa-Bbbb

## Baaa [種別] 概要
- 判定: **LABEL**
- 範囲: 何を計算/確認したか
- 証拠: 具体的な数値・配置・スクリプトパス
- メモ: 競合仮説・弱めた命題・次の手

（以下 Bごとに繰り返し）

## バッチ総括
- SUPPORTED x, REFUTED y, PARTIAL z, INCONCLUSIVE w, NOT-CHECKED v
- 最も有望な次の一手
```

## 共有作業ディレクトリ

- 出力: `research/verification/`
- スクリプト: `research/verification/scripts/`
- 既存データ: `night-research/`, `research/findings.md`, `docs/`
- Python: システムの `python` または `py`。重い計算は C++ を検討

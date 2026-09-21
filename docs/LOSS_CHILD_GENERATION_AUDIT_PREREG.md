# `loss_child` 生成規則監査メモ（holdout-v2 結果参照前の事前固定）

固定日: 2026-09-19
対象: `probe-two-stone-subsets` / `a367b5764029de0b1838298b3306e7ace253fcab`
範囲: ソース証明CSVと生成コードの参照のみ。holdout-v2 の probe・順位・ラベル結合結果は参照していない。

## 対象CSV

- `results/10x10/two-stone-90-61-child-proof.csv`（98行）
- `results/10x10/two-stone-90-66-child-proof.csv`（98行）

両CSVとも全行 `outcome=WIN`、`loss_child` 空欄なし、`visited/maxdepth/memo/seconds` 空欄である。
すなわち両CSVだけからは候補別探索コストも、複数LOSS候補の有無も直接読めない。

## 生成コードの所在

`a367b576` 時点のリポジトリ内には、これら2CSVの `loss_child` 列へ書き込む
専用生成スクリプトは存在しない。

- `git grep -n loss_child a367b576 -- *.py` の該当は、検証・監査・選抜・順位・分析側のみ。
- CSVを `loss_child` 付きで新規作成する `open(..., "w")` 経路は該当なし。
- 両CSVは `f22b72d` と `9ca5980` で結果物として一括追加されており、生成コマンドはコミットメッセージに残っていない。

したがって `loss_child` の代入箇所・候補列挙順・選択規則を、既存proofだけから一意に特定できない。

## 既知の複数経路

コード上、WIN親に対するLOSS witnessを決める経路は少なくとも2系統ある。

1. `cpp/solvers/parts/kyouen_solver_10_kyoenc4_resume_3.inc`
   `Solver::build_proof` の `winning` 分岐（10-22行）：
   - まず保存済み `winning_witness_log` を再利用し、合法ならそれを採用する。
   - なければ `legal` の raw昇順走査で最初にLOSSと判定された子を採用し、ログへ追記する。
2. `Solver::win`（32-38行）：
   - 子候補は `(cached LOSS, 未訪問, cached WIN)` の順、次に合法手数昇順、次に正準キー昇順でソートされる。
   - 探索順で最初にLOSSと確定した子から witness を復元し、ログへ追記する。
   - 証明ログは追記専用であり、同名正準WIN位置に複数witnessが現った場合は最初の保存が残り、`conflicts` として数えられる。

すなわち、同じ親でも witness ログ再利用の有無・履歴・メモ状態により
採用witnessが変わり得る。`docs/10X10_FOUR_STONE_SUBSETS_AND_PROOF.md` も
複数witnessの存在と「最初の保存を残す」運用を明記している。

## CSV上の傍証

- `loss_child` の重複がある（61側で12件分、66側で10件分の重複）。
  例: `0,1,10,13` は `0,1,13` と `0,10,13` の両親に対応。
- `state` を文字どおり包含しない `loss_child` が多数ある（61側45件、66側29件）。
  これは後の対称性監査により、正準化された親子関係としては正当であることが確認済みである。
  `scripts/check_canonical_loss_child.py` は両CSVとも `checked=196 failures=0`。
- D4正準な一手関係は各行ちょうど1通りにほぼ定まる（195/196行で一意、残り2行も2通り）。
- したがって「正準親子の構造」は確定しているが、「複数LOSS候補からどれを選んだか」はCSVに残っていない。

## 判定

上記より、要求された3分類では **C. 判定不能** とする。

- A（default順から独立）は否定できないが、証明もできない。
- B（default順に依存）も否定できないが、証明もできない。
- 既存proofだけからは選択規則を一意に追えない。

特に注意すべき点として、ここでいう「solver-default順」は holdout-v2 で凍結された
`children_*.txt` の行順（= raw合法手の盤面index昇順）であり、
solver内部DFSの動的探索順そのものではない。

## 評価への事前固定

Cのため、中立比較として扱わない。
監査時点では独立性を証明できていないため、保守側へ倒す。

> certified LOSS witness 自体が default由来である可能性を排除できないため、
> 主要比較は「中立なordering比較」ではなく、
> 「default由来の可能性があるwitnessを別orderingがどれだけ前へ移せるか」という
> 保守的評価として解釈する。

実験自体は中止しない。
ただし `first LOSS` とは呼ばず、完全な前方exact証明がない限り
`certified LOSS witness rank` と表記する。

## holdout-v2 凍結物への非接触確認

本メモは監査用worktree（`a367b576` の detached HEAD）での参照・検証のみで作成した。
次の凍結物は変更していない。

- `results/10x10/three-stone-probe-holdout-v2.csv`
- 1161-child universe（SHA `8cec2f9ae1bee65df13ed87b7f646e8c195ac29a444feb6e59d231e6c94c2a73`）
- batch manifest（SHA `086c4d226e4511350924d3f12a78bd5fc438df9c95c2eec780d0c364deb94a69`）
- score / K / probe budget / tie-break / witness選択のいずれも変更なし。
- holdout-v2 の結果CSV・順位・ラベル結合出力は参照していない。

## 次の未解決点

- `loss_child` の生成コマンド履歴が残っていないため、将来の証明CSVでは
  生成コマンド・solver commit・witnessログの有無・候補列挙順を同時に固定する必要がある。
- 本監査は `b5172a4` の旧結果（fixed median 3 / random median 6 / 50%改善など）を
  復活させるものではない。旧結果は主結果として再主張しない。

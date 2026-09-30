# B251の7×7全単独解除を除外

作成: 2026-09-30。**B251 PARTIALを維持。7×7の全6,364単独解除に勝者反転なし。**
原文の「ある盤で一つだけ禁止四点組を解除すると空盤勝者が変わる」という存在命題は未決着。
[6×6までの除外](round23-b251-six-by-six-exclusion.md)と合わせ、証人があるなら **n≥8** が必要になる。

## 全域被覆と二方式の勝敗計算

整数の四点行列式で7×7の禁止四点組6,364個を生成した。D4軌道は935個。
各軌道の代表だけを解除しても、全四点組の解除を対称性で漏れなく覆う。
標準空盤はP、単独解除した全935ゲームもPだった。

| 方法 | 完了代表 | 再帰で訪れた状態数の和 | 勝者反転 | UNKNOWN |
|---|---:|---:|---:|---:|
| 三点補完マスクによる増分合法手更新 | 935 | 16,583,889 | 0 | 0 |
| 円・直線の占有数による増分合法手更新 | 935 | 31,567,487 | 0 | 0 |

二方式は手の探索順も逆にした。P/Nを直接解いた数値で、真のGrundy値を計算したとは言わない。
状態数は各解除ゲームの探索数の合計で、標準ゲームの全局面数や異なる盤状態数ではない。
各代表の上限200万状態に達した場合はUNKNOWNにするが、最終の二走査では全件が上限前に完了した。

第一方式は解除した四点組の四つの三点補完だけを標準の補完表から除く。
第二方式は全1,625本の円・直線を使う。解除組を含む唯一の曲線に限り、
その組の三点が置かれたときは残り一点を許し、四点全部が置かれた後は同じ曲線の他点を禁止する。
それ以外の曲線では三石で残り全点を禁止する。

## 標準ゲームへの厳密な帰着

解除組qの未占有点が途中で違法になったら、以後それを置けない。
石を増やすだけのゲームでは違法点は再び合法にならないため、qの完成が以後不可能となる。
解除ゲームで標準と異なり得る禁止はqだけなので、その局面以降は標準ゲームと完全に一致する。
この条件ではqはまだ完成しておらず、その局面は標準でも安全である。
qを既に完成させた局面にはこの帰着を適用しない。

帰着後のP/Nは[round28](round28-seven-board-original-verdicts.md)で二方式による完全列挙を照合した
179,810,350安全局面の表から引いた。二つの解除ソルバはこの表と読取コードを共有するため、
表自体についてさらに別の全域検査を行った。

[検証器](scripts/round32_standard_pn_verify.cpp)は整数幾何の円・直線占有数から各局面の合法手を求め、
全局面について「Pなら全子N、Nなら少なくとも一子P」を確認した。
全層のP数もround28の真のmex分布と一致した。終局がPであることを含むこの局所条件と
有限の非循環性により、共有した表の勝敗が確定する。
[監査記録](round32_b251_n7_audited.json)には層ごとの占有集合・P/N表のSHA-256を保存した。
巨大な作業用バイナリはGitに入れず、再生成するソースを保存している。

初期の単純な探索順では78代表がUNKNOWNとなった。その未完了記録も残したが、除外の根拠には使わない。
後の探索順改善による全935代表の完了と、別方式の完了だけを今回の根拠とする。

## 再現（WSL、作業表は約1.62 GB）

round28の`level_0.occ`〜`level_14.occ`を再生成する必要がある場合は、
先に`bash research/verification/scripts/round28_run.sh 7`を実行する。
以下はリポジトリ直下のbashで実行する。`D`は作業表のディレクトリ。

```bash
set -euo pipefail
D=/home/yuubi/round28_n7
S=research/verification/scripts
V=research/verification
python3 "$S/round32_b251_input.py"
g++ -O3 -march=native -std=c++20 -fopenmp "$S/round32_standard_pn.cpp" -o "$D/pn"
OMP_NUM_THREADS=8 "$D/pn" 7 "$D"
g++ -O3 -march=native -std=c++20 -fopenmp "$S/round32_standard_pn_verify.cpp" -o "$D/pn_check"
OMP_NUM_THREADS=8 "$D/pn_check" "$V/round32_b251_n7_input.txt" "$D" "$V/round32_standard_pn_verified.json"
g++ -O3 -march=native -std=c++20 "$S/round32_b251_accelerated.cpp" -o "$D/quad_scan"
"$D/quad_scan" "$V/round32_b251_n7_input.txt" "$D" "$V/round32_b251_n7_scan.json" 2000000
g++ -O3 -march=native -std=c++20 "$S/round32_b251_curves.cpp" -o "$D/curve_scan"
"$D/curve_scan" "$V/round32_b251_n7_input.txt" "$D" "$V/round32_b251_n7_curves.json" 2000000
python3 "$S/round32_b251_audit.py" "$D"
```

- [全幾何・D4被覆](round32_b251_n7_geometry.json)
- [第一方式](round32_b251_n7_scan.json)、[第二方式](round32_b251_n7_curves.json)
- [共有標準表の全局面証明検査](round32_standard_pn_verified.json)
- [未完了だった初期走査](round32_b251_n7_budget_probe.json)

# B065: 二点競合なし・g≥4の証人を7×7まで全域除外

作成: 2026-09-30。**B065原文PARTIAL。**
存在証人は見つからず、成立するならn≥8が必要となった。全盤での反証とは扱わない。

まず|L|≤3なら、mexの基本上界g≤|L|よりg≥4は不可能。
0・1石層は既存の全域mex表と小盤の独立再計算で全てg≤3を確認した。
残る|S|≥2かつ|L|≥4を、4×4〜7×7の全安全局面から抽出した。

| 盤 | 全安全集合 | P(S)が空の候補数 | 候補の最大g |
|---|---:|---:|---:|
| 4×4 | 5,811 | 0 | 該当なし |
| 5×5 | 151,394 | 0 | 該当なし |
| 6×6 | 5,081,289 | 2,476 | 1 |
| 7×7 | 179,810,350 | 137,292 | 3 |

7×7の候補の合法点数は4〜7個で、16個を超えた未計算候補は0。
候補のg分布は0:63,332、1:73,896、2:32、3:32。g≥4は0だった。
1×1〜3×3も全安全局面の独立全域mex再計算でg≤3を確認した。

## 二方式の完全一致

[第一方式](scripts/round39_empty_pair_search.cpp)は、追加点をID昇順にしたDFSで各安全集合を一度ずつ生成。
三点補完マスクで合法点を増分更新し、石の各ペアを含む禁止四点組の残り二点がLに含まれるかで
競合辺の有無を判定した。候補ではLに制限した全残余辺から全部分集合DPの真のmexを求めた。

[第二方式](scripts/round39_curve_census.cpp)は、別に生成・検証した安全集合の全層を読み込んだ。
整数幾何を生成し直し、円・直線Cについて|S∩C|=2かつ|L∩C|≥2なら二点競合がある、という
曲線占有数の条件で候補を判定した。
候補のLは曲線占有数で再照合し、値は残余辺を使わず、石追加後の曲線三石飽和で合法点を更新する
メモ再帰で求めた。候補数、Lの点数分布、g分布の全項目が第一方式と一致した。

[監査](scripts/round39_audit.py)はこの一致に加えて、1・2・3・5×5の全域曲線再帰で0・1石層を再検算。
4・6・7×7の既存独立mex表で同じ層を確認し、除外した層にg≥4がないことも閉じた。
入力幾何、両方式、既存表のSHA-256を[監査記録](round39_empty_pair_audited.json)に保存した。

## 二点競合なしでg=3を達成する7×7の中盤証人

    Sの点ID=[2,4,6,9,12,27,36]
    Lの点ID=[29,31,35,38,43,46]
    R={{29,31,38}, {31,43,46}, {31,35,38,43}}

点IDはx+7y。この局面はg=3で、二点辺は0。
全64拡張の安全性を曲線と極小残余族で照合し、全49安全拡張のmexも保存した。
これはB065の閾値4には届かないため、原文の証人として数えない。

## 再現（WSL）

    python research/verification/scripts/round39_geometry_inputs.py
    g++ -O3 -std=c++20 research/verification/scripts/round39_empty_pair_search.cpp -o /home/yuubi/round28_n7/round39_search
    /home/yuubi/round28_n7/round39_search 7 research/verification/round39_empty_pair_n7_search.json 16
    g++ -O3 -std=c++20 -fopenmp research/verification/scripts/round39_curve_census.cpp -o /home/yuubi/round28_n7/round39_curves
    OMP_NUM_THREADS=8 /home/yuubi/round28_n7/round39_curves research/verification/round39_n7_input.txt /home/yuubi/round28_n7 research/verification/round39_empty_pair_n7_curves.json
    python research/verification/scripts/round39_audit.py

第二方式の7×7作業層はround28の保存済み`level_*.occ`を使う。
5・6×6の作業層は`round5_prand_stream.cpp --enum`で新たに生成した。
大きな作業バイナリはGitに保存せず、生成器と層数の記録を保存する。

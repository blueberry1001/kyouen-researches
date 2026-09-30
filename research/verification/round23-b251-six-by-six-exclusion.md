# B251の6×6全単独解除を除外

作成: 2026-09-30。**B251 PARTIALを維持。6×6の全2,491単独解除に反転なし。**
原文 [B251](../hypothesis-bank-2026-09-27.md) は、ある正方形盤で禁止四点組を一つだけ解除すると
標準版と空盤勝者が反転する、という存在命題である。
この有限の不存在を全盤サイズの反証とは扱わない。

## 全域探索と異なる方式の再検算

6×6の全C(36,4)組から整数行列式で標準2,491組を生成した。
四点組のD4軌道は389個。全2,491組がちょうど一軌道に入り、各軌道の代表を一つずつ解除して解いた。
標準版は先手勝ち、全389代表の単独解除版も先手勝ち。

第一の[ソルバ](scripts/round23_b251_single_scan.cpp)は、候補点ごとに保持四点組の三点補完リストを走査する。
第二の[独立ソルバ](scripts/round23_b251_incremental.cpp)は、三点をキーにする補完ビットマスクを使い、
追加した石と既存石の全ペアから合法点集合を増分更新する。手の探索順も逆にしている。
いずれも勝敗P/Nを直接評価し、boolを真のGrundy値と呼ばない。

| 検査 | 単独解除の代表数 | 証明探索状態の合計 | 勝者反転 | 打切り |
|---|---:|---:|---:|---:|
| 三点リストによる候補点判定 | 389 | 62,862,518 | **0** | **0** |
| 補完マスクによる増分更新 | 389 | 63,129,426 | **0** | **0** |

状態の合計は各解除ゲームの勝敗証明で訪れた状態数の和である。
全安全集合数や、重複を除いた異なる盤状態数ではない。
各ゲームでは最大1,000万状態でUNKNOWNにする上限を設けたが、全てその前に正常終了した。
双方の全389結果が一致した。

[監査コード](scripts/round23_b251_audit.py)は平行移動後の3×3行列式ではなく、
元座標の[x²+y²,x,y,1]の4×4行列式でも禁止組を再生成して一致を確認した。
全D4画像・軌道の被覆・代表対応・二つのソルバの完了判定も検査した。

以前のround5はn=6の8標本だけだったので、今回初めて6×6の全単独解除を閉じた。
n≤5の既存全域除外と合わせると、B251の存在証人があるなら**n≥7**が必要になる。
n≥7の一般不存在や、7×7の単独解除の勝敗はこの計算では決まっていない。

## 再現

    python research/verification/scripts/round23_b251_input.py
    g++ -O3 -std=c++17 -Wall -Wextra research/verification/scripts/round23_b251_single_scan.cpp -o research/verification/scripts/round23_b251_single_scan.exe
    research/verification/scripts/round23_b251_single_scan.exe research/verification/round23_b251_n6_input.txt research/verification/round23_b251_n6_scan.json 10000000
    g++ -O3 -std=c++17 -Wall -Wextra research/verification/scripts/round23_b251_incremental.cpp -o research/verification/scripts/round23_b251_incremental.exe
    research/verification/scripts/round23_b251_incremental.exe research/verification/round23_b251_n6_input.txt research/verification/round23_b251_n6_incremental.json 10000000
    python research/verification/scripts/round23_b251_audit.py

- [幾何・全D4軌道](round23_b251_n6_geometry.json)
- [第一ソルバ](round23_b251_n6_scan.json)、[第二ソルバ](round23_b251_n6_incremental.json)
- [全域照合・ソースと入力SHA-256](round23_b251_n6_audited.json)

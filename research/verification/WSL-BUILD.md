# WSL C++ ビルド環境（第4回の前提）

作成: 2026-09-27。

## 何が問題だったか

第3回の未解決 359 件のうち、相当数が**計算資源**で止まっていた。
Windows 環境には C++ コンパイラが 1 つも無かった:

```
g++ -> NOT FOUND
cl  -> NOT FOUND
clang++ -> NOT FOUND
gcc -> NOT FOUND
cmake -> C:\Program Files\CMake\bin\cmake.exe   （コンパイラではない）
```

そのため 8×8 の 8 石極大全列挙（`C(64,8) ≈ 4.4×10⁹`）は
pure-Python では原理的に実行不能だった。

## 解決

**WSL2 の Ubuntu に g++ 13.3.0 がある。** スケールは **16 コア / 19 GB RAM**。

```
wsl -d Ubuntu -- bash -lc "g++ --version"
# g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
```

リポジトリは `/mnt/d/` 経由で直接見える（コピー不要）:

```
REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
```

自己検査: `scripts/wsl_check.sh`（`wsl -d Ubuntu -- bash $REPO/research/verification/scripts/wsl_check.sh`）

## 使い方

```bash
wsl -d Ubuntu -- bash -c "cd $REPO/research/verification/scripts && \
    g++ -O2 -march=native -std=c++20 -pthread -o /tmp/solver solver.cpp && \
    /tmp/solver"
```

推奨フラグ:

| フラグ | 理由 |
|---|---|
| `-O2` | 標準。`-O3` はこのコードでは効果の割にコンパイルが遅い |
| `-march=native` | `__builtin_popcountll` などの POPCNT 命令を使う（16 コア機では有効） |
| `-std=c++20` | `std::bit_cast` などが使えて writing が楽 |
| `-pthread` | 並列化する場合 |

**WSL 里有 numpy 无** → 日本語で: **WSL 側には numpy が無い**
（`ModuleNotFoundError: No module named 'numpy'`）。
numpy が必要な場合は Windows 側の Python を使うか、
`wsl -d Ubuntu -- bash -c "pip3 install --user numpy"`（要ネットワーク）。
数値だけ数百個の処理なら numpy は不要で、C++ の標準ライブラリで足りる。

## 時間の注意

WSL2 の起動オーバーヘッドが数秒ある。**1 回の呼び出しで複数の Jobs を
まとめて回す**のが効率的。Agents は长时间（数十分〜数時間）の
`wsl -- bash -c "..."` を 1 ジョブとして走らせ、`run_in_background=true` で待つこと。

## 並列化

16 コアある。`#pragma omp parallel for` を使うなら `-fopenmp` を追加。
スレッドを手で書くより OpenMP の方がコード量が少なくて済む。

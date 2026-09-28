import io
p = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round4-batch-b168-b227.md"
s = open(p, encoding="utf-8").read()
i = s.index("## ")
new = """## 途中で見つけた実装上の重要な誤り（自分の実装の記録）

第4回の C++ ソルバを最初に書いたとき、Grundy 値を**ボトムアップ**
（k=0 から上向き、g(∅)=0 を初期値）で漸化させていた。
正しい漸化は `g(S) = mex{ g(S ∪ {p}) : p 合法 }`、`g(終端) = 0` で、これは
**トップダウン**（k=K から下向き）で計算しなければならない。
ボトムアップだと `g({p}) = mex{0} = 1`、`g(∅) = mex{1} = 0` という
**偽の不動点**が得られ、全ての単独石に g=1 を渡して `W_n = ∅` になってしまう
（`g(∅)` は自由変数ではない。終端層の値から決まる）。
本回の C++ はトップダウンに直し、`g0 = 1,1,0,1,1`（n=2..6）、
`W_5 = {2,6,8,10,12,14,16,18,22}`（9 点 = 市松色 - 角、PROTOCOL と一致）で
**PROTOCOL の確定値を再現した**。
なお `round3_chunk3_core.py` の `solve_pn` / `solve_gn` はメモ化再帰
（`ev(occ)` が到達性で下降）であり本来就トップダウンなので、
先行ワーカーの実装自体にはこの誤りはない。

"""
s = s[:i] + new
open(p, "w", encoding="utf-8").write(s)
print("ok")

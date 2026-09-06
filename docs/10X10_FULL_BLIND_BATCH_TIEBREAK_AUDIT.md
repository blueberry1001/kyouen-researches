# 10×10 blind full-children cross-batch tie-break audit

最終更新: 2026-09-07

## 発見

`resume-full-blind-children` で全batchを結合して blind probe の順位を再集計できるようになったが、既存の `scripts/analyze_probe_blind_validation.py` には、batch0だけでは表面化しない cross-batch tie-break の問題がある。

`collect_batches()` は各batchの child order を

```text
(batch_index, move_index_within_batch, state)
```

として連結する。solver既定順自体はこの連結順なので正しい。

一方 fixed rule の入力では

```python
fixed_rule_order([(m, s) for _, m, s in children_with_exact], ...)
```

と `batch_index` を捨てる。

`fixed_rule_order()` の同値feature tie-breakは

```python
return (sort_val, move)
```

なので、`move` は各batchで0から再開する。

したがって、異なるbatchに同じprobe feature値を持つchildがあると、solver既定順を保つtie-breakではなく、batch内move indexで再配列される。

例えば同じfeature値の

```text
batch0: move0, move1, move2
batch1: move0, move1, move2
```

を連結した本来のsolver順は

```text
b0m0, b0m1, b0m2, b1m0, b1m1, b1m2
```

だが、現行keyでは

```text
b0m0, b1m0, b0m1, b1m1, b0m2, b1m2
```

となり得る。

これは固定規則の定義そのものを変える。特に `memo` は整数値なのでtieが起こり得る。

## 影響範囲

- batch0だけの既報7親には影響しない。batchが1個ならlocal move indexとglobal solver positionは一致する。
- これから行う全children再集計には影響し得る。
- probe feature値がすべて異なる親では影響しない。
- 同値feature値が複数batchにまたがる親では first LOSS rank が変わる可能性がある。

よって、全children exact分類の結果を評価する前に修正すべきである。

## 修正方針

fixed ruleの最終tie-breakを `move_index_within_batch` ではなく、**全batch連結後のglobal solver position** にする。

概念的には

```python
children_with_exact = [
    (global_pos, batch_index, move_index, state)
    for global_pos, (batch_index, move_index, state)
    in enumerate(children_with_exact_raw)
]

solver_order = [(global_pos, state) for global_pos, _, _, state in children_with_exact]
fixed_order = fixed_rule_order(
    [(global_pos, state) for global_pos, _, _, state in children_with_exact],
    all_probe,
    feature,
    direction,
)
```

とし、`fixed_rule_order()` の第1要素を「tie-break用のsolver global position」と解釈する。

child-level出力には調査可能性のため

```text
batch_index
batch_move_index
global_solver_position
```

を分けて残すのが望ましい。

## 回帰試験

最低限、人工データで次を固定する。

probe featureが全て同値のとき、fixed orderは全batchを連結したsolver default orderと完全一致しなければならない。

```text
input solver order:
  b0m0 b0m1 b0m2 b1m0 b1m1 b1m2

expected fixed order on all ties:
  b0m0 b0m1 b0m2 b1m0 b1m1 b1m2
```

さらに、featureの一部だけが同値の場合も、同値群内では元のglobal solver orderを保持することを確認する。

## 追加の完全性条件

全children再解析で `exact_complete=true` を主結果として扱う場合、probe側も同様に完全であるべきである。

現在はprobe rowが欠けたchildに対して欠損値を末尾へ送るfallbackがあるため、完全exact集合なのにprobeが一部欠損した状態でもfixed rankを生成できてしまう。

したがってfull-children確定解析では

```text
probe_complete = (# probe rows for evaluated children == # evaluated children)
```

を保存し、`exact_complete && !probe_complete` の親はconfirmatory ranking集計から除外するかエラーにするのが安全である。

## 結論

全children exact solveを始めた方針自体は正しい。ただし、その結果を現行解析器へそのまま流すと、batch境界をまたぐprobe同値値のtie-breakで事前固定規則と違う順位を作る可能性がある。

優先順位は

1. global solver position tie-breakへ修正
2. probe completeness assertionを追加
3. 人工cross-batch tie回帰試験
4. その後に旧7親の全children結果を再集計

とする。

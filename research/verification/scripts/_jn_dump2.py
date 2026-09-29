import json
from collections import Counter

p = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_jn_followup.json"
d = json.load(open(p))
b = d["b312"]
print("n_union single:", b["singles"]["n_union"])
print("n_inter single:", b["singles"]["n_inter"])
print("deg_sum single:", b["singles"]["deg_sum"])
print("TD n_union hist", Counter(r["n_union"] for r in b["td_rows"]))
print("nonTD n_union hist", Counter(r["n_union"] for r in b["nontd_rows"]))
print("TD n_inter hist", Counter(r["n_inter"] for r in b["td_rows"]))
print("nonTD n_inter hist", Counter(r["n_inter"] for r in b["nontd_rows"]))
print("TD deg_sum hist", Counter(r["deg_sum"] for r in b["td_rows"]))
print("nonTD deg_sum hist", Counter(r["deg_sum"] for r in b["nontd_rows"]))
print("TD n_union by d2", Counter((r["d2"], r["n_union"]) for r in b["td_rows"]))
print("nonTD n_union by d2", Counter((r["d2"], r["n_union"]) for r in b["nontd_rows"]))
# sample rows
print("TD sample", b["td_rows"][0])
print("nonTD sample", b["nontd_rows"][0])

# n=5 two-stone / one-stone detail for B318 / B320
a5 = d["n_analyses"]["5"]
print("n5 one", a5["one_stone_hist"], "two", a5["two_stone_hist"], "P", a5["n_P_pairs"], "iso", a5["n_isolated_vertices_J"])
a4 = d["n_analyses"]["4"]
print("n4 one", a4["one_stone_hist"], "two", a4["two_stone_hist"], "P", a4["n_P_pairs"], "iso", a4["n_isolated_vertices_J"])
a2 = d["n_analyses"]["2"]
print("n2 one", a2["one_stone_hist"], "two", a2["two_stone_hist"], "P", a2["n_P_pairs"])
a3 = d["n_analyses"]["3"]
print("n3 one", a3["one_stone_hist"], "two", a3["two_stone_hist"], "P", a3["n_P_pairs"])

# all-layer k>=sigma consecutive?
print("=== k>=sigma consecutive / nonpow2 ===")
for n in "2345":
    a = d["n_analyses"][n]
    sig = a["sigma"]
    for k, v in a["all_layer_holes"].items():
        if int(k) >= sig:
            print(f"n={n} k={k} bound={v['bound']} missing={v['missing']} cons={v['consecutive_pairs']} nonpow2={v['positive_missing_non_pow2']} posmiss={v['positive_missing']}")

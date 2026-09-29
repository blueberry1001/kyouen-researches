import json
p = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_jn_followup.json"
d = json.load(open(p))
print("=== SUMMARY ===")
print(json.dumps(d["summary"], indent=2)[:4000])
print("=== B312 best pair ===")
bp = d["b312"]["best_pair"]
print("keys", bp["keys"], "n_mixed", bp["n_mixed"])
print("td_only", bp["td_only"])
print("nontd_only", bp["nontd_only"])
print("=== B312 singles ===")
for k, v in d["b312"]["singles"].items():
    print(k, "perfect" if v["perfect"] else f"mixed={v['mixed_values'][:8]}")
print("=== all-layer consecutive? ===")
for n in "2345":
    a = d["n_analyses"][n]
    print(f"n={n} sigma={a['sigma']} sigma_holes={a['sigma_layer_holes']}")
    for k, v in a["all_layer_holes"].items():
        if v["missing"] or v["consecutive_pairs"] or v["positive_missing_non_pow2"]:
            print(f"  k={k} bound={v['bound']} missing={v['missing']} cons={v['consecutive_pairs']} nonpow2={v['positive_missing_non_pow2']}")
print("=== B320 ===")
b = d["b320"]
print("mixed_keys", b["mixed_keys"])
print("acc", b["accuracy"])
for k, v in b["mixed_detail"].items():
    print("key", k, "nP", v["n_P"], "nN", v["n_nonP"])
    st = v["stats"]
    for feat in ["has0", "has1", "n_child", "child_mex", "child_min", "child_max"]:
        print(" ", feat, "P", st[feat]["P"], "nonP", st[feat]["nonP"])
    print("  child_sets_P", st["child_sets_P"][:6])
    print("  child_sets_nonP", st["child_sets_nonP"][:6])
    print("  R1", st["R1_0_not_in_children_iff_P"], "mex_check", st["mex_eq_g2_check"])

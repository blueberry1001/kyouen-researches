import re
base = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification"

s = open(base + r"\round4_tstar_n45.json", encoding="utf-8").read()
i = s.find('"n=5"')
print("n=5 section:")
print(s[i:i+1500])
print("========")
s2 = open(base + r"\round4_tstar_n67.json", encoding="utf-8").read()
i2 = s2.find('"n=6"')
print("n=6 section:")
print(s2[i2:i2+1500])

print("======== chunk6 keys detail")
import json
d = json.loads(open(base + r"\round3_chunk6_wft.json", encoding="utf-8").read())
for k, v in d.items():
    if isinstance(v, dict):
        print(k, list(v.keys())[:25])
        for kk in v:
            if kk in ("Tstar_empty", "WFT_empty", "g_empty", "n_reachable", "B331", "B335", "B333", "B334"):
                print("  ", kk, v[kk] if not isinstance(v[kk], dict) else {x: v[kk][x] for x in list(v[kk])[:8]})
    else:
        print(k, type(v).__name__)

import re, json, sys

base = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification"

def dump_tstar(fn):
    s = open(base + "\\" + fn, encoding="utf-8").read()
    print("===", fn, "len", len(s))
    for m in re.finditer(r'"(Tstar_empty|WFT_empty|g_empty|safe_sets_total|K_n|V|F_n|T_size_hist|WFT_size_hist|Tstar_size_hist)"\s*:\s*[^,\n]+', s):
        print(m.group(0))
    # board-level keys
    for m in re.finditer(r'"n=(\d+)"\s*:\s*\{', s):
        print("board", m.group(1), "at", m.start())
    # find any Tstar/WFT empty arrays
    for m in re.finditer(r'"(Tstar_empty|WFT_empty)"\s*:\s*(\[[^\]]*\])', s):
        print(m.group(1), "=", m.group(2))

dump_tstar("round4_tstar_n45.json")
dump_tstar("round4_tstar_n67.json")

# round3_chunk6_wft keys
s = open(base + r"\round3_chunk6_wft.json", encoding="utf-8").read()
print("=== round3_chunk6_wft len", len(s))
try:
    d = json.loads(s)
    print("keys", list(d.keys()))
except Exception as e:
    print("json err", e)
    print(s[:500])

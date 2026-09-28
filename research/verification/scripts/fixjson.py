"""C++ が出力した JSON のカンマ/改行の体裁だけを整え、検証する（数値は変えない）。"""
import json, re, sys

p = sys.argv[1]
lines = open(p, encoding='utf-8').read().split('\n')
out = []
for ln in lines:
    t = ln.strip()
    if t == ',':
        continue                      # 孤立したカンマ行は落とす
    out.append(ln)
s = '\n'.join(out)
s = re.sub(r',([,])', r'\1', s)                       # ,, -> ,
s = re.sub(r'\{\s*,', '{', s)                         # {, -> {
# 閉じ括弧行の次 Garré にキー行があるのにカンマが無い場合のみ挿入
fixed = []
for i, ln in enumerate(s.split('\n')):
    fixed.append(ln)
lines2 = fixed
for i in range(len(lines2) - 1):
    a = lines2[i].rstrip()
    b = lines2[i + 1].strip()
    if a.endswith('}') and not a.endswith(',') and b.startswith('"') and '"' in b and ':' in b:
        lines2[i] = a + ','
s = '\n'.join(lines2)
s = re.sub(r',\s*\}\s*$', '\n}', s)
d = json.loads(s)
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print("fixjson OK, keys =", list(d.keys()))

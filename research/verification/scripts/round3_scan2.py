import re
import glob
import os
from collections import Counter

os.chdir(os.path.dirname(os.path.abspath(__file__)))
files = sorted(glob.glob("../batch-*.md")) + sorted(glob.glob("../round2-batch-*.md"))

strict = re.compile(r"^##\s+(B\d{3})\b")
loose = re.compile(r"^#{1,6}\s*(B\d{3})\b")

s_ids, l_ids = [], []
levels = Counter()
for f in files:
    for line in open(f, encoding="utf-8"):
        m = loose.match(line)
        if m:
            l_ids.append(m.group(1))
            levels[line[: line.index("#") + 1] and len(line) - len(line.lstrip("#"))] += 1
        m2 = strict.match(line)
        if m2:
            s_ids.append(m2.group(1))

print("loose", len(l_ids), "unique", len(set(l_ids)))
print("strict", len(s_ids), "unique", len(set(s_ids)))
print("heading levels:", dict(levels))
missing = sorted(set(l_ids) - set(s_ids))
print("missed by strict:", len(missing), missing[:20])

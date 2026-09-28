import re
import glob
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
files = sorted(glob.glob("../batch-*.md")) + sorted(glob.glob("../round2-batch-*.md"))
for f in files:
    t = open(f, encoding="utf-8").read()
    ids = re.findall(r"^#{1,6}\s*(B\d{3})\b", t, re.M)
    labs = re.findall(r"判定\s*[:：]", t)
    print(f"{os.path.basename(f):24s} headings={len(ids):4d} uniq={len(set(ids)):4d} labels={len(labs):4d}")

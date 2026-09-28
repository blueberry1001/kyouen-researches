"""Find and strip round3 sections that duplicate another round3 file.

Only keeps the first writer (alphabetical file order); later duplicates are
reported so a human/agent can fix, or the section is auto-marked.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW = sorted(ROOT.glob("round3-batch-*.md"))
HEAD = re.compile(r"^#{1,6}\s*(B\d{3})\b")

owner = {}
for f in NEW:
    cur = None
    for line in f.read_text(encoding="utf-8").splitlines():
        m = HEAD.match(line)
        if m:
            cur = m.group(1)
            owner.setdefault(cur, []).append(f.name)

dups = {k: v for k, v in owner.items() if len(v) > 1}
print("duplicate ids:", len(dups))
for k, v in sorted(dups.items()):
    print(f"  {k}: {v}")

"""Show the full label trajectory for specific ids across all files."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAD = re.compile(r"^#{1,6}\s*(B\d{3})\b")
LABEL = re.compile(r"判定\s*[:：]\s*\*{0,2}([A-Z\-]+)")

targets = set(sys.argv[1:]) or {"B501", "B502"}
ORIG = sorted(ROOT.glob("batch-*.md")) + sorted(ROOT.glob("round2-batch-*.md"))
NEW = sorted(ROOT.glob("round3-batch-*.md"))

for t in sorted(targets):
    print(f"===== {t} =====")
    for group, files in (("orig", ORIG), ("round3", NEW)):
        for f in files:
            cur = None
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                m = HEAD.match(line)
                if m:
                    cur = m.group(1)
                    continue
                if cur == t:
                    lm = LABEL.search(line)
                    if lm:
                        print(f"  [{group:6s}] {f.name}:{i}  {lm.group(1)}")
                        cur = None
    print()

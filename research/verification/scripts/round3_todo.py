import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG = sorted(ROOT.glob("batch-*.md")) + sorted(ROOT.glob("round2-batch-*.md"))
NEW = sorted(ROOT.glob("round3-batch-*.md"))
HEAD = re.compile(r"^#{1,6}\s*(B\d{3})\b")
LABEL = re.compile(r"判定\s*[:：]\s*\*{0,2}([A-Z\-]+)")
UNRES = {"PARTIAL", "INCONCLUSIVE", "NOT-CHECKED"}

orig = {}
for f in ORIG:
    cur = None
    for line in f.read_text(encoding="utf-8").splitlines():
        m = HEAD.match(line)
        if m:
            cur = m.group(1)
            orig.setdefault(cur, None)
            continue
        if cur and orig[cur] is None:
            lm = LABEL.search(line)
            if lm:
                orig[cur] = lm.group(1)

covered = set()
for f in NEW:
    for line in f.read_text(encoding="utf-8").splitlines():
        m = HEAD.match(line)
        if m:
            covered.add(m.group(1))

unres = {b for b, l in orig.items() if l in UNRES}
print(f"originally unresolved: {len(unres)}")
print(f"covered by round3:     {len(unres & covered)}")
todo = sorted(unres - covered, key=lambda b: int(b[1:]))
print(f"TODO:                  {len(todo)}")


def rng(nums):
    if not nums:
        return "-"
    parts, s, p = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == p + 1:
            p = n
            continue
        parts.append((s, p))
        s = p = n
    parts.append((s, p))
    return ", ".join(f"B{a:03d}" if a == b else f"B{a:03d}-B{b:03d}" for a, b in parts)


print()
print(rng([int(b[1:]) for b in todo]))
print()
CH = 20
for i in range(0, len(todo), CH):
    ch = sorted(int(b[1:]) for b in todo[i:i + CH])
    print(f"### grp{i // CH + 1} ({len(ch)}): {rng(ch)}")

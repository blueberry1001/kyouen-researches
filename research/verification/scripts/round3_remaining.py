import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG = sorted(ROOT.glob("batch-*.md")) + sorted(ROOT.glob("round2-batch-*.md"))
NEW = sorted(ROOT.glob("round3-batch-*.md"))
HEAD = re.compile(r"^#{1,6}\s*(B\d{3})\b")
UNRES = {"PARTIAL", "INCONCLUSIVE", "NOT-CHECKED"}

orig = set()
for f in ORIG:
    for line in f.read_text(encoding="utf-8").splitlines():
        m = HEAD.match(line)
        if m:
            orig.add(m.group(1))

covered = set()
for f in NEW:
    for line in f.read_text(encoding="utf-8").splitlines():
        m = HEAD.match(line)
        if m:
            covered.add(m.group(1))

remaining = sorted(int(b[1:]) for b in (orig - covered))
print(f"remaining: {len(remaining)}")


def rng(nums):
    parts, s, p = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == p + 1:
            p = n
            continue
        parts.append((s, p))
        s = p = n
    parts.append((s, p))
    return ", ".join(f"B{a:03d}" if a == b else f"B{a:03d}-B{b:03d}" for a, b in parts)


print(rng(remaining))
print()
# split into chunks of <=20 for finer agents
CH = 20
for i in range(0, len(remaining), CH):
    ch = remaining[i:i + CH]
    print(f"### grp{i // CH + 1} ({len(ch)}): {rng(ch)}")

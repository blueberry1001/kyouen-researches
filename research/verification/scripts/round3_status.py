"""Count verdict labels across original + round3 batch files.

Also detect duplicate coverage (same ID written by two round3 files).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG = sorted(ROOT.glob("batch-*.md")) + sorted(ROOT.glob("round2-batch-*.md"))
NEW = sorted(ROOT.glob("round3-batch-*.md"))

HEAD = re.compile(r"^#{1,6}\s*(B\d{3})\b")
LABEL = re.compile(r"判定\s*[:：]\s*\*{0,2}([A-Z\-]+)")

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

new = {}
dupes = []
for f in NEW:
    cur = None
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines()):
        m = HEAD.match(line)
        if m:
            cur = m.group(1)
            if cur in new:
                dupes.append((cur, new[cur][0], f.name))
            new.setdefault(cur, (f.name, None, i + 1))
            continue
        if cur and new[cur][1] is None:
            lm = LABEL.search(line)
            if lm:
                rec = new[cur]
                new[cur] = (rec[0], lm.group(1), rec[2])

print(f"original files: {len(ORIG)}  ids: {len(orig)}")
print(f"round3 files:   {len(NEW)}  ids: {len(new)}")
if dupes:
    print("DUPLICATE coverage:")
    for d in dupes:
        print("  ", d)

UNRES = {"PARTIAL", "INCONCLUSIVE", "NOT-CHECKED"}
changed, still = [], []
for bid in sorted(new, key=lambda b: int(b[1:])):
    old, (fname, newlabel, line) = orig.get(bid), new[bid]
    if newlabel is None:
        still.append((bid, old, None, "NO LABEL"))
        continue
    if old in UNRES and newlabel not in UNRES:
        changed.append((bid, old, newlabel, fname))
    else:
        still.append((bid, old, newlabel, fname))

print()
print(f"=== DECIDED (unresolved -> SUPPORTED/REFUTED): {len(changed)} ===")
for bid, old, nl, f in changed:
    print(f"  {bid}: {old:13s} -> {nl:11s} [{f}]")

print()
print(f"=== STILL UNRESOLVED: {len(still)} ===")
for bid, old, nl, f in still:
    tag = "NO-LABEL!" if nl is None else nl
    print(f"  {bid}: prev={old:13s} now={tag:13s} [{f}]")

# global unresolved total
covered = set(new)
remaining = sorted(set(b for b, l in orig.items() if l in UNRES) - covered,
                   key=lambda b: int(b[1:]))
print()
print(f"=== NOT YET WRITTEN AT ALL: {len(remaining)} ===")


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


print(rng([int(b[1:]) for b in remaining]))

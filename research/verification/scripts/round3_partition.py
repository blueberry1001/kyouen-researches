import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "round3_unresolved.json").read_text(encoding="utf-8"))
ids = sorted(int(k[1:]) for k in data)
ids = [i for i in ids if i != 116]  # F-BG settled B116 (min cover = 21)

TIER1 = [501, 502, 371, 372, 373, 374, 375, 378, 380,
         451, 452, 453, 454, 455, 456, 457, 475, 476, 591, 592]
rest = [i for i in ids if i not in TIER1]


def fmt(nums):
    parts, start, prev = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        parts.append((start, prev))
        start = prev = n
    parts.append((start, prev))
    return ", ".join(f"B{a:03d}" if a == b else f"B{a:03d}-B{b:03d}" for a, b in parts)


print("tier1", len(TIER1), fmt(TIER1))
print("rest", len(rest))

# contiguous split of the rest into balanced chunks
TARGET = 45
chunks, cur = [], []
for i in rest:
    cur.append(i)
    if len(cur) >= TARGET:
        chunks.append(cur)
        cur = []
if cur:
    chunks.append(cur)
for n, ch in enumerate(chunks, 1):
    print(f"--- chunk {n} ({len(ch)}) ---")
    print(fmt(ch))

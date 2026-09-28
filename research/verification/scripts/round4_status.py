"""Measure round4 progress: label movement vs round3, per file."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R3 = sorted(ROOT.glob("round3-batch-*.md"))
R4 = sorted(ROOT.glob("round4-batch-*.md"))
HEAD = re.compile(r"^#{1,6}\s*(B\d{3})\b")
LABEL = re.compile(r"判定\s*[:：]\s*\*{0,2}([A-Z\-]+)")
RANK = {"SUPPORTED": 4, "REFUTED": 4, "PARTIAL": 2, "INCONCLUSIVE": 1, "NOT-CHECKED": 0}
UNRES = {"PARTIAL", "INCONCLUSIVE", "NOT-CHECKED"}


def collect(files):
    out = {}
    for f in files:
        cur = None
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            m = HEAD.match(line)
            if m:
                cur = m.group(1)
                out.setdefault(cur, [])
                continue
            if cur:
                lm = LABEL.search(line)
                if lm:
                    out[cur].append((lm.group(1), f.name, i))
    return out


r3, r4 = collect(R3), collect(R4)


def best(hits):
    return max(hits, key=lambda h: (RANK.get(h[0], 0), -h[2]))[0] if hits else None


rows = []
for bid, hits in r4.items():
    prev3 = best(r3.get(bid, []))
    prev4 = best(hits)
    # a heading may exist with no verdict line yet (agent still writing)
    src = hits[0][1] if hits else "?"
    rows.append((bid, prev3, prev4, src))

decided = [r for r in rows if r[2] and r[2] not in UNRES and r[1] in UNRES]
changed_lab = [r for r in rows if r[2] and r[1] and r[2] != r[1]]
print(f"round4 files: {len(R4)}   ids touched: {len(r4)}")
print(f"decided (r3-unresolved -> SUPPORTED/REFUTED): {len(decided)}")
for b, p, n, f in sorted(decided, key=lambda r: int(r[0][1:])):
    print(f"  {b}: {p} -> {n}  [{f}]")
print()
print(f"label changes of any kind: {len(changed_lab)}")
print("current round4 label distribution:", dict(Counter(r[2] for r in rows if r[2])))
print()
byfile = {}
for b, p, n, f in rows:
    s = byfile.setdefault(f, {"ids": 0, "dec": 0})
    s["ids"] += 1
    if n and n not in UNRES:
        s["dec"] += 1
print("per-file:")
for f, s in sorted(byfile.items()):
    print(f"  {f:34s} ids={s['ids']:3d} decided={s['dec']:3d}")
json.dump({"rows": [list(r) for r in rows]}, (ROOT / "round4_status.json").open("w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

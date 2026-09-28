"""Build the round3 master status, resolving duplicate-ID collisions.

For each ID we take the FIRST writer in sorted file order as canonical, and
report collisions so they can be reconciled. Emits JSON + markdown.
"""
import json
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG = sorted(ROOT.glob("batch-*.md")) + sorted(ROOT.glob("round2-batch-*.md"))
NEW = sorted(ROOT.glob("round3-batch-*.md"))
HEAD = re.compile(r"^#{1,6}\s*(B\d{3})\b")
LABEL = re.compile(r"判定\s*[:：]\s*\*{0,2}([A-Z\-]+)")
UNRES = {"PARTIAL", "INCONCLUSIVE", "NOT-CHECKED"}


def parse(files):
    out = OrderedDict()
    for f in files:
        cur = None
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            m = HEAD.match(line)
            if m:
                cur = m.group(1)
                out.setdefault(cur, {"file": f.name, "line": i, "label": None})
                continue
            if cur and out[cur]["label"] is None:
                lm = LABEL.search(line)
                if lm:
                    out[cur]["label"] = lm.group(1)
    return out


orig = parse(ORIG)
new = parse(NEW)

# per-id: every round3 label seen anywhere, with its file
allnew = {}
for f in NEW:
    cur = None
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        m = HEAD.match(line)
        if m:
            cur = m.group(1)
            allnew.setdefault(cur, [])
            continue
        if cur:
            lm = LABEL.search(line)
            if lm:
                allnew[cur].append((lm.group(1), f.name, i))

# resolution ranking: stronger evidence wins when several files disagree
RANK = {"SUPPORTED": 4, "REFUTED": 4, "PARTIAL": 2, "INCONCLUSIVE": 1, "NOT-CHECKED": 0}
canon, collisions = OrderedDict(), {}
for bid, hits in allnew.items():
    best = max(hits, key=lambda h: (RANK.get(h[0], 0), -h[2]))
    canon[bid] = {"label": best[0], "file": best[1], "line": best[2]}
    if len({h[1] for h in hits}) > 1:
        collisions[bid] = sorted({h[1] for h in hits})

rows, decided, still, missing = [], [], [], []
for bid, rec in orig.items():
    prev = rec["label"]
    if bid in canon:
        now = canon[bid]["label"]
        row = (bid, prev, now, canon[bid]["file"], collisions.get(bid))
        rows.append(row)
        if now is None:
            still.append(row)
        elif prev in UNRES and now not in UNRES:
            decided.append(row)
        elif prev == "SUPPORTED" and now == "PARTIAL":
            decided.append(row)
        else:
            still.append(row)
    elif prev in UNRES:
        missing.append(bid)

print(f"original ids: {len(orig)}")
print(f"round3 ids (with collisions): {len(new)}")
print(f"canonical ids: {len(canon)}")
print(f"colliding ids: {len(collisions)}")
print()
print(f"DECIDED (unresolved -> SUPPORTED/REFUTED): {len(decided)}")
for bid, prev, now, f, _ in decided:
    print(f"  {bid}: {prev:13s} -> {now}")
print()
print(f"STILL UNRESOLVED: {len(still)}")
print(f"MISSING (never written): {len(missing)} {missing}")
print()
lab = {}
for bid, prev, now, f, _ in rows:
    lab[now] = lab.get(now, 0) + 1
print("current label distribution over written ids:", lab)

# aggregate by round3 file
byfile = {}
for bid, prev, now, f, _ in rows:
    byfile.setdefault(f, {"dec": 0, "unres": 0, "ids": 0})
    byfile[f]["ids"] += 1
    if now and now not in UNRES:
        byfile[f]["dec"] += 1
    else:
        byfile[f]["unres"] += 1
print()
print("per-file:")
for f, s in sorted(byfile.items()):
    print(f"  {f:36s} ids={s['ids']:3d} decided={s['dec']:3d} unresolved={s['unres']:3d}")

json.dump(
    {
        "decided": [list(r[:4]) for r in decided],
        "still_unresolved": [list(r[:4]) for r in still],
        "missing": missing,
        "collisions": collisions,
        "per_file": byfile,
    },
    (ROOT / "round3_master.json").open("w", encoding="utf-8"),
    ensure_ascii=False,
    indent=1,
)
print("\nwrote research/verification/round3_master.json")

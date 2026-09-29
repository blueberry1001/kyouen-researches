"""Full census of all 600 hypotheses: latest label, which round settled it.

Combines the original round-1/round-2 verdicts with every round3/round4 file,
taking the strongest (most resolved) label for each id, and reports which file
carries it. Emits a per-id table and a per-range summary.
"""
import json
import re
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAD = re.compile(r"^#{1,6}\s*(B\d{3})\b")
LABEL = re.compile(r"判定\s*[:：]\s*\*{0,2}([A-Z\-]+)")
RANK = {"SUPPORTED": 4, "REFUTED": 4, "PARTIAL": 2, "INCONCLUSIVE": 1, "NOT-CHECKED": 0}
UNRES = {"PARTIAL", "INCONCLUSIVE", "NOT-CHECKED"}

ORIG = sorted(ROOT.glob("batch-*.md")) + sorted(ROOT.glob("round2-batch-*.md"))
NEW = (sorted(ROOT.glob("round3-batch-*.md"))
       + sorted(ROOT.glob("round4-batch-*.md"))
       + sorted(ROOT.glob("round5-batch-*.md")))
PROOF = [ROOT / "round4-collinear-asymptotic.md"]

ALL_IDS = [f"B{i:03d}" for i in range(1, 601)]


def collect(files):
    out = {}
    for f in files:
        if not f.exists():
            continue
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


orig = collect(ORIG)
new = collect(NEW)

# the collinear proof file carries no 判定 lines; B141/145/150/471/472/473 are
# settled there and recorded explicitly.
PROOF_IDS = {"B141": "SUPPORTED", "B145": "SUPPORTED", "B150": "SUPPORTED",
             "B471": "SUPPORTED", "B472": "SUPPORTED", "B473": "SUPPORTED"}


def best(hits, default=None):
    if not hits:
        return default, None, None
    b = max(hits, key=lambda h: (RANK.get(h[0], 0), h[1], -h[2]))
    return b[0], b[1], b[2]


rows = OrderedDict()
for bid in ALL_IDS:
    ol, of, oln = best(orig.get(bid, []))
    nl, nf, nln = best(new.get(bid, []))
    if bid in PROOF_IDS and (nl is None or RANK.get(nl, 0) < 4):
        nl, nf, nln = PROOF_IDS[bid], "round4-collinear-asymptotic.md", None
    final = nl or ol
    rows[bid] = {
        "r1r2": ol, "r1r2_file": of, "r1r2_line": oln,
        "r3r4": nl, "r3r4_file": nf, "r3r4_line": nln,
        "final": final,
        "settled": final in ("SUPPORTED", "REFUTED") and final is not None,
    }

print("=" * 78)
print("全 600 仮説の状態")
print("=" * 78)
lab = Counter(r["final"] for r in rows.values())
for k, v in lab.most_common():
    print(f"  {k:14s} {v:4d}")

settled = [b for b, r in rows.items() if r["settled"]]
unres = [b for b, r in rows.items() if not r["settled"]]
print()
print(f"決着（SUPPORTED/REFUTED）: {len(settled)}")
print(f"未解決（PARTIAL/INCONCLUSIVE/NOT-CHECKED）: {len(unres)}")
print()


def rng(nums):
    if not nums:
        return "—"
    parts, s, p = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == p + 1:
            p = n
            continue
        parts.append((s, p))
        s = p = n
    parts.append((s, p))
    return ", ".join(f"B{a:03d}" if a == b else f"B{a:03d}-B{b:03d}" for a, b in parts)


ids = lambda lst: sorted(int(b[1:]) for b in lst)

print("--- 100 個単位 ---")
for lo in range(1, 601, 100):
    band = [f"B{i:03d}" for i in range(lo, min(lo + 100, 601))]
    s = [b for b in band if rows[b]["settled"]]
    u = [b for b in band if not rows[b]["settled"]]
    print(f"B{lo:03d}-B{min(lo+99,600):03d}: 決着 {len(s):3d} / 未解決 {len(u):3d}")
    if u:
        print(f"    未解決: {rng(ids(u))}")

print()
print("--- 未解決の前ラベル内訳 ---")
pre = Counter(rows[b]["final"] for b in unres)
for k, v in pre.most_common():
    print(f"  {k:14s} {v:4d}")

print()
print("--- 第4回で SUPPORTED/REFUTED に動いた ID（30件） ---")
moved = []
for bid in ALL_IDS:
    r = rows[bid]
    if r["r1r2"] in UNRES and r["r3r4"] in ("SUPPORTED", "REFUTED"):
        moved.append((bid, r["r1r2"], r["r3r4"], r["r3r4_file"]))
print(f"  {len(moved)} 件")
for bid, a, b, f in moved:
    print(f"    {bid}: {a:13s} -> {b:10s} [{f}]")

print()
print("--- 第4回が記録した ID（Vjercall only、未決着も含む） ---")
touched = [b for b in ALL_IDS if rows[b]["r3r4"]]
print(f"  {len(touched)} 件")
print(f"  {rng(ids(touched))}")

(ROOT / "round4_status.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
print()
print("wrote research/verification/round4_status.json")

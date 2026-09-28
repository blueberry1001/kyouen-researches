"""Collect per-hypothesis verdict labels from batch-*.md / round2-batch-*.md.

Output: JSON mapping hypothesis id -> {label, batch_file, heading}
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted(ROOT.glob("batch-*.md")) + sorted(ROOT.glob("round2-batch-*.md"))

HEAD = re.compile(r"^#{1,6}\s*(B\d{3})\b")
LABEL = re.compile(r"判定\s*[:：]\s*\*{0,2}([A-Z\-]+)")
UNRESOLVED = {"PARTIAL", "INCONCLUSIVE", "NOT-CHECKED"}


def main() -> int:
    out = {}
    missing = []
    for f in FILES:
        lines = f.read_text(encoding="utf-8").splitlines()
        current = None
        for i, line in enumerate(lines):
            m = HEAD.match(line)
            if m:
                current = m.group(1)
                out.setdefault(current, {"label": None, "file": f.name, "line": i + 1})
                continue
            if current is None:
                continue
            lm = LABEL.search(line)
            if lm and out[current]["label"] is None:
                out[current]["label"] = lm.group(1)

    for bid, rec in sorted(out.items()):
        if rec["label"] is None:
            missing.append(bid)

    unres = sorted(b for b, r in out.items() if r["label"] in UNRESOLVED)
    print("total parsed:", len(out))
    print("label counts:")
    counts = {}
    for r in out.values():
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    print("missing labels:", len(missing), missing[:20])
    print("unresolved:", len(unres))

    def ranges(ids):
        nums = sorted(int(b[1:]) for b in ids)
        parts, start, prev = [], nums[0], nums[0]
        for n in nums[1:]:
            if n == prev + 1:
                prev = n
                continue
            parts.append((start, prev))
            start = prev = n
        parts.append((start, prev))
        return ", ".join(
            f"B{a:03d}" if a == b else f"B{a:03d}-B{b:03d}" for a, b in parts
        )

    print("UNRESOLVED:", ranges(unres))
    payload = {b: out[b] for b in unres}
    (ROOT / "round3_unresolved.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

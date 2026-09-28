"""Map which hypothesis IDs each round3 artifact appears to cover.

Heuristic: scan the script source and JSON top-level keys for B-ids and id
numbers mentioned, so we can tell which IDs already have computed data.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PAT = re.compile(r"\bB(\d{3})\b")

rows = []
for p in sorted(SCRIPTS.glob("round3_*.py")):
    txt = p.read_text(encoding="utf-8", errors="replace")
    ids = sorted({int(m) for m in PAT.findall(txt)})
    rows.append((p.name, len(txt), ids))

print("=== scripts -> ids mentioned ===")
for name, size, ids in rows:
    rng = f"{ids[0]}-{ids[-1]}" if ids else "-"
    print(f"{name:34s} {size:7d}  n_ids={len(ids):3d}  {rng}")

print()
print("=== json files ===")
for p in sorted(ROOT.glob("round3_*.json")):
    if p.name == "round3_unresolved.json":
        continue
    size = p.stat().st_size
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        keys = list(d.keys())[:12] if isinstance(d, dict) else f"<list len={len(d)}>"
    except Exception as e:
        keys = f"<parse error: {type(e).__name__}>"
    print(f"{p.name:34s} {size:9d}  keys={keys}")

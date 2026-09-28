import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "round3_unresolved.json").read_text(encoding="utf-8"))
for k in ["B086", "B087", "B501", "B502"]:
    print(k, data.get(k, "<NOT in unresolved set>"))

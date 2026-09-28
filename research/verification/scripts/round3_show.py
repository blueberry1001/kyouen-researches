import json
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "round3_unresolved.json"
d = json.loads(p.read_text(encoding="utf-8"))
for k in ["B116", "B431", "B432", "B433", "B434", "B442", "B450", "B460", "B500", "B502"]:
    print(k, d.get(k, "<resolved / not unresolved>"))

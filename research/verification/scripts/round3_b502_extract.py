"""Extract the n=6 p_rand witness for B502 from the round3 JSON."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "round3_b502_pgrand_n6.json"
if not p.exists():
    print("MISSING", p.name)
    raise SystemExit(1)

d = json.loads(p.read_text(encoding="utf-8"))
print("top keys:", list(d.keys()))
for k, v in d.items():
    if isinstance(v, dict):
        print(f"\n=== {k} ===")
        for kk, vv in v.items():
            s = str(vv)
            print(f"  {kk}: {s[:300]}")
    else:
        print(f"\n=== {k} ===\n  {str(v)[:600]}")

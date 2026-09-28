"""Inspect the round4 p_rand C++ output: what did n=7 reach?"""
import json
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "round4_b501_prand.json"
d = json.loads(p.read_text(encoding="utf-8"))
print("top keys:", list(d.keys()))
for k, v in d.items():
    print(f"\n=== {k} ===")
    if isinstance(v, dict):
        for kk, vv in v.items():
            s = str(vv)
            print(f"  {kk}: {s[:400]}")
    else:
        print(f"  {str(v)[:600]}")

"""Inspect the smaller round3 JSONs to see what verdict they can actually support."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SMALL = ["round3_b475_mn.json", "round3_b501_pgrand_n5.json", "round3_chunk8_tworow.json",
         "round3_chunk5_sharp.json", "round3_chunk5_verify.json", "round3_chunk6_wft.json",
         "round3_chunk2_saturation.json"]

for name in SMALL:
    p = ROOT / name
    if not p.exists():
        print(f"--- {name}: MISSING")
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    print(f"--- {name} ({p.stat().st_size} bytes)")
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, dict):
                sub = list(v.keys())[:8]
                print(f"    {k}: dict keys={sub}")
            elif isinstance(v, list):
                print(f"    {k}: list len={len(v)} head={v[:3]}")
            else:
                print(f"    {k}: {str(v)[:120]}")
    print()

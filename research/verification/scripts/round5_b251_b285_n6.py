#!/usr/bin/env python3
"""B285: get a 3rd grundy value via n=6 for one config (T4)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square

print("solving n=6 ...", flush=True)
b = board_square(6)
g = b.solve_grundy()
print("n6 states", len(g), flush=True)

configs = {
    "T4": [(0, 0), (1, 0), (2, 0), (1, 1)],
    "Z4": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "L3": [(0, 0), (1, 0), (0, 1)],
    "diag3": [(0, 0), (1, 1), (2, 2)],
}
out = {}
for cname, pts in configs.items():
    mask = 0
    idxs = []
    for (x, y) in pts:
        idx = y * 6 + x
        idxs.append(idx)
        mask |= 1 << idx
    safe = b.is_safe(mask)
    gv = g.get(mask) if safe else None
    L = b.legal_moves(mask) if safe else []
    out[cname] = {"safe": safe, "g": gv, "n_legal": len(L), "idxs": idxs}
    print(cname, out[cname], flush=True)

# also try translations of T4 on n=6 to see if g varies
t4_g = {}
for y0 in range(4):
    for x0 in range(4):
        pts = [(x0, y0), (x0+1, y0), (x0+2, y0), (x0+1, y0+1)]
        mask = 0
        ok = True
        for (x, y) in pts:
            if x >= 6 or y >= 6:
                ok = False
                break
            mask |= 1 << (y * 6 + x)
        if not ok or not b.is_safe(mask):
            continue
        t4_g[f"{x0},{y0}"] = g.get(mask)
print("T4 translations on n=6:", t4_g, flush=True)
out["T4_translations_n6"] = t4_g

path = Path(__file__).resolve().parents[1] / "round5_b251_b285_n6.json"
path.write_text(json.dumps(out, indent=2))
print("WROTE", path)

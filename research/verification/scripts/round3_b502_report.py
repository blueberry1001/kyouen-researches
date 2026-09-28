"""Rewrite the B502 n=6 record with the full n=6 evidence (agent was cut off)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "round3_b502_pgrand_n6.json").read_text(encoding="utf-8"))
n6 = d["n6"]
top = n6["top"][0]

P = "5162/6615"
print("P_max =", P, "=", float(n6["P_max_dec"]))
print("3/4 = 0.75; excess =", float(n6["P_max_dec"]) - 0.75)
print("P_gt_3_4 =", n6["P_gt_3_4"], " P_gt_2_3 =", n6["P_gt_2_3"])
print("witness occ =", top["occ"], "k =", top["k"], "g =", top["g"],
      "L =", top["L"], "max_rem =", top["max_rem"])
n = 6
coords = [(x, y) for y in range(n) for x in range(n) if (top["occ"] >> (y * n + x)) & 1]
print("coords =", coords)
print("n_safe_subsets =", f"{n6['n_safe_subsets']:,}", " edges =", f"{n6['edge_total']:,}")
print("n_P =", f"{n6['n_P']:,}", " n_N =", f"{n6['n_N']:,}")
print("total_s =", n6["timing_s"]["total"])
print("P_max_level =", n6["P_max_level"], " attaining =", n6["P_max_n_attaining"])

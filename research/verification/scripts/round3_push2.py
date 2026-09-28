"""Second-push worklist: still-unresolved IDs, ranked by tractability.

Ranks by whether an existing script/JSON already produced data for the ID
(high tractability) and by whether the previous round said NOT-CHECKED
(cheap to advance by just documenting a real blocker).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
master = json.loads((ROOT / "round3_master.json").read_text(encoding="utf-8"))

# id -> scripts that already computed it
SCRIPTS = {
    "round3_b371_analysis": list(range(371, 381)),
    "round3_b451_census": list(range(451, 458)),
    "round3_b451_analysis": list(range(451, 458)),
    "round3_b475_mn": [475, 476],
    "round3_b501_pgrand_n5": [501, 502],
    "round3_chunk2_saturation": list(range(92, 101)),
    "round3_chunk2_shape": [103, 104, 106, 107, 110],
    "round3_chunk2_deform": [111, 115, 118, 120, 121, 122, 123, 124, 125, 127],
    "round3_chunk3_core": [168, 169, 170] + list(range(174, 228)),
    "round3_chunk4_core": list(range(228, 259)) + list(range(260, 274)),
    "round3_chunk4_relax": list(range(251, 259)),
    "round3_chunk4_u": list(range(261, 271)),
    "round3_chunk5_partition": list(range(271, 281)),
    "round3_chunk5_jn": [312, 313, 314, 315, 317, 318, 319, 320],
    "round3_chunk5_sharp": list(range(291, 301)),
    "round3_chunk6_wft": [336, 338, 339, 340, 341],
    "round3_chunk6_cover": list(range(351, 361)),
    "round3_chunk6_residual": [343, 344, 347, 348, 349],
    "round3_chunk7_geom": [429, 437, 440, 442, 450],
    "round3_chunk7_geocirc": list(range(458, 471)) + [472, 473, 474, 477],
    "round3_chunk7_stats": list(range(482, 491)),
    "round3_chunk7_greedy": list(range(494, 501)),
    "round3_chunk7_del": list(range(504, 520)),
    "round3_chunk8_a_quads": list(range(521, 531)),
    "round3_chunk8_c_tworow": [542, 546, 550],
    "round3_chunk8_d_3row": list(range(551, 561)),
    "round2_b321_holes": [321, 322],
    "round2_b325_followup": [325],
    "round2_b330_indep": [330],
    "round2_b331_wft": [333, 334, 335],
    "round2_b561_homology": [563, 564, 565, 569, 570],
    "round2_b561_fvec": [572, 575],
    "round2_b591_dmax": [591, 592],
    "round2_b591_followup": [591, 592],
    "round2_b541_pairsum": [542, 546],
    "round2_b551_3row": [551, 552, 553, 554],
    "round2_b538_synergy": [538, 539, 540],
    "round2_b531_lines": [531, 532, 533, 534, 535],
    "round2_b421_components": [421, 422, 423],
    "round2_b422_cycle": [422, 423],
    "round2_b411_paths": [412, 413, 414, 415],
    "round2_b411_strict": [431, 432, 433, 434],
    "round2_b401_identify": [400, 402, 404, 405, 406, 407, 408],
    "round2_b411_followup": [410, 416, 425, 426, 428],
}

has_data = {}
for stem, ids in SCRIPTS.items():
    for i in ids:
        has_data.setdefault(i, []).append(stem)

rows = []
for bid, prev, now, f in master["still_unresolved"]:
    n = int(bid[1:])
    scripts = has_data.get(n, [])
    rows.append((bid, prev, now, f, scripts))

with_data = [r for r in rows if r[4]]
without = [r for r in rows if not r[4]]

print(f"still unresolved: {len(rows)}")
print(f"  with an existing script that already computed it: {len(with_data)}")
print(f"  with no script at all: {len(without)}")
print()


def rng(nums):
    if not nums:
        return "-"
    parts, s, p = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == p + 1:
            p = n
            continue
        parts.append((s, p))
        s = p = n
    parts.append((s, p))
    return ", ".join(f"B{a:03d}" if a == b else f"B{a:03d}-B{b:03d}" for a, b in parts)


print("=== A: has script but still unresolved (highest value) ===")
for bid, prev, now, f, sc in with_data:
    print(f"  {bid} ({prev}->{now}) [{f}] via {','.join(sorted(set(sc)))}")
print()
print("A-range:", rng([int(b[1:]) for b, *_ in with_data]))
print()
print("=== B: no script (lower tractability) ===")
print("B-range:", rng([int(b[1:]) for b, *_ in without]))

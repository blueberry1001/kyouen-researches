"""Assign each hypothesis ID to the artifact(s) that already computed it.

Then emit a per-ID plan for finer-grained write-up agents.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PAT = re.compile(r"\bB(\d{3})\b")

# script basename -> ids it actually targets (dominant range, not mention noise)
TARGETS = {
    "round3_b371_analysis": list(range(371, 381)),
    "round3_b451_census": list(range(451, 458)),
    "round3_b451_analysis": list(range(451, 458)),
    "round3_b475_mn": [475, 476],
    "round3_b475_mn_asymptotic": [475, 476],
    "round3_b501_pgrand_n5": [501, 502],
    "round3_chunk2_saturation": list(range(92, 101)),
    "round3_chunk2_scover": [92, 93, 94, 95, 96, 97, 98],
    "round3_chunk2_shape": [103, 104, 106, 107, 110],
    "round3_chunk2_deform": [111, 115, 118, 120, 121, 122, 123, 124, 125, 127],
    "round3_chunk3_core": [168, 169, 170] + list(range(174, 228)),
    "round3_chunk4_core": list(range(228, 259)) + list(range(260, 274)),
    "round3_chunk4_A": list(range(228, 243)),
    "round3_chunk4_A1": [228, 229, 230, 231],
    "round3_chunk4_A2": [232, 233, 234, 235, 236, 237],
    "round3_chunk4_relax": list(range(251, 259)),
    "round3_chunk4_u": list(range(261, 271)),
    "round3_chunk5_partition": list(range(271, 281)),
    "round3_chunk5_jn": [312, 313, 314, 315, 317, 318, 319, 320],
    "round3_chunk5_sharp": list(range(291, 301)),
    "round3_chunk5_verify": list(range(291, 301)),
    "round3_chunk5_b300": [300],
    "round3_chunk6_wft": [336, 338, 339, 340, 341],
    "round3_chunk6_cover": list(range(351, 361)),
    "round3_chunk6_residual": [343, 344, 347, 348, 349],
    "round3_chunk7_geom": [429, 437, 440, 442, 450],
    "round3_chunk7_lp": [440],
    "round3_chunk7_geocirc": list(range(458, 471)) + [472, 473, 474, 477],
    "round3_chunk7_stats": list(range(482, 491)),
    "round3_chunk7_greedy": list(range(494, 501)),
    "round3_chunk7_del": list(range(504, 520)),
    "round3_chunk8_a_quads": list(range(521, 531)),
    "round3_chunk8_b521": [521],
    "round3_chunk8_e_quads2": list(range(520, 531)),
    "round3_chunk8_c_tworow": [542, 546, 550],
    "round3_chunk8_d_3row": list(range(551, 561)),
    "round3_chunk8_lib": [214],
}

by_id = {}
for stem, ids in TARGETS.items():
    for i in ids:
        by_id.setdefault(i, []).append(stem)

# unresolved universe
unres = {int(k[1:]) for k in
         json.loads((ROOT / "round3_unresolved.json").read_text(encoding="utf-8"))} - {116}

covered = sorted(i for i in unres if i in by_id)
uncovered = sorted(i for i in unres if i not in by_id)

print(f"unresolved total: {len(unres)}")
print(f"has computed artifact: {len(covered)}")
print(f"NO artifact: {len(uncovered)}")


def rng(nums):
    parts, s, p = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == p + 1:
            p = n
            continue
        parts.append((s, p))
        s = p = n
    parts.append((s, p))
    return ", ".join(f"B{a:03d}" if a == b else f"B{a:03d}-B{b:03d}" for a, b in parts)


print()
print("COVERED:", rng(covered))
print()
print("UNCOVERED:", rng(uncovered))
print()
print("=== per-id artifact map (covered) ===")
for i in covered:
    print(f"B{i:03d}: {', '.join(sorted(set(by_id[i])))}")

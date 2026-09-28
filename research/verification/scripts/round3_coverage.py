import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "round3_unresolved.json").read_text(encoding="utf-8"))
expected = {int(k[1:]) for k in data} - {116}

assigned = {
    "bg-1 B501-502": [501, 502],
    "bg-2 B371-380": [371, 372, 373, 374, 375, 378, 380],
    "bg-3 B451-457": [451, 452, 453, 454, 455, 456, 457],
    "bg-4 B431-434": [431, 432, 433, 434],
    "bg-5 B475-476": [475, 476],
    "bg-6 B591-592": [591, 592],
    "chunk1": [2, 7, 8, 9, 10, 16] + list(range(20, 25)) + [29, 31, 32, 34, 35, 37, 39, 40,
                42, 43, 45, 47, 50, 54, 58, 59, 60, 63, 65, 66, 67, 69, 70, 74, 79]
               + list(range(81, 92)),
    "chunk2": list(range(92, 101)) + [103, 104, 106, 107, 110, 111, 115, 118]
               + list(range(120, 126)) + [127] + list(range(129, 134)) + [136, 138, 140, 145,
               149, 150, 153, 154] + list(range(157, 161)) + [162, 165, 166, 167],
    "chunk3": [168, 169, 170] + list(range(174, 183)) + [184, 185, 188, 189, 190, 193]
               + list(range(195, 204)) + list(range(205, 211)) + [213, 216]
               + list(range(218, 228)),
    "chunk4": list(range(228, 259)) + list(range(260, 274)),
    "chunk5": list(range(274, 301)) + list(range(312, 316)) + list(range(317, 323))
               + [325, 327] + list(range(329, 332)) + [333, 334, 335],
    "chunk6": [336] + list(range(338, 342)) + [343, 344] + list(range(347, 350))
               + list(range(351, 357)) + list(range(358, 361)) + list(range(363, 367))
               + [370, 376, 377, 379, 382] + list(range(384, 387)) + [388, 390, 400, 402]
               + list(range(404, 409)) + [410, 416, 425, 426, 428],
    "chunk7": [429, 437, 440, 442, 450] + list(range(458, 461)) + [463, 464]
               + list(range(467, 471)) + [472, 473, 474, 477] + list(range(482, 491))
               + [494, 495, 496, 499, 500, 504, 505, 507, 508, 510, 512, 513, 514, 519],
    "chunk8": list(range(520, 525)) + list(range(527, 531)) + [536, 542, 546, 550, 555,
               556, 560, 563, 564, 565, 569, 570, 572, 575] + list(range(578, 583))
               + [585] + list(range(587, 591)) + [593] + list(range(596, 600)),
}

seen = {}
dups = []
for name, ids in assigned.items():
    for i in ids:
        if i in seen:
            dups.append((i, seen[i], name))
        seen[i] = name
    print(f"{name:20s} {len(ids):3d}")

print()
print("assigned total:", len(seen))
print("expected total:", len(expected))
print("duplicates:", dups)
print("MISSING (expected but unassigned):", sorted(expected - set(seen)))
print("EXTRA (assigned but not unresolved):", sorted(set(seen) - expected))

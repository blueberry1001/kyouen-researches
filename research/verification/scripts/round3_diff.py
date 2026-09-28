import json
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "round3_unresolved.json"
data = json.loads(p.read_text(encoding="utf-8"))

# list as stated by the requester (B116 already removed as resolved via F-BG)
stated = """B002, B007-B010, B016, B020-B024, B029, B031, B032, B034, B035, B037, B039,
B040, B042, B043, B045, B047, B050, B054, B058-B060, B063, B065-B067, B069, B070, B074,
B079, B081-B085, B088-B100, B103, B104, B106, B107, B110, B111, B115, B118, B120-B125,
B127, B129-B133, B136, B138, B140, B145, B149, B150, B153, B154, B157-B160, B162,
B165-B170, B174-B182, B184, B185, B188-B190, B193, B195-B200, B201-B203, B205-B210, B213,
B216, B218-B258, B260-B300, B312-B315, B317-B322, B325, B327, B329-B331, B333-B336,
B338-B341, B343, B344, B347-B349, B351-B356, B358-B360, B363-B366, B370-B380, B382,
B384-B386, B388, B390, B400, B402, B404-B408, B410, B416, B425, B426, B428, B429, B437,
B440, B442, B450-B460, B463, B464, B467-B470, B472-B477, B482-B490, B494-B496, B499,
B500, B502, B504, B505, B507, B508, B510, B512-B514, B519-B524, B527-B530, B536, B542,
B546, B550, B555, B556, B560, B563-B565, B569, B570, B572, B575, B578-B582, B585,
B587-B593, B596-B599"""


def expand(spec: str) -> set[int]:
    out = set()
    for part in spec.replace("\n", " ").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a[1:]), int(b[1:]) + 1))
        else:
            out.add(int(part[1:]))
    return out


stated_set = expand(stated)
parsed = {int(k[1:]) for k in data}

print("stated:", len(stated_set), "parsed:", len(parsed))
print("in parsed not stated:", sorted(parsed - stated_set))
print("in stated not parsed:", sorted(stated_set - parsed))

#!/usr/bin/env python3
"""補完数 9 のトリプルと補完数 8 の不在を幾何で説明する。"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
N = 10
PTS = N * N


def main() -> None:
    # rebuild triple completions and classify each by line vs circle
    pts = [(x, y) for y in range(N) for x in range(N)]

    def det3(r0, r1, r2):
        return (
            r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
            - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
            + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0])
        )

    quads = []
    for a in range(PTS):
        for b in range(a + 1, PTS):
            for c in range(b + 1, PTS):
                for d in range(c + 1, PTS):
                    coords = [pts[a], pts[b], pts[c], pts[d]]
                    A = [(x * x + y * y, x, y, 1) for x, y in coords]
                    det = (
                        A[0][0] * det3(A[1][1:], A[2][1:], A[3][1:])
                        - A[0][1] * det3((A[1][0], A[1][2], A[1][3]), (A[2][0], A[2][2], A[2][3]), (A[3][0], A[3][2], A[3][3]))
                        + A[0][2] * det3((A[1][0], A[1][1], A[1][3]), (A[2][0], A[2][1], A[2][3]), (A[3][0], A[3][1], A[3][3]))
                        - A[0][3] * det3((A[1][0], A[1][1], A[1][2]), (A[2][0], A[2][1], A[2][2]), (A[3][0], A[3][1], A[3][2]))
                    )
                    if det == 0:
                        quads.append((a, b, c, d, coords))

    triple_comp = defaultdict(list)  # triple -> list of 4th points
    for a, b, c, d, coords in quads:
        # collinear?
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = coords
        col = (x1 - x0) * (y2 - y0) == (y1 - y0) * (x2 - x0) and (x1 - x0) * (y3 - y0) == (y1 - y0) * (x3 - x0)
        for t, fourth in (
            ((b, c, d), a),
            ((a, c, d), b),
            ((a, b, d), c),
            ((a, b, c), d),
        ):
            triple_comp[t].append((fourth, "line" if col else "circle"))

    hist = Counter()
    kind_when9 = Counter()
    for t, comps in triple_comp.items():
        hist[len(comps)] += 1
        if len(comps) == 9:
            kinds = Counter(k for _, k in comps)
            kind_when9[tuple(sorted(kinds.items()))] += 1

    print("hist", hist)
    print("when 9 completions, line/circle mix:", kind_when9)

    # examples of 9-completion triples
    examples = []
    for t, comps in triple_comp.items():
        if len(comps) == 9 and len(examples) < 8:
            examples.append({"triple": list(t), "fourths": [p for p, _ in comps], "kinds": [k for _, k in comps]})
    payload = {
        "hist": {str(k): int(v) for k, v in sorted(hist.items())},
        "kind_when_9": {str(k): int(v) for k, v in kind_when9.items()},
        "examples_9": examples,
    }
    path = OUT / "fact_10x10_triple9_geometry.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()

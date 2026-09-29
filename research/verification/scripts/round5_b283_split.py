#!/usr/bin/env python3
"""B283 quick: same Q size but different line/circle counts."""
import json
from itertools import combinations
from pathlib import Path

OUT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b283_split.json")


def det4(rows):
    a = [[int(rows[i][j]) for j in range(4)] for i in range(4)]
    total = 0
    for i in range(4):
        mm = [[a[r2][c2] for c2 in range(1, 4)] for r2 in range(4) if r2 != i]
        d3 = (mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
              - mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0])
              + mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0]))
        total += (1 if i % 2 == 0 else -1) * a[i][0] * d3
    return total


def is_collinear(pts4):
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = pts4
    return (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1)


def analyze(pts):
    k = len(pts)
    rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
    n_line = n_circ = 0
    quads = []
    for a, b, c, d in combinations(range(k), 4):
        q = (a, b, c, d)
        if det4([rows[a], rows[b], rows[c], rows[d]]) == 0:
            quads.append(q)
            p4 = [pts[i] for i in q]
            if is_collinear(p4):
                n_line += 1
            else:
                n_circ += 1
    return len(quads), n_line, n_circ


def main():
    out = {}
    for m in (4,):
        grid = [(x, y) for x in range(m) for y in range(m)]
        for k in (5, 6):
            # group by (Q_size, n_line, n_circ)
            groups = {}
            for subset in combinations(range(len(grid)), k):
                pts = [grid[i] for i in subset]
                nq, nl, nc = analyze(pts)
                if nq == 0:
                    continue
                key = (nq, nl, nc)
                groups.setdefault(key, 0)
                groups[key] += 1
            # find Q_size values that appear with multiple (nl,nc) splits
            by_nq = {}
            for (nq, nl, nc), cnt in groups.items():
                by_nq.setdefault(nq, []).append(((nl, nc), cnt))
            multi = {nq: v for nq, v in by_nq.items() if len(v) >= 2}
            out[f"m{m}_k{k}"] = {
                "total_nonemptyQ": sum(groups.values()),
                "n_distinct_Qcounts": len(by_nq),
                "Qcounts_with_multiple_splits": {str(nq): v for nq, v in multi.items()},
                "n_multi_split_Qcounts": len(multi),
            }
            print(f"m={m} k={k} nonemptyQ={sum(groups.values())} multi-split Qcounts={len(multi)}")
            for nq, v in list(multi.items())[:5]:
                print(f"  Qsize={nq} splits={v}")
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()

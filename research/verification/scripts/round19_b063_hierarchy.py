"""Integer certificates for the original B063, including minimal graph order."""
from itertools import combinations, permutations
from pathlib import Path
import hashlib
import json

from kyouen_core import is_forbidden_quad


def safe(points):
    return not any(is_forbidden_quad(q) for q in combinations(points, 4))


def competition(stones, vertices):
    assert safe(stones)
    assert len(set(stones + vertices)) == len(stones + vertices)
    assert all(safe(stones + [v]) for v in vertices)
    return [(i, j) for i, j in combinations(range(len(vertices)), 2)
            if not safe(stones + [vertices[i], vertices[j]])]


def main():
    points = [(x, y) for y in range(4) for x in range(4)]
    stones = [(2, 0), (3, 0), (0, 1), (2, 1)]
    center = (2, 3)
    leaves = [(1, 1), (2, 2), (0, 3), (1, 3)]
    star_edges = competition(stones, [center] + leaves)
    assert star_edges == [(0, i) for i in range(1, 5)]

    # All 64 labeled graphs on four vertices, modulo all 24 permutations.
    pairs = list(combinations(range(4), 2))
    perms = list(permutations(range(4)))

    def canonical(mask):
        edges = {e for i, e in enumerate(pairs) if mask >> i & 1}
        return min(sum(1 << i for i, (a, b) in enumerate(pairs)
                       if tuple(sorted((p[a], p[b]))) in edges)
                   for p in perms)

    canonical_types = {canonical(mask) for mask in range(64)}
    assert len(canonical_types) == 11
    three_stones = [(0, 0), (1, 0), (2, 0)]
    candidate_ids = {
        0: [5, 7, 9, 12], 1: [4, 5, 9, 12], 3: [4, 5, 7, 9],
        7: [6, 12, 14, 15], 11: [4, 5, 6, 9], 12: [4, 5, 9, 10],
        13: [4, 5, 7, 15], 15: [4, 5, 6, 7], 30: [4, 6, 8, 10],
        31: [4, 5, 6, 13], 63: [4, 7, 8, 11],
    }
    records = []
    for expected, ids in sorted(candidate_ids.items()):
        vs = [points[i] for i in ids]
        edges = competition(three_stones, vs)
        mask = sum(1 << pairs.index(e) for e in edges)
        assert canonical(mask) == expected
        records.append({"canonical_mask": expected, "vertex_indices": ids,
                        "vertices": vs, "edge_pairs": edges})
    assert set(candidate_ids) == canonical_types

    # A 3x3 board is the only smaller square that can fit four stones plus
    # the five vertices of K_(1,4). Inspect every safe four-stone subset.
    small = [(x, y) for y in range(3) for x in range(3)]
    checked = candidates = 0
    for ss in combinations(small, 4):
        ss = list(ss)
        if not safe(ss):
            continue
        checked += 1
        vs = [v for v in small if v not in ss]
        if not all(safe(ss + [v]) for v in vs):
            continue
        candidates += 1
        edges = competition(ss, vs)
        degrees = [sum(i in e for e in edges) for i in range(5)]
        assert sorted(degrees) != [1, 1, 1, 1, 4]

    out = {
        "claim": "B063 SUPPORTED: K_(1,4), minimum order 5, minimum square side 4",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "geometry_source_sha256": hashlib.sha256(
            Path(__file__).with_name('kyouen_core.py').read_bytes()).hexdigest(),
        "all_n_exclusion": "For k stones each neighborhood is covered by binom(k,2) cliques; round18 proof.",
        "star": {"n": 4, "S": stones, "center": center, "leaves": leaves,
                 "edge_pairs": star_edges},
        "all_four_vertex_types": {"n": 4, "S": three_stones, "certificates": records},
        "n3_exclusion": {"safe_four_stone_sets_checked": checked,
                         "sets_with_five_legal_vertices": candidates},
    }
    target = Path(__file__).resolve().parents[1] / 'round19_b063_hierarchy.json'
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS: K_(1,4), all 11 graph types, and smaller-board exclusion')
    print(json.dumps(out['n3_exclusion']))


if __name__ == '__main__':
    main()

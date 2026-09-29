"""Exact checks for B070, B227, B261 and B266.

General proofs are in the companion markdown files. This script independently
checks finite state identities and constructs integer witnesses for sharp stars.
"""
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from math import comb, gcd, isqrt, lcm
from pathlib import Path
import hashlib
import json

from kyouen_core import is_forbidden_quad


def det3(rows):
    a, b, c = rows
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def curve(points):
    rows = [(x*x+y*y, x, y, 1) for x, y in points]
    cs = [(-1)**j * det3([tuple(row[t] for t in range(4) if t != j)
                         for row in rows]) for j in range(4)]
    denominator = lcm(*(Fraction(c).denominator for c in cs))
    integers = [int(c*denominator) for c in cs]
    common = gcd(*integers)
    assert common
    integers = [x//common for x in integers]
    if next(x for x in integers if x) < 0:
        integers = [-x for x in integers]
    return tuple(integers)


def on_curve(key, point):
    a, b, c, d = key
    x, y = point
    return a*(x*x+y*y)+b*x+c*y+d == 0


def members(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


def small_board(n):
    points = [(x, y) for y in range(n) for x in range(n)]
    v = len(points)
    full = (1 << v)-1
    completions = defaultdict(int)
    quad_count = 0
    for ids in combinations(range(v), 4):
        if is_forbidden_quad([points[i] for i in ids]):
            quad_count += 1
            mask = sum(1 << i for i in ids)
            for i in ids:
                completions[mask ^ (1 << i)] |= 1 << i
    assert quad_count == {1: 0, 2: 1, 3: 14, 4: 194}[n]
    triple_curve = {}
    curve_masks = {}
    for ids in combinations(range(v), 3):
        key = curve([points[i] for i in ids])
        triple_curve[sum(1 << i for i in ids)] = key
        if key not in curve_masks:
            curve_masks[key] = sum(1 << i for i, p in enumerate(points) if on_curve(key, p))

    legal = {0: full}
    for occupied in range(1, 1 << v):
        bit = occupied & -occupied
        previous = occupied ^ bit
        if previous not in legal or not (legal[previous] & bit):
            continue
        lm = full ^ occupied
        for ids in combinations(members(occupied), 3):
            lm &= ~completions[sum(1 << i for i in ids)]
        legal[occupied] = lm
    if n == 4:
        assert len(legal) == 5811

    covered_neighborhoods = paired_moves = synergy_points = 0
    max_joint = max_pure = 0
    max_pure_witness = None
    for occupied, lm in legal.items():
        stones = list(members(occupied))
        moves = list(members(lm))
        predicted = [0]*v
        # Build pairwise competition from the independent geometric partition.
        for a, b in combinations(stones, 2):
            groups = defaultdict(int)
            for p in moves:
                key = triple_curve[(1 << a) | (1 << b) | (1 << p)]
                groups[key] |= 1 << p
            for group in groups.values():
                for p in members(group):
                    predicted[p] |= group ^ (1 << p)
        for p in moves:
            actual = lm & ~legal[occupied | (1 << p)] & ~(1 << p)
            assert predicted[p] == actual
            covered_neighborhoods += 1

        for p, q in combinations(moves, 2):
            bp, bq = 1 << p, 1 << q
            lp, lq = legal[occupied | bp], legal[occupied | bq]
            if not lp & bq:
                continue
            assert lq & bp
            after = legal[occupied | bp | bq]
            ap = lm & ~lp & ~bp
            aq = lm & ~lq & ~bq
            pure = lp & lq & ~after
            joint = lm & ~(bp | bq) & ~after
            assert joint == (ap | aq | pure)
            assert not pure & (ap | aq)
            union = upper = lines = 0
            seen_keys = set()
            for s in stones:
                key = triple_curve[(1 << s) | bp | bq]
                assert key not in seen_keys
                seen_keys.add(key)
                lines += key[0] == 0
                part = curve_masks[key] & lp & lq
                assert not union & part
                union |= part
                upper += curve_masks[key].bit_count()-3
            assert union == pure
            assert lines <= 1
            assert pure.bit_count() <= upper
            paired_moves += 1
            synergy_points += pure.bit_count()
            max_joint = max(max_joint, joint.bit_count())
            if pure.bit_count() > max_pure:
                max_pure = pure.bit_count()
                max_pure_witness = {"S": [points[i] for i in stones],
                                    "p": points[p], "q": points[q],
                                    "single_gains": [ap.bit_count(), aq.bit_count()],
                                    "pure_points": [points[i] for i in members(pure)]}

    grundy = {}
    for occupied in sorted(legal, key=int.bit_count, reverse=True):
        child_values = {grundy[occupied | (1 << p)] for p in members(legal[occupied])}
        g = 0
        while g in child_values:
            g += 1
        grundy[occupied] = g
    pass_results = []
    for terminal_pass_allowed in (False, True):
        @lru_cache(maxsize=None)
        def win(occupied, own, opponent):
            lm = legal[occupied]
            if not lm and not terminal_pass_allowed:
                return False
            for p in members(lm):
                if not win(occupied | (1 << p), opponent, own):
                    return True
            return own > 0 and not win(occupied, opponent, own-1)

        comparisons = 0
        for occupied in legal:
            for r in range(3):
                assert win(occupied, r, r) == (grundy[occupied] != 0)
                comparisons += 1
        pass_results.append({"terminal_pass_allowed": terminal_pass_allowed,
                             "equal_pass_comparisons": comparisons,
                             "expanded_states": win.cache_info().currsize})
    return {"n": n, "forbidden_quads": quad_count, "safe_states": len(legal),
            "clique_cover_neighborhoods": covered_neighborhoods,
            "jointly_legal_pairs": paired_moves,
            "pure_synergy_points_checked": synergy_points,
            "max_joint": max_joint, "max_pure": max_pure,
            "max_pure_witness": max_pure_witness,
            "empty_grundy": grundy[0], "pass_checks": pass_results}


def sharp_star(k):
    stones = [(i, i*i) for i in range(1, k+1)]
    center = (0, 0)
    pairs = list(combinations(range(k), 2))
    base_curves = {pair: curve([center, *(stones[i] for i in pair)]) for pair in pairs}
    assert len(set(base_curves.values())) == comb(k, 2)
    triples = {curve(t) for t in combinations(stones, 3)}
    leaves, used_slopes = [], []
    for pair in pairs:
        target = base_curves[pair]
        excluded = triples | (set(base_curves.values())-{target})
        for previous in leaves:
            excluded |= {curve([previous, stones[a], stones[b]]) for a, b in pairs}
        assert target not in excluded
        slope = 0
        while True:
            a, b, c, d = target
            assert d == 0 and a != 0
            x = Fraction(-b-c*slope, a*(1+slope*slope))
            point = (x, slope*x)
            if (point not in stones+[center]+leaves
                    and not any(on_curve(key, point) for key in excluded)):
                break
            slope += 1
        assert on_curve(target, point)
        leaves.append(point)
        used_slopes.append(slope)

    rational_points = stones+[center]+leaves
    scale = lcm(*(Fraction(x).denominator for p in rational_points for x in p))
    scaled = [tuple(int(x*scale) for x in p) for p in rational_points]
    lower = tuple(min(p[j] for p in scaled) for j in range(2))
    integer_points = [(x-lower[0], y-lower[1]) for x, y in scaled]
    ss = integer_points[:k]
    pp = integer_points[k]
    qq = integer_points[k+1:]
    assert not any(is_forbidden_quad(q) for q in combinations(ss, 4))
    for p in [pp]+qq:
        assert not any(is_forbidden_quad((*t, p)) for t in combinations(ss, 3))
    for pair, q in zip(pairs, qq):
        witnesses = [ab for ab in pairs if is_forbidden_quad((ss[ab[0]], ss[ab[1]], pp, q))]
        assert witnesses == [pair]
    for q, r in combinations(qq, 2):
        assert not any(is_forbidden_quad((ss[a], ss[b], q, r)) for a, b in pairs)
    return {"k": k, "independent_leaves": len(qq), "S": ss, "center": pp,
            "leaves": qq, "stone_pairs": pairs, "integer_ray_slopes": used_slopes,
            "scale": scale, "translation": [-lower[0], -lower[1]],
            "board_side": 1+max(max(p) for p in integer_points)}


def gaussian_mul(z, w):
    a, b = z
    c, d = w
    return a*c-b*d, a*d+b*c


def gaussian_pow(z, n):
    value = (1, 0)
    for _ in range(n):
        value = gaussian_mul(value, z)
    return value


def infinite_families():
    line_records = []
    for n in range(3, 31):
        s, p, q = (0, 0), (1, 0), (2, 0)
        banned = [(x, y) for y in range(n) for x in range(n)
                  if (x, y) not in (s, p, q) and is_forbidden_quad((s, p, q, (x, y)))]
        assert banned == [(x, 0) for x in range(3, n)]
        line_records.append({"n": n, "joint": len(banned), "single_gains": [0, 0]})
    circle_records = []
    for m in range(8):
        radius = 5**m
        by_norm = set()
        for x in range(-radius, radius+1):
            y = isqrt(radius*radius-x*x)
            if x*x+y*y == radius*radius:
                by_norm |= {(x, y), (x, -y)}
        by_factor = set()
        for j in range(2*m+1):
            z = gaussian_mul(gaussian_pow((2, 1), j), gaussian_pow((2, -1), 2*m-j))
            for unit in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                by_factor.add(gaussian_mul(z, unit))
        assert by_norm == by_factor and len(by_norm) == 8*m+4
        shifted = sorted((x+radius, y+radius) for x, y in by_norm)
        s, p, q = (radius, 2*radius), (0, radius), (2*radius, radius)
        banned = [r for r in shifted if r not in (s, p, q)]
        assert len(banned) == 8*m+1
        assert all(is_forbidden_quad((s, p, q, r)) for r in banned)
        n = 2*radius+1
        if m <= 2:
            brute = {(x, y) for x in range(n) for y in range(n)
                     if (x, y) not in (s, p, q) and is_forbidden_quad((s, p, q, (x, y)))}
            assert brute == set(banned)
        circle_records.append({"m": m, "n": n, "radius": radius, "S": [s],
                               "p": p, "q": q, "single_gains": [0, 0],
                               "complete_circle_points": shifted, "joint": len(banned)})
    return {"line": line_records, "circle": circle_records}


def main():
    boards = [small_board(n) for n in range(1, 5)]
    print('small-board identities and equal-pass DP: PASS', flush=True)
    stars = [sharp_star(k) for k in range(2, 9)]
    print('integer sharp-star certificates k=2..8: PASS', flush=True)
    families = infinite_families()
    out = {
        "claims": {"B070": "SUPPORTED general sharp induced-star bound",
                   "B227": "REFUTED by equal-pass strategy",
                   "B261": "SUPPORTED explicit infinite families",
                   "B266": "SUPPORTED disjoint decomposition and local bound"},
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Finite verification supplements general proofs in companion markdown.",
        "boards": boards, "sharp_stars": stars, "infinite_family_checks": families,
        "totals": {"safe_states": sum(b['safe_states'] for b in boards),
                   "clique_cover_neighborhoods": sum(b['clique_cover_neighborhoods'] for b in boards),
                   "jointly_legal_pairs": sum(b['jointly_legal_pairs'] for b in boards),
                   "pure_synergy_points_checked": sum(b['pure_synergy_points_checked'] for b in boards),
                   "equal_pass_comparisons": sum(c['equal_pass_comparisons']
                                                 for b in boards for c in b['pass_checks'])}
    }
    target = Path(__file__).resolve().parents[1] / 'round18_local_geometry.json'
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(out['totals']), flush=True)


if __name__ == '__main__':
    main()

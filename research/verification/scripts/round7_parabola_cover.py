"""Polynomial-board B357 counterexamples, with exact integer certificates.

P_t=(t,t*t). The translated circle determinant on four distinct parameters
is their Vandermonde product times their sum. Positive parameters are safe;
negative parameters encode three-term sums and have quadratic cover counts.
"""
from itertools import combinations
from math import comb, prod
from pathlib import Path
import json

from kyouen_core import is_forbidden_quad
from round7_ellipse_cover import cover_count, determinant


def main():
    output = {
        'universal_proof_not_finite_extrapolation': True,
        'base_coordinates': ['t', 't^2'],
        'k': '6m', 'board_side': '81m^2 = 9k^2/4',
        'high_point_count': 'm = k/6',
        'epsilon_all_m': '1/36', 'epsilon_m_at_least_3': '1/10',
        'examples': [],
    }
    for m in (1, 2, 3, 4, 6, 8, 12):
        k, side = 6*m, 81*m*m
        q_values = list(range(8*m+1, 9*m+1))
        exponents = list(range(1, k+1)) + [-q for q in q_values]
        points = [(t+9*m, t*t-1) for t in exponents]
        assert len(set(points)) == len(points)
        assert all(0 <= x < side and 0 <= y < side for x, y in points)
        stones, marked = points[:k], points[k:]
        core_checks = 0
        for indices in combinations(range(k), 4):
            ts = [i+1 for i in indices]
            quad = [stones[i] for i in indices]
            expected = sum(ts)*prod(ts[j]-ts[i] for i in range(4) for j in range(i+1, 4))
            assert determinant(quad) == expected > 0
            if core_checks < 100:
                assert not is_forbidden_quad(quad)
                core_checks += 1
        triples = list(combinations(range(1, k+1), 3))
        observed, max_degrees, lower_bounds = [], [], []
        for q, p in zip(q_values, marked):
            b, degrees = 0, [0]*k
            for triple in triples:
                ts = [*triple, -q]
                expected_det = sum(ts)*prod(ts[j]-ts[i] for i in range(4) for j in range(i+1, 4))
                actual_det = determinant([*(stones[t-1] for t in triple), p])
                assert actual_det == expected_det
                if actual_det == 0:
                    b += 1
                    for t in triple:
                        degrees[t-1] += 1
            assert b == cover_count(k, q) >= m*m
            if m >= 3:
                assert 10*b >= k*k
            assert 2*max(degrees) <= k-1
            lower_bound = (b+max(degrees)-1)//max(degrees)
            if m >= 3:
                assert lower_bound > k/5
            observed.append(b)
            max_degrees.append(max(degrees))
            lower_bounds.append(lower_bound)
        profile = [0]*(3*k+1)
        for triple in triples:
            profile[sum(triple)] += 1
        assert all(cover_count(k, q) == v for q, v in enumerate(profile))
        assert sum(profile) == comb(k, 3)
        output['examples'].append({
            'm': m, 'k': k, 'side': side, 'stones': stones,
            'marked_empty_points': marked, 'q_values': q_values,
            'b_values': observed, 'max_cover_vertex_degrees': max_degrees,
            'deletions_to_release_lower_bounds': lower_bounds,
            'safety_checks': comb(k, 4), 'cover_checks': m*comb(k, 3),
            'independent_core_checks': core_checks,
        })
        print(f'm={m} k={k} n={side} b={min(observed)}..{max(observed)} '
              f'local deletion lower bounds={min(lower_bounds)}..{max(lower_bounds)}', flush=True)
    target = Path(__file__).resolve().parents[1]/'round7_parabola_cover.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(target, flush=True)


if __name__ == '__main__':
    main()

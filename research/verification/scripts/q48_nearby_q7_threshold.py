#!/usr/bin/env python3
"""Exact verification for M_{4,7}=13; see research/q48-nearby-q7-threshold.md.

Standard-library-only.  Reuses the separately written exact triple-to-curve
geometry routine for independent witness verification, not for the finite
blocker search or the chord recurrence classification.
"""
from __future__ import annotations

from functools import lru_cache
from itertools import combinations
import json
from math import comb
from pathlib import Path

from q48_exact_threshold import chord_patterns, curve_masks, local_circles


def finite_exclusion(m: int, target: int) -> dict:
    row_masks = [((1 << m) - 1) << (m * y) for y in range(4)]
    curves = [sum(c[y] << (m * y) for y in range(4)) for c in local_circles(m)]
    stats = {'target_subsets': 0, 'subsets_with_blocker_options': 0,
             'visited_states': 0, 'cache_hits': 0, 'surviving_subsets': 0}

    def safe(mask: int) -> bool:
        return (all((mask & row).bit_count() <= 6 for row in row_masks)
                and all((mask & circle).bit_count() <= 6 for circle in curves))

    for size in range(6):
        for subset in combinations(range(m), size):
            stats['target_subsets'] += 1
            occupied = sum(1 << (target * m + x) for x in subset)
            options = []
            for x in range(m):
                if occupied >> (target * m + x) & 1:
                    continue
                choices = []
                for circle in curves:
                    if not circle >> (target * m + x) & 1:
                        continue
                    exterior = circle & ~row_masks[target]
                    if circle & occupied:
                        # Existing target partner: force any five of six exterior points.
                        for k in range(4 * m):
                            if exterior >> k & 1:
                                choices.append(exterior ^ (1 << k))
                    else:
                        # Both target points blank: all six exterior points are needed.
                        choices.append(exterior)
                if not choices:
                    break
                options.append(tuple(choices))
            else:
                stats['subsets_with_blocker_options'] += 1

                @lru_cache(None)
                def visit(mask: int) -> bool:
                    stats['visited_states'] += 1
                    next_masks = None
                    for choices in options:
                        if any(mask & choice == choice for choice in choices):
                            continue
                        allowed = {mask | choice for choice in choices if safe(mask | choice)}
                        if not allowed:
                            return False
                        if next_masks is None or len(allowed) < len(next_masks):
                            next_masks = allowed
                    if next_masks is None:
                        return True
                    return any(visit(next_mask) for next_mask in sorted(next_masks))

                survives = visit(occupied)
                stats['cache_hits'] += visit.cache_info().hits
                stats['surviving_subsets'] += int(survives)
                assert not survives, (m, target, subset)
    assert stats['target_subsets'] == sum(comb(m, size) for size in range(6))
    return {'m': m, 'target_row': target, **stats}


def witness_check() -> dict:
    m, q = 12, 7
    rows = [[5, 6, 7, 8, 9, 10], [0, 1, 2, 3, 7],
            [5, 6, 7, 8, 9, 11], [5, 6, 7, 8, 9, 10]]
    occupied = sum(1 << (m * y + x) for y, row in enumerate(rows) for x in row)
    curves, geometry = curve_masks(m, q)
    assert all((occupied & curve).bit_count() < q for curve in curves)
    blanks = []
    for k in range(4 * m):
        if occupied >> k & 1:
            continue
        assert any(((occupied | (1 << k)) & curve).bit_count() >= q for curve in curves), k
        blanks.append([k % m, k // m])
    assert geometry['lines'] == 4 and geometry['circles'] == 9
    return {'m': m, 'q': q, 'rows': rows, 'stones': occupied.bit_count(),
            'row_counts': list(map(len, rows)), 'safe': True, 'maximal': True,
            'blocked_blank_points': blanks, 'independent_geometry': geometry}


def main() -> None:
    patterns = chord_patterns(241)
    assert patterns == [(1, 3, 3, 1), (35, 51, 63, 73), (73, 63, 51, 35)]
    # Endpoint tangency would require d3^2=3*d1^2-24, impossible mod 9.
    residues = {x * x % 9 for x in range(9)}
    tangency_values = {(3 * x * x - 24) % 9 for x in range(9)}
    assert not residues & tangency_values
    # Each profile has a distinct difference on every fixed row, so a pair
    # in that row belongs to at most one of these full lattice circles.
    assert all(len({p[y] for p in patterns}) == 3 for y in range(4))
    result = {
        'statement': 'M_{4,7}=13; all m>=13 and all safe S have g(S)=(24-|S|) mod 2',
        'universal_counting_stability_from': 141,
        'extended_circle_classification': {'board_lengths_covered': [1, 140],
                                           'maximum_lattice_chord_span_checked': 241,
                                           'patterns': patterns,
                                           'square_residues_mod_9': sorted(residues),
                                           'endpoint_tangency_values_mod_9': sorted(tangency_values)},
        'three_profile_counting_stability_from': 36,
        'local_counting_stability_from': 16,
        'finite_exclusions': [finite_exclusion(m, r) for m in (13, 14, 15) for r in (0, 1)],
        'lower_bound_witness': witness_check(),
        'proof_scope': {'finite_search': 'm=13..15, target rows 0,1, all subsets of sizes 0..5',
                        'local_circle_counting': 'm=16..35',
                        'three_profile_counting': 'm=36..140',
                        'universal_counting': 'all m>=141'},
    }
    destination = Path(__file__).resolve().parents[1] / 'q48_nearby_q7_threshold.json'
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

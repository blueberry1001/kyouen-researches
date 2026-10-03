#!/usr/bin/env python3
"""Reproduce 16 <= M_{4,6} <= 68.  No claim of an exact threshold."""
from __future__ import annotations
from collections import Counter
from itertools import combinations
import json
from pathlib import Path

from q48_exact_threshold import chord_patterns, curve_masks
from curve_packing_fixed_width import bound


def difference_graph_check(gaps: list[int]) -> dict:
    directions = [sign * gap for sign in (-1, 1) for gap in gaps]
    multiplicities = Counter(b - a for a in directions for b in directions if a != b)
    assert all(gap % 2 == 1 for gap in gaps)
    assert max(multiplicities.values()) == 2
    # Odd gaps make the graph bipartite.  Six edges on five vertices would
    # force a K_{2,3}; at most two common neighbors rules that out.
    return {'gaps': gaps, 'bipartite_by_parity': True,
            'maximum_common_neighbors_of_distinct_vertices': 2,
            'maximum_edges_on_five_vertices_upper_bound': 5}


def witness_check() -> dict:
    m, q = 15, 6
    rows = [[8, 10, 13, 14], [3, 5, 6, 9, 10],
            [2, 3, 8, 11, 12], [4, 5, 9, 10, 11]]
    occupied = sum(1 << (y*m+x) for y,row in enumerate(rows) for x in row)
    curves, geometry = curve_masks(m, q)
    assert all((occupied & curve).bit_count() <= 5 for curve in curves)
    blanks = []
    target_blockers = []
    for k in range(4*m):
        if occupied >> k & 1:
            continue
        witnesses = [curve for curve in curves if ((occupied | (1<<k)) & curve).bit_count() >= q]
        assert witnesses, k
        blanks.append([k%m, k//m])
        if k < m:
            used = (occupied | (1<<k)) & witnesses[0]
            target_blockers.append({'x': k, 'six_points': [[v%m,v//m] for v in range(4*m) if used>>v&1]})
    return {'m': m, 'q': q, 'rows': rows, 'stones': occupied.bit_count(),
            'row_counts': list(map(len,rows)), 'safe': True, 'maximal': True,
            'blocked_blank_points': blanks, 'target_row_blockers': target_blockers,
            'independent_geometry': geometry}


def main() -> None:
    packing=bound(4,6)
    assert packing['packing_U']==103
    profiles=chord_patterns(175)
    assert profiles == [(1,3,3,1),(35,51,63,73),(73,63,51,35)]
    assert all(len({p[y] for p in profiles})==3 for y in range(4))
    result={'statement':'16 <= M_{4,6} <= 68; exact threshold remains unresolved',
            'packing_tail':packing,
            'four_occupied_rows_circle_profiles_for_m_at_most_102':profiles,
            'maximum_chord_checked':175,
            'gap_graphs':[difference_graph_check([1,35,73]),difference_graph_check([3,51,63])],
            'blocker_budget':{'three_occupied_rows_circles':48,
                              'four_occupied_rows_circles':15,
                              'target_occupied_points':4,
                              'total_unavailable_upper_bound':67},
            'lower_bound_witness':witness_check(),
            'scope':'Only the witness is computational search output; upper bound follows the documented counting proof and finite chord classification.'}
    destination=Path(__file__).resolve().parents[1]/'q48_nearby_q6_bounds.json'
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()

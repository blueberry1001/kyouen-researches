"""Check a depth-two collision directly using a separate integer determinant."""
from functools import lru_cache
from itertools import combinations
from pathlib import Path
import json
from independent_geometry import circle_det


def main():
    n = 5
    states = [(0, 1, 3, 10, 12, 19), (0, 1, 13, 14, 15, 19)]
    board = set(range(n*n))
    legal_target = (6, 17, 20)

    def forbidden_quad(q):
        return circle_det([(i % n, i // n) for i in q]) == 0

    def safe(s):
        return not any(forbidden_quad(q) for q in combinations(s, 4))

    @lru_cache(None)
    def legal(s):
        return tuple(v for v in sorted(board-set(s)) if safe(tuple(sorted(s+(v,)))))

    @lru_cache(None)
    def grundy(s):
        opts = {grundy(tuple(sorted(s+(v,)))) for v in legal(s)}
        g = 0
        while g in opts:
            g += 1
        return g

    results = []
    for state in states:
        assert safe(state)
        assert legal(state) == legal_target
        for k in range(3):
            assert all(safe(tuple(sorted(state+q))) for q in combinations(legal_target, k))
        combined = tuple(sorted(state+legal_target))
        bad = [q for q in combinations(combined, 4) if forbidden_quad(q)]
        results.append(dict(state=state, coordinates=[(i%n, i//n) for i in state],
                            legal=legal(state), grundy=grundy(state),
                            all_three_safe=safe(combined), forbidden_after_all_three=bad))
    assert [r['grundy'] for r in results] == [0, 1]
    assert [r['all_three_safe'] for r in results] == [False, True]
    out = dict(n=n, coordinate_convention='id=x+5*y, zero based', witnesses=results)
    Path(__file__).with_suffix('.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out))


if __name__ == '__main__':
    main()

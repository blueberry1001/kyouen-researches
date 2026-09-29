"""Complete D4-reduced check of all one/two forbidden-quad removals on 4x4."""
from functools import lru_cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
import time

from round19_rule_certificates import build, members, FULL, POINTS


def main():
    started = time.perf_counter()
    quads, signatures = build()
    qid = {q: i for i, q in enumerate(quads)}
    permutations = []
    for reflect in (False, True):
        for rotation in range(4):
            image = []
            for x, y in POINTS:
                if reflect:
                    x = 3 - x
                for _ in range(rotation):
                    x, y = 3 - y, x
                image.append(x + 4*y)
            assert sorted(image) == list(range(16))
            permutations.append([qid[sum(1 << image[p] for p in members(q))] for q in quads])
    assert len({tuple(p) for p in permutations}) == 8

    possible = {s for s in range(1 << 16) if signatures[s].bit_count() <= 2}
    children = {s: [(t, signatures[t]) for p in members(FULL ^ s)
                    if (t := s | (1 << p)) in possible] for s in possible}
    records = []
    for count in (1, 2):
        orbits = {}
        for ids in combinations(range(len(quads)), count):
            key = min(tuple(sorted(p[i] for i in ids)) for p in permutations)
            orbits[key] = orbits.get(key, 0) + 1
        checks = []
        for ids, orbit_size in sorted(orbits.items()):
            removed = sum(1 << i for i in ids)

            @lru_cache(maxsize=None)
            def win(s):
                return any(not signature & ~removed and not win(t)
                           for t, signature in children[s])

            assert not win(0), ids
            checks.append({"representative": ids, "orbit_size": orbit_size,
                           "empty_outcome": "P", "states_evaluated": win.cache_info().currsize})
        records.append({"removed_count": count, "total_variants": sum(orbits.values()),
                        "orbits": len(orbits), "checks": checks})
        print(json.dumps({k: v for k, v in records[-1].items() if k != 'checks'}), flush=True)
    assert [r['total_variants'] for r in records] == [194, 18721]
    source = Path(__file__)
    out = {"claim": "No one/two-quad removal flips 4x4; combined with triple witness distance is 3",
           "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "dependencies_sha256": {name: hashlib.sha256(source.with_name(name).read_bytes()).hexdigest()
                                   for name in ['round19_rule_certificates.py', 'kyouen_core.py']},
           "exact_integer_geometry": True, "families": records,
           "seconds": time.perf_counter() - started}
    target = source.resolve().parents[1] / 'round19_rule_pair_lower.json'
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS: all 18,915 variants, seconds=' + str(out['seconds']), flush=True)


if __name__ == '__main__':
    main()

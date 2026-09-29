"""Exact 4x4 rule-removal certificates for B253/B522 and the n=4 case of B255.

The robust strategy allows the opponent to choose any move compatible with a
removal family, while our move must introduce no newly revealed removed quad.
This proves a whole class of variants at once, without sampling variants.
"""
from itertools import combinations
from functools import lru_cache
from pathlib import Path
import hashlib
import json

from kyouen_core import is_forbidden_quad


N = 16
FULL = (1 << N) - 1
POINTS = [(x, y) for y in range(4) for x in range(4)]


def members(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


def build():
    quads = [sum(1 << i for i in ids) for ids in combinations(range(N), 4)
             if is_forbidden_quad([POINTS[i] for i in ids])]
    assert len(quads) == 194
    signatures = [0] * (1 << N)
    for i, q in enumerate(quads):
        complement = FULL ^ q
        rest = complement
        while True:
            signatures[q | rest] |= 1 << i
            if not rest:
                break
            rest = (rest - 1) & complement
    return quads, signatures


def exact_variant(signatures, removed):
    safe = [s for s in range(1 << N) if not signatures[s] & ~removed]
    gs = {}
    for s in reversed(safe):
        child_values = {gs[t] for p in members(FULL ^ s)
                        if (t := s | (1 << p)) in gs}
        g = 0
        while g in child_values:
            g += 1
        gs[s] = g
    max_size = max(s.bit_count() for s in safe)
    maxima = [s for s in safe if s.bit_count() == max_size]
    return {"removed_quad_indices": list(members(removed)), "g0": gs[0],
            "winning_first_moves": [p for p in range(N) if gs[1 << p] == 0],
            "safe_states": len(safe), "maximum_size": max_size,
            "maximum_sets": maxima}


def direct_grundy(quads, removed):
    retained = [q for i, q in enumerate(quads) if not removed >> i & 1]

    @lru_cache(maxsize=None)
    def grundy(s):
        child_values = set()
        for p in members(FULL ^ s):
            t = s | (1 << p)
            if not any(t & q == q for q in retained):
                child_values.add(grundy(t))
        g = 0
        while g in child_values:
            g += 1
        return g

    return grundy(0)


def smaller_boards():
    records = []
    for n in (1, 2, 3):
        points = [(x, y) for y in range(n) for x in range(n)]
        quads = [sum(1 << i for i in ids) for ids in combinations(range(n*n), 4)
                 if is_forbidden_quad([points[i] for i in ids])]
        signatures = [sum(1 << i for i, q in enumerate(quads) if s & q == q)
                      for s in range(1 << (n*n))]
        k = max(s.bit_count() for s, sig in enumerate(signatures) if not sig)
        forced = {}
        for s, sig in enumerate(signatures):
            if s.bit_count() == k and sig.bit_count() == 1:
                forced.setdefault(sig.bit_length()-1, s)
        if n == 3:
            assert len(forced) == len(quads) == 14
        records.append({"n": n, "quad_masks": quads, "maximum_size": k,
                        "unique_quad_maximum_layer_witnesses": forced})
    assert records[0]['quad_masks'] == []
    assert records[1]['quad_masks'] == [15] and records[1]['maximum_size'] == 3
    return records


def robust_certificate(signatures, permitted, quads):
    possible = {s for s in range(1 << N) if permitted(signatures[s])}
    defender, opponent, policy = {}, {}, {}
    for s in sorted(possible, reverse=True):
        children = [s | (1 << p) for p in members(FULL ^ s)
                    if s | (1 << p) in possible]
        good = [t for t in children if signatures[t] == signatures[s] and opponent[t]]
        defender[s] = bool(good)
        if good:
            policy[s] = (good[0] ^ s).bit_length() - 1
        opponent[s] = all(defender[t] for t in children)
    result = {"possible_states": len(possible), "robust_second": opponent[0],
              "robust_first": defender[0]}
    if not opponent[0]:
        return result

    # Verify the reachable strategy separately, recomputing forbidden sets
    # directly rather than reading the signature construction or DP values.
    visited = set()
    reached_policy = {}

    def direct_signature(s):
        return sum(1 << i for i, q in enumerate(quads) if s & q == q)

    def verify(s, our_turn):
        key = (s, our_turn)
        if key in visited:
            return
        visited.add(key)
        sigma = direct_signature(s)
        assert permitted(sigma)
        if our_turn:
            p = policy[s]
            assert not s & (1 << p)
            t = s | (1 << p)
            assert direct_signature(t) == sigma
            reached_policy[str(s)] = p
            verify(t, False)
        else:
            for p in members(FULL ^ s):
                t = s | (1 << p)
                if permitted(direct_signature(t)):
                    verify(t, True)

    verify(0, False)
    result.update({"verified_reachable_states": len(visited),
                   "defender_policy": reached_policy,
                   "verification": "All possible opponent moves; defender adds no new forbidden quad."})
    return result


def main():
    quads, sigs = build()
    baseline = exact_variant(sigs, 0)
    assert baseline['g0'] == 0 and baseline['maximum_size'] == 7
    assert len(baseline['maximum_sets']) == 64

    # Each forced quad is the only forbidden quad in a seven-point witness.
    forced_witnesses = {}
    for s, signature in enumerate(sigs):
        if s.bit_count() == 7 and signature.bit_count() == 1:
            forced_witnesses.setdefault(signature.bit_length() - 1, s)
    assert len(forced_witnesses) == 152
    forced_mask = sum(1 << i for i in forced_witnesses)
    optional = ((1 << len(quads)) - 1) ^ forced_mask
    assert optional.bit_count() == 42
    robust_max = robust_certificate(sigs, lambda sig: not sig & forced_mask, quads)
    assert robust_max['robust_second']
    print('PASS: robust second-player strategy for every subset of 42 optional quads', flush=True)

    witness = [127, 138, 171]
    variants = []
    for mask in range(8):
        removed = sum(1 << witness[i] for i in range(3) if mask >> i & 1)
        result = exact_variant(sigs, removed)
        assert (result['g0'] != 0) == (mask == 7)
        variants.append(result)
    assert len(variants[-1]['maximum_sets']) == 86
    assert direct_grundy(quads, 0) == baseline['g0'] == 0
    assert direct_grundy(quads, sum(1 << i for i in witness)) == variants[-1]['g0'] == 2
    print('PASS: all eight subfamilies of the known triple-removal witness', flush=True)

    out = {
        "claims": {"B253": "SUPPORTED: independently rechecked existing witness",
                   "B522": "SUPPORTED: same existing triple satisfies original statement",
                   "B255": "PARTIAL overall; impossible on every standard square n<=4"},
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "geometry_source_sha256": hashlib.sha256(
            Path(__file__).with_name('kyouen_core.py').read_bytes()).hexdigest(),
        "n": 4, "point_order": POINTS, "quad_masks": quads,
        "baseline": baseline,
        "B255_forced_quad_witnesses": {str(i): s for i, s in sorted(forced_witnesses.items())},
        "B255_optional_quad_indices": list(members(optional)),
        "B255_robust_strategy": robust_max,
        "B255_smaller_boards": smaller_boards(),
        "independent_direct_grundy_checks": {"standard": 0, "triple_removed": 2},
        "triple_witness": {"indices": witness,
                           "coordinates": [[POINTS[p] for p in members(quads[i])] for i in witness],
                           "all_subfamilies": variants},
    }
    target = Path(__file__).resolve().parents[1] / 'round19_rule_certificates.json'
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({"robust_max": {k: v for k, v in robust_max.items() if k != 'defender_policy'}}))


if __name__ == '__main__':
    main()

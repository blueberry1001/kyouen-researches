"""Exact search for original B255 on the complete 5x5 board.

First identify quads forced by preservation of all maximum configurations.
No sampling or use of maximal configurations in place of maximum ones.
"""
from collections import defaultdict
from functools import lru_cache
from itertools import combinations
from pathlib import Path
from random import Random
import hashlib
import json
import time

from kyouen_core import is_forbidden_quad


def members(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


class Board:
    def __init__(self, n):
        self.n = n
        self.points = [(x, y) for y in range(n) for x in range(n)]
        self.v = len(self.points)
        self.full = (1 << self.v) - 1
        self.quads = [sum(1 << i for i in ids)
                      for ids in combinations(range(self.v), 4)
                      if is_forbidden_quad([self.points[i] for i in ids])]
        self.completions = self.completion_table(range(len(self.quads)))

    def completion_table(self, kept):
        result = defaultdict(int)
        for i in kept:
            q = self.quads[i]
            for p in members(q):
                result[q ^ (1 << p)] |= 1 << p
        return result

    def legal(self, s, table=None):
        if table is None:
            table = self.completions
        legal = self.full ^ s
        for ids in combinations(members(s), 3):
            legal &= ~table.get(sum(1 << i for i in ids), 0)
        return legal

    def after(self, s, legal, p, table=None):
        if table is None:
            table = self.completions
        bit = 1 << p
        result = legal & ~bit
        for a, b in combinations(members(s), 2):
            result &= ~table.get((1 << a) | (1 << b) | bit, 0)
        return result

    def unique_quad_extension(self, qi, target):
        start = self.quads[qi]
        nodes = 0

        def dfs(s, candidates):
            nonlocal nodes
            nodes += 1
            needed = target - s.bit_count()
            if needed == 0:
                return s
            if candidates.bit_count() < needed:
                return None
            while candidates.bit_count() >= needed:
                bit = candidates & -candidates
                candidates ^= bit
                p = bit.bit_length() - 1
                after = self.after(s, candidates, p)
                witness = dfs(s | bit, after)
                if witness is not None:
                    return witness
            return None

        # Removing the quad already inside start does not change completion
        # bans on points outside start; all subsequent additions use the full table.
        found = dfs(start, self.legal(start))
        if found is not None:
            assert found.bit_count() == target and found & start == start
            assert [i for i, q in enumerate(self.quads) if found & q == q] == [qi]
        return found, nodes

    def enumerate_rules(self, forced):
        retained = self.completion_table(forced)
        optional = set(range(len(self.quads))) - set(forced)
        by_point = [[] for _ in range(self.v)]
        for i in optional:
            q = self.quads[i]
            for p in members(q):
                by_point[p].append((q ^ (1 << p), 1 << i))
        states = {}

        def visit(s, candidates, legal, neutral, signature):
            states[s] = (legal, neutral, signature)
            while candidates:
                bit = candidates & -candidates
                candidates ^= bit
                p = bit.bit_length() - 1
                after = self.after(s, legal, p, retained)
                next_neutral = self.after(s, neutral, p)
                next_signature = signature
                if not neutral & bit:
                    for triple, flag in by_point[p]:
                        if s & triple == triple:
                            next_signature |= flag
                visit(s | bit, candidates & after, after, next_neutral, next_signature)

        visit(0, self.full, self.full, self.full, 0)
        return states


def robust_strategy(states, our_first=True):
    values, policy = {}, {}
    for s in sorted(states, reverse=True):
        legal, neutral, _ = states[s]
        chosen = next((p for p in members(neutral) if values[s | (1 << p)] & 2), None)
        opponent_loses = all(values[s | (1 << p)] & 1 for p in members(legal))
        values[s] = (chosen is not None) | (int(opponent_loses) << 1)
        if chosen is not None:
            policy[s] = chosen
    result = {"first_has_common_strategy": bool(values[0] & 1),
              "second_has_common_strategy": bool(values[0] & 2), "possible_states": len(states)}
    if not (values[0] & (1 if our_first else 2)):
        return result
    reached, chosen_moves = set(), {}

    def visit(s, our_turn):
        if (s, our_turn) in reached:
            return
        reached.add((s, our_turn))
        legal, neutral, _ = states[s]
        if our_turn:
            p = policy[s]
            assert neutral & (1 << p)
            chosen_moves[str(s)] = p
            visit(s | (1 << p), False)
        else:
            for p in members(legal):
                visit(s | (1 << p), True)

    visit(0, our_first)
    result.update({"reached_states": len(reached), "policy": chosen_moves})
    return result


def maximum_preserving_states(states, k):
    witnesses = {}
    for s, (_, _, sig) in states.items():
        if s.bit_count() == k and sig:
            witnesses.setdefault(sig, s)
    minimal = []
    for sig in sorted(witnesses, key=lambda x: (x.bit_count(), x)):
        if not any(t & sig == t for t in minimal):
            minimal.append(sig)
    signatures = {sig for _, _, sig in states.values()}
    allowed = {sig for sig in signatures
               if not any(t & sig == t for t in minimal)}
    # Membership in a union of hereditary safe families is itself hereditary.
    filtered = {}
    for s, (legal, neutral, sig) in states.items():
        if sig in allowed:
            new_legal = sum(1 << p for p in members(legal)
                            if states[s | (1 << p)][2] in allowed)
            assert not neutral & ~new_legal
            filtered[s] = (new_legal, neutral, sig)
    return filtered, minimal, {str(sig): witnesses[sig] for sig in minimal}


def variant_outcome(states, removed):
    @lru_cache(maxsize=None)
    def win(s):
        for p in members(states[s][0]):
            t = s | (1 << p)
            if not states[t][2] & ~removed and not win(t):
                return True
        return False
    result = win(0)
    return result, win.cache_info().currsize


def search_variants(states, optional, conflicts, trials=300):
    rng = Random(200255)
    seen = set()
    for attempt in range(trials):
        order = optional[:]
        rng.shuffle(order)
        probability = (attempt % 10 + 1) / 10
        removed = 0
        for i in order:
            if rng.random() > probability:
                continue
            enlarged = removed | (1 << i)
            if not any(sig & enlarged == sig for sig in conflicts):
                removed = enlarged
        if removed in seen:
            continue
        seen.add(removed)
        winning, evaluated = variant_outcome(states, removed)
        if not winning:
            print('FOUND preserving flip, trial=' + str(attempt) + ', size=' + str(removed.bit_count()), flush=True)
            # Greedy one-pass shrinking; neither inclusion nor size minimality is claimed.
            for i in list(members(removed)):
                candidate = removed ^ (1 << i)
                if not variant_outcome(states, candidate)[0]:
                    removed = candidate
            return {"seed": 200255, "attempt": attempt, "distinct_tested": len(seen),
                    "removed_indices": list(members(removed)), "empty_outcome": "P",
                    "first_found_states_evaluated": evaluated}
    return {"seed": 200255, "attempts": trials, "distinct_tested": len(seen), "witness": None}


def main():
    started = time.perf_counter()
    board = Board(5)
    assert len(board.quads) == 826
    witnesses, optional, search_nodes = {}, [], 0
    for i in range(len(board.quads)):
        witness, nodes = board.unique_quad_extension(i, 9)
        search_nodes += nodes
        if witness is None:
            optional.append(i)
        else:
            witnesses[str(i)] = witness
    result = {
        "n": 5, "target_maximum_size": 9,
        "forced_count": len(witnesses), "optional_count": len(optional),
        "unique_quad_maximum_layer_witnesses": witnesses,
        "no_unique_quad_extension": optional,
        "extension_search_nodes": search_nodes,
        "quad_masks": board.quads, "point_order": board.points,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "geometry_source_sha256": hashlib.sha256(
            Path(__file__).with_name('kyouen_core.py').read_bytes()).hexdigest(),
        "seconds": time.perf_counter() - started,
    }
    target = Path(__file__).resolve().parents[1] / 'round20_b255_n5.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['forced_count', 'optional_count', 'extension_search_nodes', 'seconds']}), flush=True)
    states = board.enumerate_rules([int(i) for i in witnesses])
    layers = defaultdict(int)
    original_layers = defaultdict(int)
    for s, (_, _, signature) in states.items():
        layers[s.bit_count()] += 1
        if not signature:
            original_layers[s.bit_count()] += 1
    result['retaining_forced_layer_counts'] = dict(sorted(layers.items()))
    result['standard_layer_counts'] = dict(sorted(original_layers.items()))
    print(json.dumps({'retaining_forced': result['retaining_forced_layer_counts'],
                      'standard': result['standard_layer_counts']}), flush=True)
    assert max(original_layers) == 9 and original_layers[9] == 100
    result['all_optional_robust_strategy'] = robust_strategy(states)
    print(json.dumps({k: v for k, v in result['all_optional_robust_strategy'].items() if k != 'policy'}), flush=True)
    filtered, conflicts, conflict_witnesses = maximum_preserving_states(states, 9)
    result['minimal_maximum_preservation_conflicts'] = conflict_witnesses
    result['maximum_preserving_robust_strategy'] = robust_strategy(filtered)
    print(json.dumps({'minimal_conflicts': len(conflicts),
                      **{k: v for k, v in result['maximum_preserving_robust_strategy'].items() if k != 'policy'}}), flush=True)
    if not result['maximum_preserving_robust_strategy']['first_has_common_strategy']:
        result['variant_search'] = search_variants(filtered, optional, conflicts)
        print(json.dumps(result['variant_search']), flush=True)
    result['seconds'] = time.perf_counter() - started
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

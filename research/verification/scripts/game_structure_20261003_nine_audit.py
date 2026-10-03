#!/usr/bin/env python3
"""Independent, bounded audit of the frozen 9x9 experimental solver.

No 9x9 root search is attempted beyond deliberate time/node-cap failures.
The geometry oracle groups triples by primitive circle/line equations; it
does not import the solver's determinant or completion-table implementation.
Temporary small-board builds change only N and the table allocation size.
Small-board certificates are verified in full from their postorder records.

Example from the repository root:
  python research/verification/scripts/game_structure_20261003_nine_audit.py \
      --output research/verification/game_structure_20261003_nine_audit.json
"""

import argparse
from functools import lru_cache
import hashlib
from itertools import combinations
import json
from math import comb, gcd
from pathlib import Path
import struct
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'game_structure_20261003_nine.cpp'
DOMAIN_SOURCE = HERE / 'game_structure_20261003_nine_audit_domains.cpp'
FROZEN_SHA256 = '4681a1e92ccc4f4c43fb6c8760b15c46e4ae4fa48989fa9bbc642b7bf0bdaec3'
FLAGS = ['-std=c++17', '-O2', '-Wall', '-Wextra']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Geometry:
    """Independent exact circles and lines, represented by all their points."""

    def __init__(self, n):
        self.n, self.v = n, n * n
        self.all = (1 << self.v) - 1
        self.points = [(i % n, i // n) for i in range(self.v)]
        entities = {}
        for ids in combinations(range(self.v), 3):
            (x, y), (xx, yy), (u, v) = [self.points[i] for i in ids]
            xx, yy, u, v = xx - x, yy - y, u - x, v - y
            a = xx * v - u * yy
            if a:
                b = -((xx * xx + yy * yy) * v - (u * u + v * v) * yy) - 2 * a * x
                c = -(xx * (u * u + v * v) - u * (xx * xx + yy * yy)) - 2 * a * y
                d = -a * (x * x + y * y) - b * x - c * y
                factor = gcd(gcd(a, b), gcd(c, d)) * (1 if a > 0 else -1)
                key = tuple(t // factor for t in (a, b, c, d))
            else:
                b, c = yy, -xx
                d = -b * x - c * y
                factor = gcd(gcd(b, c), d)
                if b < 0 or (b == 0 and c < 0):
                    factor = -factor
                key = (0, b // factor, c // factor, d // factor)
            entities[key] = entities.get(key, 0) | sum(1 << i for i in ids)
        self.entities = [mask for mask in entities.values() if mask.bit_count() >= 4]
        # Every forbidden quadruple belongs to a unique circle or line.
        self.forbidden_count = sum(comb(mask.bit_count(), 4) for mask in self.entities)

    def legal(self, occupied):
        assert not occupied & ~self.all
        legal = self.all ^ occupied
        for edge in self.entities:
            hit = (edge & occupied).bit_count()
            assert hit <= 3, 'unsafe state in probe or certificate'
            if hit == 3:
                legal &= ~edge
        return legal

    def canonical(self, occupied):
        xy = [self.points[i] for i in range(self.v) if occupied >> i & 1]
        answers = []
        for reflected in [False, True]:
            current = [(self.n - 1 - x, y) if reflected else (x, y) for x, y in xy]
            for _ in range(4):
                answers.append(sum(1 << (y * self.n + x) for x, y in current))
                current = [(self.n - 1 - y, x) for x, y in current]
        return min(answers)


def rank(occupied, v):
    positions = [i for i in range(v) if occupied >> i & 1]
    k = len(positions)
    return sum(comb(v, j) for j in range(k)) + sum(
        comb(p, j) for j, p in enumerate(positions, 1))


def unrank(code, v, max_stones=20):
    offset = 0
    for k in range(max_stones + 1):
        if code < offset + comb(v, k):
            break
        offset += comb(v, k)
    else:
        raise AssertionError('rank outside audited domain')
    remaining, p, positions = code - offset, v - 1, []
    for j in range(k, 0, -1):
        while comb(p, j) > remaining:
            p -= 1
        positions.append(p)
        remaining -= comb(p, j)
        p -= 1
    assert remaining == 0
    return sum(1 << p for p in positions)


def validate_probes(path, samples):
    geometry = Geometry(9)
    assert geometry.forbidden_count == 29152
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(records) == samples + 1
    assert records[0] == {'n': 9, 'forbidden': 29152, 'samples': samples}

    @lru_cache(None)
    def direct_tiny(occupied, possible):
        moves = geometry.legal(occupied) & possible
        if not moves:
            return True  # No move wins under the misere convention.
        while moves:
            p = moves & -moves
            moves -= p
            if not direct_tiny(occupied | p, possible ^ p):
                return True
        return False

    tiny_count, max_stones, high_bits = 0, 0, 0
    for record in records[1:]:
        occupied = record['occupied_lo'] + (record['occupied_hi'] << 64)
        legal = record['legal_lo'] + (record['legal_hi'] << 64)
        canonical = record['canonical_lo'] + (record['canonical_hi'] << 64)
        assert not (occupied | legal) & ~geometry.all
        assert geometry.legal(occupied) == legal
        assert geometry.canonical(occupied) == canonical
        assert rank(canonical, 81) == record['rank']
        assert unrank(record['rank'], 81) == canonical
        if record['misere'] >= 0:
            assert legal.bit_count() <= 6
            assert direct_tiny(occupied, legal) == bool(record['misere'])
            tiny_count += 1
        high_bits += bool(occupied >> 64)
        max_stones = max(max_stones, occupied.bit_count())
    return {
        'geometric_entities_with_at_least_four_points': len(geometry.entities),
        'forbidden_quadruples': geometry.forbidden_count,
        'probes_verified': samples,
        'tiny_endgames_verified': tiny_count,
        'occupied_high_bits_exercised': high_bits,
        'maximum_probe_stones': max_stones,
        'rank_upper_exclusive': sum(comb(81, j) for j in range(21)),
    }


def validate_small_proof(n, path, expected_win):
    geometry = Geometry(n)
    legal = lru_cache(None)(geometry.legal)
    canonical = lru_cache(None)(geometry.canonical)
    data = path.read_bytes()
    assert data and len(data) % 17 == 0
    verified = {}
    # The exporter writes native-endian uint64, without padding between records.
    for lo, hi, win in struct.iter_unpack('=QQB', data):
        occupied = lo + (hi << 64)
        assert win in (0, 1)
        assert canonical(occupied) == occupied and occupied not in verified
        children, moves = [], legal(occupied)
        while moves:
            p = moves & -moves
            moves -= p
            children.append(canonical(occupied | p))
        if not children:
            assert win == 1
        elif win:
            assert any(child in verified and not verified[child] for child in children)
        else:
            assert all(child in verified and verified[child] for child in children)
        verified[occupied] = bool(win)
    assert occupied == 0 and verified[0] == expected_win

    @lru_cache(None)
    def direct_root(occupied):
        moves = legal(occupied)
        if not moves:
            return True
        while moves:
            p = moves & -moves
            moves -= p
            if not direct_root(occupied | p):
                return True
        return False

    if n <= 4:
        assert direct_root(0) == verified[0]
    return {
        'n': n, 'forbidden_quadruples': geometry.forbidden_count,
        'proof_records': len(verified), 'verified_first_wins': verified[0],
        'independent_root_states': direct_root.cache_info().currsize,
    }


def compile_source(source, binary, compiler):
    subprocess.run([compiler, *FLAGS, str(source), '-o', str(binary)], check=True,
                   timeout=120)


def audit(work, compiler, samples):
    assert digest(SOURCE) == FROZEN_SHA256, 'solver changed; re-audit the new snapshot explicitly'
    source = SOURCE.read_text()
    domain_binary = work / 'domains'
    compile_source(DOMAIN_SOURCE, domain_binary, compiler)
    domain = subprocess.run([str(domain_binary)], check=True, capture_output=True,
                            text=True, timeout=30)
    assert domain.stdout.strip().endswith('PASS')
    small_results, unknown_results = [], []
    for n in (3, 4, 5, 9):
        assert source.count('N=9,V=N*N') == source.count('slots=201326611') == 1
        variant = source.replace('N=9,V=N*N', f'N={n},V=N*N').replace(
            'slots=201326611', 'slots=4000037')
        # 4,000,037 slots and a 1M search cap leave ample space for these
        # tiny certificates. No production source is modified.
        cpp, binary = work / f'n{n}.cpp', work / f'n{n}'
        cpp.write_text(variant)
        compile_source(cpp, binary, compiler)
        if n == 9:
            probes = work / 'probes.jsonl'
            with probes.open('w') as output:
                subprocess.run([str(binary), '--probe', str(samples)], check=True,
                               stdout=output, timeout=30)
            probe_result = validate_probes(probes, samples)
            trials = [('node_cap', '30', '1'), ('time_cap', '0.000000001', '1000000')]
        else:
            trials = [('normal', '30', '1000000')]
        for label, seconds, cap in trials:
            proof = work / f'n{n}_{label}.bin'
            process = subprocess.run([str(binary), str(proof), seconds, cap,
                                      str(n * n // 2)], capture_output=True,
                                     text=True, timeout=40)
            result = json.loads(process.stdout)
            if n == 9:
                assert process.returncode == 2
                assert result['complete'] is False and result['winner'] == 'UNKNOWN'
                reason = 'node cap reached' if label == 'node_cap' else 'wall time cap reached'
                assert reason in process.stderr and not proof.exists()
                unknown_results.append({
                    'guard': label, 'complete': False, 'winner': 'UNKNOWN',
                    'exit_code': 2, 'memo_size': result['memo_size'],
                    'proof_created': False,
                })
            else:
                assert process.returncode == 0 and result['complete'] is True
                assert result['independently_verified'] is False
                small_results.append(validate_small_proof(
                    n, proof, result['provisional_misere_first_wins']))
    return {
        'experiment': 'independent lightweight audit of bounded 9x9 solver',
        'nine_by_nine_root_status': 'UNKNOWN',
        'source_sha256': {path.name: digest(path) for path in
                          (SOURCE, DOMAIN_SOURCE, Path(__file__).resolve())},
        'compiler_flags': FLAGS, 'production_source_modified': False,
        'domain_checks': {
            'status': 'PASS', 'empty_rank': 0, 'highest_singleton_rank': 81,
            'lowest_twenty_stone_rank': 2143508038974053704,
            'highest_twenty_stone_rank': 6837944227813170423,
            'twenty_one_stones_rejected': True, 'outside_bit_81_rejected': True,
            'all_eight_transforms_preserve_board': True,
        },
        'independent_geometry_and_probes': probe_result,
        'small_board_certificates': small_results,
        'unknown_propagation': unknown_results,
    }


def main():
    if not __debug__:
        raise RuntimeError('run without -O: assertions are part of this audit')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--compiler', default='g++')
    parser.add_argument('--samples', type=int, default=1000)
    args = parser.parse_args()
    assert args.samples >= 1
    with tempfile.TemporaryDirectory(prefix='kyouen-nine-audit-') as directory:
        result = audit(Path(directory), args.compiler, args.samples)
    encoded = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end='')


if __name__ == '__main__':
    main()

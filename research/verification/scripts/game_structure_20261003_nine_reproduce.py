#!/usr/bin/env python3
"""Compile, validate primitives, and repeat the bounded 9x9 misere trial.

Exit code 2 from the search means UNKNOWN, and is an expected bounded result.
This runner does not certify a root outcome: even a complete exported proof
requires an independent certificate checker before a winner may be claimed.
Large temporary artifacts stay in --work-dir, not in the repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import time

from game_structure_20261003_nine_validate import validate


HERE = Path(__file__).resolve().parent
SOURCES = ['game_structure_20261003_nine.cpp',
           'game_structure_20261003_nine_validate.py',
           'game_structure_20261003_nine_reproduce.py']


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=800)
    parser.add_argument('--node-cap', type=int, default=130000000)
    parser.add_argument('--opening', type=int, default=40)
    parser.add_argument('--samples', type=int, default=1000)
    parser.add_argument('--collect-existing', action='store_true')
    args = parser.parse_args()
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    binary = work / 'search'
    compile_command = ['g++', '-O3', '-std=c++17', '-Wall', '-Wextra',
                       str(HERE / SOURCES[0]), '-o', str(binary)]
    if not args.collect_existing:
        subprocess.run(compile_command, check=True)
        with (work / 'probes.jsonl').open('w') as out:
            subprocess.run([str(binary), '--probe', str(args.samples)],
                           check=True, stdout=out)
    validation = validate(work / 'probes.jsonl')
    if not args.collect_existing:
        # A previous run's proof must not be attributed to an interrupted run.
        (work / 'proof.bin').unlink(missing_ok=True)
        previous = resource.getrusage(resource.RUSAGE_CHILDREN)
        start = time.monotonic()
        with (work / 'search.json').open('w') as out, (work / 'search.log').open('w') as err:
            try:
                process = subprocess.run([str(binary), str(work / 'proof.bin'),
                                          str(args.seconds), str(args.node_cap),
                                          str(args.opening)], stdout=out, stderr=err,
                                         timeout=args.seconds + 120)
                code = process.returncode
            except subprocess.TimeoutExpired:
                code = 'external_watchdog'
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        resources = {'exit_code': code, 'elapsed_seconds': time.monotonic() - start,
                     'max_rss_kib': usage.ru_maxrss,
                     'user_seconds': usage.ru_utime - previous.ru_utime,
                     'system_seconds': usage.ru_stime - previous.ru_stime}
        (work / 'resources.json').write_text(json.dumps(resources, indent=2) + '\n')
        if code not in (0, 2):
            # A crash or external stop cannot be interpreted as a game result.
            (work / 'search.json').write_text(json.dumps({
                'n': 9, 'complete': False, 'winner': 'UNKNOWN',
                'interruption': code}) + '\n')
    search = json.loads((work / 'search.json').read_text())
    resources = json.loads((work / 'resources.json').read_text())
    assert search['n'] == 9
    assert search['complete'] or search['winner'] == 'UNKNOWN'
    if search['complete']:
        assert search['independently_verified'] is False
    result = {
        'experiment': 'bounded 9x9 misere root search',
        'root_status': 'UNVERIFIED' if search['complete'] else 'UNKNOWN',
        'parameters': {'seconds': args.seconds, 'search_memo_cap': args.node_cap,
                       'opening_point': args.opening, 'samples': args.samples,
                       'hash_slots': 201326611, 'max_encoded_stones': 20,
                       'tiny_cache_type_cap': 2000000},
        'source_sha256': {name: digest(HERE / name) for name in SOURCES},
        'compiler_flags': compile_command[1:5],
        'primitive_validation': validation,
        'probe_sha256': digest(work / 'probes.jsonl'),
        'search': search,
        'resources': resources,
        'proof': {'exists': (work / 'proof.bin').exists(), 'independently_verified': False},
    }
    if (work / 'proof.bin').exists():
        result['proof'].update(bytes=(work / 'proof.bin').stat().st_size,
                               sha256=digest(work / 'proof.bin'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'root_status': result['root_status'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()

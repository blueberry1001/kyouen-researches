#!/usr/bin/env python3
"""Stage 2: B572 jump vs max nimber; B578 shared winning move symdiff."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kyouen_core import board_square


def main():
    out = {}

    # --- B572 ---
    print('=== B572 one-stone exchange jump ===')
    b572 = {}
    for n, max_sz in ((4, 6), (5, 5)):
        board = board_square(n)
        grundy = board.solve_grundy()
        max_nimber = max(grundy.values()) if grundy else 0
        max_jump = 0
        jump_rec = None
        n_pairs = 0
        for occ in grundy:
            if occ == 0 or occ.bit_count() > max_sz:
                continue
            bits = [i for i in range(board.V) if (occ >> i) & 1]
            g0 = grundy[occ]
            for i in bits:
                base = occ ^ (1 << i)
                for j in range(board.V):
                    if (base >> j) & 1:
                        continue
                    nxt = base | (1 << j)
                    if nxt not in grundy:
                        continue
                    if not board.is_safe(nxt):
                        continue
                    n_pairs += 1
                    jump = abs(grundy[nxt] - g0)
                    if jump > max_jump:
                        max_jump = jump
                        jump_rec = {
                            'n': n,
                            'from': [board.points[k] for k in bits],
                            'remove': board.points[i],
                            'add': board.points[j],
                            'g_from': g0,
                            'g_to': grundy[nxt],
                            'jump': jump,
                        }
        b572[f'n{n}'] = {
            'max_nimber': max_nimber,
            'max_jump': max_jump,
            'n_exchange_pairs': n_pairs,
            'witness': jump_rec,
        }
        print(f'n={n}: max_nimber={max_nimber}, max_jump={max_jump}, pairs={n_pairs}')
    out['b572'] = b572

    # --- B578 ---
    print()
    print('=== B578 shared winning move symdiff ===')
    b578 = {}
    for n, max_sz in ((4, 6), (5, 5)):
        board = board_square(n)
        outcomes = board.solve_outcomes()
        by_win_move = defaultdict(list)
        for occ, val in outcomes.items():
            if val != 1:
                continue
            if occ == 0 or occ.bit_count() > max_sz:
                continue
            for v in board.legal_moves(occ):
                nxt = occ | (1 << v)
                if outcomes.get(nxt) == 0:
                    by_win_move[v].append(occ)
        max_sd = 0
        sd_rec = None
        n_groups = 0
        for v, positions in by_win_move.items():
            if len(positions) < 2:
                continue
            n_groups += 1
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    sd = (positions[i] ^ positions[j]).bit_count()
                    if sd > max_sd:
                        max_sd = sd
                        sd_rec = {
                            'n': n,
                            'win_move': board.points[v],
                            'A': [board.points[k] for k in range(board.V) if (positions[i] >> k) & 1],
                            'B': [board.points[k] for k in range(board.V) if (positions[j] >> k) & 1],
                            'symdiff': sd,
                        }
        b578[f'n{n}'] = {
            'max_symdiff': max_sd,
            'ratio': max_sd / (n * n),
            'n_groups': n_groups,
            'witness': sd_rec,
        }
        print(f'n={n}: max_symdiff={max_sd} ({max_sd}/{n*n}={max_sd/(n*n):.2f}), groups={n_groups}')
    out['b578'] = b578

    path = Path(__file__).resolve().parent.parent / 'round5_b551_b600_followup.json'
    data = {}
    if path.exists():
        with open(path) as f:
            data = json.load(f)
    data.update(out)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print('wrote', path)


if __name__ == '__main__':
    main()

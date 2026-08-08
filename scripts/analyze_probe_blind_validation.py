#!/usr/bin/env python3
"""Analyze pre-registered blind validation of fixed probe ranking rules.

Inputs:
    results/10x10/blind-probe-parent-selection.csv
    results/10x10/blind_probe_children/children_<parent>_batch<N>.txt
    results/10x10/blind_probe_children/probe_<parent>_batch<N>_<budget>.csv
    results/10x10/blind_probe_children/exact_<parent>_batch<N>.csv

Outputs:
    results/10x10/blind-probe-rankings.csv
    results/10x10/blind-probe-results.csv
    results/10x10/blind-probe-analysis.json
"""
import csv
import json
import random
import statistics
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
CHILDREN_DIR = REPO_ROOT / 'results' / '10x10' / 'blind_probe_children'
OUT_DIR = REPO_ROOT / 'results' / '10x10'
SELECTION_FILE = OUT_DIR / 'blind-probe-parent-selection.csv'

FIXED_RULES = {
    3: ('memo', 'desc', 1_000_000),
    4: ('memo', 'asc', 10_000),
    5: ('maxdepth', 'desc', 10_000),
}

RANDOM_ITERS = 1000
RANDOM_SEED = 42


def safe_parent(parent: str) -> str:
    return parent.replace(',', '_')


def state_key(state: str) -> tuple:
    """Canonical sorted tuple from '0-2-9-33' or '0,2,9,33'."""
    parts = state.replace('-', ',').split(',')
    return tuple(sorted(int(x) for x in parts if x != ''))


def load_selection(path: Path = SELECTION_FILE) -> list[dict]:
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def load_children_order(batch_path: Path) -> list[tuple]:
    """Return list of (move_index, state_key) in solver default order.

    The children input file lists one child state per line as comma-separated
    stones; the leading value is part of the state, not a move index.
    """
    order = []
    with batch_path.open() as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            state = state_key(line)
            order.append((idx, state))
    return order


def load_probe_csv(path: Path) -> dict[tuple, dict]:
    rows = {}
    with path.open(newline='') as f:
        for r in csv.DictReader(f):
            key = state_key(r['state'])
            rows[key] = r
    return rows


def load_exact_csv(path: Path) -> dict[tuple, dict]:
    rows = {}
    with path.open(newline='') as f:
        for r in csv.DictReader(f):
            key = state_key(r['state'])
            rows[key] = r
    return rows


def parse_int(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def parse_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def collect_batches(parent: str, stones: int):
    """Collect batch info for a parent.

    Returns a list of dicts:
        batch_index, order (list of (move, state)), probe_rows, exact_rows, probe_path, exact_path
    """
    safe = safe_parent(parent)
    budget = FIXED_RULES[stones][2]
    batch_files = sorted(CHILDREN_DIR.glob(f'children_{safe}_batch*.txt'))
    # If there are no batch files, fall back to the unbatched file.
    if not batch_files:
        batch_files = sorted(CHILDREN_DIR.glob(f'children_{safe}.txt'))

    batches = []
    for bp in batch_files:
        stem = bp.stem
        if '_batch' in stem:
            batch_index = int(stem.split('_batch')[-1])
        else:
            batch_index = 0
        probe_path = CHILDREN_DIR / f'probe_{safe}_batch{batch_index}_{budget}.csv'
        exact_path = CHILDREN_DIR / f'exact_{safe}_batch{batch_index}.csv'
        batches.append({
            'batch_index': batch_index,
            'order': load_children_order(bp),
            'probe_path': probe_path,
            'exact_path': exact_path,
            'probe_rows': load_probe_csv(probe_path) if probe_path.exists() else {},
            'exact_rows': load_exact_csv(exact_path) if exact_path.exists() else {},
        })
    return batches


def first_loss_position(order: list[tuple], outcomes: dict[tuple, str]) -> int:
    """1-indexed position of first LOSS in order; len+1 if none."""
    for i, (_, state) in enumerate(order, start=1):
        if outcomes.get(state) == 'LOSS':
            return i
    return len(order) + 1


def full_search_cost(order: list[tuple], visited: dict[tuple, int], outcomes: dict[tuple, str]) -> int:
    """Sum exact visited up to and including first LOSS; if no LOSS, sum all."""
    cost = 0
    for _, state in order:
        v = visited.get(state)
        if v is None:
            # Incomplete exact data; stop here and mark as None.
            return None
        cost += v
        if outcomes.get(state) == 'LOSS':
            return cost
    return cost


def fixed_rule_order(children: list[tuple], probe: dict[tuple, dict], feature: str, direction: str) -> list[tuple]:
    """Sort children by probe feature; ties broken by solver default move index."""
    def key(item):
        move, state = item
        row = probe.get(state, {})
        val = parse_float(row.get(feature))
        if val is None:
            val = -np.inf if direction == 'desc' else np.inf
        # For descending, negate value; for ascending, use value.
        sort_val = -val if direction == 'desc' else val
        return (sort_val, move)
    return sorted(children, key=key)


def random_stats(order: list[tuple], outcomes: dict[tuple, str], visited: dict[tuple, int], iters: int = RANDOM_ITERS, seed: int = RANDOM_SEED):
    rng = random.Random(seed)
    positions = []
    costs = []
    base = list(order)
    for _ in range(iters):
        shuffled = base[:]
        rng.shuffle(shuffled)
        pos = first_loss_position(shuffled, outcomes)
        cost = full_search_cost(shuffled, visited, outcomes)
        positions.append(pos)
        costs.append(cost if cost is not None else np.nan)
    arr_pos = np.array(positions, dtype=float)
    arr_cost = np.array(costs, dtype=float)
    n = len(outcomes)
    k = sum(1 for o in outcomes.values() if o == 'LOSS')
    theoretical_expected = (n + 1) / (k + 1) if k > 0 else None
    return {
        'expected_first_loss_position': float(np.mean(arr_pos)),
        'theoretical_expected_first_loss_position': theoretical_expected,
        'median_first_loss_position': float(np.median(arr_pos)),
        'q25_first_loss_position': float(np.percentile(arr_pos, 25)),
        'q75_first_loss_position': float(np.percentile(arr_pos, 75)),
        'median_total_cost_visited': float(np.nanmedian(arr_cost)),
        'mean_total_cost_visited': float(np.nanmean(arr_cost)),
        'distribution_positions': positions,
        'distribution_costs': costs,
    }


def percentile_in_distribution(value, distribution):
    return float(np.mean(np.array(distribution, dtype=float) <= value))


def evaluate_parent(parent: str, stones: int, selection: dict):
    feature, direction, budget = FIXED_RULES[stones]
    batches = collect_batches(parent, stones)
    if not batches:
        return None

    # Combine children across batches.  Preserve solver default ordering: batch index then move.
    all_children = []
    all_probe = {}
    all_exact = {}
    exact_complete_batches = 0
    ranking_generated_at = None
    outcome_revealed_at = None
    for b in batches:
        all_children.extend([(b['batch_index'], move, state) for move, state in b['order']])
        all_probe.update(b['probe_rows'])
        all_exact.update(b['exact_rows'])
        if b['probe_rows'] and b['probe_path'].exists():
            ts = b['probe_path'].stat().st_mtime
            ranking_generated_at = max(ranking_generated_at, ts) if ranking_generated_at else ts
        if b['exact_rows'] and b['exact_path'].exists():
            ts = b['exact_path'].stat().st_mtime
            outcome_revealed_at = max(outcome_revealed_at, ts) if outcome_revealed_at else ts
        if len(b['exact_rows']) == len(b['order']) and len(b['order']) > 0:
            exact_complete_batches += 1

    # If exact data is incomplete, restrict analysis to children with exact outcomes.
    # This yields an optimistic lower bound on first-loss position.
    children_with_exact = [(bi, m, s) for bi, m, s in all_children if s in all_exact]
    exact_complete = len(children_with_exact) == len(all_children) and len(all_children) > 0

    if not children_with_exact:
        return None

    outcomes = {s: all_exact[s].get('outcome') for _, _, s in children_with_exact}
    visited = {}
    for _, _, s in children_with_exact:
        v = parse_int(all_exact[s].get('visited'))
        if v is None:
            return None
        visited[s] = v

    loss_children = [s for s, o in outcomes.items() if o == 'LOSS']
    n_loss = len(loss_children)

    # Solver default order restricted to children with exact outcomes.
    solver_order = [(m, s) for _, m, s in children_with_exact]
    # Fixed rule order uses probe values from all children if available; falls back.
    fixed_order = fixed_rule_order([(m, s) for _, m, s in children_with_exact], all_probe, feature, direction)

    fixed_pos = first_loss_position(fixed_order, outcomes)
    solver_pos = first_loss_position(solver_order, outcomes)
    oracle_pos = 1 if n_loss > 0 else len(children_with_exact) + 1

    fixed_cost = full_search_cost(fixed_order, visited, outcomes)
    solver_cost = full_search_cost(solver_order, visited, outcomes)
    # Oracle: cheapest LOSS child visited.
    if n_loss > 0:
        oracle_cost = min(visited[s] for s in loss_children)
    else:
        oracle_cost = sum(visited.values())

    random_results = random_stats(solver_order, outcomes, visited)
    fixed_percentile = percentile_in_distribution(fixed_pos, random_results['distribution_positions'])

    probe_cost_all = budget * len(children_with_exact)

    def total(cost):
        return cost + probe_cost_all if cost is not None else None

    result = {
        'parent': parent,
        'stones': stones,
        'lopo_source_used': str(selection.get('lopo_source_used', '')).lower() == 'true',
        'child_count': len(children_with_exact),
        'loss_child_count': n_loss,
        'fixed_rule_feature': feature,
        'fixed_rule_direction': direction,
        'fixed_rule_budget': budget,
        'fixed_first_loss_position': fixed_pos,
        'solver_default_first_loss_position': solver_pos,
        'oracle_first_loss_position': oracle_pos,
        'random_expected_first_loss_position': random_results['expected_first_loss_position'],
        'theoretical_expected_first_loss_position': random_results['theoretical_expected_first_loss_position'],
        'random_median_first_loss_position': random_results['median_first_loss_position'],
        'random_q25_first_loss_position': random_results['q25_first_loss_position'],
        'random_q75_first_loss_position': random_results['q75_first_loss_position'],
        'fixed_percentile_among_random': fixed_percentile,
        'probe_cost_all_visited': probe_cost_all,
        'fixed_full_search_to_first_loss_visited': fixed_cost,
        'solver_default_full_search_to_first_loss_visited': solver_cost,
        'oracle_full_search_to_first_loss_visited': oracle_cost,
        'fixed_total_cost_visited': total(fixed_cost),
        'random_median_total_cost_visited': random_results['median_total_cost_visited'] + probe_cost_all,
        'random_mean_total_cost_visited': random_results['mean_total_cost_visited'] + probe_cost_all,
        'solver_default_total_cost_visited': total(solver_cost),
        'oracle_total_cost_visited': oracle_cost + probe_cost_all,
        'exact_complete': exact_complete,
        'ranking_generated_at': datetime.fromtimestamp(ranking_generated_at).isoformat() if ranking_generated_at else None,
        'outcome_revealed_at': datetime.fromtimestamp(outcome_revealed_at).isoformat() if outcome_revealed_at else None,
        'selection_reason': selection.get('selection_reason', ''),
        'selected_before_probe': selection.get('selected_before_probe', ''),
        'source': selection.get('source', ''),
        'notes': (selection.get('notes', '') + ('; PARTIAL_EXACT: only some batches classified' if not exact_complete else '')).strip('; '),
    }

    # Build per-child ranking records.
    fixed_rank = {s: i for i, (_, s) in enumerate(fixed_order, start=1)}
    solver_rank = {s: i for i, (_, s) in enumerate(solver_order, start=1)}
    child_records = []
    for _, move, state in children_with_exact:
        row = {
            'parent': parent,
            'stones': stones,
            'child_state': '-'.join(str(x) for x in state),
            'move_index': move,
            'fixed_rank': fixed_rank[state],
            'solver_default_rank': solver_rank[state],
            'outcome': outcomes.get(state),
            'exact_visited': visited.get(state),
            'probe_memo': parse_int(all_probe.get(state, {}).get('memo')),
            'probe_maxdepth': parse_int(all_probe.get(state, {}).get('maxdepth')),
            'probe_budget': budget,
        }
        child_records.append(row)

    return result, child_records


def aggregate(results: list[dict]):
    agg = {}
    for r in results:
        s = r['stones']
        agg.setdefault(s, []).append(r)
    stones_summary = {}
    for s, group in agg.items():
        group = [r for r in group if r['loss_child_count'] > 0]
        if not group:
            continue
        fixed_positions = [r['fixed_first_loss_position'] for r in group]
        random_medians = [r['random_median_first_loss_position'] for r in group]
        solver_positions = [r['solver_default_first_loss_position'] for r in group]
        fixed_costs = [r['fixed_total_cost_visited'] for r in group if r['fixed_total_cost_visited'] is not None]
        random_costs = [r['random_median_total_cost_visited'] for r in group if r['random_median_total_cost_visited'] is not None]
        solver_costs = [r['solver_default_total_cost_visited'] for r in group if r['solver_default_total_cost_visited'] is not None]
        better_than_random = sum(1 for r in group if r['fixed_first_loss_position'] < r['random_median_first_loss_position'])
        worse_than_random = sum(1 for r in group if r['fixed_first_loss_position'] > r['random_median_first_loss_position'])
        equal_random = sum(1 for r in group if r['fixed_first_loss_position'] == r['random_median_first_loss_position'])
        better_than_solver = sum(1 for r in group if r['fixed_first_loss_position'] < r['solver_default_first_loss_position'])
        worse_than_solver = sum(1 for r in group if r['fixed_first_loss_position'] > r['solver_default_first_loss_position'])
        equal_solver = sum(1 for r in group if r['fixed_first_loss_position'] == r['solver_default_first_loss_position'])
        better_cost_than_random = sum(1 for r in group if r['fixed_total_cost_visited'] is not None and r['random_median_total_cost_visited'] is not None and r['fixed_total_cost_visited'] < r['random_median_total_cost_visited'])
        better_cost_than_solver = sum(1 for r in group if r['fixed_total_cost_visited'] is not None and r['solver_default_total_cost_visited'] is not None and r['fixed_total_cost_visited'] < r['solver_default_total_cost_visited'])
        stones_summary[s] = {
            'n_parents': len(group),
            'fixed_first_loss_positions': fixed_positions,
            'fixed_first_loss_median': float(np.median(fixed_positions)),
            'fixed_first_loss_mean': float(np.mean(fixed_positions)),
            'random_median_first_loss_positions': random_medians,
            'random_median_first_loss_median': float(np.median(random_medians)),
            'solver_default_first_loss_positions': solver_positions,
            'solver_default_first_loss_median': float(np.median(solver_positions)),
            'fixed_total_cost_median': float(np.median(fixed_costs)) if fixed_costs else None,
            'random_median_total_cost_median': float(np.median(random_costs)) if random_costs else None,
            'solver_default_total_cost_median': float(np.median(solver_costs)) if solver_costs else None,
            'better_than_random_count': better_than_random,
            'worse_than_random_count': worse_than_random,
            'equal_random_count': equal_random,
            'better_than_solver_count': better_than_solver,
            'worse_than_solver_count': worse_than_solver,
            'equal_solver_count': equal_solver,
            'better_cost_than_random_count': better_cost_than_random,
            'better_cost_than_solver_count': better_cost_than_solver,
        }
    return stones_summary


def main():
    exclude_lopo_source = '--exclude-lopo-source' in sys.argv
    selection_rows = load_selection()
    # Assert every evaluated parent was selected before probe.
    bad = [r['parent'] for r in selection_rows if str(r.get('selected_before_probe')).lower() != 'true']
    if bad:
        raise RuntimeError(f"Parents not selected before probe: {bad}")
    if exclude_lopo_source:
        before = len(selection_rows)
        selection_rows = [r for r in selection_rows if str(r.get('lopo_source_used')).lower() != 'true']
        print(f"Excluded {before - len(selection_rows)} parents with LOPO-used source.")
    selection = {r['parent']: r for r in selection_rows}
    results = []
    child_records = []
    lopo_source_parents = []
    for parent, info in selection.items():
        stones = int(info['stones'])
        if stones not in FIXED_RULES:
            print(f"Skip {parent}: unsupported stones {stones}")
            continue
        res = evaluate_parent(parent, stones, info)
        if res is None:
            print(f"Skip {parent}: no evaluable children")
            continue
        result, records = res
        results.append(result)
        child_records.extend(records)
        print(f"{parent} stones={stones}: fixed_pos={result['fixed_first_loss_position']} "
              f"random_median={result['random_median_first_loss_position']} "
              f"solver={result['solver_default_first_loss_position']} "
              f"loss={result['loss_child_count']}/{result['child_count']} "
              f"exact_complete={result['exact_complete']}")

    if not results:
        print("No evaluable parents.")
        return

    # Write rankings CSV.
    rankings_path = OUT_DIR / 'blind-probe-rankings.csv'
    if child_records:
        fieldnames = [
            'parent', 'stones', 'child_state', 'move_index', 'fixed_rank',
            'solver_default_rank', 'outcome', 'exact_visited', 'probe_memo',
            'probe_maxdepth', 'probe_budget',
        ]
        with rankings_path.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(child_records)
        print(f"Wrote {rankings_path}")

    # Write results CSV.
    results_path = OUT_DIR / 'blind-probe-results.csv'
    fieldnames = [
        'parent', 'stones', 'lopo_source_used', 'child_count', 'loss_child_count', 'fixed_rule_feature',
        'fixed_rule_direction', 'fixed_rule_budget', 'fixed_first_loss_position',
        'solver_default_first_loss_position', 'oracle_first_loss_position',
        'random_expected_first_loss_position', 'theoretical_expected_first_loss_position',
        'random_median_first_loss_position', 'random_q25_first_loss_position',
        'random_q75_first_loss_position',
        'fixed_percentile_among_random', 'probe_cost_all_visited',
        'fixed_full_search_to_first_loss_visited', 'solver_default_full_search_to_first_loss_visited',
        'oracle_full_search_to_first_loss_visited', 'fixed_total_cost_visited',
        'random_median_total_cost_visited', 'random_mean_total_cost_visited',
        'solver_default_total_cost_visited', 'oracle_total_cost_visited',
        'exact_complete', 'ranking_generated_at', 'outcome_revealed_at',
        'selection_reason', 'selected_before_probe', 'source', 'notes',
    ]
    with results_path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)
    print(f"Wrote {results_path}")

    # Write analysis JSON.
    analysis = {
        'description': 'Blind validation of pre-registered fixed probe ranking rules',
        'fixed_rules': {str(k): {'feature': v[0], 'direction': v[1], 'budget': v[2]} for k, v in FIXED_RULES.items()},
        'random_iterations': RANDOM_ITERS,
        'random_seed': RANDOM_SEED,
        'n_parents': len(results),
        'parents': [r['parent'] for r in results],
        'parent_results': results,
        'stones_aggregate': aggregate(results),
    }
    analysis_path = OUT_DIR / 'blind-probe-analysis.json'
    with analysis_path.open('w') as f:
        json.dump(analysis, f, indent=2, default=str)
    print(f"Wrote {analysis_path}")


if __name__ == '__main__':
    main()

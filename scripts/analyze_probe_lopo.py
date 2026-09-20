#!/usr/bin/env python3
"""Leave-One-Parent-Out validation of stones-specific probe ranking rules.

This script strictly evaluates whether the stones-specific probe rules discovered
in the previous report generalize to unknown parent positions.  No information
about the evaluation parent (feature choice, budget, sign, threshold/model) is
used during rule selection.

Outputs:
    results/10x10/probe-lopo-results.csv
    results/10x10/probe-lopo-analysis.json
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import warnings
from scipy.stats import spearmanr, ConstantInputWarning

warnings.filterwarnings('ignore', category=ConstantInputWarning)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / 'results' / '10x10'
BUDGETS = [10_000, 100_000, 1_000_000]
RANDOM_ITERS = 1000
RANDOM_SEED = 42
MIN_TRAIN_LOSS_PARENTS = 1


def load_data():
    df = pd.read_csv(OUT_DIR / 'probe-features.csv')
    # The previous study restricted analysis to 10k/100k/1M budgets.
    df = df[df['probe_budget'].isin(BUDGETS)].copy()

    numeric_cols = [
        'final_visited', 'visited', 'memo', 'seconds', 'maxdepth',
        'memo_per_visited', 'visited_per_second',
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    df['loss'] = (df['outcome'] == 'LOSS').astype(int)
    df['parent_key'] = df['parent'].fillna('unknown')
    df['stones'] = pd.to_numeric(df['stones'], errors='coerce')

    # Depth features.
    for d in range(20):
        c = f'depth_visited_{d}'
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # Memo fill features.
    for d in range(9, 22):
        used = pd.to_numeric(df.get(f'memo_used_d{d}'), errors='coerce')
        cap = pd.to_numeric(df.get(f'memo_capacity_d{d}'), errors='coerce')
        df[f'memo_fill_d{d}'] = used / cap
    fill_cols = [f'memo_fill_d{d}' for d in range(9, 22)]
    df['max_memo_fill'] = df[fill_cols].max(axis=1)

    return df


def feature_candidates(df):
    base = [
        'memo', 'visited', 'maxdepth', 'seconds',
        'memo_per_visited', 'visited_per_second', 'max_memo_fill',
    ]
    depths = [c for c in df.columns if c.startswith('depth_visited_')]
    fills = [c for c in df.columns if c.startswith('memo_fill_d')]
    candidates = [c for c in base + depths + fills if c in df.columns]
    # Drop candidates that are constant/NaN in the full data.
    valid = []
    for c in candidates:
        if df[c].notna().sum() >= 10 and df[c].nunique(dropna=True) > 1:
            valid.append(c)
    return valid


def first_loss_position(order, loss_arr):
    """Return 1-indexed position of first loss in `order`, or len+1 if none."""
    for i, idx in enumerate(order):
        if loss_arr[idx]:
            return i + 1
    return len(loss_arr) + 1


def evaluate_ranking(g, feature, direction):
    """Return first-loss position for group `g` sorted by `feature`."""
    g = g.dropna(subset=[feature]).copy()
    if len(g) == 0:
        return None
    loss_arr = g['loss'].values.astype(bool)
    if not loss_arr.any():
        return None
    order = np.argsort(g[feature].values, kind='stable')
    if direction == 'desc':
        order = order[::-1]
    return first_loss_position(order, loss_arr)


def full_search_cost_to_first_loss(g, feature, direction):
    """Sum final_visited up to and including the first LOSS in the ranking."""
    g = g.dropna(subset=[feature, 'final_visited']).copy()
    if len(g) == 0:
        return None
    loss_arr = g['loss'].values.astype(bool)
    if not loss_arr.any():
        return g['final_visited'].sum()  # would solve all children
    order = np.argsort(g[feature].values, kind='stable')
    if direction == 'desc':
        order = order[::-1]
    cost = 0.0
    for idx in order:
        cost += g['final_visited'].iloc[idx]
        if loss_arr[idx]:
            break
    return cost


def random_first_loss_stats(g, random_state=RANDOM_SEED):
    """Return distribution of first-loss position and full-search cost."""
    g = g.copy()
    loss_arr = g['loss'].values.astype(bool)
    if not loss_arr.any():
        return None
    n = len(g)
    rng = np.random.default_rng(random_state)
    positions = np.empty(RANDOM_ITERS, dtype=np.float64)
    costs = np.empty(RANDOM_ITERS, dtype=np.float64)
    final_arr = g['final_visited'].values
    for i in range(RANDOM_ITERS):
        order = rng.permutation(n)
        pos = first_loss_position(order, loss_arr)
        positions[i] = pos
        cost = 0.0
        for idx in order:
            cost += final_arr[idx]
            if loss_arr[idx]:
                break
        costs[i] = cost
    return {
        'positions': positions,
        'costs': costs,
        'mean_pos': float(np.mean(positions)),
        'median_pos': float(np.median(positions)),
        'q25_pos': float(np.percentile(positions, 25)),
        'q75_pos': float(np.percentile(positions, 75)),
        'mean_cost': float(np.mean(costs)),
        'median_cost': float(np.median(costs)),
        'q25_cost': float(np.percentile(costs, 25)),
        'q75_cost': float(np.percentile(costs, 75)),
    }


def percentile_in_distribution(value, distribution):
    """Fraction of `distribution` values <= `value`."""
    return float(np.mean(distribution <= value))


def select_rule(train_df, stones_val, features, restrict_budget=None):
    """Select the best (feature, budget, direction) using training parents only.

    If `stones_val` is None, ignore stones and use all LOSS-containing training
    parents.  The selection criterion is the mean first-LOSS-position across
    LOSS-containing parents (lower is better), with median as tie-breaker and
    top-20% LOSS recall as final tie-breaker.
    """
    sub = train_df.copy()
    if stones_val is not None:
        sub = sub[sub['stones'] == stones_val].copy()

    loss_parents = sub[sub['loss'] == 1]['parent_key'].unique()
    if len(loss_parents) < MIN_TRAIN_LOSS_PARENTS:
        return None

    budgets = [restrict_budget] if restrict_budget else BUDGETS
    best = None
    best_score = np.inf

    for budget in budgets:
        bsub = sub[sub['probe_budget'] == budget].copy()
        if len(bsub) == 0:
            continue
        for feature in features:
            if bsub[feature].isna().all():
                continue
            for direction in ['desc', 'asc']:
                positions = []
                recalls_20 = []
                for parent in loss_parents:
                    g = bsub[bsub['parent_key'] == parent].copy()
                    pos = evaluate_ranking(g, feature, direction)
                    if pos is not None:
                        positions.append(pos)
                        # top-20% recall for tie-breaking
                        g_sorted = g.sort_values(feature, ascending=(direction == 'asc'))
                        n = len(g_sorted)
                        k = max(1, int(n * 0.20))
                        tp = g_sorted.head(k)['loss'].sum()
                        recall = tp / g_sorted['loss'].sum() if g_sorted['loss'].sum() else 0
                        recalls_20.append(recall)
                if len(positions) == 0:
                    continue
                mean_pos = float(np.mean(positions))
                median_pos = float(np.median(positions))
                mean_recall = float(np.mean(recalls_20))
                # Prefer lower mean, then lower median, then higher recall.
                better = False
                if best is None:
                    better = True
                elif mean_pos < best_score - 1e-9:
                    better = True
                elif abs(mean_pos - best_score) < 1e-9:
                    if median_pos < best['median_pos'] - 1e-9:
                        better = True
                    elif abs(median_pos - best['median_pos']) < 1e-9:
                        if mean_recall > best['mean_recall_20'] + 1e-9:
                            better = True
                if better:
                    best_score = mean_pos
                    best = {
                        'stones': stones_val,
                        'budget': budget,
                        'feature': feature,
                        'direction': direction,
                        'mean_pos': mean_pos,
                        'median_pos': median_pos,
                        'mean_recall_20': mean_recall,
                        'n_train_loss_parents': int(len(loss_parents)),
                        'train_loss_parents': sorted(loss_parents.tolist()),
                        'train_positions': [float(p) for p in positions],
                    }
    return best


def build_fixed_rules(all_train_folds_rules):
    """Build a simple fixed rule per stones by majority vote across training folds.

    Returns dict stones -> rule, using the most frequently selected
    (feature, budget, direction).  Ties broken by lower mean first-loss position.
    """
    by_stones = defaultdict(list)
    for rule in all_train_folds_rules:
        if rule['stones'] is None:
            continue
        by_stones[rule['stones']].append(rule)

    fixed = {}
    for stones, rules in by_stones.items():
        if not rules:
            continue
        # Count (feature, budget, direction) frequency.
        counts = defaultdict(list)
        for r in rules:
            key = (r['feature'], r['budget'], r['direction'])
            counts[key].append(r)
        best_key = None
        best_count = -1
        best_mean = np.inf
        for key, rs in counts.items():
            cnt = len(rs)
            mean_pos = np.mean([r['mean_pos'] for r in rs])
            if cnt > best_count or (cnt == best_count and mean_pos < best_mean):
                best_key = key
                best_count = cnt
                best_mean = mean_pos
        feature, budget, direction = best_key
        fixed[int(stones)] = {
            'feature': feature,
            'budget': budget,
            'direction': direction,
            'frequency': best_count,
            'total_folds': len(rules),
            'mean_train_pos': float(best_mean),
        }
    return fixed


def four_stone_per_parent_analysis(df):
    """Hypothesis testing for the 4-stone negative correlation phenomenon."""
    records = []
    budget = 100_000  # use the budget where the original observation was made
    sub = df[(df['stones'] == 4) & (df['probe_budget'] == budget)].copy()
    parents = sub['parent_key'].unique()
    for parent in parents:
        g = sub[sub['parent_key'] == parent].copy()
        g = g.dropna(subset=['memo', 'final_visited', 'loss'])
        if len(g) < 3:
            continue
        rho_memo_final, p_memo_final = spearmanr(g['memo'], g['final_visited'])
        rho_memo_loss, p_memo_loss = spearmanr(g['memo'], g['loss'])
        losses = g[g['loss'] == 1]
        wins = g[g['loss'] == 0]
        memo_loss_median = losses['memo'].median() if len(losses) else np.nan
        memo_win_median = wins['memo'].median() if len(wins) else np.nan
        # Rank of LOSS children in descending memo (high memo first).
        g_sorted_desc = g.sort_values('memo', ascending=False).reset_index(drop=True)
        loss_ranks_desc = (g_sorted_desc[g_sorted_desc['loss'] == 1].index + 1).to_series()
        # Rank of LOSS children in ascending memo (low memo first).
        g_sorted_asc = g.sort_values('memo', ascending=True).reset_index(drop=True)
        loss_ranks_asc = (g_sorted_asc[g_sorted_asc['loss'] == 1].index + 1).to_series()
        records.append({
            'parent': parent,
            'n_children': len(g),
            'n_loss': int(g['loss'].sum()),
            'memo_vs_final_rho': float(rho_memo_final) if not math.isnan(rho_memo_final) else None,
            'memo_vs_final_pvalue': float(p_memo_final) if not math.isnan(p_memo_final) else None,
            'memo_vs_loss_rho': float(rho_memo_loss) if not math.isnan(rho_memo_loss) else None,
            'memo_vs_loss_pvalue': float(p_memo_loss) if not math.isnan(p_memo_loss) else None,
            'memo_loss_median': float(memo_loss_median) if not math.isnan(memo_loss_median) else None,
            'memo_win_median': float(memo_win_median) if not math.isnan(memo_win_median) else None,
            'loss_median_rank_desc': float(loss_ranks_desc.median()) if len(loss_ranks_desc) else None,
            'loss_median_rank_asc': float(loss_ranks_asc.median()) if len(loss_ranks_asc) else None,
        })
    return pd.DataFrame(records)


def stones_sign_analysis(df, features):
    """For each stones, compute correlation with final visited, correlation with LOSS,
    and the actual effective direction for first-LOSS discovery."""
    records = []
    for stones_val in sorted(df['stones'].dropna().unique()):
        sub = df[df['stones'] == stones_val].copy()
        for budget in BUDGETS:
            bsub = sub[sub['probe_budget'] == budget].copy()
            if len(bsub) < 5:
                continue
            for feature in features:
                g = bsub.dropna(subset=[feature, 'final_visited', 'loss'])
                if len(g) < 5:
                    continue
                rho_final, p_final = spearmanr(g[feature], g['final_visited'])
                rho_loss, p_loss = spearmanr(g[feature], g['loss'])
                # Effective first-loss direction across LOSS-containing parents.
                loss_parents = g[g['loss'] == 1]['parent_key'].unique()
                pos_desc = []
                pos_asc = []
                for parent in loss_parents:
                    pg = g[g['parent_key'] == parent]
                    pdesc = evaluate_ranking(pg, feature, 'desc')
                    pasc = evaluate_ranking(pg, feature, 'asc')
                    if pdesc is not None:
                        pos_desc.append(pdesc)
                    if pasc is not None:
                        pos_asc.append(pasc)
                effective_direction = None
                if pos_desc and pos_asc:
                    effective_direction = 'desc' if np.mean(pos_desc) <= np.mean(pos_asc) else 'asc'
                records.append({
                    'stones': int(stones_val),
                    'budget': budget,
                    'feature': feature,
                    'n': len(g),
                    'n_loss_parents': int(len(loss_parents)),
                    'spearman_final_visited': float(rho_final) if not math.isnan(rho_final) else None,
                    'pvalue_final_visited': float(p_final) if not math.isnan(p_final) else None,
                    'spearman_loss': float(rho_loss) if not math.isnan(rho_loss) else None,
                    'pvalue_loss': float(p_loss) if not math.isnan(p_loss) else None,
                    'mean_first_loss_position_desc': float(np.mean(pos_desc)) if pos_desc else None,
                    'mean_first_loss_position_asc': float(np.mean(pos_asc)) if pos_asc else None,
                    'effective_direction': effective_direction,
                })
    return pd.DataFrame(records)


def data_all_best_feature_analysis(df, features):
    """Compute the data-leaking 'best per-stones rule' baseline for comparison.

    This is the procedure used in the previous report: choose the best
    feature/budget/direction per stones using ALL parents, then apply that rule
    back to the same parents.  It demonstrates how optimistic the earlier
    2.6 -> 1.2 figure was.
    """
    records = []
    best_rules = {}
    for stones_val in sorted(df['stones'].dropna().unique()):
        rule = select_rule(df, stones_val, features)
        if rule is None:
            continue
        best_rules[int(stones_val)] = rule
        budget = rule['budget']
        feature = rule['feature']
        direction = rule['direction']
        loss_parents = df[(df['stones'] == stones_val) & (df['loss'] == 1)]['parent_key'].unique()
        for parent in loss_parents:
            g = df[(df['parent_key'] == parent) & (df['stones'] == stones_val) &
                   (df['probe_budget'] == budget)].copy()
            pos = evaluate_ranking(g, feature, direction)
            records.append({
                'stones': int(stones_val),
                'parent': parent,
                'n_children': len(g),
                'n_loss': int(g['loss'].sum()),
                'data_all_rule': f"{budget}/{feature}/{direction}",
                'first_loss_position': pos,
            })
    df_res = pd.DataFrame(records)
    summary = {}
    if len(df_res):
        summary['overall'] = {
            'mean': float(df_res['first_loss_position'].mean()),
            'median': float(df_res['first_loss_position'].median()),
            'q25': float(df_res['first_loss_position'].quantile(0.25)),
            'q75': float(df_res['first_loss_position'].quantile(0.75)),
        }
        by_stones = {}
        for s, g in df_res.groupby('stones'):
            by_stones[int(s)] = {
                'mean': float(g['first_loss_position'].mean()),
                'median': float(g['first_loss_position'].median()),
                'n_parents': int(len(g)),
            }
        summary['by_stones'] = by_stones
    return df_res, best_rules, summary


def main():
    df = load_data()
    features = feature_candidates(df)
    parents = sorted(df['parent_key'].unique())

    # Data-leaking baseline for comparison with the previous report.
    data_all_df, data_all_rules, data_all_summary = data_all_best_feature_analysis(df, features)

    # Assert no child state belongs to multiple parents.
    state_parent_counts = df.groupby('state')['parent_key'].nunique()
    assert state_parent_counts.max() == 1, \
        f"Some states belong to multiple parents: {state_parent_counts[state_parent_counts > 1].index.tolist()}"

    lopo_records = []
    rule_records = []
    all_train_fold_rules = []

    for test_parent in parents:
        train_df = df[df['parent_key'] != test_parent].copy()
        test_df = df[df['parent_key'] == test_parent].copy()

        # Per-stones rule selection from training data only.
        stones_rules = {}
        for stones_val in sorted(train_df['stones'].dropna().unique()):
            rule = select_rule(train_df, stones_val, features)
            if rule is not None:
                # Mechanical no-leakage assertion.
                assert test_parent not in rule.get('train_loss_parents', []), \
                    f"Data leakage: test_parent {test_parent} in train_loss_parents for stones {stones_val}"
                stones_rules[int(stones_val)] = rule
                rule_records.append({
                    'test_parent': test_parent,
                    **{k: v for k, v in rule.items() if k != 'train_positions'},
                })
                all_train_fold_rules.append(rule)

        # Global fallback rule from all training LOSS parents.
        global_rule = select_rule(train_df, None, features)

        # Fixed rules derived from majority vote over all *other* folds will be
        # applied later; here just store the training rules.

        # Apply rules to each stones group of the test parent.
        for stones_val in sorted(test_df['stones'].dropna().unique()):
            g_all = test_df[test_df['stones'] == stones_val].copy()
            # We evaluate on the 100k budget rows for loss check, but ranking uses
            # the budget selected on training data.
            g_eval = g_all[g_all['probe_budget'] == 100_000].copy()
            loss_arr = g_eval['loss'].values.astype(bool)
            n_children = len(g_eval)
            n_loss = int(loss_arr.sum())
            if n_loss == 0:
                continue

            rule = stones_rules.get(int(stones_val), global_rule)
            if rule is None:
                # Should not happen because training always has some LOSS parents.
                continue

            budget = rule['budget']
            feature = rule['feature']
            direction = rule['direction']

            g_budget = g_all[g_all['probe_budget'] == budget].copy()
            # Ensure we are not accidentally using rows that don't exist for this budget.
            if len(g_budget) == 0:
                continue

            probe_pos = evaluate_ranking(g_budget, feature, direction)
            probe_cost_to_first = full_search_cost_to_first_loss(g_budget, feature, direction)

            # Oracle: sort by final_visited descending on 100k rows.
            oracle_pos = evaluate_ranking(g_eval, 'final_visited', 'desc')
            oracle_cost = full_search_cost_to_first_loss(g_eval, 'final_visited', 'desc')

            # Random baseline.
            rand = random_first_loss_stats(g_eval)
            random_pos_expected = (n_children + 1) / (n_loss + 1)  # analytic
            probe_percentile = percentile_in_distribution(probe_pos, rand['positions'])

            # Probe + full-search total cost.
            probe_cost_all = float(g_budget['visited'].sum())
            probe_seconds_all = float(g_budget['seconds'].sum())
            random_total_cost = float(rand['mean_cost'] + probe_cost_all)
            oracle_total_cost = float(oracle_cost + probe_cost_all) if oracle_cost is not None else None
            probe_total_cost = float(probe_cost_to_first + probe_cost_all) if probe_cost_to_first is not None else None

            # Random no-probe cost is just the random full-search cost.
            random_no_probe_cost = float(rand['mean_cost'])

            lopo_records.append({
                'test_parent': test_parent,
                'stones': int(stones_val),
                'n_children': n_children,
                'n_loss': n_loss,
                'selected_budget': budget,
                'selected_feature': feature,
                'selected_direction': direction,
                'probe_first_loss_position': probe_pos,
                'random_expected_first_loss_position': random_pos_expected,
                'random_median_first_loss_position': rand['median_pos'],
                'random_q25_first_loss_position': rand['q25_pos'],
                'random_q75_first_loss_position': rand['q75_pos'],
                'probe_percentile_among_random': probe_percentile,
                'oracle_first_loss_position': oracle_pos,
                'probe_cost_all_visited': probe_cost_all,
                'probe_cost_all_seconds': probe_seconds_all,
                'probe_full_search_to_first_loss_visited': probe_cost_to_first,
                'probe_total_cost_visited': probe_total_cost,
                'random_total_cost_visited': random_total_cost,
                'random_no_probe_cost_visited': random_no_probe_cost,
                'oracle_total_cost_visited': oracle_total_cost,
                'n_train_loss_parents_for_stones': rule.get('n_train_loss_parents'),
                'train_mean_first_loss_position': rule.get('mean_pos'),
                'train_median_first_loss_position': rule.get('median_pos'),
                'global_fallback': int(stones_val) not in stones_rules,
            })

    results_df = pd.DataFrame(lopo_records)
    rules_df = pd.DataFrame(rule_records)

    # Simple fixed rules: majority vote across all training folds.
    fixed_rules = build_fixed_rules(all_train_fold_rules)

    # Evaluate fixed rules with a second LOPO pass to avoid any leakage.
    fixed_records = []
    for test_parent in parents:
        test_df = df[df['parent_key'] == test_parent].copy()
        for stones_val in sorted(test_df['stones'].dropna().unique()):
            g_all = test_df[test_df['stones'] == stones_val].copy()
            g_eval = g_all[g_all['probe_budget'] == 100_000].copy()
            loss_arr = g_eval['loss'].values.astype(bool)
            n_children = len(g_eval)
            n_loss = int(loss_arr.sum())
            if n_loss == 0:
                continue
            rule = fixed_rules.get(int(stones_val))
            if rule is None:
                continue
            budget = rule['budget']
            feature = rule['feature']
            direction = rule['direction']
            g_budget = g_all[g_all['probe_budget'] == budget].copy()
            if len(g_budget) == 0:
                continue
            probe_pos = evaluate_ranking(g_budget, feature, direction)
            fixed_records.append({
                'test_parent': test_parent,
                'stones': int(stones_val),
                'n_children': n_children,
                'n_loss': n_loss,
                'fixed_budget': budget,
                'fixed_feature': feature,
                'fixed_direction': direction,
                'fixed_first_loss_position': probe_pos,
            })
    fixed_df = pd.DataFrame(fixed_records)

    # Aggregates.
    def summarize_positions(series, name):
        arr = np.array([x for x in series if x is not None and not math.isnan(x)])
        if len(arr) == 0:
            return {'count': 0}
        return {
            'count': int(len(arr)),
            'mean': float(np.mean(arr)),
            'median': float(np.median(arr)),
            'q25': float(np.percentile(arr, 25)),
            'q75': float(np.percentile(arr, 75)),
            'min': float(np.min(arr)),
            'max': float(np.max(arr)),
        }

    merged = results_df.merge(
        fixed_df[['test_parent', 'stones', 'fixed_first_loss_position']],
        on=['test_parent', 'stones'], how='left')

    improved = []
    worsened = []
    equal = []
    cost_improved = []
    for _, row in merged.iterrows():
        probe = row['probe_first_loss_position']
        rnd = row['random_median_first_loss_position']
        if probe < rnd - 1e-9:
            improved.append(1)
        elif probe > rnd + 1e-9:
            worsened.append(1)
        else:
            equal.append(1)
        if row['probe_total_cost_visited'] is not None and row['random_total_cost_visited'] is not None:
            if row['probe_total_cost_visited'] < row['random_total_cost_visited']:
                cost_improved.append(1)

    aggregate = {
        'n_folds': len(parents),
        'n_evaluated_parent_stones': len(results_df),
        'probe_first_loss_position': summarize_positions(
            results_df['probe_first_loss_position'], 'probe'),
        'random_median_first_loss_position': summarize_positions(
            results_df['random_median_first_loss_position'], 'random_median'),
        'random_expected_first_loss_position': summarize_positions(
            results_df['random_expected_first_loss_position'], 'random_expected'),
        'oracle_first_loss_position': summarize_positions(
            results_df['oracle_first_loss_position'], 'oracle'),
        'fixed_rule_first_loss_position': summarize_positions(
            merged['fixed_first_loss_position'], 'fixed'),
        'improved_over_random_median_count': int(len(improved)),
        'worsened_over_random_median_count': int(len(worsened)),
        'equal_to_random_median_count': int(len(equal)),
        'improved_fraction': float(len(improved) / len(merged)) if len(merged) else None,
        'worsened_fraction': float(len(worsened) / len(merged)) if len(merged) else None,
        'equal_fraction': float(len(equal) / len(merged)) if len(merged) else None,
        'cost_improved_over_random_count': int(len(cost_improved)),
        'cost_improved_fraction': float(len(cost_improved) / len(merged)) if len(merged) else None,
    }

    # Stones-level aggregates.
    stones_agg = {}
    for stones_val, g in results_df.groupby('stones'):
        improved_s = []
        worsened_s = []
        equal_s = []
        for _, row in g.iterrows():
            probe = row['probe_first_loss_position']
            rnd = row['random_median_first_loss_position']
            if probe < rnd - 1e-9:
                improved_s.append(1)
            elif probe > rnd + 1e-9:
                worsened_s.append(1)
            else:
                equal_s.append(1)
        stones_agg[int(stones_val)] = {
            'n_evaluated': int(len(g)),
            'probe': summarize_positions(g['probe_first_loss_position'], 'probe'),
            'random_median': summarize_positions(g['random_median_first_loss_position'], 'random_median'),
            'random_expected': summarize_positions(g['random_expected_first_loss_position'], 'random_expected'),
            'oracle': summarize_positions(g['oracle_first_loss_position'], 'oracle'),
            'improved_fraction': float(len(improved_s) / len(g)) if len(g) else None,
            'worsened_fraction': float(len(worsened_s) / len(g)) if len(g) else None,
            'equal_fraction': float(len(equal_s) / len(g)) if len(g) else None,
        }

    # Rule stability.
    stability = {}
    for stones_val, g in rules_df.groupby('stones'):
        combos = g.groupby(['feature', 'budget', 'direction']).size().reset_index(name='count')
        combos = combos.sort_values(['count', 'feature'], ascending=[False, True])
        top = combos.iloc[0]
        stability[int(stones_val)] = {
            'total_folds': int(len(g)),
            'most_common_feature': top['feature'],
            'most_common_budget': int(top['budget']),
            'most_common_direction': top['direction'],
            'most_common_frequency': int(top['count']),
            'most_common_fraction': float(top['count'] / len(g)),
            'all_selections': g[['test_parent', 'feature', 'budget', 'direction', 'mean_pos']].to_dict(orient='records'),
            'combination_counts': combos.to_dict(orient='records'),
        }

    # 4-stone analysis.
    four_analysis = four_stone_per_parent_analysis(df)
    four_summary = {
        'n_parents': int(len(four_analysis)),
        'n_parents_negative_memo_vs_final': int((four_analysis['memo_vs_final_rho'] < 0).sum()),
        'fraction_negative_memo_vs_final': float((four_analysis['memo_vs_final_rho'] < 0).mean()),
        'mean_memo_vs_final_rho': float(four_analysis['memo_vs_final_rho'].mean()),
        'median_memo_vs_final_rho': float(four_analysis['memo_vs_final_rho'].median()),
        'n_parents_loss_lower_memo_than_win': int(
            (four_analysis['memo_loss_median'] < four_analysis['memo_win_median']).sum()),
        'per_parent': four_analysis.to_dict(orient='records'),
    }

    # Sign analysis.
    sign_df = stones_sign_analysis(df, features)

    # Counterexamples.
    counterexamples = []
    for _, row in merged.iterrows():
        if row['probe_first_loss_position'] > row['random_q75_first_loss_position']:
            counterexamples.append({
                'type': 'probe_worse_than_random_q75',
                'test_parent': row['test_parent'],
                'stones': int(row['stones']),
                'probe_position': row['probe_first_loss_position'],
                'random_q75': row['random_q75_first_loss_position'],
                'rule': f"{row['selected_budget']}/{row['selected_feature']}/{row['selected_direction']}",
            })
        if row['probe_first_loss_position'] == row['n_children'] and row['n_children'] > 1:
            counterexamples.append({
                'type': 'loss_sent_to_last_place',
                'test_parent': row['test_parent'],
                'stones': int(row['stones']),
                'probe_position': row['probe_first_loss_position'],
                'rule': f"{row['selected_budget']}/{row['selected_feature']}/{row['selected_direction']}",
            })
    # Worst cases by position degradation.
    merged['degradation'] = merged['probe_first_loss_position'] - merged['random_median_first_loss_position']
    worst = merged.nlargest(5, 'degradation')
    for _, row in worst.iterrows():
        counterexamples.append({
            'type': 'top_degradation',
            'test_parent': row['test_parent'],
            'stones': int(row['stones']),
            'probe_position': row['probe_first_loss_position'],
            'random_median': row['random_median_first_loss_position'],
            'degradation': row['degradation'],
            'rule': f"{row['selected_budget']}/{row['selected_feature']}/{row['selected_direction']}",
        })

    # Cost summary.
    cost_summary = {
        'mean_probe_total_cost_visited': float(results_df['probe_total_cost_visited'].mean()),
        'mean_random_total_cost_visited': float(results_df['random_total_cost_visited'].mean()),
        'mean_random_no_probe_cost_visited': float(results_df['random_no_probe_cost_visited'].mean()),
        'mean_oracle_total_cost_visited': float(results_df['oracle_total_cost_visited'].mean()),
        'median_probe_total_cost_visited': float(results_df['probe_total_cost_visited'].median()),
        'median_random_total_cost_visited': float(results_df['random_total_cost_visited'].median()),
        'median_random_no_probe_cost_visited': float(results_df['random_no_probe_cost_visited'].median()),
        'median_oracle_total_cost_visited': float(results_df['oracle_total_cost_visited'].median()),
    }
    # Percentage improvement of probe vs random total cost.
    cost_ratios = []
    for _, row in results_df.iterrows():
        if row['random_total_cost_visited'] and row['random_total_cost_visited'] > 0:
            cost_ratios.append(
                (row['random_total_cost_visited'] - row['probe_total_cost_visited']) / row['random_total_cost_visited']
            )
    cost_summary['mean_cost_reduction_vs_random_total'] = float(np.mean(cost_ratios)) if cost_ratios else None
    cost_summary['median_cost_reduction_vs_random_total'] = float(np.median(cost_ratios)) if cost_ratios else None

    # Nested-CV feasibility note.
    nested_feasibility = {}
    for stones_val in sorted(df['stones'].dropna().unique()):
        n_loss_parents = df[(df['stones'] == stones_val) & (df['loss'] == 1)]['parent_key'].nunique()
        nested_feasibility[int(stones_val)] = {
            'n_loss_parents_total': int(n_loss_parents),
            'inner_lopo_possible_after_outer_leave_one_out': bool(n_loss_parents >= 3),
            'note': 'inner LOPO requires >=3 LOSS parents; outer leave-one-out leaves n-1.'
        }

    analysis = {
        'description': 'Leave-One-Parent-Out validation of stones-specific probe rules',
        'budgets': BUDGETS,
        'random_iterations': RANDOM_ITERS,
        'n_parents_total': len(parents),
        'parents': parents,
        'data_all_baseline': {
            'summary': data_all_summary,
            'rules': {int(k): {kk: vv for kk, vv in v.items() if kk != 'train_positions'}
                      for k, v in data_all_rules.items()},
            'note': 'Uses all parents for rule selection; demonstrates optimistic leakage baseline.',
        },
        'aggregate': aggregate,
        'stones_aggregate': stones_agg,
        'rule_stability': stability,
        'fixed_rules': fixed_rules,
        'four_stone_analysis': four_summary,
        'cost_summary': cost_summary,
        'counterexamples': counterexamples,
        'sign_analysis': sign_df.to_dict(orient='records'),
        'nested_cv_feasibility': nested_feasibility,
    }

    # Serialize.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUT_DIR / 'probe-lopo-results.csv', index=False)

    def to_json_safe(obj):
        if isinstance(obj, dict):
            return {k: to_json_safe(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [to_json_safe(v) for v in obj]
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating, float)):
            if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None
            val = float(obj)
            return val if not (math.isnan(val) or math.isinf(val)) else None
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return obj

    with open(OUT_DIR / 'probe-lopo-analysis.json', 'w', encoding='utf-8') as f:
        json.dump(to_json_safe(analysis), f, ensure_ascii=False, indent=2)

    print(f"LOPO results: {OUT_DIR / 'probe-lopo-results.csv'}")
    print(f"LOPO analysis: {OUT_DIR / 'probe-lopo-analysis.json'}")
    print(f"Evaluated {len(results_df)} parent-stones combinations across {len(parents)} folds.")


if __name__ == '__main__':
    main()

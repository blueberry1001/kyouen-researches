#!/usr/bin/env python3
"""Build the 10x10 search-cost-vs-outcome dataset and run the analysis."""
import csv
import os
import re
from collections import OrderedDict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / 'results' / '10x10'
PLOT_DIR = OUT_DIR / 'analysis'
PLOT_DIR.mkdir(parents=True, exist_ok=True)

# The solver commit that produced the most recent 10x10 results in this repo.
SOLVER_COMMIT = '3ab84cee8a138102c648209b81a93e4f9a7bd301'


def norm_state(s):
    return s.strip().strip('"')


def stone_count(s):
    return s.count(',') + 1 if s else 0


def parse_shrink_load(text):
    if text is None:
        return None, None
    m = re.search(r'shrink=(\d+)', text)
    n = re.search(r'load=(\d+)', text)
    return (int(m.group(1)) if m else None,
            int(n.group(1)) if n else None)


class DatasetBuilder:
    def __init__(self):
        self.rows = OrderedDict()  # state -> dict

    def add(self, state, outcome, visited=None, memo=None, seconds=None,
            maxdepth=None, source_file='', classification_source='',
            profile='standard', shrink=None, load=None, shared_memo=False,
            notes='', winning_move=None, commit=SOLVER_COMMIT):
        state = norm_state(state)
        if not state or outcome not in ('WIN', 'LOSS'):
            return
        if state in self.rows:
            return
        self.rows[state] = {
            'state': state,
            'outcome': outcome,
            'stones': stone_count(state),
            'visited': int(visited) if visited not in (None, '') else None,
            'memo': int(memo) if memo not in (None, '') else None,
            'runtime_seconds': float(seconds) if seconds not in (None, '') else None,
            'maxdepth': int(maxdepth) if maxdepth not in (None, '') else None,
            'source_file': source_file,
            'classification_source': classification_source,
            'profile': profile,
            'shrink': shrink,
            'load': load,
            'shared_memo': shared_memo,
            'notes': notes,
            'winning_move_to_loss': winning_move,
            'solver_commit': commit,
        }

    def load_csv(self, path, **defaults):
        with open(path, newline='', encoding='utf-8') as f:
            for d in csv.DictReader(f):
                self.add(source_file=str(path), **self._row_kwargs(d, defaults))

    def _row_kwargs(self, d, defaults):
        kw = dict(defaults)
        kw.setdefault('state', d.get('state', d.get('child_state', d.get('parent_state', ''))))
        kw.setdefault('outcome', d.get('outcome', d.get('child_outcome', d.get('parent_outcome', ''))))
        # try common column names
        for col in ('visited', 'search_visited'):
            if col in d and d[col] not in (None, ''):
                kw.setdefault('visited', d[col])
                break
        for col in ('memo', 'search_memo', 'cumulative_memo'):
            if col in d and d[col] not in (None, ''):
                kw.setdefault('memo', d[col])
                break
        for col in ('seconds', 'solver_seconds', 'search_seconds', 'wall_seconds'):
            if col in d and d[col] not in (None, ''):
                kw.setdefault('seconds', d[col])
                break
        for col in ('maxdepth', 'search_maxdepth', 'max_depth'):
            if col in d and d[col] not in (None, ''):
                kw.setdefault('maxdepth', d[col])
                break
        if 'classification_source' in d:
            kw.setdefault('classification_source', d['classification_source'])
        if 'search_profile' in d:
            kw.setdefault('profile', d['search_profile'] or 'standard')
        if 'shrink' in d and d['shrink'] not in (None, ''):
            kw.setdefault('shrink', int(d['shrink']))
        if 'load' in d and d['load'] not in (None, ''):
            kw.setdefault('load', int(d['load']))
        return kw


def build_dataset():
    b = DatasetBuilder()

    # 1. Verified LOSS proof exports (exact independent searches).
    for path in [
        OUT_DIR / 'six-stone-loss-proof-90-61-2-73-69-66.csv',
        OUT_DIR / 'five-stone-loss-proof-61-2-73-13-91.csv',
        OUT_DIR / 'four-stone-loss-proof-61-73-66-13.csv',
    ]:
        b.load_csv(path, classification_source='LOSS-proof-export')

    # 2. Expanded-memo re-runs (same search logic, larger tables).
    b.load_csv(OUT_DIR / '69-91-expanded-memo.csv',
               classification_source='split-exact-search expanded-memo')

    # 3. Child-proof CSVs (final exact classifications).
    child_files = [
        OUT_DIR / 'two-stone-69-91-child-proof.csv',
        OUT_DIR / 'two-stone-61-66-child-proof.csv',
        OUT_DIR / 'two-stone-90-66-child-proof.csv',
        OUT_DIR / 'two-stone-90-61-child-proof.csv',
        OUT_DIR / 'three-stone-9-10-30-child-proof.csv',
    ]
    for path in child_files:
        with open(path, newline='', encoding='utf-8') as f:
            for d in csv.DictReader(f):
                src = d.get('source', '')
                if 'expanded-memo' in src:
                    continue  # already added with profile from expanded-memo CSV
                shrink, load = parse_shrink_load(src)
                b.add(d['state'], d['outcome'], d.get('visited'), d.get('memo'),
                      d.get('seconds'), d.get('maxdepth'), str(path), src,
                      shrink=shrink, load=load)

    # 4. Subset classifications.
    subset_files = [
        (OUT_DIR / 'three-stone-subsets-of-medium-loss.csv', 'three-stone-subsets'),
        (OUT_DIR / 'four-stone-subsets-of-medium-loss.csv', 'four-stone-subsets'),
        (OUT_DIR / 'five-stone-subsets-of-medium-loss.csv', 'five-stone-subsets'),
    ]
    for path, label in subset_files:
        with open(path, newline='', encoding='utf-8') as f:
            for d in csv.DictReader(f):
                cs = d['classification_source']
                shared = cs == 'EXACT_SHARED_MEMO_SEARCH'
                notes = 'shared-memo cumulative memo/runtime' if shared else ''
                profile = d.get('search_profile', 'standard') or 'standard'
                shrink = int(d['shrink']) if d.get('shrink') not in (None, '') else None
                load = int(d['load']) if d.get('load') not in (None, '') else None
                b.add(d['state'], d['outcome'], d.get('visited'), d.get('memo'),
                      d.get('solver_seconds'), d.get('maxdepth'), str(path), cs,
                      profile=profile, shrink=shrink, load=load,
                      shared_memo=shared, notes=notes)

    # 5. Six-stone subsets: one shared-memo batch; visited is per-root new work.
    with open(OUT_DIR / 'six-stone-subsets-of-medium-loss.csv', newline='', encoding='utf-8') as f:
        for d in csv.DictReader(f):
            b.add(d['state'], d['outcome'], d['visited'], None, None,
                  d['maxdepth'], str(OUT_DIR / 'six-stone-subsets-of-medium-loss.csv'),
                  'EXACT_SHARED_MEMO_BATCH', shared_memo=True,
                  notes='batch shared memo; memo/runtime are cumulative batch totals')

    # 6. Seven-stone subsets.
    b.load_csv(OUT_DIR / 'seven-stone-subsets-of-medium-loss.csv',
               classification_source='EXACT_BATCH')

    # 7. 90-69 heavy-three-stone campaign summary.
    with open(REPO_ROOT / 'results' / '90-69-heavy-three-stone-results.csv', newline='', encoding='utf-8') as f:
        for d in csv.DictReader(f):
            if d['outcome'] not in ('WIN', 'LOSS'):
                continue
            shrink = int(d['shrink']) if d.get('shrink') not in (None, '') else None
            load = int(d['load']) if d.get('load') not in (None, '') else None
            b.add(d['state'], d['outcome'], d.get('visited'), d.get('memo'),
                  d.get('seconds'), d.get('maxdepth'),
                  'results/90-69-heavy-three-stone-results.csv', d.get('source', ''),
                  shrink=shrink, load=load, notes=d.get('proof_method', ''))

    # 8. 90-69 split-proof: parents + children.
    parents = {}
    children = []
    split_path = REPO_ROOT / 'results' / '90-69-split-proof.csv'
    with open(split_path, newline='', encoding='utf-8') as f:
        for d in csv.DictReader(f):
            parents[norm_state(d['parent_state'])] = d['parent_outcome']
            children.append((
                d['child_state'], d['child_outcome'], d.get('visited'), d.get('memo'),
                d.get('seconds'), d.get('maxdepth'), d.get('shrink'), d.get('load')
            ))
    for pstate, outcome in parents.items():
        b.add(pstate, outcome, source_file=str(split_path),
              classification_source='split-exact-proof parent',
              shrink=2, load=80, notes='all children WIN')
    for c in children:
        state, outcome, visited, memo, seconds, maxdepth, shrink, load = c
        b.add(state, outcome, visited, memo, seconds, maxdepth, str(split_path),
              'split-exact-search child', shrink=int(shrink) if shrink else 2,
              load=int(load) if load else 80)

    # 9. Manual proof-benchmark entries from docs.
    b.add('90,61,2,73,69,66,13,91', 'LOSS', 10471, 24499, 1.6, 17,
          'docs/10X10_PROOF_BENCHMARKS.md', 'proof-benchmark')
    b.add('7,16,17,28,30,33,41,48,54,68,69,71,81,92', 'WIN', 2, 1, 0.0, 14,
          'docs/10X10_PROOF_BENCHMARKS.md', 'proof-benchmark')

    df = pd.DataFrame(list(b.rows.values()))
    df['has_search_cost'] = df['visited'].notna() & (df['visited'] > 0)
    df['memo_runtime_reliable'] = df['has_search_cost'] & (~df['shared_memo'])
    df['visited_per_second'] = np.where(
        df['memo_runtime_reliable'] & df['runtime_seconds'].notna() & (df['runtime_seconds'] > 0),
        df['visited'] / df['runtime_seconds'], np.nan)
    df['memo_per_visited'] = np.where(
        df['memo_runtime_reliable'] & df['visited'].notna() & (df['visited'] > 0),
        df['memo'] / df['visited'], np.nan)
    return df


def quantiles(s):
    if s.empty:
        return {}
    return {
        'min': int(s.min()),
        'p25': float(s.quantile(0.25)),
        'median': float(s.median()),
        'mean': float(s.mean()),
        'p75': float(s.quantile(0.75)),
        'p90': float(s.quantile(0.90)),
        'p95': float(s.quantile(0.95)),
        'max': int(s.max()),
    }


def summarize(df, value_col, mask):
    out = {}
    for outcome in ('WIN', 'LOSS'):
        s = df.loc[mask & (df['outcome'] == outcome), value_col]
        out[outcome] = {'count': len(s), **quantiles(s)}
    return out


def overlap_analysis(df, cost_col='visited'):
    mask = df[cost_col].notna() & (df[cost_col] > 0)
    win_vals = df.loc[mask & (df['outcome'] == 'WIN'), cost_col]
    loss_vals = df.loc[mask & (df['outcome'] == 'LOSS'), cost_col]
    if loss_vals.empty or win_vals.empty:
        return {}
    min_loss = int(loss_vals.min())
    max_win = int(win_vals.max())
    return {
        'min_loss': min_loss,
        'max_win': max_win,
        'max_win_exceeds_min_loss': max_win > min_loss,
        'wins_heavier_than_min_loss': int((win_vals > min_loss).sum()),
        'losses_lighter_than_max_win': int((loss_vals < max_win).sum()),
        'total_win_with_cost': int(len(win_vals)),
        'total_loss_with_cost': int(len(loss_vals)),
        'heaviest_win_state': df.loc[win_vals.idxmax(), 'state'],
        'heaviest_win_value': max_win,
        'lightest_loss_state': df.loc[loss_vals.idxmin(), 'state'],
        'lightest_loss_value': min_loss,
    }


def threshold_table(df, cost_col='visited'):
    mask = df[cost_col].notna() & (df[cost_col] > 0)
    sub = df[mask]
    losses = set(sub[sub['outcome'] == 'LOSS'].index)
    total_loss = len(losses)
    total = len(sub)
    thresholds = np.percentile(sub[cost_col].values, [50, 75, 80, 85, 90, 95, 99])
    rows = []
    for T in thresholds:
        pred = set(sub[sub[cost_col] >= T].index)
        tp = len(pred & losses)
        fp = len(pred - losses)
        fn = len(losses - pred)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / total_loss if total_loss else 0.0
        rows.append({
            'threshold': int(T),
            'percentile': (sub[cost_col] >= T).mean() * 100,
            'precision': precision,
            'recall': recall,
            'fp': fp,
            'fn': fn,
            'tp': tp,
        })
    return pd.DataFrame(rows)


def rank_concentration(df, cost_col='visited'):
    mask = df[cost_col].notna() & (df[cost_col] > 0)
    sub = df[mask].sort_values(cost_col, ascending=False).reset_index(drop=True)
    total_loss = (sub['outcome'] == 'LOSS').sum()
    n = len(sub)
    cuts = {'1%': max(1, n // 100), '5%': max(1, n * 5 // 100),
            '10%': max(1, n * 10 // 100), '20%': max(1, n * 20 // 100)}
    result = {}
    for label, k in cuts.items():
        top = sub.head(k)
        loss_in_top = (top['outcome'] == 'LOSS').sum()
        result[label] = {
            'k': int(k),
            'loss_in_top': int(loss_in_top),
            'recall': float(loss_in_top / total_loss) if total_loss else 0.0,
            'random_expected': float(k / n * total_loss),
            'enrichment': float(loss_in_top / (k / n * total_loss)) if total_loss else 0.0,
        }
    return result, sub


def same_stone_analysis(df, cost_col='visited'):
    mask = df[cost_col].notna() & (df[cost_col] > 0)
    groups = []
    for stones, g in df[mask].groupby('stones'):
        if len(g) < 3:
            continue
        win = g[g['outcome'] == 'WIN'][cost_col]
        loss = g[g['outcome'] == 'LOSS'][cost_col]
        groups.append({
            'stones': int(stones),
            'win_count': len(win),
            'loss_count': len(loss),
            'win_median': float(win.median()) if len(win) else np.nan,
            'loss_median': float(loss.median()) if len(loss) else np.nan,
            'win_mean': float(win.mean()) if len(win) else np.nan,
            'loss_mean': float(loss.mean()) if len(loss) else np.nan,
            'min_loss': int(loss.min()) if len(loss) else None,
            'max_win': int(win.max()) if len(win) else None,
        })
    return pd.DataFrame(groups)


def parent_child_analysis(df):
    summaries = []
    # 69,91 children: every state listed in the final child-proof CSV
    # (some of the hardest are also present as expanded-memo rows).
    child69_states = set()
    with open(OUT_DIR / 'two-stone-69-91-child-proof.csv', newline='', encoding='utf-8') as f:
        for d in csv.DictReader(f):
            child69_states.add(norm_state(d['state']))
    parent69 = df[df['state'].isin(child69_states)]
    summaries.append(parent_stats('69,91', parent69))

    # Split-proof parents: re-read the CSV to know which child belongs to which parent.
    split_path = REPO_ROOT / 'results' / '90-69-split-proof.csv'
    parents = {}
    with open(split_path, newline='', encoding='utf-8') as f:
        for d in csv.DictReader(f):
            p = norm_state(d['parent_state'])
            parents.setdefault(p, []).append(norm_state(d['child_state']))
    for pstate, children in parents.items():
        g = df[df['state'].isin(children)]
        summaries.append(parent_stats(pstate, g))
    return summaries


def parent_stats(name, g):
    win = g[g['outcome'] == 'WIN']
    loss = g[g['outcome'] == 'LOSS']
    return {
        'parent': name,
        'children': len(g),
        'win_children': len(win),
        'loss_children': len(loss),
        'win_median_visited': float(win['visited'].median()) if len(win) and win['visited'].notna().any() else np.nan,
        'loss_median_visited': float(loss['visited'].median()) if len(loss) and loss['visited'].notna().any() else np.nan,
        'loss_max_visited': int(loss['visited'].max()) if len(loss) and loss['visited'].notna().any() else None,
        'win_max_visited': int(win['visited'].max()) if len(win) and win['visited'].notna().any() else None,
    }


def mann_whitney(df, cost_col='visited'):
    mask = df[cost_col].notna() & (df[cost_col] > 0)
    win = df.loc[mask & (df['outcome'] == 'WIN'), cost_col].values
    loss = df.loc[mask & (df['outcome'] == 'LOSS'), cost_col].values
    if len(win) == 0 or len(loss) == 0:
        return None
    u, p = stats.mannwhitneyu(loss, win, alternative='two-sided')
    n1, n2 = len(loss), len(win)
    # Rank-biserial correlation effect size
    rbc = 1 - (2 * u) / (n1 * n2)
    return {'U': float(u), 'p': float(p), 'loss_n': n1, 'win_n': n2,
            'rank_biserial_r': float(rbc)}


def make_plots(df):
    mask = df['has_search_cost']
    sub = df[mask].copy()
    sub['log10visited'] = np.log10(sub['visited'])

    # 1. Histograms of log10 visited
    fig, ax = plt.subplots(figsize=(8, 5))
    bins = np.linspace(sub['log10visited'].min(), sub['log10visited'].max(), 40)
    ax.hist(sub[sub['outcome'] == 'WIN']['log10visited'], bins=bins, alpha=0.6, label='WIN', color='steelblue')
    ax.hist(sub[sub['outcome'] == 'LOSS']['log10visited'], bins=bins, alpha=0.8, label='LOSS', color='darkorange')
    ax.set_xlabel('log10(visited)')
    ax.set_ylabel('frequency')
    ax.set_title('10x10 visited distribution by outcome')
    ax.legend()
    fig.savefig(PLOT_DIR / 'visited_distribution.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    # 2. Sorted scatter
    fig, ax = plt.subplots(figsize=(10, 5))
    sorted_sub = sub.sort_values('visited').reset_index(drop=True)
    colors = sorted_sub['outcome'].map({'WIN': 'steelblue', 'LOSS': 'darkorange'})
    ax.scatter(sorted_sub.index, sorted_sub['visited'], c=colors, s=10, alpha=0.7)
    ax.set_yscale('log')
    ax.set_xlabel('rank by visited (light to heavy)')
    ax.set_ylabel('visited (log scale)')
    ax.set_title('All searched positions sorted by visited')
    fig.savefig(PLOT_DIR / 'visited_sorted_scatter.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    # 3. Box plot
    fig, ax = plt.subplots(figsize=(6, 5))
    data = [sub[sub['outcome'] == 'WIN']['log10visited'].values,
            sub[sub['outcome'] == 'LOSS']['log10visited'].values]
    bp = ax.boxplot(data, tick_labels=['WIN', 'LOSS'], patch_artist=True)
    bp['boxes'][0].set_facecolor('steelblue')
    bp['boxes'][1].set_facecolor('darkorange')
    ax.set_ylabel('log10(visited)')
    ax.set_title('Visited by outcome')
    fig.savefig(PLOT_DIR / 'visited_boxplot.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    # 4. memo vs visited
    msub = sub[sub['memo_runtime_reliable'] & sub['memo'].notna()]
    fig, ax = plt.subplots(figsize=(7, 7))
    for outcome, color in [('WIN', 'steelblue'), ('LOSS', 'darkorange')]:
        g = msub[msub['outcome'] == outcome]
        ax.scatter(g['visited'], g['memo'], c=color, label=outcome, s=12, alpha=0.6)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('visited')
    ax.set_ylabel('memo entries')
    ax.set_title('memo vs visited (non-shared exact searches)')
    ax.legend()
    fig.savefig(PLOT_DIR / 'memo_vs_visited.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    # 5. Cumulative LOSS recall by rank
    _, ranked = rank_concentration(df, 'visited')
    ranked['loss_cum'] = (ranked['outcome'] == 'LOSS').cumsum()
    ranked['frac'] = ranked.index / len(ranked)
    total_loss = (ranked['outcome'] == 'LOSS').sum()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ranked['frac'] * 100, ranked['loss_cum'] / total_loss * 100, color='darkgreen')
    for pct in [1, 5, 10, 20]:
        ax.axvline(pct, color='gray', linestyle='--', alpha=0.5)
    ax.set_xlabel('top % by visited')
    ax.set_ylabel('cumulative % of LOSS states recovered')
    ax.set_title('LOSS cumulative recall by visited rank')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 105)
    fig.savefig(PLOT_DIR / 'loss_recall_by_rank.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


def print_report(df, stats_dict):
    print(f"Dataset rows: {len(df)}")
    print(f"WIN: {(df['outcome']=='WIN').sum()}, LOSS: {(df['outcome']=='LOSS').sum()}")
    print(f"Rows with visited>0: {df['has_search_cost'].sum()}")
    print("\n=== visited statistics (visited>0) ===")
    print(pd.DataFrame(stats_dict['visited']).T)
    print("\n=== memo statistics (reliable memo/runtime rows) ===")
    print(pd.DataFrame(stats_dict['memo']).T)
    print("\n=== runtime statistics (reliable rows) ===")
    print(pd.DataFrame(stats_dict['runtime']).T)
    print("\n=== overlap ===")
    for k, v in stats_dict['overlap'].items():
        print(f"{k}: {v}")
    print("\n=== thresholds ===")
    print(stats_dict['thresholds'])
    print("\n=== rank concentration ===")
    print(pd.DataFrame(stats_dict['rank_concentration']).T)
    print("\n=== same-stone comparison ===")
    print(stats_dict['same_stone'])
    print("\n=== parent-child comparison ===")
    print(pd.DataFrame(stats_dict['parent_child']))
    print("\n=== Mann-Whitney ===")
    print(stats_dict['mann_whitney'])


def main():
    df = build_dataset()
    df.to_csv(OUT_DIR / 'search-cost-outcomes.csv', index=False)

    stats_dict = {
        'visited': summarize(df, 'visited', df['has_search_cost']),
        'memo': summarize(df, 'memo', df['memo_runtime_reliable'] & df['memo'].notna()),
        'runtime': summarize(df, 'runtime_seconds', df['memo_runtime_reliable'] & df['runtime_seconds'].notna()),
        'overlap': overlap_analysis(df, 'visited'),
        'thresholds': threshold_table(df, 'visited'),
        'rank_concentration': rank_concentration(df, 'visited')[0],
        'same_stone': same_stone_analysis(df, 'visited'),
        'parent_child': parent_child_analysis(df),
        'mann_whitney': mann_whitney(df, 'visited'),
    }
    print_report(df, stats_dict)
    make_plots(df)

    # Save numeric report as JSON for Markdown generator
    import json
    report_path = OUT_DIR / 'analysis' / 'report_numbers.json'
    # Convert dataframes to dicts for JSON
    serializable = {
        'visited': stats_dict['visited'],
        'memo': stats_dict['memo'],
        'runtime': stats_dict['runtime'],
        'overlap': stats_dict['overlap'],
        'thresholds': stats_dict['thresholds'].to_dict(orient='records'),
        'rank_concentration': stats_dict['rank_concentration'],
        'same_stone': stats_dict['same_stone'].to_dict(orient='records'),
        'parent_child': stats_dict['parent_child'],
        'mann_whitney': stats_dict['mann_whitney'],
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(serializable, f, indent=2, default=str)


if __name__ == '__main__':
    main()

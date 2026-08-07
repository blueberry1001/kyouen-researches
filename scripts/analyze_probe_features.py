#!/usr/bin/env python3
"""Analyze probe features vs final search cost and LOSS ranking."""
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / 'results' / '10x10'
PLOT_DIR = OUT_DIR / 'probe_analysis'
PLOT_DIR.mkdir(parents=True, exist_ok=True)

BUDGETS = [10_000, 100_000, 1_000_000]


def load_data():
    df = pd.read_csv(OUT_DIR / 'probe-features.csv')
    df = df[df['probe_budget'].isin(BUDGETS)].copy()
    df['final_visited'] = pd.to_numeric(df['final_visited'], errors='coerce')
    df['visited'] = pd.to_numeric(df['visited'], errors='coerce')
    df['memo'] = pd.to_numeric(df['memo'], errors='coerce')
    df['seconds'] = pd.to_numeric(df['seconds'], errors='coerce')
    df['maxdepth'] = pd.to_numeric(df['maxdepth'], errors='coerce')
    df['memo_per_visited'] = pd.to_numeric(df['memo_per_visited'], errors='coerce')
    df['visited_per_second'] = pd.to_numeric(df['visited_per_second'], errors='coerce')
    df['depth_visited_3'] = pd.to_numeric(df.get('depth_visited_3'), errors='coerce')
    df['loss'] = (df['outcome'] == 'LOSS').astype(int)
    df['log_final_visited'] = np.log1p(df['final_visited'])
    for d in range(9, 22):
        used = pd.to_numeric(df[f'memo_used_d{d}'], errors='coerce')
        cap = pd.to_numeric(df[f'memo_capacity_d{d}'], errors='coerce')
        df[f'memo_fill_d{d}'] = used / cap
    df['max_memo_fill'] = df[[f'memo_fill_d{d}' for d in range(9, 22)]].max(axis=1)
    df['parent_key'] = df['parent'].fillna('unknown')
    df['stones'] = pd.to_numeric(df['stones'], errors='coerce')
    return df


def safe_corr(x, y, method='spearman'):
    mask = pd.notna(x) & pd.notna(y)
    if mask.sum() < 3:
        return np.nan, np.nan
    if method == 'spearman':
        return spearmanr(x[mask], y[mask])
    return pearsonr(x[mask], y[mask])


def rank_recall(y_true_order, y_pred_order, k_frac):
    n = len(y_true_order)
    k = max(1, int(n * k_frac))
    true_top = set(y_true_order[:k])
    pred_top = set(y_pred_order[:k])
    return len(true_top & pred_top) / k


def single_feature_analysis(df):
    records = []
    features = [
        'memo', 'memo_per_visited', 'visited_per_second', 'maxdepth',
        'max_memo_fill', 'seconds', 'depth_visited_3',
    ] + [f'depth_visited_{d}' for d in range(20)] + [f'memo_fill_d{d}' for d in range(9, 22)]
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget]
        for feat in features:
            if feat not in sub.columns:
                continue
            rho, pval = safe_corr(sub['final_visited'], sub[feat], 'spearman')
            rho_loss, pval_loss = safe_corr(sub['loss'], sub[feat], 'spearman')
            records.append({
                'budget': budget, 'feature': feat,
                'spearman_final_visited': rho, 'pvalue_final_visited': pval,
                'spearman_loss': rho_loss, 'pvalue_loss': pval_loss,
            })
    return pd.DataFrame(records)


def loss_ranking(df, feature='memo'):
    records = []
    overall_loss_rate = df['loss'].mean()
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget].copy()
        if feature not in sub.columns or sub[feature].isna().all():
            continue
        sub_sorted = sub.sort_values(feature, ascending=False)
        n = len(sub_sorted)
        for k_pct in [1, 5, 10, 20]:
            k = max(1, int(n * k_pct / 100))
            top = sub_sorted.head(k)
            tp = top['loss'].sum()
            precision = tp / k
            recall = tp / sub_sorted['loss'].sum() if sub_sorted['loss'].sum() else 0
            concentration = precision / overall_loss_rate if overall_loss_rate else 0
            records.append({
                'budget': budget, 'feature': feature, 'top_pct': k_pct,
                'n_top': k, 'loss_in_top': int(tp), 'precision': precision,
                'recall': recall, 'concentration': concentration,
            })
    return pd.DataFrame(records)


def final_visited_prediction(df):
    records = []
    features = ['memo', 'memo_per_visited', 'maxdepth', 'visited_per_second']
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget].copy()
        sub = sub.dropna(subset=['final_visited'] + features)
        if len(sub) < 10:
            continue
        y_true = sub['final_visited'].values
        true_order = np.argsort(-y_true)
        for feat in features:
            pred_order = np.argsort(-sub[feat].values)
            for k_frac in [0.01, 0.05, 0.10, 0.20]:
                records.append({
                    'budget': budget, 'model': f'rank_{feat}',
                    'metric': f'top{k_frac*100:.0f}_recall',
                    'value': rank_recall(true_order, pred_order, k_frac),
                })
        X = sub[features].values
        y = sub['log_final_visited'].values
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        cv = GroupKFold(n_splits=min(5, sub['parent_key'].nunique()))
        r2s = []
        spearmans = []
        for tr, te in cv.split(Xs, y, groups=sub['parent_key'].values):
            m = LinearRegression().fit(Xs[tr], y[tr])
            pred = m.predict(Xs[te])
            r2s.append(m.score(Xs[te], y[te]))
            spearmans.append(spearmanr(np.expm1(pred), sub['final_visited'].iloc[te].values)[0])
        records.append({'budget': budget, 'model': 'linear_log', 'metric': 'cv_r2', 'value': float(np.mean(r2s))})
        records.append({'budget': budget, 'model': 'linear_log', 'metric': 'cv_spearman', 'value': float(np.mean(spearmans))})
    return pd.DataFrame(records)


def parent_level_speedup(df, feature='memo', label='probe'):
    """For each parent with at least one LOSS, compare random vs probe ranking vs oracle."""
    records = []
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget].copy()
        parents = sub[sub['loss'] == 1]['parent_key'].unique()
        for parent in parents:
            g = sub[sub['parent_key'] == parent].copy()
            if len(g) < 2 or g['loss'].sum() == 0:
                continue
            if feature not in g.columns or g[feature].isna().all():
                continue
            n = len(g)
            loss_positions = np.where(g['loss'].values == 1)[0]
            random_expected = (loss_positions[0] + 1) if len(loss_positions) else n
            g_sorted = g.sort_values(feature, ascending=False).reset_index(drop=True)
            probe_positions = np.where(g_sorted['loss'].values == 1)[0]
            probe_first = (probe_positions[0] + 1) if len(probe_positions) else n
            g_oracle = g.sort_values('final_visited', ascending=False).reset_index(drop=True)
            oracle_positions = np.where(g_oracle['loss'].values == 1)[0]
            oracle_first = (oracle_positions[0] + 1) if len(oracle_positions) else n
            records.append({
                'budget': budget, 'parent': parent, 'children': n, 'losses': int(g['loss'].sum()),
                'stones_min': int(g['stones'].min()) if g['stones'].notna().any() else None,
                'stones_max': int(g['stones'].max()) if g['stones'].notna().any() else None,
                'random_first_loss_position': random_expected,
                f'{label}_first_loss_position': probe_first,
                'oracle_first_loss_position': oracle_first,
            })
    return pd.DataFrame(records)


def parent_speedup_with_best_feature(df):
    """For each parent, pick best feature by stones if known, else memo."""
    best_feature = {3: 'memo', 4: 'depth_visited_3', 5: 'memo'}
    records = []
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget].copy()
        parents = sub[sub['loss'] == 1]['parent_key'].unique()
        for parent in parents:
            g = sub[sub['parent_key'] == parent].copy()
            if len(g) < 2 or g['loss'].sum() == 0:
                continue
            stones = int(g['stones'].iloc[0]) if g['stones'].notna().any() else None
            feature = best_feature.get(stones, 'memo')
            if feature not in g.columns or g[feature].isna().all():
                feature = 'memo'
            n = len(g)
            loss_positions = np.where(g['loss'].values == 1)[0]
            random_expected = (loss_positions[0] + 1) if len(loss_positions) else n
            g_sorted = g.sort_values(feature, ascending=False).reset_index(drop=True)
            probe_positions = np.where(g_sorted['loss'].values == 1)[0]
            probe_first = (probe_positions[0] + 1) if len(probe_positions) else n
            g_oracle = g.sort_values('final_visited', ascending=False).reset_index(drop=True)
            oracle_positions = np.where(g_oracle['loss'].values == 1)[0]
            oracle_first = (oracle_positions[0] + 1) if len(oracle_positions) else n
            records.append({
                'budget': budget, 'parent': parent, 'children': n, 'losses': int(g['loss'].sum()),
                'stones': stones, 'feature': feature,
                'random_first_loss_position': random_expected,
                'best_probe_first_loss_position': probe_first,
                'oracle_first_loss_position': oracle_first,
            })
    return pd.DataFrame(records)


def probe_cost_analysis(df):
    records = []
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget]
        probe_cost_total = sub['visited'].sum()
        probe_seconds_total = sub['seconds'].sum()
        final_cost_total = sub['final_visited'].sum()
        records.append({
            'budget': budget,
            'probe_visited_total': int(probe_cost_total),
            'probe_seconds_total': float(probe_seconds_total),
            'final_visited_total': int(final_cost_total),
            'probe_plus_final_visited': int(probe_cost_total + final_cost_total),
            'probe_fraction_of_final': float(probe_cost_total / final_cost_total) if final_cost_total else None,
        })
    return pd.DataFrame(records)


def stones_analysis(df):
    records = []
    features = ['memo', 'memo_per_visited', 'maxdepth', 'depth_visited_3']
    for budget in BUDGETS:
        sub = df[(df['probe_budget'] == budget) & df['stones'].notna()].copy()
        sub['stones'] = sub['stones'].astype(int)
        for stones, g in sub.groupby('stones'):
            if len(g) < 5:
                continue
            for feat in features:
                if feat not in g.columns or g[feat].isna().all():
                    continue
                rho, _ = safe_corr(g['final_visited'], g[feat], 'spearman')
                rho_loss, _ = safe_corr(g['loss'], g[feat], 'spearman')
                records.append({
                    'budget': budget, 'stones': stones, 'feature': feat,
                    'n': len(g), 'loss_count': int(g['loss'].sum()),
                    'spearman_final_visited': rho, 'spearman_loss': rho_loss,
                })
    return pd.DataFrame(records)


def stones_loss_ranking(df):
    records = []
    features_by_stones = {3: ['memo', 'depth_visited_3'], 4: ['memo', 'depth_visited_3'], 5: ['memo', 'depth_visited_3']}
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget].copy()
        for stones, features in features_by_stones.items():
            g = sub[sub['stones'] == stones]
            if len(g) < 5 or g['loss'].sum() == 0:
                continue
            overall = g['loss'].mean()
            for feat in features:
                if feat not in g.columns or g[feat].isna().all():
                    continue
                g_sorted = g.sort_values(feat, ascending=False)
                n = len(g_sorted)
                for k_pct in [10, 20, 50]:
                    k = max(1, int(n * k_pct / 100))
                    top = g_sorted.head(k)
                    tp = top['loss'].sum()
                    precision = tp / k
                    recall = tp / g_sorted['loss'].sum() if g_sorted['loss'].sum() else 0
                    concentration = precision / overall if overall else 0
                    records.append({
                        'budget': budget, 'stones': stones, 'feature': feat, 'top_pct': k_pct,
                        'n': n, 'loss_count': int(g['loss'].sum()),
                        'precision': precision, 'recall': recall, 'concentration': concentration,
                    })
    return pd.DataFrame(records)


def estimated_savings(df, feature='memo', top_pct=20):
    """Estimate total cost if we probe all, then fully solve only top_pct by probe feature."""
    records = []
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget].copy()
        probe_cost = sub['visited'].sum()
        probe_seconds = sub['seconds'].sum()
        n = len(sub)
        k = max(1, int(n * top_pct / 100))
        sub_sorted = sub.sort_values(feature, ascending=False)
        solved_cost = sub_sorted.head(k)['final_visited'].sum()
        solved_seconds = sub_sorted.head(k)['seconds'].sum()  # rough proxy
        total_cost = probe_cost + solved_cost
        baseline_cost = sub['final_visited'].sum()
        savings = baseline_cost - total_cost
        records.append({
            'budget': budget, 'feature': feature, 'top_pct': top_pct,
            'probe_visited': int(probe_cost), 'solved_visited': int(solved_cost),
            'total_visited': int(total_cost), 'baseline_visited': int(baseline_cost),
            'savings_visited': int(savings), 'savings_fraction': float(savings / baseline_cost) if baseline_cost else None,
            'recall_loss_in_top': float(sub_sorted.head(k)['loss'].sum() / sub['loss'].sum()) if sub['loss'].sum() else 0,
        })
    return pd.DataFrame(records)


def counterexamples(df):
    records = []
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget].copy()
        sub['probe_rank'] = sub['memo'].rank(ascending=False)
        sub['final_rank'] = sub['final_visited'].rank(ascending=False)
        heavy_probe_light_final = sub[(sub['probe_rank'] <= len(sub)*0.05) & (sub['final_rank'] > len(sub)*0.5) & (sub['outcome'] == 'WIN')]
        for _, r in heavy_probe_light_final.head(3).iterrows():
            records.append({
                'budget': budget, 'type': 'heavy_probe_light_final_WIN',
                'state': r['state'], 'final_visited': r['final_visited'],
                'probe_memo': r['memo'], 'probe_rank': r['probe_rank'], 'final_rank': r['final_rank'],
            })
        light_probe_heavy_final = sub[(sub['probe_rank'] > len(sub)*0.5) & (sub['final_rank'] <= len(sub)*0.05) & (sub['outcome'] == 'LOSS')]
        for _, r in light_probe_heavy_final.head(3).iterrows():
            records.append({
                'budget': budget, 'type': 'light_probe_heavy_final_LOSS',
                'state': r['state'], 'final_visited': r['final_visited'],
                'probe_memo': r['memo'], 'probe_rank': r['probe_rank'], 'final_rank': r['final_rank'],
            })
    return pd.DataFrame(records)


def make_plots(df):
    # probe memo vs final visited by budget
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget]
        fig, ax = plt.subplots(figsize=(8, 6))
        win = sub[sub['outcome'] == 'WIN']
        loss = sub[sub['outcome'] == 'LOSS']
        ax.scatter(win['memo'], win['final_visited'], alpha=0.5, label=f'WIN ({len(win)})', s=20)
        ax.scatter(loss['memo'], loss['final_visited'], alpha=0.8, label=f'LOSS ({len(loss)})', s=30, color='red')
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel(f'Probe memo at budget {budget}')
        ax.set_ylabel('Final visited')
        ax.set_title(f'Probe memo vs final visited (budget={budget})')
        ax.legend()
        fig.savefig(PLOT_DIR / f'memo_vs_final_budget_{budget}.png', dpi=150, bbox_inches='tight')
        plt.close(fig)

    # Spearman by budget for key features
    key_feats = ['memo', 'memo_per_visited', 'maxdepth', 'visited_per_second', 'depth_visited_3']
    corr_records = []
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget]
        for feat in key_feats:
            if feat not in sub.columns:
                continue
            rho, _ = safe_corr(sub['final_visited'], sub[feat], 'spearman')
            corr_records.append({'budget': budget, 'feature': feat, 'rho': rho})
    corr_df = pd.DataFrame(corr_records)
    fig, ax = plt.subplots(figsize=(10, 6))
    for feat in key_feats:
        d = corr_df[corr_df['feature'] == feat]
        ax.plot(d['budget'], d['rho'], marker='o', label=feat)
    ax.set_xscale('log')
    ax.set_xlabel('Probe budget')
    ax.set_ylabel('Spearman correlation with final visited')
    ax.set_title('Spearman correlation vs probe budget')
    ax.legend()
    ax.grid(True)
    fig.savefig(PLOT_DIR / 'spearman_by_budget.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    # LOSS concentration by budget (memo)
    loss_df = loss_ranking(df, 'memo')
    fig, ax = plt.subplots(figsize=(10, 6))
    for budget in BUDGETS:
        d = loss_df[(loss_df['budget'] == budget)]
        ax.plot(d['top_pct'], d['concentration'], marker='o', label=f'budget={budget}')
    ax.set_xlabel('Top % by probe memo')
    ax.set_ylabel('LOSS concentration factor')
    ax.set_title('LOSS concentration by probe memo rank')
    ax.legend()
    ax.grid(True)
    fig.savefig(PLOT_DIR / 'loss_concentration_memo.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    # Stones-specific memo vs final visited
    for budget in BUDGETS:
        sub = df[df['probe_budget'] == budget]
        fig, ax = plt.subplots(figsize=(10, 6))
        for stones in sorted(sub['stones'].dropna().unique()):
            g = sub[sub['stones'] == stones]
            if len(g) < 5:
                continue
            win = g[g['outcome'] == 'WIN']
            loss = g[g['outcome'] == 'LOSS']
            ax.scatter(win['memo'], win['final_visited'], alpha=0.5, label=f'stones={int(stones)} WIN ({len(win)})', s=20)
            ax.scatter(loss['memo'], loss['final_visited'], alpha=0.8, label=f'stones={int(stones)} LOSS ({len(loss)})', s=30)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('Probe memo')
        ax.set_ylabel('Final visited')
        ax.set_title(f'Memo vs final visited by stones (budget={budget})')
        ax.legend()
        fig.savefig(PLOT_DIR / f'memo_vs_final_by_stones_budget_{budget}.png', dpi=150, bbox_inches='tight')
        plt.close(fig)

    # Parent-level speedup bar chart
    parent_speed = parent_level_speedup(df, 'memo', 'memo')
    if not parent_speed.empty:
        for budget in BUDGETS:
            d = parent_speed[parent_speed['budget'] == budget].sort_values('losses', ascending=False)
            if len(d) == 0:
                continue
            fig, ax = plt.subplots(figsize=(12, 6))
            x = np.arange(len(d))
            width = 0.25
            ax.bar(x - width, d['random_first_loss_position'], width, label='random')
            ax.bar(x, d['memo_first_loss_position'], width, label='probe memo')
            ax.bar(x + width, d['oracle_first_loss_position'], width, label='oracle')
            ax.set_xticks(x)
            ax.set_xticklabels([p[:30] for p in d['parent']], rotation=45, ha='right')
            ax.set_ylabel('First LOSS child position')
            ax.set_title(f'Parent-level first LOSS position (budget={budget})')
            ax.legend()
            fig.savefig(PLOT_DIR / f'parent_speedup_budget_{budget}.png', dpi=150, bbox_inches='tight')
            plt.close(fig)


def main():
    df = load_data()
    print(f"Data rows: {len(df)} (budgets: {sorted(df['probe_budget'].unique())})")
    print(f"Parents: {df['parent_key'].nunique()}, LOSS rows: {df['loss'].sum()}")

    single = single_feature_analysis(df)
    loss_rank_memo = loss_ranking(df, 'memo')
    loss_rank_dv3 = loss_ranking(df, 'depth_visited_3')
    pred = final_visited_prediction(df)
    parent_memo = parent_level_speedup(df, 'memo', 'memo')
    parent_dv3 = parent_level_speedup(df, 'depth_visited_3', 'depth_visited_3')
    parent_best = parent_speedup_with_best_feature(df)
    cost = probe_cost_analysis(df)
    stones = stones_analysis(df)
    stones_loss = stones_loss_ranking(df)
    savings = estimated_savings(df, 'memo', 20)
    counter = counterexamples(df)

    print("\n=== Single feature Spearman with final visited (top per budget) ===")
    for budget in BUDGETS:
        top = single[(single['budget'] == budget)].nlargest(5, 'spearman_final_visited')
        print(f"\nBudget {budget}:")
        print(top[['feature', 'spearman_final_visited', 'pvalue_final_visited']].to_string(index=False))

    print("\n=== LOSS ranking by probe memo ===")
    print(loss_rank_memo[['budget', 'top_pct', 'loss_in_top', 'precision', 'recall', 'concentration']].to_string(index=False))

    print("\n=== LOSS ranking by depth_visited_3 ===")
    print(loss_rank_dv3[['budget', 'top_pct', 'loss_in_top', 'precision', 'recall', 'concentration']].to_string(index=False))

    print("\n=== Final visited prediction (linear model CV) ===")
    print(pred[pred['model'] == 'linear_log'][['budget', 'metric', 'value']].to_string(index=False))

    print("\n=== Parent-level first LOSS position (memo, avg) ===")
    if not parent_memo.empty:
        print(parent_memo.groupby('budget')[['random_first_loss_position', 'memo_first_loss_position', 'oracle_first_loss_position']].mean().to_string())

    print("\n=== Parent-level first LOSS position (depth_visited_3, avg) ===")
    if not parent_dv3.empty:
        print(parent_dv3.groupby('budget')[['random_first_loss_position', 'depth_visited_3_first_loss_position', 'oracle_first_loss_position']].mean().to_string())

    print("\n=== Parent-level first LOSS position (best feature by stones, avg) ===")
    if not parent_best.empty:
        print(parent_best.groupby('budget')[['random_first_loss_position', 'best_probe_first_loss_position', 'oracle_first_loss_position']].mean().to_string())
        print('Per-parent details:')
        print(parent_best[['budget', 'parent', 'children', 'losses', 'stones', 'feature', 'random_first_loss_position', 'best_probe_first_loss_position', 'oracle_first_loss_position']].to_string(index=False))

    print("\n=== Probe cost analysis ===")
    print(cost.to_string(index=False))

    print("\n=== Estimated savings (probe + solve top 20% by memo) ===")
    print(savings.to_string(index=False))

    print("\n=== Stones-specific Spearman (memo vs final visited) ===")
    print(stones[stones['feature'] == 'memo'][['budget', 'stones', 'n', 'loss_count', 'spearman_final_visited', 'spearman_loss']].to_string(index=False))

    print("\n=== Stones LOSS ranking (precision@20%) ===")
    print(stones_loss[stones_loss['top_pct'] == 20][['budget', 'stones', 'feature', 'precision', 'recall', 'concentration']].to_string(index=False))

    print("\n=== Counterexamples ===")
    print(counter.to_string(index=False))

    results = {
        'n_rows': len(df),
        'budgets': sorted(df['probe_budget'].unique().tolist()),
        'single_feature': single.to_dict(orient='records'),
        'loss_ranking_memo': loss_rank_memo.to_dict(orient='records'),
        'loss_ranking_depth_visited_3': loss_rank_dv3.to_dict(orient='records'),
        'final_visited_prediction': pred.to_dict(orient='records'),
        'parent_speedup_memo': parent_memo.to_dict(orient='records'),
        'parent_speedup_depth_visited_3': parent_dv3.to_dict(orient='records'),
        'parent_speedup_best_feature': parent_best.to_dict(orient='records'),
        'probe_cost': cost.to_dict(orient='records'),
        'estimated_savings': savings.to_dict(orient='records'),
        'stones': stones.to_dict(orient='records'),
        'stones_loss_ranking': stones_loss.to_dict(orient='records'),
        'counterexamples': counter.to_dict(orient='records'),
    }
    with open(OUT_DIR / 'probe-analysis.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    make_plots(df)
    print(f"\nPlots saved to {PLOT_DIR}")
    print(f"Results saved to {OUT_DIR / 'probe-analysis.json'}")


if __name__ == '__main__':
    main()

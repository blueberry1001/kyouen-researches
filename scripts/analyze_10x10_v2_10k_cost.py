#!/usr/bin/env python3
import argparse, csv, math, statistics
from collections import defaultdict
from pathlib import Path

EXPECTED_TASKS = 1136
EXPECTED_PARENTS = 12


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def f(row, key):
    x = float(row[key])
    if not math.isfinite(x) or x < 0:
        raise ValueError(f'bad {key}={row[key]!r} for {row.get("state")}')
    return x


def task_key(r):
    return (int(r['batch']), int(r['batch_position']), r['state'])


def auc_lower_memo(rows):
    # Probability that a random LOSS has lower memo than a random WIN,
    # with half credit for ties.
    loss = [float(r['memo']) for r in rows if r['outcome'] == 'LOSS']
    win = [float(r['memo']) for r in rows if r['outcome'] == 'WIN']
    if not loss or not win:
        return float('nan')
    score = 0.0
    for a in loss:
        for b in win:
            score += (a < b) + 0.5 * (a == b)
    return score / (len(loss) * len(win))


def analyze(probe_path, exact_path):
    probe = read_csv(probe_path)
    exact = read_csv(exact_path)
    if len(probe) != EXPECTED_TASKS or len(exact) != EXPECTED_TASKS:
        raise SystemExit(f'task-count mismatch: probe={len(probe)} exact={len(exact)} expected={EXPECTED_TASKS}')

    ps = {(r['parent'], r['state']) for r in probe}
    es = {(r['parent'], r['state']) for r in exact}
    if len(ps) != EXPECTED_TASKS or len(es) != EXPECTED_TASKS:
        raise SystemExit('duplicate (parent,state) rows')
    if ps != es:
        raise SystemExit(f'state-set mismatch: probe-only={len(ps-es)} exact-only={len(es-ps)}')

    parents = sorted({r['parent'] for r in exact})
    if len(parents) != EXPECTED_PARENTS:
        raise SystemExit(f'parent-count mismatch: {len(parents)}')

    pmap = {(r['parent'], r['state']): r for r in probe}
    emap = {(r['parent'], r['state']): r for r in exact}
    out = []

    for parent in parents:
        erows = [r for r in exact if r['parent'] == parent]
        for r in erows:
            if r['outcome'] not in ('WIN', 'LOSS'):
                raise SystemExit(f'non-exact outcome {r["outcome"]} for {r["state"]}')
            f(r, 'seconds')

        joined = []
        for e in erows:
            p = pmap[(parent, e['state'])]
            if p.get('probe_outcome', 'PROBE') not in ('PROBE', 'WIN', 'LOSS'):
                raise SystemExit(f'bad probe outcome for {e["state"]}: {p.get("probe_outcome")}')
            f(p, 'seconds')
            q = dict(e)
            q['memo'] = p['memo']
            q['probe_seconds'] = p['seconds']
            joined.append(q)

        file_order = sorted(joined, key=task_key)
        file_exact = 0.0
        file_pos = None
        for i, r in enumerate(file_order, 1):
            file_exact += f(r, 'seconds')
            if r['outcome'] == 'LOSS':
                file_pos = i
                break
        if file_pos is None:
            raise SystemExit(f'parent has no LOSS: {parent}')

        memo_order = sorted(joined, key=lambda r: (float(r['memo']),) + task_key(r))
        memo_exact = 0.0
        memo_pos = None
        for i, r in enumerate(memo_order, 1):
            memo_exact += f(r, 'seconds')
            if r['outcome'] == 'LOSS':
                memo_pos = i
                break
        probe_cost = sum(f(r, 'probe_seconds') for r in joined)
        total = probe_cost + memo_exact
        ratio = total / file_exact
        losses = sum(r['outcome'] == 'LOSS' for r in joined)
        top5_loss = sum(r['outcome'] == 'LOSS' for r in memo_order[:5])

        out.append({
            'parent': parent,
            'm': len(joined),
            'loss_children': losses,
            'file_first_loss_rank': file_pos,
            'file_exact_cost_s': file_exact,
            'memo_first_loss_rank': memo_pos,
            'normalized_first_loss_rank': memo_pos / len(joined),
            'auc': auc_lower_memo(joined),
            'top1_outcome': memo_order[0]['outcome'],
            'top5_loss_count': top5_loss,
            'probe_cost_s': probe_cost,
            'memo_exact_cost_s': memo_exact,
            'total_10k_cost_s': total,
            'ratio_10k_over_file': ratio,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', required=True)
    ap.add_argument('--exact', default='results/10x10/clean-holdout-v2/exact_outcomes.csv')
    ap.add_argument('--out-prefix', default='results/10x10/clean-holdout-v2/v2_10k_cost')
    args = ap.parse_args()
    rows = analyze(args.probe, args.exact)

    prefix = Path(args.out_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = prefix.with_suffix('.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as fobj:
        w = csv.DictWriter(fobj, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    ratios = [r['ratio_10k_over_file'] for r in rows]
    ranks = [r['memo_first_loss_rank'] for r in rows]
    aucs = [r['auc'] for r in rows if math.isfinite(r['auc'])]
    improved = sum(x < 1 for x in ratios)
    summary = {
        'parents': len(rows),
        'tasks': sum(r['m'] for r in rows),
        'first_loss_ranks': ranks,
        'rank_sum': sum(ranks),
        'rank_median': statistics.median(ranks),
        'rank_max': max(ranks),
        'mean_auc': statistics.mean(aucs),
        'median_auc': statistics.median(aucs),
        'median_total_cost_ratio': statistics.median(ratios),
        'geomean_total_cost_ratio': math.exp(statistics.mean(math.log(x) for x in ratios)),
        'improved_parents': improved,
        'worse_parents': sum(x > 1 for x in ratios),
        'aggregate_cost_ratio': sum(r['total_10k_cost_s'] for r in rows) / sum(r['file_exact_cost_s'] for r in rows),
        'preregistered_success': statistics.median(ratios) < 1 and improved >= 7,
    }
    import json
    json_path = prefix.with_suffix('.json')
    json_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()

import json
from collections import defaultdict

with open('research/verification/round5_b482b500.json') as f:
    d = json.load(f)

print('=== B482 ===')
for n in ['3', '4', '5']:
    cells = d['B482'][n]['cells_cont']
    usable = [c for c in cells if c['rho_comp_g'] is not None]
    pos = [c for c in usable if c['rho_comp_g'] > 0]
    neg = [c for c in usable if c['rho_comp_g'] < 0]
    both = [c for c in cells if c.get('mean_g_comp_hi') is not None]
    spread_win = [c for c in both if c['g_kinds_comp_hi'] > c['g_kinds_comp_lo']]
    conc_win = [c for c in both if c['g_kinds_comp_lo'] > c['g_kinds_comp_hi']]
    print(f'n={n}: cont_cells {len(cells)} usable_rho {len(usable)} pos {len(pos)} neg {len(neg)} '
          f'spread_more_kinds {len(spread_win)} conc_more {len(conc_win)} '
          f'exact_cells {d["B482"][n]["cell_tri_l"]["n_cells"]}')
    # show cells where rho_comp != rho_tri sign or strength
    for c in usable:
        if c['rho_comp_g'] is not None and c['rho_tri_g'] is not None:
            if abs(c['rho_comp_g'] - c['rho_tri_g']) > 0.2:
                print('  diff', {k: c[k] for k in ['k','nL','n','rho_comp_g','rho_tri_g','g_kinds_comp_lo','g_kinds_comp_hi']})

print('=== B484 ===')
for n in ['4', '5']:
    cells = d['B484'][n]
    with_var = [c for c in cells if c['var_of_bvarpos'] > 0]
    with_rho = [c for c in cells if c['rho_bvarpos_win'] is not None]
    rhos = [c['rho_bvar_win'] for c in cells if c['rho_bvar_win'] is not None]
    print(f'n={n}: cells {len(cells)} bvarpos_has_var {len(with_var)} rho_bvarpos_def {len(with_rho)}')
    if rhos:
        print(f'  rho_bvar_win min {min(rhos):.3f} max {max(rhos):.3f} mean {sum(rhos)/len(rhos):.3f}')
    for c in with_var[:8]:
        print('  var', c)
    for c in with_rho[:8]:
        print('  rho', c)

print('=== B485 ===')
for n in ['4', '5']:
    cells = d['B485'][n]
    rhos = [(c, c['rho_spread_win']) for c in cells if c['rho_spread_win'] is not None]
    pos = [r for _, r in rhos if r > 0]
    neg = [r for _, r in rhos if r < 0]
    print(f'n={n}: usable {len(rhos)} pos {len(pos)} neg {len(neg)} mean {sum(r for _,r in rhos)/len(rhos):.3f}')
    for c, r in sorted(rhos, key=lambda z: -abs(z[1]))[:6]:
        print(' ', {k: c[k] for k in ['k','nL','n','rho_spread_win','mean_n_b1','mean_spread']})

print('=== B486 gaps ===')
for n in ['3', '4', '5']:
    v = d['B486'][n]
    print(f'n={n} overall', v['overall'])
    if v['cells']:
        gaps = [c['gap'] for c in v['cells']]
        print(f'  cells {len(v["cells"])} gaps neg {sum(1 for g in gaps if g<0)} pos {sum(1 for g in gaps if g>0)}')

print('=== B488 flips ===')
for n in ['3', '4', '5']:
    flips = sum(1 for c in d['B488'][n] if c['sign_flip_sig'] or c['sign_flip_rhash'])
    # also rhash attenuation
    att = []
    for c in d['B488'][n]:
        if c['rho_raw'] is not None and c['rho_rhash'] is not None and abs(c['rho_raw']) > 0.05:
            att.append(abs(c['rho_rhash']) / abs(c['rho_raw']))
    print(f'n={n} flips {flips} rhash_attenuation ratios {att}')

print('=== B487 overall vs within ===')
for n in ['4', '5']:
    cells = d['B487'][n]
    better_nd = sum(1 for c in cells if c['rho_ndistinct_g'] is not None and c['rho_umax_g'] is not None and c['rho_ndistinct_g'] > c['rho_umax_g'])
    usable = sum(1 for c in cells if c['rho_ndistinct_g'] is not None and c['rho_umax_g'] is not None)
    within_pos = 0
    within_neg = 0
    for c in cells:
        for w in c['within_uminmax']:
            r = w['rho_ndistinct_g']
            if r is None:
                continue
            if r > 0:
                within_pos += 1
            else:
                within_neg += 1
    print(f'n={n} k-cells better_nd {better_nd}/{usable} within_pos {within_pos} within_neg {within_neg}')

print('=== B490 ===')
for n in ['3', '4', '5']:
    v = d['B490'][n]
    print(n, v)

print('=== B494 ===')
for n in ['4', '5']:
    print(n, d['B494'][n])

print('=== B495 ===')
for n in ['4', '5']:
    print(n, d['B495'][n])

print('=== B496 best ===')
for n in ['4', '5']:
    cells = d['B496'][n]
    best = max(cells, key=lambda c: c['ratio'] if isinstance(c['ratio'], (int, float)) else 0)
    print(n, 'best', best, 'all', cells)

print('=== B499 ===')
for n in ['4', '5']:
    v = d['B499'][n]
    print(n, 'min_sz', v['min_sz'], 'n_pairs', v['n_pairs'])
    # find max ratio among finite
    pairs = v['top_pairs']
    print('  top', pairs[:4])
    # E_X range
    exs = [f['E_X'] for f in v['first']]
    pmins = [f['P_min'] for f in v['first']]
    print(f'  E_X range {min(exs):.4f}..{max(exs):.4f}  P_min range {min(pmins):.6f}..{max(pmins):.6f}')

print('=== B500 ===')
for n in ['4', '5']:
    v = d['B500'][n]
    print(n, v['reach_stats'])
    for c in v['cuts']:
        layers = c['layer_hi']
        print('  sz', c['sz'], 'reach', c['reach'], 'layers', layers)

import json, os
D = r'D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round4_b237'
out = []
for line in open(os.path.join(D, 'mc.jsonl')):
    line = line.strip().lstrip('﻿')
    if not line.startswith('{'):
        continue
    d = json.loads(line)
    n = int(d['key'][4:])
    tot = d['runs']; bd = dict(d['boarddeg_hist'])
    out.append('n=%d  E[X]=%.6f  K=%d  E/K=%.6f' % (n, d['S1']/tot, d['K'], (d['S1']/tot)/d['K']))
    out.append('   boarddeg_hist=%s' % d['boarddeg_hist'])
    if d['lastdeg_hist']:
        for dd, c in d['lastdeg_hist']:
            bc = bd.get(dd, 0)
            out.append('   d=%-4d lastcount=%-8d lastshare=%.6f  boardshare=%d/%d=%.6f  ratio=%.4f'
                       % (dd, c, c/tot, bc, n*n, bc/(n*n), (c/tot)/(bc/(n*n))))
    else:
        out.append('   lastdeg_hist EMPTY')
    fm = [v for _, v in d['firstmove_S1']]; fr = d['firstmove_runs']
    m = sum(fm)/fr
    out.append('   E[firstmove] max=%d min=%d spread=%d relspread=%.6f' % (max(fm), min(fm), max(fm)-min(fm), (max(fm)-min(fm))/m))
    # moments -> variance, skew, kurtosis  (exact rationals as floats for reporting only)
    S1, S2, S3, S4, N = d['S1'], d['S2'], d['S3'], d['S4'], tot
    m1 = S1/N; m2 = S2/N; m3 = S3/N; m4 = S4/N
    var = m2 - m1*m1
    sd = var ** 0.5
    sk = (m3 - 3*m1*m2 + 2*m1**3)/ (sd**3 if sd else 1)
    ku = (m4 - 4*m1*m3 + 6*m1*m1*m2 - 3*m1**4)/(sd**4 if sd else 1) - 3
    out.append('   var=%.6f sd=%.6f  CV^2=var/mu^2=%.6f  skew=%.6f  exkurt=%.6f' % (var, sd, var/(m1*m1), sk, ku))
    out.append('   dist=%s' % d['dist'])
    # B182 candidate scales
    out.append('   n^(2/3)=%.6f  n^(2/3)*log(n)^(1/3)=%.6f  n=%.6f' % (n**(2/3), n**(2/3)*(n and __import__('math').log(n))**(1/3), n))
    out.append('   ratio to n^(2/3)ln^(1/3) = %.6f' % (m1/(n**(2/3)*__import__('math').log(n)**(1/3))))
    out.append('')
open(os.path.join(D, 'mc_summary.txt'), 'w', encoding='utf-8').write('\n'.join(out))
print('written', len(out), 'lines')

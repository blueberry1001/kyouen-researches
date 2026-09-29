"""Heuristic smooth-norm candidate search; NOT an exhaustive width certificate."""
from collections import defaultdict
from math import gcd, isqrt
import argparse
import json
from pathlib import Path


def mul(z, w):
    return z[0]*w[0]-z[1]*w[1], z[0]*w[1]+z[1]*w[0]


def gaussian_prime(p):
    for a in range(1, isqrt(p)+1):
        b = isqrt(p-a*a)
        if a*a+b*b == p:
            return a, b
    raise AssertionError(p)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-norm', type=int, default=10000000)
    parser.add_argument('--max-prime', type=int, default=97)
    parser.add_argument('--max-q', type=int, default=32)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    primes = [p for p in range(5, args.max_prime+1, 4)
              if all(p%d for d in range(2, isqrt(p)+1))]
    factors = {}
    for p in primes:
        z = gaussian_prime(p)
        pos = [(1, 0)]
        n = p
        while n <= args.max_norm:
            pos.append(mul(pos[-1], z))
            e = len(pos)-1
            factors[p, e] = [mul(pos[j], (pos[e-j][0], -pos[e-j][1])) for j in range(e+1)]
            n *= p
    best = {}
    examined = 0

    def inspect(n, reps, fs):
        nonlocal examined
        if len(reps) < 5:
            return
        for tw in (0, 1):
            norm = n*(2**tw)
            if norm > args.max_norm:
                continue
            examined += 1
            base = [mul(z, (1, 1)) for z in reps] if tw else reps
            all_reps = [mul(z, u) for z in base for u in ((1,0),(-1,0),(0,1),(0,-1))]
            assert len(set(all_reps)) == len(all_reps)
            for q in range(1, args.max_q+1):
                fam = 'power2' if q & (q-1) == 0 else 'odd' if q%2 else None
                if fam is None:
                    continue
                groups = defaultdict(list)
                for u, v in all_reps:
                    rx, ry = u%q, v%q
                    if gcd(gcd(rx, ry), q) == 1:
                        groups[rx, ry].append((u, v))
                for res, points in groups.items():
                    m = len(points)
                    if m < 5 or m%2 == 0:
                        continue
                    span = max(max(u for u,v in points)-min(u for u,v in points),
                               max(v for u,v in points)-min(v for u,v in points))//q
                    key = fam, m
                    if key not in best or span < best[key]['span']:
                        best[key] = dict(family=fam, m=m, span=span, q=q, M=norm,
                                         residue=res, factors=fs+([(2,1)] if tw else []),
                                         points=[((u-res[0])//q,(v-res[1])//q) for u,v in points])

    def visit(i, n, reps, fs):
        inspect(n, reps, fs)
        for j in range(i, len(primes)):
            p = primes[j]
            ne, e = n*p, 1
            while ne <= args.max_norm:
                visit(j+1, ne, [mul(z,w) for z in reps for w in factors[p,e]], fs+[(p,e)])
                ne *= p
                e += 1

    visit(0, 1, [(1,0)], [])
    out = dict(scope='heuristic restricted smooth norms, exact representations',
               max_norm=args.max_norm, primes=primes, max_q=args.max_q,
               norms_examined=examined, minima=[best[k] for k in sorted(best)])
    args.output.write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    print('norms', examined)
    for k in sorted(best):
        r = best[k]
        print(k, 'span', r['span'], 'q', r['q'], 'M', r['M'], 'factors', r['factors'])


if __name__ == '__main__':
    main()

"""Verify the q=11 character formula for every exponent 0..30.

The markdown proves it for all nonnegative exponents. Gaussian construction
here uses unbounded Python integers; no radius scan or floating-point decision.
"""
import json
from pathlib import Path
from collections import Counter
from math import gcd, isqrt

ROOT = Path(__file__).resolve().parents[3]


def mul(z,w):
    return z[0]*w[0]-z[1]*w[1],z[0]*w[1]+z[1]*w[0]


def mod(z):
    return tuple(x%11 for x in z)


def power(z,e):
    r=(1,0)
    for _ in range(e):
        r=mul(r,z)
    return r


def main():
    units=((1,0),(-1,0),(0,1),(0,-1))
    g=(6,3)
    cosets=[{mod(mul(u,power(g,t))) for u in units} for t in range(3)]
    H={(x,y) for x in range(11) for y in range(11) if (x*x+y*y)%11==1}
    assert set.union(*cosets)==H and len(H)==12
    assert mod(power(g,3))==(10,0)
    primes={5:(1,2),13:(2,3),17:(1,4),29:(2,5)}
    chars={}
    for p,z in primes.items():
        ratio=mod(tuple(v*pow(p,-1,11) for v in mul(z,z)))
        chars[p]=next(t for t,c in enumerate(cosets) if ratio in c)
    assert chars=={5:1,13:2,17:1,29:1}
    cases=[]
    for e in range(31):
        fs=[(5,e),(13,1),(17,1),(29,1)]
        reps=[(1,0)]
        baseline=(1,0)
        norm=1
        for p,ex in fs:
            z=primes[p]; conj=(z[0],-z[1])
            terms=[mul(power(z,a),power(conj,ex-a)) for a in range(ex+1)]
            reps=[mul(r,s) for r in reps for s in terms]
            baseline=mul(baseline,power(conj,ex))
            norm*=p**ex
        all_reps={mul(r,u) for r in reps for u in units}
        assert len(all_reps)==32*(e+1)
        assert all(x*x+y*y==norm for x,y in all_reps)
        counts=Counter(mod(z) for z in all_reps)
        h,r=divmod(e,3)
        expected=([8*h+3,8*h+3,8*h+2] if r==0 else
                  [8*h+5,8*h+6,8*h+5] if r==1 else [8*h+8]*3)
        for t,c in enumerate(cosets):
            targets={mod(mul(baseline,z)) for z in c}
            assert len(targets)==4
            assert all(counts[z]==expected[t] for z in targets)
            assert all(gcd(gcd(x,y),11)==1 for x,y in targets)
        assert len(counts)==12
        if e<=4:
            # Independent direct norm enumeration for the first five cases.
            direct=set()
            for x in range(-isqrt(norm),isqrt(norm)+1):
                y=isqrt(norm-x*x)
                if y*y==norm-x*x:
                    direct.add((x,y));direct.add((x,-y))
            assert direct==all_reps
        cases.append({'e':e,'M':norm,'representations':len(all_reps),
                      'orbit_counts':expected,'direct_norm_scan':e<=4})
    result={'modulus':11,'generator':g,'cosets':[sorted(c) for c in cosets],
            'prime_characters':chars,'cases':cases,
            'claim_scope':'general proof in round12-q11-counts.md; these are finite integer cross-checks'}
    output=ROOT/'research/verification/round12_q11_counts.json'
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('31 exponent cases; 5 independent direct norm scans; all passed')


if __name__=='__main__':
    main()

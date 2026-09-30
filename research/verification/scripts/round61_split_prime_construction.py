"""Explicit full-p safe set for split primes, with independent determinants."""
from pathlib import Path
from itertools import combinations
from math import factorial,prod,comb
import hashlib
import json
from round25_forced_verify import det4

ROOT=Path(__file__).resolve().parents[1]


def prime(n):
    return n>=2 and all(n%d for d in range(2,int(n**0.5)+1))


def main():
    records=[]
    for p in [p for p in range(5,102) if p%4==1 and prime(p)]:
        a=factorial((p-1)//2)%p
        assert a*a%p==p-1
        points=[((t*t+t)%p,a*(t*t-t)%p) for t in range(p)]
        assert len(set(points))==p
        for ts in combinations(range(p),3):
            (x,y),(u,v),(w,z)=[points[t] for t in ts]
            determinant=(u-x)*(z-y)-(w-x)*(v-y)
            assert determinant!=0
            vandermonde=prod(ts[j]-ts[i] for i in range(3) for j in range(i+1,3))
            assert (determinant-2*a*vandermonde)%p==0
        for ts in combinations(range(p),4):
            determinant=det4([points[t] for t in ts])
            assert determinant!=0
            vandermonde=prod(ts[j]-ts[i] for i in range(4) for j in range(i+1,4))
            assert (determinant-8*a*vandermonde)%p==0
        records.append({'p':p,'sqrt_minus_one':a,'stone_count':p,
                        'three_point_subsets':comb(p,3),'four_point_subsets':comb(p,4),
                        'coordinates':points})
        print('PASS prime',p,'safe stones',p,flush=True)
    files=['scripts/round61_split_prime_construction.py','scripts/round25_forced_verify.py']
    result={'B088_original_verdict':'PARTIAL','proved_family':'K_p >= p for every prime p ==1 mod4',
            'two_n_minus_constant_construction_proved':False,
            'three_point_subsets_checked':sum(r['three_point_subsets'] for r in records),
            'four_point_subsets_checked':sum(r['four_point_subsets'] for r in records),
            'records':records,'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round61_split_prime_verified.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()

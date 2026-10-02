from itertools import combinations, permutations
from pathlib import Path
import json, time

PERMS = [(p,(-1)**sum(p[i]>p[j] for i in range(4) for j in range(i+1,4))) for p in permutations(range(4))]
def det4(points):
    rows=[(x*x+y*y,x,y,1) for x,y in points]
    return sum(sign*rows[0][p[0]]*rows[1][p[1]]*rows[2][p[2]]*rows[3][p[3]] for p,sign in PERMS)
def points(n,mask):return [(p%n,p//n) for p in range(n*n) if (mask>>p)&1]
def quads(n):
    return [sum(1<<p for p in t) for t in combinations(range(n*n),4) if det4([(p%n,p//n) for p in t])==0]
def is_safe(s,qs):return all((s&q)!=q for q in qs)
def R(s,L,qs):
    candidates={q&~s for q in qs if (q&~s)&~L==0}
    return tuple(sorted(r for r in candidates if not any(t!=r and (t&r)==t for t in candidates)))

out={'method':'24-term 4x4 determinant; full power set for n<=4; full 8 extension subsets for witnesses','boards':[]}
for n in range(1,5):
    start=time.time();qs=quads(n);N=n*n
    safe={s for s in range(1<<N) if is_safe(s,qs)}
    keys={};keys_nok={}
    for s in safe:
        L=sum(1<<p for p in range(N) if not(s>>p&1) and s|(1<<p) in safe)
        r=R(s,L,qs);pairs=tuple(t for t in r if t.bit_count()==2)
        key=(s.bit_count(),L,pairs); key_nok=(L,pairs)
        if key in keys:assert keys[key]==r
        else:keys[key]=r
        if key_nok in keys_nok:assert keys_nok[key_nok]==r
        else:keys_nok[key_nok]=r
    row={'n':n,'forbidden_quads':len(qs),'safe_positions':len(safe),'same_k_signatures':len(keys),'any_k_signatures':len(keys_nok),'both_determine_complete_residual':True,'seconds':time.time()-start}
    out['boards'].append(row);print(row,flush=True)

n=5;qs=quads(n)
states=[[0,1,3,10,12,19],[0,1,13,14,15,19]]
out['witnesses']=[]
for arr in states:
    s=sum(1<<p for p in arr);assert is_safe(s,qs)
    L=[p for p in range(25) if p not in arr and is_safe(s|1<<p,qs)]
    assert L==[6,17,20]
    safe_extensions=[]
    for k in range(4):
        for t in combinations(L,k):
            if is_safe(s|sum(1<<p for p in t),qs):safe_extensions.append(list(t))
    g={}
    for t in sorted((tuple(t) for t in safe_extensions),key=len,reverse=True):
        child={g[tuple(sorted(t+(p,)))] for p in L if p not in t and tuple(sorted(t+(p,))) in g}
        v=0
        while v in child:v+=1
        g[t]=v
    bad=[]
    union=s|sum(1<<p for p in L)
    for q in qs:
        if q&union==q:bad.append(points(n,q))
    out['witnesses'].append({'s':arr,'coordinates':points(n,s),'L':L,'safe_extensions':safe_extensions,'g':g[()],'forbidden_quad_after_all_three':bad})
assert out['witnesses'][0]['g']==0 and out['witnesses'][1]['g']==1
assert out['witnesses'][0]['safe_extensions']==out['witnesses'][1]['safe_extensions'][:-1]
Path(__file__).with_name('independent_verification.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out['witnesses']),flush=True)

import itertools, functools, json, time
from pathlib import Path

def det3(a,b,c):
    return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])

def run(n):
    start=time.time(); N=n*n; full=(1<<N)-1
    points=[(i%n,i//n) for i in range(N)]
    lifts=[(x*x+y*y,x,y) for x,y in points]
    quads=[]; completions={}
    for q in itertools.combinations(range(N),4):
        base=lifts[q[0]]
        rows=[tuple(lifts[i][j]-base[j] for j in range(3)) for i in q[1:]]
        if det3(*rows)==0:
            mask=sum(1<<i for i in q); quads.append(mask)
            for i in q:
                t=tuple(j for j in q if j!=i)
                completions[t]=completions.get(t,0)|(1<<i)
    def bits(mask):
        out=[]
        while mask:
            b=mask&-mask; mask^=b; out.append(b.bit_length()-1)
        return out
    legal={}; gs={}
    def solve(s):
        if s in gs:return gs[s]
        forbidden=s
        for t in itertools.combinations(bits(s),3):forbidden|=completions.get(t,0)
        l=full^forbidden; legal[s]=l; childvalues=set()
        for p in bits(l):childvalues.add(solve(s|1<<p))
        g=0
        while g in childvalues:g+=1
        gs[s]=g;return g
    solve(0)
    print('enumerated',n,len(gs),len(quads),'seconds',time.time()-start,flush=True)
    groups={}
    for s,l in legal.items():
        pair_edges=tuple((1<<p)|(1<<q) for p,q in itertools.combinations(bits(l),2) if not (legal[s|1<<p]>>q)&1)
        key=(l,pair_edges)
        groups.setdefault(key,[]).append(s)
    residual_mixed=[]; nimber_mixed=[]; pn_mixed=[]; maxgroup=0
    for key,states in groups.items():
        if len(states)<2:continue
        maxgroup=max(maxgroup,len(states))
        bytriple={}
        l=key[0];pairs=key[1]
        for s in states:
            triples=tuple(sorted({q&~s for q in quads if (q&~s).bit_count()==3 and ((q&~s)&l)==(q&~s) and not any((p&(q&~s))==p for p in pairs)}))
            bytriple.setdefault(triples,[]).append(s)
        if len(bytriple)>1:
            witness={'legal':bits(l),'pairs':[bits(e) for e in pairs],'quadruples':[bits(q) for q in quads if q&l==q],'states':[{'s':bits(v[0]),'g':gs[v[0]],'multiplicity':len(v),'stone_sizes':sorted({s.bit_count() for s in v}),'triples':[bits(e) for e in k]} for k,v in bytriple.items()]}
            residual_mixed.append(witness)
        if len({gs[s] for s in states})>1:nimber_mixed.append(key)
        if len({gs[s]==0 for s in states})>1:pn_mixed.append(key)
    out={'n':n,'quads':len(quads),'states':len(gs),'g_empty':gs[0],'signature_groups':len(groups),'max_group_size':maxgroup,'mixed_residual_groups':len(residual_mixed),'mixed_nimber_groups':len(nimber_mixed),'mixed_pn_groups':len(pn_mixed),'residual_witnesses':sorted(residual_mixed,key=lambda w:len(w['legal'])),'elapsed':time.time()-start}
    Path(__file__).with_name(f'ambiguities_n{n}.json').write_text(json.dumps(out,indent=2))
    from collections import Counter
    print({k:v for k,v in out.items() if k!='residual_witnesses'},flush=True)
    print(Counter((len(w['legal']),len(w['pairs']),tuple(sorted({s['g'] for s in w['states']})),tuple(sorted(len(s['triples']) for s in w['states']))) for w in residual_mixed),flush=True)

if __name__=='__main__':
    run(5)

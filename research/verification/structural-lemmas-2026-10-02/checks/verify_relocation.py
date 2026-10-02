"""Independent all-subset witness audit and full 5x5 signature census.

No repository code imports. Geometry: 24-term integer determinant.
Census enumeration: increasing point subsets, checking incident forbidden quads.
"""
from itertools import combinations, permutations
from pathlib import Path
from collections import Counter
import json, time

PERMS=[(p,(-1)**sum(p[i]>p[j] for i in range(4) for j in range(i+1,4))) for p in permutations(range(4))]
def det(points):
    rows=[(x*x+y*y,x,y,1) for x,y in points]
    return sum(sign*rows[0][p[0]]*rows[1][p[1]]*rows[2][p[2]]*rows[3][p[3]] for p,sign in PERMS)
def bitlist(s):return [p for p in range(25) if s>>p&1]
def bm(points):return sum(1<<p for p in points)
def geom_safe(s):return all(det([(p%5,p//5) for p in quad])!=0 for quad in combinations(bitlist(s),4))
def mex(vals):
    v=0
    while v in vals:v+=1
    return v

start=time.time()
quads=[bm(q) for q in combinations(range(25),4) if det([(p%5,p//5) for p in q])==0]
assert len(quads)==826
out={'geometry':'integer 4x4 determinant expanded into all 24 permutations','quads':len(quads)}
S=[1,3,5,6,11];T=[1,3,5,11,17];L=[4,20,22,24]
records=[]
for sarr in [S,T]:
    s=bm(sarr);assert geom_safe(s)
    legal=[p for p in range(25) if p not in sarr and geom_safe(s|1<<p)]
    assert legal==L
    safe=[];g={};table=[]
    for u in range(16):
        extra=[L[i] for i in range(4) if u>>i&1]
        direct=geom_safe(s|bm(extra))
        inclusion=all((s|bm(extra))&q!=q for q in quads)
        assert direct==inclusion
        if direct:safe.append(u)
        table.append({'subset':extra,'safe':direct})
    for u in sorted(safe,key=int.bit_count,reverse=True):
        g[u]=mex({g[u|1<<i] for i in range(4) if not u>>i&1 and u|1<<i in g})
    R=sorted({q&~s for q in quads if (q&~s)&~bm(L)==0},key=lambda x:(x.bit_count(),x))
    minimal=[r for r in R if not any(t!=r and t&r==t for t in R)]
    origin={','.join(map(str,bitlist(r))):[bitlist(q) for q in quads if q&~s==r] for r in minimal}
    records.append({'state':sarr,'legal':legal,'minimal_residual':[bitlist(r) for r in minimal],'quad_witnesses':origin,'all_16_subsets':table,'all_safe_grundy':{str(u):g[u] for u in sorted(g)},'g':g[0],'child_g':[g[1<<i] for i in range(4)],'winning_moves':[L[i] for i in range(4) if g[1<<i]==0]})
assert records[0]['g']==0 and records[1]['g']==3
assert records[0]['child_g']==[1,1,1,1]
assert records[1]['child_g']==[0,1,2,0]
assert records[0]['minimal_residual']==[[4,20],[20,24],[4,22,24]]
assert records[1]['minimal_residual']==[[4,20],[20,24]]
out['witnesses']=records
print('witnesses verified',time.time()-start,flush=True)

# Independent exhaustive enumeration: each safe subset is generated once,
# using its unique increasing order. A new forbidden quad must contain p.
incident=[[] for _ in range(25)]
for q in quads:
    for p in bitlist(q):incident[p].append(q^(1<<p))
safe=set()
def enumerate_safe(s,first):
    safe.add(s)
    for p in range(first,25):
        if all(s&r!=r for r in incident[p]):enumerate_safe(s|1<<p,p+1)
enumerate_safe(0,0)
assert len(safe)==151394
print('all safe subsets enumerated',time.time()-start,flush=True)
legal={s:sum(1<<p for p in range(25) if not s>>p&1 and s|1<<p in safe) for s in safe}
gs={}
for s in sorted(safe,key=int.bit_count,reverse=True):gs[s]=mex({gs[s|1<<p] for p in bitlist(legal[s])})
assert gs[0]==1
groups={};groups_by_k={}
for s in safe:
    l=legal[s]
    pairs=tuple(bm((p,q)) for p,q in combinations(bitlist(l),2) if s|1<<p|1<<q not in safe)
    key=(l,pairs)
    groups.setdefault(key,[]).append(s)
    groups_by_k.setdefault((s.bit_count(),)+key,[]).append(s)
mixed=[v for v in groups.values() if len({gs[s] for s in v})>1]
mixed_same_k=[(k[0],v) for k,v in groups_by_k.items() if len({gs[s] for s in v})>1]
mixed_small=[v for v in groups.values() if len({gs[s] for s in v if s.bit_count()<=4})>1]
maximum_difference=max(max(gs[s] for s in v)-min(gs[s] for s in v) for v in mixed)
assert len(mixed)==32 and len(mixed_small)==0 and maximum_difference==3
assert min(k for k,v in mixed_same_k)==5
out['census']={'complete':True,'safe_positions':len(safe),'safe_layer_counts':dict(sorted(Counter(s.bit_count() for s in safe).items())),'signature_groups':len(groups),'mixed_grundy_groups':len(mixed),'maximum_grundy_spread':maximum_difference,'all_states_with_at_most_four_stones_mixed_groups':len(mixed_small),'minimum_equal_stone_count_in_mixed_groups':min(k for k,v in mixed_same_k),'same_k_group_counts_by_stone_count':dict(sorted(Counter(k for k,v in mixed_same_k).items())),'seconds':time.time()-start}
Path(__file__).with_name('relocation_verified.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out['census']),flush=True)

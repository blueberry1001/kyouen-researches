"""Independent n4 orbit/height check and bounded-scope n7 result manifest."""
from collections import Counter
from functools import cache
from pathlib import Path
import hashlib
import json
from round27_response_graphs import game
from round25_forced_verify import bits,geometry

ROOT=Path(__file__).resolve().parents[1]

def main():
    n=4;_,_,values,*_=game(n);_,_,curves=geometry(n);full=(1<<(n*n))-1
    @cache
    def children(s):
        legal=full^s
        for curve in curves:
            if (curve&s).bit_count()==3:legal&=~curve
        return [s|(1<<p) for p in bits(legal)]
    @cache
    def height(s):return max((1+height(c) for c in children(s)),default=0)
    permutations=[]
    for swap in (False,True):
        for flip_x in (False,True):
            for flip_y in (False,True):
                image=[]
                for p in range(16):
                    x,y=p%n,p//n
                    if swap:x,y=y,x
                    if flip_x:x=n-1-x
                    if flip_y:y=n-1-y
                    image.append(x+n*y)
                permutations.append(image)
    checked={k:{'count':0,'sym':0,'margin':{}} for k in range(8)}
    for s,v in values.items():
        h=height(s);g=v[0];k=s.bit_count()
        if g!=h:continue
        margin=len(children(s))-h
        checked[k]['margin'][str(h)]=min(checked[k]['margin'].get(str(h),100),margin)
        if g<3:continue
        checked[k]['count']+=1
        stabilizer=[perm for perm in permutations if sum(1<<perm[p] for p in bits(s))==s]
        if len(stabilizer)<4:continue
        checked[k]['sym']+=1
        winning=[(c^s).bit_length()-1 for c in children(s) if values[c][0]==0]
        assert any(len({perm[p] for perm in stabilizer})<=2 for p in winning)
    small=json.loads((ROOT/'round30_n4_ceiling.json').read_text())
    for L in small['levels']:
        row=checked[L['k']]
        assert row['count']==L['ceiling_g_ge3'] and row['sym']==L['stabilizer_ge4']
        assert row['margin']==L['min_legal_minus_h'] and not L['counterexamples']
    seven=json.loads((ROOT/'round30_n7_ceiling.json').read_text())
    assert sum(L['states'] for L in seven['levels'])==179810350
    assert not any(L['counterexamples'] or L['stabilizer_ge4'] for L in seven['levels'])
    count=sum(L['ceiling_g_ge3'] for L in seven['levels']);assert count==58123224
    margin={}
    for L in seven['levels']:
        for h,v in L['min_legal_minus_h'].items():margin[h]=min(margin.get(h,100),v)
    result={'B325_original':'PARTIAL','B326_original':'PARTIAL',
            'n4_independent_curve_height_and_orbit_check':True,
            'n7_ceiling_g_ge3':count,'n7_ceiling_stabilizer_ge4':0,
            'n7_minimum_legal_minus_h':margin,
            'scope':'n7 height/orbit census uses one new DP on independently validated safe layers. n4 was checked by a separate Python recurrence. Finite support is not a proof of either infinite original.'}
    files=['scripts/round30_ceiling_orbits.cpp','scripts/round30_ceiling_verify.py',
           'scripts/kc_core.h','scripts/round27_response_graphs.py','scripts/round25_forced_verify.py',
           'round30_n4_ceiling.json','round30_n7_ceiling.json']
    result['sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
    (ROOT/'round30_ceiling_audited.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Finite ceiling/orbit census checked; B325/B326 remain PARTIAL')

if __name__=='__main__':main()

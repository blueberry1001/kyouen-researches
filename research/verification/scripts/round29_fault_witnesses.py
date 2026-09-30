"""Exact whole-curve/quad audit of finite saturation witnesses."""
from collections import Counter
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits

ROOT=Path(__file__).resolve().parents[1]

def evaluate(n,ids):
    points,quads,curves=geometry(n)
    s=sum(1<<i for i in ids)
    assert len(ids)==len(set(ids)) and not any(s&q==q for q in quads)
    assert all((s&c).bit_count()<=3 for c in curves)
    empty=list(bits(((1<<(n*n))-1)^s))
    families={p:[q^(1<<p) for q in quads if q>>p&1 and (q^(1<<p))&s==(q^(1<<p))]
              for p in empty}
    assert all(families.values())
    def unlock(removal):return [p for p in empty if all(t&removal for t in families[p])]
    single={a:unlock(1<<a) for a in ids}
    rho=next(r for r in range(1,len(ids)+1)
             if any(unlock(sum(1<<a for a in choice)) for choice in combinations(ids,r)))
    removal=next(list(choice) for choice in combinations(ids,rho)
                 if unlock(sum(1<<a for a in choice)))
    return {'n':n,'mask':s,'ids':ids,'coordinates':[points[i] for i in ids],
            'b':{p:len(f) for p,f in families.items()},'blocker_triples':{p:list(map(lambda t:list(bits(t)),f)) for p,f in families.items()},
            'single_removal_unlock':single,'redundant_stones':[p for p,v in single.items() if not v],
            'rho':rho,'rho_removal':removal,'rho_unlocked':unlock(sum(1<<a for a in removal))}

def main():
    small={}
    for n in (2,3,4):
        _,quads,curves=geometry(n);full=(1<<(n*n))-1
        safe=[s for s in range(full+1) if all((s&c).bit_count()<=3 for c in curves)]
        terminal=[]
        for s in safe:
            legal=full^s
            for c in curves:
                if (s&c).bit_count()==3:legal&=~c
            if not legal:terminal.append(s)
        spectrum=Counter(s.bit_count() for s in terminal)
        small[n]={'safe_count':len(safe),'terminal_spectrum':dict(spectrum),
                  'minimum_maximal':min(spectrum),'maximum_safe':max(spectrum)}
    assert small[3]['terminal_spectrum']=={5:56}
    common=evaluate(3,[0,1,2,3,7])
    assert 2 in common['redundant_stones'] and common['rho']==1
    many=evaluate(4,[0,1,2,5,10,14])
    assert min(many['b'].values())>=2 and len(many['single_removal_unlock'][2])==4
    robust=evaluate(5,[0,1,4,6,7,10,17,19,23])
    assert robust['rho']==2
    # The legacy ten-entry n=5 "K=9" example is not safe.
    wrong=[0,1,2,5,9,11,13,15,22,24]
    _,quads,_=geometry(5);mask=sum(1<<i for i in wrong)
    violated=[list(bits(q)) for q in quads if mask&q==q]
    assert violated
    result={'small_board_exhaustion':small,'B368_B369_witness':common,
            'B367_witness':many,'B362_witness':robust,
            'legacy_B369_invalid_n5_witness':{'ids':wrong,'size':len(wrong),'forbidden_quads':violated},
            'legacy_n6_rho_distribution':{'source':'round2_b351.json rho.n6_k11','rho1':296,'rho2':168,
                                          'note':'Legacy JSON itself contradicts the prose claim of all 464 rho=2; not rerun here.'}}
    files=['scripts/round29_fault_witnesses.py','scripts/round25_forced_verify.py']
    result['sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
    (ROOT/'round29_fault_witnesses.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Finite saturation witness audit passed: B362/B367/B369 supported, B368 refuted')

if __name__=='__main__':main()

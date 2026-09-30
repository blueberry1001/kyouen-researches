"""Original B524: empty intersection at the already certified minimum size three."""
from collections import Counter
from functools import cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits

ROOT=Path(__file__).resolve().parents[1]


def main():
    found=json.loads((ROOT/'round35_empty_intersection_search.json').read_bytes())
    points,quads,curves=geometry(4);full=(1<<16)-1
    indices=found['removed_indices'];masks=[quads[i] for i in indices]
    assert masks==found['removed_masks'] and len(set(masks))==3
    assert masks[0]&masks[1]&masks[2]==0
    signatures=[0]*(1<<16)
    for i,q in enumerate(quads):
        rest=full^q;t=rest
        while True:
            signatures[t|q]|=1<<i
            if not t:break
            t=(t-1)&rest
    records=[]
    for subset in range(8):
        chosen=[indices[i] for i in range(3) if subset>>i&1]
        removed=sum(1<<i for i in chosen)
        safe=[s for s in range(1<<16) if not signatures[s]&~removed]
        values={}
        for s in reversed(safe):
            seen={values[t] for p in bits(full^s) if (t:=s|(1<<p)) in values}
            g=0
            while g in seen:g+=1
            values[s]=g
        retained=[q for i,q in enumerate(quads) if i not in chosen]
        @cache
        def direct(s):
            seen=set()
            for p in reversed(range(16)):
                if s>>p&1:continue
                t=s|(1<<p)
                if any(t&q==q for q in retained):continue
                seen.add(direct(t))
            g=0
            while g in seen:g+=1
            assert g==values[s]
            return g
        assert direct(0)==values[0]
        assert direct.cache_info().currsize==len(values)
        # Every safe state is reachable because safety is hereditary.
        assert bool(values[0])==(subset==7)
        K=max(s.bit_count() for s in safe)
        records.append({'subset':subset,'removed_indices':chosen,'g0':values[0],
                        'child_g':[values[1<<p] for p in range(16)],
                        'safe_states':len(safe),'all_safe_states_independent_mex_checked':True,
                        'g_histogram':dict(Counter(values.values())),
                        'maximum_size':K,'maximum_count':sum(s.bit_count()==K for s in safe)})
    lower=json.loads((ROOT/'round19_rule_pair_lower.json').read_bytes())
    assert [r['total_variants'] for r in lower['families']]==[194,18721]
    for family in lower['families']:
        assert sum(r['orbit_size'] for r in family['checks'])==family['total_variants']
        assert all(r['empty_outcome']=='P' for r in family['checks'])
    files=['scripts/round35_minimum_family_verify.py','scripts/round35_empty_intersection_search.cpp',
           'scripts/round25_forced_verify.py','scripts/kc_core.h',
           'round35_empty_intersection_search.json','round19_rule_pair_lower.json',
           'round19-rule-removal-audit.md','scripts/round19_rule_pair_lower.py']
    out={'B524_original_verdict':'SUPPORTED','B523_original_verdict':'REFUTED',
         'n':4,'minimum_cardinality':3,'removed_indices':indices,
         'removed_ids':[list(bits(q)) for q in masks],
         'removed_coordinates':[[points[p] for p in bits(q)] for q in masks],
         'common_intersection':[], 'all_eight_subfamilies':records,
         'lower_bound_source':'round19_rule_pair_lower.json (previously certified full one/pair census)',
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round35_minimum_family_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS B524: cardinality minimum3 with EMPTY common intersection; eight subsets full independent mex')
    print('removed IDs',out['removed_ids'],'g0s',[r['g0'] for r in records])


if __name__=='__main__':main()

"""Validate resumed DFS against independent complete n4 k5 enumeration."""
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry
from round56_resume_run import invoke

ROOT=Path(__file__).resolve().parents[1]


def main():
    _,quads,_=geometry(4)
    full=(1<<16)-1
    expected=[]
    for ids in combinations(range(16),5):
        s=sum(1<<p for p in ids)
        if any(s&q==q for q in quads):
            continue
        if all(any((s|(1<<p))&q==q for q in quads) for p in range(16) if not s>>p&1):
            expected.append(ids)
    assert len(expected)==176
    runs=[]
    collected=[]
    for root in range(12):
        baseline,_=invoke(4,5,root,0,[],True)
        assert baseline['complete']
        target=[q for q in expected if q[0]==root]
        assert list(map(tuple,baseline['maximal_sets']))==target
        prefix=[]
        resumed=[]
        chunks=0
        while True:
            chunk,_=invoke(4,5,root,0,prefix,True,100)
            chunks+=1
            resumed.extend(map(tuple,chunk['maximal_sets']))
            assert chunks<=200
            if chunk['complete']:
                break
            next_prefix=chunk['timeout_prefix']
            assert not prefix or next_prefix>=prefix
            prefix=next_prefix
        assert resumed==target
        collected.extend(resumed)
        runs.append({'root':root,'chunks_with_node_limit_100':chunks,'maximal_sets':len(target),
                     'baseline_nodes':baseline['nodes']})
    assert collected==expected
    # Check the conservative frontiers inferred from legacy counters.
    legacy=[]
    for root in range(5):
        file=f'round53_n10_k8_root{root}.json'
        d=json.loads((ROOT/file).read_text())
        assert not d['complete'] and not d['found'] and d['nodes_by_depth'][1]==1
        count=d['nodes_by_depth'][2]
        assert count>1
        legacy.append({'root':root,'fully_processed_second_ids':[root+1,root+count-1],
                       'conservative_resume_prefix':[root,root+count]})
    files=['scripts/round56_resumable_kmin.cpp','scripts/round53_n10_eight_roots.cpp',
           'scripts/round56_resume_audit.py','scripts/round56_resume_run.py',
           'scripts/round25_forced_verify.py']+[f'round53_n10_k8_root{r}.json' for r in range(5)]
    result={'complete_independent_n4_k5_maximal_count':176,'chunk_validation':runs,
            'legacy_n10_frontiers':legacy,'legacy_total_nodes':sum(json.loads((ROOT/f'round53_n10_k8_root{r}.json').read_text())['nodes'] for r in range(5)),
            'legacy_n10_eight_stone_exclusion_proved':False,
            'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round56_resume_verified.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS all 176 n4 five-stone maximals match complete and resumed DFS; n10 legacy is UNKNOWN')


if __name__=='__main__':
    main()

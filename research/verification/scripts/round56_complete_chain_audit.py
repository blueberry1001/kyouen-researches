"""Check the five resumed absence chains, proving s10 >=9."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]


def main():
    validation=json.loads((ROOT/'round56_resume_verified.json').read_text())
    assert validation['complete_independent_n4_k5_maximal_count']==176
    for f,h in validation['sha256'].items():
        assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,(f,'changed')
    rows=[]
    files=['scripts/round56_complete_chain_audit.py','scripts/round56_resumable_kmin.cpp',
           'scripts/round53_n10_eight_roots.cpp','scripts/round56_resume_run.py',
           'round56_resume_verified.json','round46_saturation_verified.json',
           'round51_n10_k7_window.json','round49_s10_verified.json']
    for root,expected in enumerate([15,18,13,27,20]):
        oldname=f'round53_n10_k8_root{root}.json'
        newname=f'round56_n10_k8_root{root}_step1.json'
        old=json.loads((ROOT/oldname).read_text())
        new=json.loads((ROOT/newname).read_text())
        assert old['complete'] is False and old['found'] is False
        assert old['nodes_by_depth'][1]==1 and root+old['nodes_by_depth'][2]==expected
        assert new['parent']==oldname and new['resume_prefix']==[root,expected]
        assert new['complete'] is True and new['found'] is False and new['timeout_prefix']==[]
        assert new['enumerate_all'] is False and new['node_limit']==0
        assert new['n']==10 and new['k']==8 and new['first_stone_root']==root
        assert new['forbidden_quads']==54441 and new['triple_completion_incidence']==217764
        for f,h in new['sha256'].items():
            assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,(f,'changed')
        rows.append({'root':root,'legacy_complete_second_ids':[root+1,expected-1],
                     'suffix_start':[root,expected],'suffix_complete':True,
                     'legacy_nodes':old['nodes'],'suffix_nodes':new['nodes'],
                     'suffix_seconds':new['seconds']})
        files.extend([oldname,newname])
    assert json.loads((ROOT/'round46_saturation_verified.json').read_text())['s9_bounds']==[9,9]
    lower=json.loads((ROOT/'round51_n10_k7_window.json').read_text())
    assert lower['n']==10 and lower['k']==7 and lower['complete'] and not lower['found']
    upper=json.loads((ROOT/'round49_s10_verified.json').read_text())
    # Its actual witness is independently certified in round48_49_audit.py.
    assert upper['s10_bounds'][1]==10
    result={'B093_original_verdict':'PARTIAL','s10_bounds':[9,10],
            'all_eight_stone_maximals_excluded':True,'five_complete_prefix_suffix_chains':rows,
            'old_runs_alone_are_not_complete':True,
            'finite_B097_monotonicity_now_supported_through_n':10,
            'suffix_nodes_total':sum(d['suffix_nodes'] for d in rows),
            'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round56_complete_verified.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS all five eight-stone chains complete and absent; 9<=s10<=10')


if __name__=='__main__':
    main()

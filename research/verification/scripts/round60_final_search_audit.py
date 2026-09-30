"""Audit completed local radius nine and preserve the unknown nine-stone SAT."""
from pathlib import Path
from itertools import combinations,islice
from math import comb
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]


def main():
    sat=json.loads((ROOT/'round59_n10_atmost9.json').read_text())
    assert sat['status']=='UNKNOWN' and sat['witness_ids'] is None
    assert sat['n']==10 and sat['stone_count_bound']==9
    assert sat['quad_count']==54441 and sat['triple_completion_incidence']==217764
    for f,h in sat['sha256'].items():
        assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h
    local=json.loads((ROOT/'round60_n10_deep_neighborhood.json').read_text())
    prior=json.loads((ROOT/'round57_n10_neighborhood.json').read_text())
    assert local['seed_ids']==prior['seed_ids']
    assert prior['local_complete'] and prior['complete_deletion_radius']==8 and not prior['found']
    assert local['found'] is False and local['local_complete'] is False
    assert local['complete_deletion_radius']==9 and local['active_radius']==10
    assert local['starting_radius']==9 and local['last_radius_requested']==12
    assert local['source_sha256']==hashlib.sha256((ROOT/'scripts/round60_n10_deep_neighborhood.cpp').read_bytes()).hexdigest()
    assert local['prior_source_sha256']==hashlib.sha256((ROOT/local['prior_completed_radii_source']).read_bytes()).hexdigest()
    # The leaf counter includes the currently interrupted deletion subset.
    # Repeating this last subset is a conservative restart for radius ten.
    entered_at_ten=local['subsets_examined']-comb(19,9)
    assert entered_at_ten==22086
    frontier=list(next(islice(combinations(range(19),10),entered_at_ten-1,None)))
    files=['scripts/round60_final_search_audit.py','scripts/round59_n10_nine_sat.py',
           'scripts/round60_n10_deep_neighborhood.cpp','round59_n10_atmost9.json',
           'round60_n10_deep_neighborhood.json','round57_n10_neighborhood.json']
    out={'s10_bounds_unchanged':[9,10],'round59_status':'UNKNOWN',
         'K10_bounds_unchanged':[19,23],'complete_local_deletion_radius':9,
         'all_radius_nine_subsets_checked':comb(19,9),
         'any_twenty_stone_set_overlap_with_this_seed_at_most':9,
         'twenty_stone_set_global_absence_proved':False,
         'radius_ten_completed_first_subsets':entered_at_ten-1,
         'radius_ten_conservative_resume_deletion_indices':frontier,
         'radius_ten_conservative_resume_deleted_point_ids':[local['seed_ids'][i] for i in frontier],
         'resume_code_for_deep_neighborhood_not_yet_implemented':True,
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round60_final_verified.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print('PASS radius nine complete; radius ten interrupted; SAT UNKNOWN; global bounds unchanged')


if __name__=='__main__':
    main()

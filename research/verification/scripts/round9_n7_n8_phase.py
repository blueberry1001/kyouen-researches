"""Find matching two-deletion certificates for phase B (15-stone targets).

The lower bound comes from the complete round9 zero/one-deletion audit.
This script only searches for the matching upper bound, not all n8 maxima.
"""
from pathlib import Path
from itertools import combinations, product
import json

from kyouen_core import is_forbidden_quad
from round9_geometry import curve, evaluate, determinant


def main():
    directory = Path(__file__).resolve().parents[1]
    prior = json.loads((directory/'round9_n7_n8_overlap.json').read_text(encoding='utf-8'))
    record = next(r for r in prior['records'] if not (r['mask_n7']>>24&1))
    base = [(i%7,i//7) for i in range(49) if record['mask_n7']>>i&1]
    all_witnesses = []
    counts = {'retained_12_sets_tested':0,'new_triples_tested':0}
    for dx,dy in product(range(2),repeat=2):
        stones = [(x+dx,y+dy) for x,y in base]
        outside = [(x,y) for y in range(8) for x in range(8) if (x,y) not in stones]
        found = None
        for remove in combinations(range(14),2):
            kept = [p for i,p in enumerate(stones) if i not in remove]
            cc = [curve(t) for t in combinations(kept,3)]
            additions = [p for p in outside if all(evaluate(c,p) for c in cc)]
            counts['retained_12_sets_tested'] += 1
            for new in combinations(additions,3):
                counts['new_triples_tested'] += 1
                if not all(determinant([*old,*pair]) for pair in combinations(new,2)
                           for old in combinations(kept,2)):
                    continue
                if not all(determinant([stone,*new]) for stone in kept):
                    continue
                target = [*kept,*new]
                assert all(not is_forbidden_quad(q) for q in combinations(target,4))
                found = {'source_index':record['source_index'],'offset':[dx,dy],
                         'original':stones,'removed':[stones[i] for i in remove],
                         'added':list(new),'points':target,'overlap':len(set(stones)&set(target))}
                break
            if found:
                break
        all_witnesses.append(found)
        print('offset',dx,dy,'found',bool(found),flush=True)
    result = {'source_mask':record['mask_n7'],'source_index':record['source_index'],
              'target_size':15,'B387_scope':'minimum removals to a safe 15-set',
              'phase_A_minimum':1,
              'phase_B_minimum':2 if any(all_witnesses) else None,
              'counts':counts,'witnesses_by_offset':all_witnesses}
    target = directory/'round9_n7_n8_phase.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()

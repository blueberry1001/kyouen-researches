"""B386: exhaustive zero/one-deletion extension audit, no n8 maximum census.

All 16 saved n7 maxima, all four embeddings in n8, and every original stone
deletion. A 15-set sharing >=13 stones must occur in this finite search.
"""
from itertools import combinations, product
from pathlib import Path
from collections import Counter
from hashlib import sha256
import json
import struct

from kyouen_core import is_forbidden_quad
from round9_geometry import curve, evaluate, determinant


def main():
    root = Path(__file__).resolve().parents[3]
    source = root/'night-research/maxsafe_n7_K14.bin'
    raw = source.read_bytes()
    masks = struct.unpack('<'+'Q'*(len(raw)//8),raw)
    assert len(masks) == len(set(masks)) == 16
    records, witnesses, direct_audit = [], [], 0
    single_hist = Counter()
    board = [(x,y) for y in range(8) for x in range(8)]
    for source_index, mask in enumerate(masks):
        base = [(i%7,i//7) for i in range(49) if mask>>i&1]
        assert len(base)==14
        assert all(not is_forbidden_quad(q) for q in combinations(base,4))
        for dx,dy in product(range(2),repeat=2):
            stones = [(x+dx,y+dy) for x,y in base]
            outside = [p for p in board if p not in stones]
            triples = [(sum(1<<i for i in ids),curve([stones[i] for i in ids]))
                       for ids in combinations(range(14),3)]
            candidates = [[] for _ in range(14)]
            no_deletion = []
            for p in outside:
                common, blocked = (1<<14)-1, False
                for triple_mask, coefficients in triples:
                    if evaluate(coefficients,p)==0:
                        common &= triple_mask
                        blocked = True
                if not blocked:
                    no_deletion.append(p)
                    witnesses.append({'source_index':source_index,'offset':[dx,dy],
                                      'removed':[], 'added':[p],'points':stones+[p]})
                for i in range(14):
                    if common>>i&1:
                        candidates[i].append(p)
            trials = []
            for removed, additions in enumerate(candidates):
                kept = stones[:removed]+stones[removed+1:]
                single_hist[len(additions)] += 1
                # Independent point-by-point test of every candidate list.
                expected = [p for p in outside if all(determinant([*q,p])!=0
                                                       for q in combinations(kept,3))]
                assert expected == additions
                direct_audit += len(outside)
                good_pairs = []
                for p,q in combinations(additions,2):
                    if all(determinant([*two,p,q])!=0 for two in combinations(kept,2)):
                        result = [*kept,p,q]
                        assert all(not is_forbidden_quad(four) for four in combinations(result,4))
                        good_pairs.append([p,q])
                        witnesses.append({'source_index':source_index,'offset':[dx,dy],
                                          'removed':[stones[removed]],'added':[p,q],'points':result})
                trials.append({'removed':stones[removed],'individually_legal_new_points':additions,
                               'compatible_pairs':good_pairs})
            records.append({'source_index':source_index,'mask_n7':mask,'offset':[dx,dy],
                            'no_deletion_additions':no_deletion,'one_deletion_trials':trials})
        print('n7 maximum',source_index,'checked; 15-set witnesses',len(witnesses),flush=True)
    result = {'complete':True,'source':str(source.relative_to(root)),
              'source_sha256':sha256(raw).hexdigest(),'maxima_n7':len(masks),
              'embeddings':len(records),'one_deletion_trials':14*len(records),
              'independent_single_point_tests':direct_audit,
              'single_candidate_count_histogram':dict(sorted(single_hist.items())),
              'B386':'REFUTED' if witnesses else 'SUPPORTED',
              'fifteen_set_witnesses':witnesses,'records':records}
    target = root/'research/verification/round9_n7_n8_overlap.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print({k:v for k,v in result.items() if k not in ('records','fifteen_set_witnesses')},flush=True)
    print(target,flush=True)


if __name__=='__main__':
    main()

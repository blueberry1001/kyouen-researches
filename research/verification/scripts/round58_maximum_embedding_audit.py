"""Original B087: every n7 maximum embedding is already maximal on n8."""
from itertools import combinations
from pathlib import Path
import hashlib
import json
import struct
import subprocess
from round25_forced_verify import bits,curve,det4

ROOT=Path(__file__).resolve().parents[1]


def main():
    data=json.loads((ROOT/'round9_n7_outer_patterns.json').read_text())
    masks=sorted(r['mask'] for r in data['records'])
    assert len(masks)==len(set(masks))==16
    # Independent complete n7 traversal (round28) must have exactly the same
    # highest layer as the earlier catalogue. This tiny file has no header.
    raw=subprocess.run(['wsl','--exec','cat','/home/yuubi/round28_n7/level_14.occ'],capture_output=True,check=True).stdout
    assert len(raw)==128 and sorted(struct.unpack('<16Q',raw))==masks
    layers=json.loads((ROOT/'round28_n7_layers.json').read_text())
    assert layers['max_safe']==14 and layers['levels'][0]['states']==16
    record=[]
    tests=0
    for s in masks:
        coordinates=[(p%7,p//7) for p in bits(s)]
        assert len(coordinates)==14
        assert all(det4(q) for q in combinations(coordinates,4))
        assert {min(x for x,y in coordinates),max(x for x,y in coordinates)}=={0,6}
        assert {min(y for x,y in coordinates),max(y for x,y in coordinates)}=={0,6}
        for dx,dy in [(0,0),(0,1),(1,0),(1,1)]:
            image=[(x+dx,y+dy) for x,y in coordinates]
            triples=list(combinations(image,3))
            coefficients=[curve(t) for t in triples]
            certificates={}
            for y in range(8):
                for x in range(8):
                    if (x,y) in image:
                        continue
                    tests+=1
                    direct=[i for i,t in enumerate(triples) if det4((*t,(x,y)))==0]
                    via_curve=[i for i,(a,b,c,d) in enumerate(coefficients) if a*(x*x+y*y)+b*x+c*y+d==0]
                    assert direct==via_curve and direct
                    certificates[str(x+8*y)]=list(triples[direct[0]])
            assert len(certificates)==50
            record.append({'n7_mask':s,'offset':[dx,dy],'all_empty_points_blocked':True,
                           'blocking_triple_by_empty_id':certificates})
    fifteen=json.loads((ROOT/'round9_n7_n8_overlap.json').read_text())['fifteen_set_witnesses'][0]['points']
    assert len(fifteen)==len(set(map(tuple,fifteen)))==15
    assert all(0<=x<8 and 0<=y<8 for x,y in fifteen)
    assert all(det4(q) for q in combinations(fifteen,4))
    assert tests==3200 and len(record)==64
    files=['scripts/round58_maximum_embedding_audit.py','scripts/round25_forced_verify.py',
           'round9_n7_outer_patterns.json','round9_n7_n8_overlap.json',
           'round28_n7_layers.json','round28_n7_independent.json','round28_n7_audited.json',
           'round28-seven-board-original-verdicts.md']
    result={'B087_original_verdict':'SUPPORTED','witness_board_n':7,
            'K7':14,'K8_independent_lower_bound':15,'K8_matching_upper_bound_needed':False,
            'complete_maximum_count_n7':16,'translations_checked':64,
            'empty_point_tests_in_two_methods':3200,'fifteen_stone_witness':fifteen,
            'complete_n7_highest_layer_sha256':hashlib.sha256(raw).hexdigest(),
            'records':record,'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round58_embedding_verified.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS B087 n7: all 16 maxima x four embeddings are maximal on n8; independent K8>=15')


if __name__=='__main__':
    main()

"""Fresh determinant geometry and full D4 orbit inventory for n7 single removal."""
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits
ROOT=Path(__file__).resolve().parents[1]

def main():
    n=7;points,quads,curves=geometry(n);index={q:i for i,q in enumerate(quads)};orbits={}
    for i,q in enumerate(quads):
        images=[]
        for reflect in (False,True):
            for rotation in range(4):
                image=0
                for p in bits(q):
                    x,y=points[p]
                    if reflect:x=n-1-x
                    for _ in range(rotation):x,y=n-1-y,x
                    image|=1<<(x+n*y)
                images.append(index[image])
        rep=min(images);orbits.setdefault(rep,set()).add(i)
    assert sorted(i for orbit in orbits.values() for i in orbit)==list(range(len(quads)))
    # All representatives, with smaller supporting curves first. Each run is
    # budgeted; UNKNOWN is never a losing verdict.
    def score(rep):
        q=quads[rep];support=next(c.bit_count() for c in curves if c&q==q)
        distance=sum((points[p][0]-3)**2+(points[p][1]-3)**2 for p in bits(q))
        return support,distance,rep
    reps=sorted(orbits,key=score)
    data={'n':n,'quad_masks':quads,'curve_masks':curves,'orbits':[{'rep':rep,'members':sorted(orbits[rep])} for rep in reps],
          'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (ROOT/'round32_b251_n7_geometry.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    (ROOT/'round32_b251_n7_input.txt').write_text(f'49 {len(quads)} {len(reps)}\n'+' '.join(map(str,quads))+'\n'+' '.join(map(str,reps))+'\n'+str(len(curves))+'\n'+' '.join(map(str,curves))+'\n',encoding='utf-8')
    print('n7 quads',len(quads),'D4 representatives',len(reps))

if __name__=='__main__':main()

#!/usr/bin/env python3
import re, sys

HEADER=re.compile(r'^\[children\]\s+t=(\d+)s\s+n=(\d+)\s+updates=(\d+)')
ROW=re.compile(r'^\s*move=\s*(\d+)\s+pn=(\d+)\s+dn=(\d+)\s+st=(\d+)\s+work=(\d+)\s+legal=(\d+)')

def last_block(path):
    lines=open(path,encoding='utf-8',errors='replace').read().splitlines()
    starts=[i for i,l in enumerate(lines) if HEADER.match(l)]
    if not starts:
        return None,[]
    i=starts[-1]
    h=HEADER.match(lines[i])
    rows=[]
    for l in lines[i+1:]:
        m=ROW.match(l)
        if not m: break
        move,pn,dn,st,work,legal=map(int,m.groups())
        rows.append(dict(move=move,pn=pn,dn=dn,st=st,work=work,legal=legal))
    return dict(t=int(h.group(1)),n=int(h.group(2)),updates=int(h.group(3))),rows

def main():
    print("arm\tmove\tpn\tdn\tst\twork\tlegal")
    for spec in sys.argv[1:]:
        arm,path=spec.split("=",1)
        h,rows=last_block(path)
        if h is None:
            print("# %s MISSING_CHILD_BLOCK" % arm)
            continue
        print("# %s t=%d n=%d updates=%d solved_children=%d" %
              (arm,h["t"],h["n"],h["updates"],sum(r["st"] in (2,3) for r in rows)))
        for r in sorted(rows,key=lambda x:x["move"]):
            print("%s\t%d\t%d\t%d\t%d\t%d\t%d" %
                  (arm,r["move"],r["pn"],r["dn"],r["st"],r["work"],r["legal"]))

if __name__=="__main__":
    main()

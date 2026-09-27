#!/usr/bin/env python3
"""Post-hoc geometry/cost proxy analysis on the frozen AB staged-V3 cohort."""
import csv, math
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"results/10x10/ab-staged-v3-root/parent_summary.csv"
def rank(v):
    order=sorted(range(len(v)),key=lambda i:v[i]); r=[0.0]*len(v); i=0
    while i<len(order):
        j=i+1
        while j<len(order) and v[order[j]]==v[order[i]]: j+=1
        rr=(i+j-1)/2+1
        for k in range(i,j): r[order[k]]=rr
        i=j
    return r
def pearson(a,b):
    ma=sum(a)/len(a); mb=sum(b)/len(b)
    x=[z-ma for z in a]; y=[z-mb for z in b]
    den=math.sqrt(sum(z*z for z in x)*sum(z*z for z in y))
    return sum(u*v for u,v in zip(x,y))/den if den else float("nan")
def spearman(a,b): return pearson(rank(a),rank(b))
rows=list(csv.DictReader(SRC.open(newline="",encoding="utf-8")))
for r in rows:
    ids=list(map(int,r["parent"].split(","))); pts=[(p%10,p//10) for p in ids]; d=[]
    for i in range(3):
        for j in range(i):
            dx=pts[i][0]-pts[j][0]; dy=pts[i][1]-pts[j][1]; d.append(dx*dx+dy*dy)
    r["d2_sum"]=sum(d); r["d2_max"]=max(d)
    r["bbox_area"]=(max(x for x,y in pts)-min(x for x,y in pts))*(max(y for x,y in pts)-min(y for x,y in pts))
    r["center_r2_sum"]=sum((x-4.5)**2+(y-4.5)**2 for x,y in pts)
    r["a"]=int(r["a_exact_visited"]); r["ratio"]=float(r["visited_ratio"])
log_a=[math.log(r["a"]) for r in rows]
print("n",len(rows))
for f in ["d2_sum","d2_max","bbox_area","center_r2_sum"]:
    print(f,"spearman_logA",f"{spearman([r[f] for r in rows],log_a):.6f}")
print("threshold_sweep_d2_sum")
for t in sorted({r["d2_sum"] for r in rows}):
    policy=[r["ratio"] if r["d2_sum"]>=t else 1.0 for r in rows]
    agg=sum(r["a"]*(r["ratio"] if r["d2_sum"]>=t else 1.0) for r in rows)/sum(r["a"] for r in rows)
    print(t,sum(r["d2_sum"]>=t for r in rows),f"median={median(policy):.6f}",f"improved={sum(x<1 for x in policy)}",f"worst={max(policy):.6f}",f"aggregate={agg:.6f}")

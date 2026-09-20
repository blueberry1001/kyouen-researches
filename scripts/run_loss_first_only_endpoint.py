#!/usr/bin/env python3
"""Blinded endpoint collector for the frozen loss-first-only ablation.

No per-run endpoint value is printed. All 36 fresh-process runs must finish and
pass outcome parity before aggregate L statistics are emitted.  Condition order
is a frozen 3x3 cyclic counterbalance by parent index.
"""
from __future__ import annotations
import csv, json, math, statistics, subprocess, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BIN=ROOT/"tmp-kb/order_ab_native"
OUT=ROOT/"results/10x10/cache-aware-loss-first-only"
PARENTS=["0,11,35","11,38,44","11,78,87","12,24,68","12,32,55","13,52,57","14,64,74","23,44,45","3,47,63","3,53,84","4,24,26","4,42,54"]
CONDS=("B","L","F")
ORDERS=(("F","B","L"),("B","L","F"),("L","F","B"))
ARGS={
 "B":["--below-root-order","cache-blind","--cache-aware-order-impl","sort"],
 "L":["--below-root-order","cache-aware","--cache-aware-order-impl","loss-first"],
 "F":["--below-root-order","cache-aware","--cache-aware-order-impl","sort"],
}

def one(parent:str,cond:str,order_index:int)->dict:
    with tempfile.NamedTemporaryFile("w",suffix=".txt",delete=False) as f:
        f.write(parent+"\n"); state=Path(f.name)
    try:
        cmd=[str(BIN),str(state),"0","90","0","0","--root-depth","3",*ARGS[cond]]
        t=time.monotonic()
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=10800)
        wall=time.monotonic()-t
    finally: state.unlink(missing_ok=True)
    if p.returncode: raise RuntimeError(f"solver failed parent={parent} cond={cond} rc={p.returncode}")
    rows=list(csv.DictReader(p.stdout.splitlines()))
    if len(rows)!=1: raise RuntimeError(f"unexpected solver rows parent={parent} cond={cond}: {len(rows)}")
    r=rows[0]
    return {"parent":parent,"condition":cond,"order_index":order_index,"outcome":r["outcome"],
            "visited":int(r["visited"]),"solver_seconds":float(r["seconds"]),"wall_seconds":wall}

def main()->None:
    if not BIN.is_file(): raise SystemExit("missing endpoint binary")
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    # Deliberately silent: do not expose L or comparator values before cohort completion.
    for i,parent in enumerate(PARENTS):
        order=ORDERS[i%3]
        for j,cond in enumerate(order): rows.append(one(parent,cond,j))
    if len(rows)!=36 or {(r["parent"],r["condition"]) for r in rows}!={(p,c) for p in PARENTS for c in CONDS}:
        raise RuntimeError("incomplete 12x3 cohort")
    by={(r["parent"],r["condition"]):r for r in rows}
    bad=[p for p in PARENTS if len({by[p,c]["outcome"] for c in CONDS})!=1]
    if bad: raise RuntimeError("FAIL-SAFETY outcome mismatch: "+",".join(bad))
    # Cohort is now complete and parity-safe: endpoint may be opened.
    sb=sum(by[p,"B"]["visited"] for p in PARENTS); sl=sum(by[p,"L"]["visited"] for p in PARENTS); sf=sum(by[p,"F"]["visited"] for p in PARENTS)
    den=sb-sf
    if den<=0: raise RuntimeError("frozen positive-denominator assumption violated")
    recovery=(sb-sl)/den
    improved=sum(by[p,"L"]["visited"]<by[p,"B"]["visited"] for p in PARENTS)
    equal_f=sum(by[p,"L"]["visited"]==by[p,"F"]["visited"] for p in PARENTS)
    lb=[by[p,"L"]["visited"]/by[p,"B"]["visited"] for p in PARENTS]
    lf=[by[p,"L"]["visited"]/by[p,"F"]["visited"] for p in PARENTS]
    def gm(xs): return math.exp(sum(math.log(x) for x in xs)/len(xs))
    result={"cohort_complete":True,"outcome_parity":True,"n_parents":12,"sum_B":sb,"sum_L":sl,"sum_F":sf,
            "recovery":recovery,"L_improves_B_count":improved,"L_equals_F_count":equal_f,
            "median_L_over_B":statistics.median(lb),"geomean_L_over_B":gm(lb),
            "median_L_over_F":statistics.median(lf),"geomean_L_over_F":gm(lf),
            "primary_success":recovery>=0.80 and improved>=10}
    (OUT/"endpoint_raw.json").write_text(json.dumps(rows,indent=2)+"\n")
    (OUT/"endpoint_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__": main()

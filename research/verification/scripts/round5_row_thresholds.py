"""Reproduce B557's counterexample threshold and the five-row AP threshold.

Requires the already available WSL Ubuntu g++; no packages are installed.
Builds two independent engines under unique /tmp names. Data lives beside
this script's parent directory. Every saved positive witness is checked again
using Python's full determinant expansion.
"""
from itertools import combinations
import hashlib
import json
from pathlib import Path
import subprocess

from kyouen_core import is_forbidden_quad

FOLDER=Path(__file__).resolve().parents[1]
SCRIPTS=FOLDER/"scripts"


def linux_path(path):
    path=Path(path).resolve()
    return "/mnt/"+path.drive[0].lower()+str(path)[2:].replace("\\","/")


def run(args):
    proc=subprocess.run(["wsl","-d","Ubuntu","--",*map(str,args)],
                        capture_output=True,text=True,check=True,timeout=180)
    return proc.stdout


def check_witness(record):
    if not record["found"]:return
    w,m=record["w"],record["m"]
    rows=record["rows"]
    assert len(rows)==w and all(len(row)==3 and len(set(row))==3 for row in rows)
    assert all(0<=x<m for row in rows for x in row)
    if record.get("AP_only"):
        assert all(row[1]-row[0]==row[2]-row[1]>0 for row in rows)
    points=[(x,y) for y,row in enumerate(rows) for x in row]
    count=0
    for q in combinations(points,4):
        assert not is_forbidden_quad(q),(record,q)
        count+=1
    record["independent_python_quad_checks"]=count


def main():
    for stem,binary in (("round5_row_triples","/tmp/kyouen_round5_rows"),
                        ("round5_row_hypergraph","/tmp/kyouen_round5_hypergraph")):
        run(["g++","-O2","-std=c++17",linux_path(SCRIPTS/(stem+".cpp")),"-o",binary])
    result={"row_triple_engine":[],"hypergraph_engine":[],"edge_files":[],
            "source_hashes":{}}
    output=FOLDER/"round5_row_thresholds.json"
    def save():output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for name in ("round5_row_triples.cpp","round5_row_hypergraph.cpp","kyouen_core.py"):
        result["source_hashes"][name]=hashlib.sha256((SCRIPTS/name).read_bytes()).hexdigest()
    cases=[(2,4,0),(2,5,0),(3,6,0),(3,7,0),(4,8,0),(4,9,0),
           (5,11,0),(5,12,0),(4,9,1),(4,10,1),(5,13,1),(5,14,1)]
    for w,m,ap in cases:
        row=json.loads(run(["/tmp/kyouen_round5_rows",w,m,ap,2000000]))
        assert row["complete"]
        check_witness(row)
        result["row_triple_engine"].append(row)
        print('row triples',w,m,'AP',ap,'found',row['found'],'nodes',row['nodes'],flush=True)
        save()
    for w,m,ap in ((5,11,0),(5,12,0),(5,13,1)):
        points=[(x,y) for y in range(w) for x in range(m)]
        edges=[]
        for ids in combinations(range(w*m),4):
            if is_forbidden_quad([points[i] for i in ids]):
                edges.append(sum(1<<i for i in ids))
        path=FOLDER/"data"/f"round5_forbidden_w{w}_m{m}.txt"
        path.write_text("".join(str(q)+"\n" for q in edges),encoding="ascii")
        result["edge_files"].append({"w":w,"m":m,"path":str(path.relative_to(FOLDER)),
                                     "count":len(edges),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
        row=json.loads(run(["/tmp/kyouen_round5_hypergraph",w,m,linux_path(path),100000000,ap]))
        assert row["complete"]
        check_witness(row)
        first=next(r for r in result["row_triple_engine"] if (r["w"],r["m"],int(r["AP_only"]))==(w,m,ap))
        assert row["found"]==first["found"]
        assert row["rows"]==first["rows"]
        assert row["full_row_prefixes"]==first["nodes"]
        result["hypergraph_engine"].append(row)
        print('independent hypergraph',w,m,'AP',ap,'found',row['found'],'full row prefixes',row['full_row_prefixes'],flush=True)
        save()
    result["all_checks_passed"]=True
    save()
    print(output,flush=True)


if __name__=="__main__":main()

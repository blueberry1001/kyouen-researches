"""Read-only audit of the saved AP construction claims; never edits their files."""
import ast
from itertools import combinations
import json
from pathlib import Path
import re

from kyouen_core import is_forbidden_quad


def inspect(rows):
    points = [(x,y) for y,row in enumerate(rows) for x in row]
    forbidden = [q for q in combinations(points,4) if is_forbidden_quad(q)]
    return {"rows":rows,"point_count":len(points),
            "quadruples_checked":len(list(combinations(points,4))),
            "forbidden_count":len(forbidden),
            "first_forbidden":forbidden[0] if forbidden else None,
            "safe":not forbidden}


def main():
    folder=Path(__file__).resolve().parents[1]
    source=folder/"round4_b543_rect_v.json"
    raw=source.read_text(encoding="utf-8")
    try:
        json.loads(raw)
        parse_error=None
    except json.JSONDecodeError as exc:
        parse_error={"line":exc.lineno,"column":exc.colno,"message":exc.msg}
    result={"source":source.name,"json_parse_error":parse_error,"claims":[]}
    for line in raw.splitlines():
        match=re.search(r'"w(\d+)_m(\d+)":.*"rows_with_AP": (\d+).*"rows": (\[.*\])',line)
        if not match:continue
        w,m,claimed=map(int,match.group(1,2,3))
        rows=ast.literal_eval(match.group(4))
        if claimed != w or not rows:continue
        assert len(rows)==w
        assert all(len(row)==3 and row[1]-row[0]==row[2]-row[1]>0 for row in rows)
        assert all(0<=x<m for row in rows for x in row)
        data=inspect(rows)
        data.update(w=w,m=m,claimed_full=True)
        result["claims"].append(data)
        print(w,m,"safe",data["safe"],"bad quads",data["forbidden_count"],
              "first",data["first_forbidden"])
    known=[[[0,1,2],[1,3,5],[4,5,6]],
           [[0,1,2],[0,4,8],[1,5,9],[7,8,9]],
           [[0,1,6],[1,2,3],[5,6,7],[2,6,8]]]
    result["round2_comparison_witnesses"]=[inspect(rows) for rows in known]
    assert all(row["safe"] for row in result["round2_comparison_witnesses"])
    assert result["claims"]
    output=folder/"round4_ap_witness_audit.json"
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print('valid',sum(x['safe'] for x in result['claims']),'/',len(result['claims']))
    print('older independent witnesses: all safe')


if __name__=="__main__":main()

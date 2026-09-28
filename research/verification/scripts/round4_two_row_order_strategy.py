"""Construct and check an order-type response policy for B542.

Critical coordinates are labelled integer linear forms in occupied coordinates
and the two board endpoints. The policy uses only their weak order; lengths of
gaps are NOT included in its key. An action chooses a row and a boundary or the
leftmost or central lattice point in an open interval. Exact finite DP covers m=6..8;
the fixed-width theorem covers every m>=9.
"""
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import json

from round4_fixed_width import solve_two_rows


def critical_order(m, a, b):
    rows = [[x for x in range(m) if mask >> x & 1] for mask in (a,b)]
    labels = defaultdict(list)
    labels[0].append("L")
    labels[m-1].append("R")
    labelled_points=[(f"{r}.{i}",x) for r in (0,1) for i,x in enumerate(rows[r])]
    for pname,px in labelled_points:
        for qname,qx in labelled_points:
            if pname != qname:
                labels[2*px-qx].append(f"r{pname}:{qname}")
    for r in (0,1):
        for i,x in enumerate(rows[r]):
            labels[x].append(f"p{r}.{i}")
            labels[m-1-x].append(f"h{r}.{i}")
        for j,k in combinations(range(len(rows[1-r])),2):
            total = rows[1-r][j]+rows[1-r][k]
            for i,x in enumerate(rows[r]):
                # New x' in row r makes a forbidden 2+2 iff x'=total-x.
                labels[total-x].append(f"f{r}.{i}.{j}.{k}")
    coordinates = sorted(labels)
    # The three finite board lengths have separate tables. No occupied
    # coordinate value or gap length is used within any such table.
    key = ((f"board_length={m}",),)+tuple(tuple(sorted(labels[x])) for x in coordinates)
    return key, coordinates, rows


def candidate_actions(m, a, b, coordinates):
    for r,mask in enumerate((a,b)):
        for i,x in enumerate(coordinates):
            if 0<=x<m and not (mask>>x&1):
                yield (r,i,"boundary"), x
            if i+1<len(coordinates):
                for kind,xx in (("leftmost_open",x+1),
                                ("middle_open",(x+coordinates[i+1])//2)):
                    if 0<=xx<m and x<xx<coordinates[i+1] and not (mask>>xx&1):
                        yield (r,i,kind), xx


def main():
    groups = {}
    checked = {}
    games = {}
    for m in range(6,9):
        _,g = solve_two_rows(m)
        games[m] = g
        count = 0
        for (a,b),value in g.items():
            if a.bit_count()+b.bit_count() not in (1,3) or value == 0:
                continue
            count += 1
            key, coordinates, rows = critical_order(m,a,b)
            good = set()
            for action,x in candidate_actions(m,a,b,coordinates):
                child = (a|1<<x,b) if action[0]==0 else (a,b|1<<x)
                if child in g:
                    if g[child] == 0:
                        good.add(action)
            item = groups.setdefault(key, {"common":set(good),"members":[]})
            item["common"] &= good
            item["members"].append({"m":m,"rows":rows,"g":value,
                                    "winning_actions":sorted(good)})
        checked[m] = count
    failed = [{"order":key,"members":item["members"]} for key,item in groups.items()
              if not item["common"]]
    output = {"finite_lengths":[6,7,8],"one_or_three_stone_N_states":checked,
              "order_type_count":len(groups),"failed_type_count":len(failed),
              "failures":failed,"policy":[]}
    if not failed:
        for key,item in sorted(groups.items()):
            selected = min(item["common"])
            output["policy"].append({"order":key,"action":selected,
                                     "member_count":len(item["members"])})
        policy = {tuple(tuple(block) for block in row["order"]):tuple(row["action"])
                  for row in output["policy"]}
        # Play against EVERY opponent move, not only a particular opponent.
        traces = {}
        for m,g in games.items():
            seen, stack, terminals = set(), [(0,0)], 0
            while stack:
                state=stack.pop()
                if state in seen:continue
                seen.add(state)
                a,b=state
                assert g[state]==0 and (a.bit_count()+b.bit_count())%2==0
                children=[]
                for r,mask in enumerate(state):
                    for x in range(m):
                        if mask>>x&1:continue
                        child=(a|1<<x,b) if r==0 else (a,b|1<<x)
                        if child in g:children.append(child)
                if not children:
                    terminals+=1
                    continue
                for ca,cb in children:
                    assert g[ca,cb]>0
                    if ca.bit_count()+cb.bit_count()==5:
                        # Every legal sixth stone ends the game.
                        options=[]
                        for r,mask in enumerate((ca,cb)):
                            for x in range(m):
                                if mask>>x&1:continue
                                nxt=(ca|1<<x,cb) if r==0 else (ca,cb|1<<x)
                                if nxt in g:options.append(nxt)
                        assert options and all(g[nxt]==0 for nxt in options)
                        stack.append(options[0])
                        continue
                    key,coordinates,_=critical_order(m,ca,cb)
                    action=policy[key]
                    i=action[1]
                    if action[2]=="boundary":x=coordinates[i]
                    elif action[2]=="leftmost_open":x=coordinates[i]+1
                    else:x=(coordinates[i]+coordinates[i+1])//2
                    assert not ((ca,cb)[action[0]]>>x&1)
                    response=(ca|1<<x,cb) if action[0]==0 else (ca,cb|1<<x)
                    assert response in g and g[response]==0
                    stack.append(response)
            traces[m]={"reachable_even_states":len(seen),"terminal_states":terminals}
        output["all_opponent_play_checks"]=traces
    path=Path(__file__).resolve().parents[1]/"round4_two_row_order_strategy.json"
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print({k:v for k,v in output.items() if k not in ("policy","failures")})
    if failed:print("First failure:",failed[0])
    assert not failed, "No universal action for an order type; see saved failures"


if __name__=="__main__":
    main()

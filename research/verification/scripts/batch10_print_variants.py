import json
data = json.load(open("research/verification/batch10_variants.json"))
for r in data:
    n = r["n"]
    for name, v in r["variants"].items():
        print(
            f"n={n} {name}: g0={v['g0']} winner={v['winner']} "
            f"W={v['winning_first_moves']} nL={len(v['losing_first_moves'])} "
            f"mis={v['misere_winner']} maxg={v['max_g']} pos={v['n_positions']}"
        )

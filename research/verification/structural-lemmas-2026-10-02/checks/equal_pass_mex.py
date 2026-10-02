"""Verify equal private-pass counts preserve the relative-state option-DAG mex.

This is NOT a claim that privately owned passes form an impartial sum game.
For a finite DAG G with options H, define
 F(G,a,b) = mex({F(H,b,a): H option G} U {F(G,b,a-1): a>0}).
The extra option is omitted at terminal G when terminal_passes=False.
Then F(G,r,r)=g(G) for all nonnegative r.

Proof: induct first on r, then on the height of G. Ordinary children have
F(H,r,r)=g(H). If a pass is available, its target X=F(G,r,r-1) has a pass
option F(G,r-1,r-1)=g(G), so X != g(G). Adding X to the ordinary child
values cannot change their mex. The base r=0 is the ordinary recursion.
At a terminal G with terminal_passes=False both values are zero.

Stronger theorem when terminal passes ARE allowed:
 F(G,a,b) = g(G) if a=b;
            0 if a<b;
            2 if a=b+1 and g(G)=1;
            1 otherwise (a>b).
Proof uses induction on (height(G),a+b), lexicographically. All ordinary
children reverse the strict inequality. At a>b+1 both ordinary and pass
children have value 0. At a=b+1, ordinary children (if any) have value 0,
and the pass child has value g(G). At a<b every child has positive value.
The a=b case follows from the equal-rights theorem above.
"""
from functools import lru_cache
from itertools import product
from pathlib import Path
import hashlib
import json
import random


def mex(values):
    values = set(values)
    result = 0
    while result in values:
        result += 1
    return result


def check_graph(options, terminal_passes, max_rights=4):
    @lru_cache(None)
    def plain(v):
        return mex(plain(w) for w in options[v])

    @lru_cache(None)
    def extended(v, a, b):
        values = [extended(w, b, a) for w in options[v]]
        if a > 0 and (options[v] or terminal_passes):
            values.append(extended(v, b, a - 1))
        return mex(values)

    comparisons = 0
    maximum_plain_mex = 0
    asymmetric_examples = []
    for v in range(len(options)):
        maximum_plain_mex = max(maximum_plain_mex, plain(v))
        for r in range(max_rights + 1):
            assert extended(v, r, r) == plain(v), (options, v, r)
            comparisons += 1
        for a, b in [(0, 1), (1, 0), (1, 2), (2, 1)]:
            if extended(v, a, b) != plain(v):
                asymmetric_examples.append({"vertex": v, "rights": [a,b],
                    "ordinary_mex": plain(v), "extended_mex": extended(v,a,b)})
        if terminal_passes:
            for a in range(max_rights + 1):
                for b in range(max_rights + 1):
                    expected = plain(v) if a == b else (0 if a < b else
                               (2 if a == b + 1 and plain(v) == 1 else 1))
                    assert extended(v,a,b) == expected, (options,v,a,b,expected)
                    comparisons += 1
    return comparisons, maximum_plain_mex, asymmetric_examples


def main():
    total_comparisons = 0
    maximum_plain_mex = 0
    graph_count = 0
    n = 5
    for masks in product(*(range(1 << i) for i in range(n))):
        options = tuple(tuple(j for j in range(i) if masks[i] >> j & 1)
                        for i in range(n))
        graph_count += 1
        for terminal in (False, True):
            comparisons, maxmex, _ = check_graph(options, terminal)
            total_comparisons += comparisons
            maximum_plain_mex = max(maximum_plain_mex, maxmex)
    rng = random.Random(20261002)
    random_count = 500
    for _ in range(random_count):
        n = 30
        options = tuple(tuple(j for j in range(i) if rng.randrange(4) == 0)
                        for i in range(n))
        for terminal in (False, True):
            comparisons, maxmex, _ = check_graph(options, terminal)
            total_comparisons += comparisons
            maximum_plain_mex = max(maximum_plain_mex, maxmex)
    example_options = ((), (0,), (0,1))
    _, _, examples = check_graph(example_options, True)
    result = {
        "scope": "relative-state option DAG mex, not a disjunctive-sum equivalence claim",
        "finite_dag_theorem": "F(G,r,r)=g(G)",
        "terminal_pass_allowed_full_formula": {
            "a=b": "g(G)", "a<b": 0,
            "a=b+1 and g(G)=1": 2, "all_other_a>b": 1},
        "proof": __doc__,
        "exhaustive_graphs": graph_count,
        "exhaustive_vertices": 5,
        "random_graphs": random_count,
        "random_vertices": 30,
        "seed": 20261002,
        "rights_per_player_tested": list(range(5)),
        "terminal_pass_rules": [False,True],
        "comparisons": total_comparisons,
        "maximum_plain_mex_tested": maximum_plain_mex,
        "failures": 0,
        "asymmetric_counterexamples_on_nim_0_1_2": examples,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    destination = Path(__file__).with_suffix('.json')
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('proof','asymmetric_counterexamples_on_nim_0_1_2')}, indent=2))


if __name__ == '__main__':
    main()

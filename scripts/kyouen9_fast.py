"""Faster pair-sum engine: precompute forbidden-quad completion map once.

Precomputation: for every triple (C(81,3) = 85k), the set of v completing a
forbidden quad. ~85k x 78 checks ≈ 6.7M forbidden tests (each ~µs) — one-off
cost, then every legal_moves / response-set query is set algebra.

API mirrors kyouen9_pairsum: legal_moves, is_safe, response_sets, pair_sum,
exact_mobility, overlap. Cross-checked against it in tests.
"""

import pickle
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kyouen9_pairsum as k9

N = k9.N
V = k9.V
CACHE = Path(__file__).resolve().parents[1] / "tmp-kb" / "quad_completion.pkl"

COMPLETION = {}   # triple -> frozenset(v)
PAIR_W = {}       # pair -> list of triples containing it (for W_ab w/o v? no—per (a,b,v) need quads containing a,b,v)
TRIPLES_OF_PAIR = {}


def build():
    t0 = time.time()
    comp = {}
    for triple in combinations(range(V), 3):
        s = set()
        for v in range(V):
            if v in triple:
                continue
            if k9.forbidden(triple[0], triple[1], triple[2], v):
                s.add(v)
        comp[triple] = frozenset(s)
    print(f"built {len(comp)} triples in {time.time() - t0:.0f}s")
    return comp


def load():
    global COMPLETION
    if COMPLETION:
        return COMPLETION
    if CACHE.exists():
        t0 = time.time()
        with CACHE.open("rb") as f:
            COMPLETION = pickle.load(f)
        print(f"loaded completion cache ({time.time() - t0:.1f}s)")
        return COMPLETION
    COMPLETION = build()
    with CACHE.open("wb") as f:
        pickle.dump(COMPLETION, f)
    return COMPLETION


def bans_of_set(stones):
    comp = load()
    banned = set()
    for triple in combinations(sorted(stones), 3):
        banned |= set(comp[triple])
    return banned - set(stones)


def legal_moves(stones):
    occ = set(stones)
    return set(range(V)) - occ - bans_of_set(stones)


def is_safe(stones):
    comp = load()
    st = set(stones)
    for triple in combinations(sorted(stones), 3):
        if set(comp[triple]) & st:
            return False
    return True


def response_sets(parent, v, kind=None):
    P = list(parent)
    Pv = P + [v]
    assert is_safe(Pv)
    comp = load()
    Pv_set = set(Pv)
    out = {}
    for a, b in combinations(sorted(P), 2):
        key = tuple(sorted((a, b, v)))
        s = set()
        for r in comp[key]:
            if r in Pv_set:
                continue
            if kind is not None and k9.forbidden_kind(a, b, v, r) != kind:
                continue
            ok = True
            for q in combinations(sorted(Pv_set | {r}), 4):
                if set(q) == {a, b, v, r}:
                    continue
                if set(q) <= Pv_set:
                    continue  # P+v safe by assertion
                if k9.forbidden(*q):
                    ok = False
                    break
            if ok:
                s.add(r)
        out[(a, b)] = s
    return out


def pair_sum(parent, v, kind=None):
    return sum(len(s) for s in response_sets(parent, v, kind).values())


def exact_mobility(parent, v, kind=None):
    u = set()
    for s in response_sets(parent, v, kind).values():
        u |= s
    return len(u)


def canonical(stones):
    return k9.canonical(stones)

"""Tests for scripts/kyouen9_pairsum.py (tasks 5-6).

Covers:
  - forbidden rule detects both collinear and concyclic quads (and matches
    the solver determinant on random quads);
  - on safe 3-stone parents, the 3 dangerous-response sets are pairwise
    disjoint and S == newly-killed safe responses;
  - 4-stone overlap O <= 3 on sampled safe parents (math claim of task 6).
"""

import random
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import kyouen9_pairsum as k9
import kyouen9_fast as k9fast

N = k9.N


def test_collinear_and_circle_detected():
    assert k9.collinear4(0, 1, 2, 3)  # top row
    assert k9.forbidden_kind(0, 1, 2, 3) == "line"
    assert k9.forbidden_kind(0, 9, 18, 27) == "line"  # first column
    assert k9.forbidden_kind(0, 10, 20, 30) == "line"  # diagonal
    # rectangle corners (0,0),(2,0),(0,1),(2,1) are concyclic, not collinear
    r = (k9.pid(0, 0), k9.pid(2, 0), k9.pid(0, 1), k9.pid(2, 1))
    assert k9.forbidden_kind(*r) == "circle"
    # generic safe triple + far point
    assert k9.forbidden_kind(0, 1, 9, 40) is None


def test_matches_determinant_on_random_quads():
    rng = random.Random(12345)
    for _ in range(300):
        q = tuple(sorted(rng.sample(range(k9.V), 4)))
        got = k9.forbidden(*q)
        # integer determinant (exact)
        ids = list(q)
        m = []
        for v in ids:
            x, y = v % N, v // N
            m.append([x * x + y * y, x, y, 1])
        det = (m[0][0] * (m[1][1] * (m[2][2] * m[3][3] - m[2][3] * m[3][2])
                          - m[1][2] * (m[2][1] * m[3][3] - m[2][3] * m[3][1])
                          + m[1][3] * (m[2][1] * m[3][2] - m[2][2] * m[3][1]))
               - m[0][1] * (m[1][0] * (m[2][2] * m[3][3] - m[2][3] * m[3][2])
                            - m[1][2] * (m[2][0] * m[3][3] - m[2][3] * m[3][0])
                            + m[1][3] * (m[2][0] * m[3][2] - m[2][2] * m[3][0]))
               + m[0][2] * (m[1][0] * (m[2][1] * m[3][3] - m[2][3] * m[3][1])
                            - m[1][1] * (m[2][0] * m[3][3] - m[2][3] * m[3][0])
                            + m[1][3] * (m[2][0] * m[3][1] - m[2][1] * m[3][0]))
               - m[0][3] * (m[1][0] * (m[2][1] * m[3][2] - m[2][2] * m[3][1])
                            - m[1][1] * (m[2][0] * m[3][2] - m[2][2] * m[3][0])
                            + m[1][2] * (m[2][0] * m[3][1] - m[2][1] * m[3][0])))
        assert got == (det == 0), q


def _random_safe_parent(rng, k):
    for _ in range(2000):
        p = tuple(sorted(rng.sample(range(k9.V), k)))
        if k9.is_safe(p):
            return p
    raise AssertionError("no safe parent found")


def test_3stone_disjoint_and_sum_identity():
    rng = random.Random(999)
    checked = 0
    for _ in range(6):
        P = _random_safe_parent(rng, 3)
        for v in sorted(k9.legal_moves(P))[:25]:
            Pv = tuple(sorted(P + (v,)))
            if not k9.is_safe(Pv):
                continue
            sets = k9.response_sets(P, v)
            assert len(sets) == 3
            vals = list(sets.values())
            assert vals[0] & vals[1] == set()
            assert vals[0] & vals[2] == set()
            assert vals[1] & vals[2] == set()
            S = sum(map(len, vals))
            # S counts r with {a,b,v,r} forbidden and all other quads of
            # P+v+r safe. Every such r completes a forbidden quad with a
            # triple of P+v, hence is banned after P+v (killed as a reply).
            before = k9.legal_moves(P)
            after = k9.legal_moves(Pv)
            killed = (before - {v}) - after
            assert (vals[0] | vals[1] | vals[2]) <= killed
            # circle/line split adds up
            assert (k9.pair_sum(P, v, "circle") + k9.pair_sum(P, v, "line")) == S
            assert (k9.exact_mobility(P, v, "circle") + k9.exact_mobility(P, v, "line")) == k9.exact_mobility(P, v)
            # fast engine agrees with reference engine
            assert k9fast.pair_sum(P, v) == S
            assert k9fast.exact_mobility(P, v) == k9.exact_mobility(P, v)
            checked += 1
    assert checked > 50


def test_4stone_overlap_bound():
    rng = random.Random(31337)
    worst = 0
    for _ in range(6):
        P = _random_safe_parent(rng, 4)
        for v in sorted(k9.legal_moves(P))[:25]:
            Pv = tuple(sorted(P + (v,)))
            if not k9.is_safe(Pv):
                continue
            o = k9.overlap(P, v)
            assert o >= 0
            assert o <= 3, (P, v, o)
            worst = max(worst, o)
    print(f"max O observed: {worst}")

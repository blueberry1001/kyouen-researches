"""P6 regression: raw/filtered response-set separation + C++ cross-check.

Covers the metric-definition correction
(docs/9X9_PAIRSUM_METRIC_DEFINITION_CORRECTION.md):

  - raw_response_sets has NO other-quad filter;
  - filtered_response_sets keeps the old audit filter;
  - filtered mode has E'=O'=0 by construction on sampled (P, v);
  - raw mode exhibits O > 0 AND E > 0 examples (fixtures, not sampling luck);
  - raw_decomposition satisfies raw_pair == T + E + O exactly;
  - fast cached engine agrees with the reference engine on raw quantities;
  - C++ analyzer identity: raw_ab(v) == completion(a,b,v) minus P+v, and
    occupied/existing candidate exclusion matches analyze-9x9-pair-gap-
    decomposition.cpp (v must be non-occupied AND non-existing-dangerous).

The O>0 / E>0 fixtures below were found by search and are pinned so the
regression cannot silently pass by sampling different parents.
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


# Pinned fixtures: (parent, v) with raw O > 0, resp. raw E > 0.
# Verified against the C++ raw definitions; pinned so the regression cannot
# silently pass by sampling different parents.
O_FIXTURE = ((3, 29, 58, 76), 59)
E_FIXTURE = ((8, 17, 32, 72), 28)


def _completion_reference(parent, v):
    """Independent completion-table reference (no shared code with engines).

    completion(a,b,v) = {r : forbidden(a,b,v,r)}, mirroring the C++ table.
    """
    out = {}
    for a, b in combinations(sorted(parent), 2):
        s = {r for r in range(k9.V)
             if r not in set(parent) | {v} and k9.forbidden(a, b, v, r)}
        out[(a, b)] = s
    return out


def test_3stone_filtered_disjoint_and_killed_subset():
    """Filtered 3-stone sets are disjoint and ⊆ killed safe replies (old audit claim)."""
    rng = random.Random(999)
    checked = 0
    for _ in range(6):
        P = _random_safe_parent(rng, 3)
        for v in sorted(k9.legal_moves(P))[:25]:
            Pv = tuple(sorted(P + (v,)))
            if not k9.is_safe(Pv):
                continue
            sets = k9.filtered_response_sets(P, v)
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


def test_4stone_raw_overlap_bound_and_identity():
    """Raw identity raw_pair == T + E + O; raw O <= 3 on sampled parents."""
    rng = random.Random(31337)
    worst = 0
    for _ in range(6):
        P = _random_safe_parent(rng, 4)
        for v in sorted(k9.legal_moves(P))[:25]:
            Pv = tuple(sorted(P + (v,)))
            if not k9.is_safe(Pv):
                continue
            d = k9.raw_decomposition(P, v)
            assert d["raw_pair"] == d["T"] + d["E"] + d["O"], (P, v, d)
            assert 0 <= d["O"] <= 3, (P, v, d)
            assert k9fast.raw_decomposition(P, v)["O"] == d["O"]
            worst = max(worst, d["O"])
    print(f"max raw O observed: {worst}")


def test_raw_matches_completion_table_and_cpp_candidate_rule():
    """Raw sets == completion table; candidate rule matches C++ analyzer."""
    rng = random.Random(777)
    for _ in range(10):
        P = _random_safe_parent(rng, 4)
        B = k9.existing_danger(P)
        legal = [v for v in range(k9.V) if v not in set(P) and v not in B]
        assert legal, P
        v = rng.choice(legal)
        assert k9.is_safe(tuple(sorted(P + (v,)))), (P, v)
        ref = _completion_reference(P, v)
        assert k9.raw_response_sets(P, v) == ref, (P, v)
        assert k9fast.raw_response_sets(P, v) == ref, (P, v)
        d = k9.raw_decomposition(P, v)
        assert d["raw_pair"] == d["T"] + d["E"] + d["O"], (P, v, d)
        assert d["union"] == set().union(*ref.values())
        assert d["existing"] == B


def _assert_safe4(parent):
    assert len(parent) == 4 and k9.is_safe(parent), parent


def test_raw_overlap_fixture():
    P, v = O_FIXTURE
    _assert_safe4(P)
    assert k9.is_safe(tuple(sorted(P + (v,))))
    d = k9.raw_decomposition(P, v)
    assert d["O"] > 0, d
    assert d["raw_pair"] == d["T"] + d["E"] + d["O"]
    assert k9fast.raw_decomposition(P, v)["O"] == d["O"]
    f_sets = k9.filtered_response_sets(P, v)
    fS = sum(map(len, f_sets.values()))
    fU = set().union(*f_sets.values()) if f_sets else set()
    assert fS - len(fU) == 0


def test_raw_existing_danger_fixture():
    P, v = E_FIXTURE
    _assert_safe4(P)
    assert k9.is_safe(tuple(sorted(P + (v,))))
    d = k9.raw_decomposition(P, v)
    assert d["E"] > 0, d
    assert d["raw_pair"] == d["T"] + d["E"] + d["O"]
    assert k9fast.raw_decomposition(P, v)["E"] == d["E"]


def test_filtered_has_no_overlap_or_existing_by_construction():
    rng = random.Random(999)
    for _ in range(6):
        P = _random_safe_parent(rng, 4)
        kids = [v for v in sorted(k9.legal_moves(P))
                if k9.is_safe(tuple(sorted(P + (v,))))][:10]
        for v in kids:
            sets = k9.filtered_response_sets(P, v)
            vals = list(sets.values())
            for i in range(len(vals)):
                for j in range(i + 1, len(vals)):
                    assert vals[i] & vals[j] == set(), (P, v)
            B = k9.existing_danger(P)
            for s in vals:
                assert s & B == set(), (P, v)


def test_circle_line_split_adds_up_raw():
    P, v = O_FIXTURE
    d = k9.raw_decomposition(P, v)
    dc = k9.raw_decomposition(P, v, "circle")
    dl = k9.raw_decomposition(P, v, "line")
    assert dc["raw_pair"] + dl["raw_pair"] == d["raw_pair"]

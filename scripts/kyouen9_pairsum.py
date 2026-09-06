"""9x9 pair-sum response-set metrics: raw + filtered modes.

Board indexing: cell id p = y*N + x, x = p % N, y = p // N, N = 9.

Forbidden rule: 4 points are forbidden iff concyclic OR collinear. This
matches the solver's determinant test: for points (x,y), the 4x4 matrix
[x^2+y^2, x, y, 1] has determinant 0 for concyclic-or-collinear quads
(the circle equation degenerates to a line).

Two response-set modes (see docs/9X9_PAIRSUM_METRIC_DEFINITION_CORRECTION.md;
P6 requires them to be explicitly separated so the definition error cannot
recur):

  raw_ab(v)      = {r : {a,b,v,r} is forbidden}                      (no filter)
  filtered_ab(v) = raw_ab(v) ∩ {r : every other quad in P+v+r is safe}

The main-branch C++ analyzer (scripts/analyze-9x9-pair-gap-decomposition.cpp)
uses raw completion sets:

  existing B(P) = ∪ over parent triples of completion(triple)
  raw_pair(v)   = Σ_ab |raw_ab(v)|
  U(v)          = ∪_ab raw_ab(v)
  T(v)          = |U(v) \\ B(P)|   (true one-ply mobility reduction)
  E(v)          = |U(v) ∩ B(P)|    (already-dangerous re-evaluation)
  O(v)          = raw_pair(v) - |U(v)|  (multiplicity)

The old audit-branch names ``pair_sum`` / ``exact_mobility`` / ``overlap``
referred to the FILTERED mode and must not be read as raw quantities.
They are kept as deprecated aliases, documented as filtered-only.
"""

from itertools import combinations

N = 9
V = N * N


def xy(p):
    return (p % N, p // N)


def pid(x, y):
    return y * N + x


def collinear4(a, b, c, d):
    pts = [xy(p) for p in (a, b, c, d)]
    for (x1, y1), (x2, y2), (x3, y3) in combinations(pts, 3):
        if (x2 - x1) * (y3 - y1) != (x3 - x1) * (y2 - y1):
            return False
    return True


def concyclic_noncollinear(a, b, c, d):
    """True iff the 4 points are concyclic but not all collinear."""
    if collinear4(a, b, c, d):
        return False
    pts = [xy(p) for p in (a, b, c, d)]
    for omit in range(4):
        tri = [pts[i] for i in range(4) if i != omit]
        (x1, y1), (x2, y2), (x3, y3) = tri
        area2 = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if area2 == 0:
            continue
        qpt = pts[omit]
        if _on_circumcircle(tri[0], tri[1], tri[2], qpt):
            return True
    return False


def _on_circumcircle(p1, p2, p3, q):
    (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3
    (xq, yq) = q
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    assert d != 0
    s1 = x1 * x1 + y1 * y1
    s2 = x2 * x2 + y2 * y2
    s3 = x3 * x3 + y3 * y3
    ux_num = s1 * (y2 - y3) + s2 * (y3 - y1) + s3 * (y1 - y2)
    uy_num = s1 * (x3 - x2) + s2 * (x1 - x3) + s3 * (x2 - x1)
    # |q - u|^2 == |p1 - u|^2  <=>  d^2*(|q|^2 - 2q.u) == d^2*(|p1|^2 - 2 p1.u)
    # with u = (ux_num/d, uy_num/d):
    lhs = (xq * xq + yq * yq) * d * d - 2 * xq * ux_num * d - 2 * yq * uy_num * d
    rhs = s1 * d * d - 2 * x1 * ux_num * d - 2 * y1 * uy_num * d
    return lhs == rhs


def forbidden(a, b, c, d, _kind=None):
    """Forbidden iff concyclic-or-collinear (matches solver determinant)."""
    if collinear4(a, b, c, d):
        return True
    return concyclic_noncollinear(a, b, c, d)


def forbidden_kind(a, b, c, d):
    if collinear4(a, b, c, d):
        return "line"
    if concyclic_noncollinear(a, b, c, d):
        return "circle"
    return None


def completion_bans(stones):
    """Map: triple (sorted tuple) -> set of points completing a forbidden quad."""
    bans = {}
    for triple in combinations(sorted(stones), 3):
        s = set()
        for v in range(V):
            if v in stones:
                continue
            if forbidden(*triple, v):
                s.add(v)
        bans[triple] = s
    return bans


def legal_moves(stones):
    occ = set(stones)
    banned = set()
    for triple in combinations(sorted(stones), 3):
        for v in range(V):
            if v not in occ and forbidden(*triple, v):
                banned.add(v)
    return set(range(V)) - occ - banned


def is_safe(stones):
    stones = list(stones)
    return not any(forbidden(*q) for q in combinations(stones, 4))


def raw_response_sets(parent, v, kind=None):
    """Raw mode: r qualifies iff {a,b,v,r} is forbidden (of requested kind).

    No other-quad filter. Matches the main-branch C++ completion table:
    raw_ab(v) = completion(triple(a,b,v)) restricted to r ∉ P+v.
    """
    P = list(parent)
    assert v not in P
    Pv = P + [v]
    assert is_safe(Pv), f"P+v not safe: {sorted(Pv)}"
    Pv_set = set(Pv)
    out = {}
    for a, b in combinations(sorted(P), 2):
        s = set()
        for r in range(V):
            if r in Pv_set:
                continue
            k = forbidden_kind(a, b, v, r)
            if k is None:
                continue
            if kind is not None and k != kind:
                continue
            s.add(r)
        out[(a, b)] = s
    return out


def filtered_response_sets(parent, v, kind=None):
    """Filtered mode (old audit definition): raw condition PLUS every other
    quad in P+v+r is safe.

    By construction E'=0 and O'=0 (see metric-definition correction doc).
    Kept for regression purposes only; do not use as the raw pair-sum.
    """
    P = list(parent)
    assert v not in P
    Pv = P + [v]
    assert is_safe(Pv), f"P+v not safe: {sorted(Pv)}"
    out = {}
    for a, b in combinations(sorted(P), 2):
        s = set()
        for r in range(V):
            if r in Pv:
                continue
            k = forbidden_kind(a, b, v, r)
            if k is None:
                continue
            if kind is not None and k != kind:
                continue
            ok = True
            Pv_set = set(Pv)
            for q in combinations(sorted(Pv_set | {r}), 4):
                if set(q) == {a, b, v, r}:
                    continue
                if forbidden(*q):
                    ok = False
                    break
            if ok:
                s.add(r)
        out[(a, b)] = s
    return out


def response_sets(parent, v, kind=None):
    """DEPRECATED alias for filtered_response_sets (old audit definition).

    Kept so existing callers/tests keep running, but new code must call
    raw_response_sets or filtered_response_sets explicitly.
    """
    return filtered_response_sets(parent, v, kind)


def existing_danger(parent):
    """B(P): points already completing a forbidden quad with a parent triple."""
    occ = set(parent)
    out = set()
    for triple in combinations(sorted(parent), 3):
        a, b, c = triple
        for r in range(V):
            if r in occ:
                continue
            if forbidden(a, b, c, r):
                out.add(r)
    return out


def raw_decomposition(parent, v, kind=None):
    """Full raw decomposition matching the main C++ analyzer.

    Returns dict with raw_pair, union_size, T, E, O and per-pair sets.
    T = |U \\ B(P)| is the true one-ply mobility reduction.
    """
    B = existing_danger(parent)
    sets = raw_response_sets(parent, v, kind)
    U = set().union(*sets.values()) if sets else set()
    T = len(U - B)
    E = len(U & B)
    S = sum(len(s) for s in sets.values())
    return {"raw_pair": S, "union_size": len(U), "T": T, "E": E,
            "O": S - len(U), "existing": B, "pair_sets": sets, "union": U}


def raw_pair_sum(parent, v, kind=None):
    return sum(len(s) for s in raw_response_sets(parent, v, kind).values())


def raw_union_size(parent, v, kind=None):
    sets = raw_response_sets(parent, v, kind)
    return len(set().union(*sets.values())) if sets else 0


def pair_sum(parent, v, kind=None):
    """DEPRECATED (filtered-mode) alias. Use raw_pair_sum for raw heuristic."""
    return sum(len(s) for s in filtered_response_sets(parent, v, kind).values())


def exact_mobility(parent, v, kind=None):
    """DEPRECATED (filtered-mode) alias. Use raw_decomposition()['T'] for true mobility."""
    u = set()
    for s in filtered_response_sets(parent, v, kind).values():
        u |= s
    return len(u)


def overlap(parent, v, kind=None):
    """DEPRECATED (filtered-mode) alias. Use raw_decomposition()['O'] for raw overlap."""
    return pair_sum(parent, v, kind) - exact_mobility(parent, v, kind)


# ---- D4 canonicalization (9x9) ----

def _xforms():
    fs = []
    for sx in (1, -1):
        for sy in (1, -1):
            for swap in (False, True):
                def f(p, sx=sx, sy=sy, swap=swap):
                    x, y = xy(p)
                    if swap:
                        x, y = y, x
                    x = x if sx == 1 else (N - 1 - x)
                    y = y if sy == 1 else (N - 1 - y)
                    return pid(x, y)
                fs.append(f)
    return fs


_XFORMS = _xforms()


def canonical(stones):
    return min(tuple(sorted(f(p) for p in stones)) for f in _XFORMS)

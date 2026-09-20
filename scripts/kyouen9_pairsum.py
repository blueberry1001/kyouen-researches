"""9x9 pair-sum (S) vs exact distinct-response mobility (S_mob) + D4 helpers.

Pure-python game logic for the 9x9 Kyoen board, independent of the C++/Lean
solvers. Used for:
  - task 5: verify S == newly-killed safe responses on safe 3-stone parents,
    with pairwise-disjoint dangerous-response sets (circle/line split);
  - task 6: S_pair / S_mob / O = S_pair - S_mob on 4+-stone parents;
  - task 7: enumerate safe 4-stone parents, D4-canonicalize, find discordant
    pairTop-vs-exactTop orbits (exact solving itself stays in C++/Lean).

Board indexing: cell id p = y*N + x, x = p % N, y = p // N, N = 9.

Forbidden rule: 4 points are forbidden iff concyclic OR collinear. This
matches the solver's determinant test: for points (x,y), the 4x4 matrix
[x^2+y^2, x, y, 1] has determinant 0 for concyclic-or-collinear quads
(the circle equation degenerates to a line). We implement direct checks:
  - collinear: area-determinants of all triples == 0;
  - concyclic non-collinear: circumcircle of first 3 non-collinear points
    contains the 4th (exact integer arithmetic).
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


def response_sets(parent, v, kind=None):
    """W_ab(v) per parent pair: responses r such that {a,b,v,r} is forbidden
    (of the requested kind) and P+v+r is otherwise safe, i.e. every other
    quad in P+v+r is safe. Note r is NOT legal-after-P+v in the game sense:
    playing r itself completes the forbidden quad {a,b,v,r} (an immediate
    losing response for the player to move), which is exactly what makes r
    a 'dangerous response' killed by playing v."""
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
            # quads of P+v+r not involving all of {a,b,v}: must be safe,
            # except the target quad {a,b,v,r} itself.
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


def pair_sum(parent, v, kind=None):
    return sum(len(s) for s in response_sets(parent, v, kind).values())


def exact_mobility(parent, v, kind=None):
    u = set()
    for s in response_sets(parent, v, kind).values():
        u |= s
    return len(u)


def overlap(parent, v, kind=None):
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

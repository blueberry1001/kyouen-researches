#!/usr/bin/env python3
"""Residual-game core for batch-03 (B041-B060): R(S), P(S), automorphisms.

Definitions (hypothesis bank):
  R(S) = containment-minimal residuals e\\S for e in Q_n with e\\S subseteq L(S)
  P(S) = graph on L(S) whose edges are the 2-point residuals
  D4   = the 8 geometric symmetries of the square board

Point id = y*n+x. All integer arithmetic. Depends on kyouen_core.Board.
"""
from __future__ import annotations

import sys
from collections import defaultdict, deque
from itertools import combinations, permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kyouen_core import Board, board_square, square_points  # noqa: E402


# ---------------------------------------------------------------------------
# D4
# ---------------------------------------------------------------------------

def d4_perms(n: int) -> list[list[int]]:
    """8 geometric symmetries as permutations of point ids (image list)."""
    def pid(x: int, y: int) -> int:
        return y * n + x

    def gen(fn):
        return [pid(*fn(x, y)) for y in range(n) for x in range(n)]

    ident = gen(lambda x, y: (x, y))
    rot90 = gen(lambda x, y: (n - 1 - y, x))
    rot180 = gen(lambda x, y: (n - 1 - x, n - 1 - y))
    rot270 = gen(lambda x, y: (y, n - 1 - x))
    ref_x = gen(lambda x, y: (n - 1 - x, y))   # mirror vertical axis
    ref_y = gen(lambda x, y: (x, n - 1 - y))   # mirror horizontal axis
    ref_d = gen(lambda x, y: (y, x))           # main diagonal
    ref_a = gen(lambda x, y: (n - 1 - y, n - 1 - x))  # anti-diagonal
    return [ident, rot90, rot180, rot270, ref_x, ref_y, ref_d, ref_a]


def apply_perm_mask(mask: int, perm: list[int]) -> int:
    out = 0
    m = mask
    v = 0
    while m:
        if m & 1:
            out |= 1 << perm[v]
        m >>= 1
        v += 1
    return out


def stabilizer_size(occ: int, perms: list[list[int]]) -> int:
    return sum(1 for p in perms if apply_perm_mask(occ, p) == occ)


# ---------------------------------------------------------------------------
# Residual hypergraph
# ---------------------------------------------------------------------------

def legal_mask(board: Board, occ: int) -> int:
    out = 0
    for v in board.legal_moves(occ):
        out |= 1 << v
    return out


def residual_candidates(board: Board, occ: int) -> list[int]:
    """All e\\S with e in Q_n, e\\S subseteq L(S) (size 2..4). Deduped, unsorted."""
    empties = board.full ^ occ
    L = legal_mask(board, occ)
    seen = set()
    for q in board.quads:
        rest = q & empties
        if rest and (rest & ~L) == 0:
            seen.add(rest)
    return list(seen)


def residual_R(board: Board, occ: int) -> list[int]:
    """Containment-minimal residuals (the true R(S)). Sorted bitmasks."""
    cand = residual_candidates(board, occ)
    cs = set(cand)
    minimal = []
    for r in cand:
        # keep r iff no proper subset is in cs
        ok = True
        sub = (r - 1) & r  # start below r
        # enumerate proper subsets via bitmask walk
        x = r
        while x:
            x = (x - 1) & r
            if x == 0:
                break
            if x in cs:
                ok = False
                break
        if ok:
            minimal.append(r)
    return sorted(minimal)


def P_graph_edges(R: list[int]) -> list[tuple[int, int]]:
    """2-point residuals as undirected edges on board point ids."""
    edges = []
    for r in R:
        if r.bit_count() == 2:
            a, b = [i for i in range(r.bit_length()) if (r >> i) & 1]
            edges.append((a, b) if a < b else (b, a))
    return sorted(set(edges))


def residual_size_counts(R: list[int]) -> tuple[int, int, int]:
    c2 = c3 = c4 = 0
    for r in R:
        k = r.bit_count()
        if k == 2:
            c2 += 1
        elif k == 3:
            c3 += 1
        else:
            c4 += 1
    return c2, c3, c4


def hyper_components(Lmask: int, R: list[int]) -> list[int]:
    """Connected components of the residual hypergraph on L.
    Two legal points are linked when they share a residual.
    Returns list of component bitmasks (subset of Lmask)."""
    if Lmask == 0:
        return []
    adj = defaultdict(set)
    for r in R:
        pts = bits_of(r)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                adj[pts[i]].add(pts[j])
                adj[pts[j]].add(pts[i])
    comps = []
    seen = 0
    for s in bits_of(Lmask):
        if (seen >> s) & 1:
            continue
        q = deque([s])
        seen |= 1 << s
        comp = 1 << s
        while q:
            u = q.popleft()
            for v in adj[u]:
                if not ((seen >> v) & 1):
                    seen |= 1 << v
                    comp |= 1 << v
                    q.append(v)
        comps.append(comp)
    return comps


def grid_components(n: int, Lmask: int) -> list[int]:
    """4-adjacency components of L on the grid."""
    if Lmask == 0:
        return []
    def pid(x, y):
        return y * n + x
    comps = []
    seen = 0
    for s in bits_of(Lmask):
        if (seen >> s) & 1:
            continue
        q = deque([s])
        seen |= 1 << s
        comp = 1 << s
        while q:
            u = q.popleft()
            x, y = u % n, u // n
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < n and 0 <= yy < n:
                    v = pid(xx, yy)
                    if ((Lmask >> v) & 1) and not ((seen >> v) & 1):
                        seen |= 1 << v
                        comp |= 1 << v
                        q.append(v)
        comps.append(comp)
    return comps


def bits_of(mask: int) -> list[int]:
    out = []
    v = 0
    while mask:
        if mask & 1:
            out.append(v)
        mask >>= 1
        v += 1
    return out


# ---------------------------------------------------------------------------
# Hypergraph automorphisms (on an abstract vertex set 0..m-1)
# ---------------------------------------------------------------------------

def _vertex_signatures(m: int, edges: list[frozenset]) -> list[tuple]:
    """Stable refinement signatures for vertices of a hypergraph."""
    deg = [0] * m
    pair_deg = [[0] * m for _ in range(m)]
    edge_size_through = [[] for _ in range(m)]
    for e in edges:
        el = sorted(e)
        for v in e:
            deg[v] += 1
            edge_size_through[v].append(len(e))
        for i in range(len(el)):
            for j in range(i + 1, len(el)):
                pair_deg[el[i]][el[j]] += 1
                pair_deg[el[j]][el[i]] += 1
    sig = []
    for v in range(m):
        s = (
            deg[v],
            tuple(sorted(edge_size_through[v])),
            tuple(sorted(pair_deg[v])),
        )
        sig.append(s)
    # one more refinement round using neighbor colors
    color = {}
    ordered = sorted(set(sig))
    for i, s in enumerate(ordered):
        color[s] = i
    cols = [color[s] for s in sig]
    sig2 = []
    for v in range(m):
        neigh_cols = []
        for e in edges:
            if v in e:
                neigh_cols.append(tuple(sorted(cols[u] for u in e)))
        sig2.append((cols[v], tuple(sorted(neigh_cols))))
    return sig2


def hyper_automorphisms(m: int, edges: list[frozenset], limit: int = 100000) -> list[tuple]:
    """All automorphisms of a hypergraph with vertices 0..m-1.
    Returns list of tuples perm where perm[i] = image of i. Capped at `limit`."""
    if m == 0:
        return [tuple()]
    if not edges:
        # complete symmetric group — too big; return generator flag via size
        # We only need "nontrivial exists" and group size when small.
        # Represent as all perms only if m small; else raise marker.
        if m <= 8:
            return list(permutations(range(m)))
        # sentinel: caller should treat as Sym(m)
        return [tuple(range(m))]  # identity only, caller uses empty-edge rule

    sigs = _vertex_signatures(m, edges)
    # color classes
    by_sig = defaultdict(list)
    for v, s in enumerate(sigs):
        by_sig[s].append(v)
    classes = [by_sig[s] for s in sorted(by_sig.keys())]
    # order vertices: smallest class first
    order = []
    for c in classes:
        order.extend(c)

    edge_set = set(edges)
    # map each edge to its bitmask over 0..m-1 for fast check
    edge_masks = [sum(1 << v for v in e) for e in edges]
    edge_mask_set = set(edge_masks)

    # precompute for each vertex the list of edge-masks containing it
    edges_at = [[] for _ in range(m)]
    for em in edge_masks:
        for v in bits_of(em):
            edges_at[v].append(em)

    assigned = [-1] * m  # assigned[i] = image of i (only for i in domain_done)
    used = [False] * m
    auts: list[tuple] = []

    def rec(pos: int) -> None:
        if len(auts) >= limit:
            return
        if pos == m:
            auts.append(tuple(assigned))
            return
        v = order[pos]
        cands = by_sig[sigs[v]]
        for t in cands:
            if used[t]:
                continue
            # check compatibility: v is provisionally mapped to t
            ok = True
            for em in edges_at[v]:
                mapped = 0
                unmapped = 0
                for u in bits_of(em):
                    if u == v:
                        mapped |= 1 << t
                    elif assigned[u] != -1:
                        mapped |= 1 << assigned[u]
                    else:
                        unmapped += 1
                if unmapped == 0:
                    # complete edge: image must be an edge
                    if mapped not in edge_mask_set:
                        ok = False
                        break
            if not ok:
                continue
            assigned[v] = t
            used[t] = True
            rec(pos + 1)
            assigned[v] = -1
            used[t] = False

    rec(0)
    return auts


def hyper_has_nontrivial_aut(m: int, edges: list[frozenset]) -> bool:
    if m <= 1:
        return False
    if not edges:
        return m >= 2  # Sym(m) nontrivial
    # quick: if a signature class has size >1, possible; still run search but stop early
    auts = hyper_automorphisms(m, edges, limit=2)
    if not auts:
        return False  # should not happen (identity)
    if len(auts) >= 2:
        return True
    return False


def hyper_aut_group_size(m: int, edges: list[frozenset]) -> int | None:
    """Exact |Aut| if small; None if empty edges and m large (Sym(m))."""
    if not edges:
        if m <= 8:
            import math
            return math.factorial(m)
        return None
    auts = hyper_automorphisms(m, edges, limit=200000)
    return len(auts)


def hyper_canonical(m: int, edges: list[frozenset]) -> tuple:
    """Canonical form for iso type: lex-min sorted edge tuple over all
    consistent vertex relabelings induced by the color refinement."""
    if m == 0:
        return tuple()
    if not edges:
        return (m, tuple())  # empty hypergraph on m vertices
    sigs = _vertex_signatures(m, edges)
    by_sig = defaultdict(list)
    for v, s in enumerate(sigs):
        by_sig[s].append(v)
    classes = [by_sig[s] for s in sorted(by_sig.keys())]
    order = []
    for c in classes:
        order.extend(c)

    edge_masks = [sum(1 << v for v in e) for e in edges]
    best = None
    assigned = [-1] * m
    used = [False] * m

    def rec(pos: int, acc_edges: list[int]) -> None:
        nonlocal best
        if pos == m:
            # encode edges under mapping: map old label i -> assigned[i]
            enc = []
            for em in edge_masks:
                bits = bits_of(em)
                image = sum(1 << assigned[i] for i in bits)
                enc.append(image)
            t = tuple(sorted(enc))
            if best is None or t < best:
                best = t
            return
        v = order[pos]
        for t in by_sig[sigs[v]]:
            if used[t]:
                continue
            assigned[v] = t
            used[t] = True
            rec(pos + 1, acc_edges)
            assigned[v] = -1
            used[t] = False

    rec(0, [])
    return (m, best)


def residual_iso(R1: list[int], L1: list[int], R2: list[int], L2: list[int]) -> bool:
    """Abstract isomorphism of residual hypergraphs (vertices = L points)."""
    if len(L1) != len(L2):
        return False
    return hyper_canonical(len(L1), to_abs_edges(R1, L1)) == hyper_canonical(len(L2), to_abs_edges(R2, L2))


def to_abs_edges(R: list[int], L: list[int]) -> list[frozenset]:
    idx = {p: i for i, p in enumerate(L)}
    out = []
    for r in R:
        out.append(frozenset(idx[p] for p in bits_of(r)))
    return out


# ---------------------------------------------------------------------------
# Pairing strategy (fixed involution on board points)
# ---------------------------------------------------------------------------

def pairing_works(board: Board, occ: int, tau: dict[int, int], depth_limit: int = 30) -> bool:
    """Fixed-pair response: tau is a board involution, tau(occ)=occ (as set).
    For every legal p, tau(p) must be a legal reply and the pairing continues
    from occ+p+tau(p) with the same tau. Free on legal points."""
    L = board.legal_moves(occ)
    if not L:
        return True
    if depth_limit <= 0:
        return True  # give up deep recursion as success (depth bounded by |L| anyway)
    Lset = set(L)
    for p in L:
        q = tau.get(p)
        if q is None or q == p or q not in Lset:
            return False
        # occ must be tau-invariant
    # verify tau-invariance of occ
    if apply_perm_mask(occ, [tau.get(i, i) for i in range(board.V)]) != occ:
        # only require tau maps occ to itself; tau given as dict with default fixed
        perm = [tau.get(i, i) for i in range(board.V)]
        if apply_perm_mask(occ, perm) != occ:
            return False
    for p in L:
        q = tau[p]
        if not board.safe_add(occ, p):
            return False
        occ1 = occ | (1 << p)
        if not board.safe_add(occ1, q):
            return False
        if not pairing_works(board, occ1 | (1 << q), tau, depth_limit - 1):
            return False
    return True


def geometric_involutions(n: int) -> list[tuple[str, list[int]]]:
    """The 4 geometric involutions of D4 (identity excluded)."""
    perms = d4_perms(n)
    names = ["id", "rot90", "rot180", "rot270", "ref_x", "ref_y", "ref_d", "ref_a"]
    out = []
    for name, p in zip(names, perms):
        if name == "id":
            continue
        # involution iff p∘p = id
        comp = [p[p[i]] for i in range(n * n)]
        if comp == list(range(n * n)):
            out.append((name, p))
    return out


# ---------------------------------------------------------------------------
# Graph helpers for P(S)
# ---------------------------------------------------------------------------

def p_graph_is_vertex_transitive(m: int, edges: list[tuple[int, int]]) -> bool:
    """Exact check: Aut(P) acts transitively on vertices. Vertices 0..m-1."""
    if m == 0:
        return True
    efs = [frozenset(e) for e in edges]
    # if no edges, Sym(m) is transitive for m>=1
    if not efs:
        return True
    auts = hyper_automorphisms(m, efs, limit=200000)
    if not auts:
        return False
    # orbit of 0
    orbit = set(a[0] for a in auts)
    return len(orbit) == m


def p_graph_aut_count(m: int, edges: list[tuple[int, int]]) -> int | None:
    efs = [frozenset(e) for e in edges]
    return hyper_aut_group_size(m, efs)


# ---------------------------------------------------------------------------
# Convenience: full residual snapshot
# ---------------------------------------------------------------------------

def residual_snapshot(board: Board, occ: int) -> dict:
    L = legal_mask(board, occ)
    R = residual_R(board, occ)
    Llist = bits_of(L)
    return {
        "occ": occ,
        "k": occ.bit_count(),
        "L": L,
        "R": R,
        "P_edges": P_graph_edges(R),
        "counts": residual_size_counts(R),
        "hyper_comps": hyper_components(L, R),
        "grid_comps": grid_components(board.n if hasattr(board, "n") else int(board.V ** 0.5), L),
    }


class BoardN(Board):
    """Board that remembers n."""

    def __init__(self, n: int):
        super().__init__(square_points(n), name=f"{n}x{n}")
        self.n = n

    def safe_add(self, occ: int, v: int) -> bool:
        return self.is_safe(occ | (1 << v))

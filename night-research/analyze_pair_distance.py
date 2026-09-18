#!/usr/bin/env python3
"""Cycle 7: pairwise exchange-distance structure of maximal safe sets.

No new search: reads the fully-enumerated set lists from 99659da
  night-research/maxsafe_n7_K14.bin (16 sets, K=14)
  night-research/maxsafe_n6_K11.bin (464 sets, K=11)
D4 canonical keys are cross-checked against results/maxsafe_exchange_n*.csv.

Writes:
  results/maxsafe_pair_distance_n7.csv
  results/maxsafe_distance_components_n7.csv
  results/maxsafe_orbit_profile_n7.csv
  results/maxsafe_cell_pair_frequency_n7.csv
  results/maxsafe_pair_distance_n6.csv
  results/maxsafe_distance_components_n6.csv
Run: python night-research/analyze_pair_distance.py
"""
import csv
import struct
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NR = ROOT / "night-research"
RES = ROOT / "results"


def load_sets(name, K, V):
    d = (NR / name).read_bytes()
    S = [struct.unpack_from("<Q", d, i)[0] for i in range(0, len(d), 8)]
    for s in S:
        assert s.bit_count() == K and s < (1 << V)
    return S


def d4_perms(n):
    P = []
    for m in range(8):
        fx, fy, tr = bool(m & 1), bool(m & 2), bool(m & 4)
        p = []
        for y in range(n):
            for x in range(n):
                sx = (n - 1 - x) if fx else x
                sy = (n - 1 - y) if fy else y
                nx, ny = (sy, sx) if tr else (sx, sy)
                p.append(ny * n + nx)
        P.append(p)
    return P


def apply_perm(mask, p):
    o = 0
    w = mask
    while w:
        l = w & (-w)
        i = l.bit_length() - 1
        w ^= l
        o |= 1 << p[i]
    return o


def canon(mask, P):
    return min(apply_perm(mask, p) for p in P)


def stones(mask, V):
    return [i for i in range(V) if (mask >> i) & 1]


def comps_of(N, E):
    par = list(range(N))

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for a, b in E:
        ra, rb = f(a), f(b)
        if ra != rb:
            par[ra] = rb
    d = defaultdict(list)
    for i in range(N):
        d[f(i)].append(i)
    return list(d.values())


def cell_key(n, x, y):
    return min({(x, y), (n - 1 - x, y), (x, n - 1 - y), (n - 1 - x, n - 1 - y),
                (y, x), (n - 1 - y, x), (y, n - 1 - x), (n - 1 - y, n - 1 - x)})
def sweep(N, pairs, ths):
    out = []
    for t in ths:
        E = [(i, j) for (i, j, _, _, d, _) in pairs if d <= t]
        C = comps_of(N, E)
        sz = sorted([len(c) for c in C], reverse=True)
        h = ";".join(f"{k}:{v}" for k, v in Counter(sz).most_common())
        out.append((t, len(C), sz[0] if sz else 0, h, len(E)))
    return out


def orbit_index(C):
    o2i = {}
    orb = []
    for c in C:
        o2i.setdefault(c, len(o2i))
        orb.append(o2i[c])
    return orb, o2i


def main():
    S7 = load_sets("maxsafe_n7_K14.bin", 14, 49)
    assert len(S7) == 16
    P7 = d4_perms(7)
    C7 = [canon(s, P7) for s in S7]
    assert len(set(C7)) == 2
    ex = list(csv.DictReader(open(RES / "maxsafe_exchange_n7.csv")))
    assert {f"{c:016x}" for c in set(C7)} == {r["canonical_key_hex"].lower() for r in ex}
    orb7, _ = orbit_index(C7)
    cen = 3 * 7 + 3
    hc = [1 if (s >> cen) & 1 else 0 for s in S7]
    oc = {}
    for i, o in enumerate(orb7):
        oc.setdefault(o, set()).add(hc[i])
    assert all(len(v) == 1 for v in oc.values())
    pairs7 = []
    for i, j in combinations(range(16), 2):
        a = (S7[i] & S7[j]).bit_count()
        d = 14 - a
        assert (S7[i] ^ S7[j]).bit_count() == 2 * d
        pairs7.append((i, j, a, 2 * d, d, 1 if orb7[i] == orb7[j] else 0))
    with open(RES / "maxsafe_pair_distance_n7.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["i", "j", "inter", "symdiff", "d", "same_d4_orbit",
                    "orbit_i", "orbit_j", "center_i", "center_j", "center_split"])
        for (i, j, a, s, d, so) in pairs7:
            w.writerow([i, j, a, s, d, so, orb7[i], orb7[j], hc[i], hc[j],
                        1 if hc[i] != hc[j] else 0])
    sw7 = sweep(16, pairs7, list(range(1, 8)))
    with open(RES / "maxsafe_distance_components_n7.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["threshold_d_le", "num_components", "largest_component",
                    "size_histogram", "num_edges"])
        w.writerows(sw7)
    first_of = {}
    for i, o in enumerate(orb7):
        first_of.setdefault(o, i)
    orb_of_center = {o: hc[first_of[o]] for o in first_of}
    assert sorted(orb_of_center.values()) == [0, 1]
    rA = first_of[[o for o in first_of if orb_of_center[o] == 1][0]]
    rB = first_of[[o for o in first_of if orb_of_center[o] == 0][0]]
    cA = Counter(cell_key(7, v % 7, v // 7) for v in stones(S7[rA], 49))
    cB = Counter(cell_key(7, v % 7, v // 7) for v in stones(S7[rB], 49))
    assert sum(cA.values()) == 14 and sum(cB.values()) == 14
    assert cA[cell_key(7, 2, 2)] == 0 and cB[cell_key(7, 2, 2)] == 0
    with open(RES / "maxsafe_orbit_profile_n7.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rep_label", "rep_id", "repA_repB_ids", "orbit_rep_x",
                    "orbit_rep_y", "orbit_size", "stones_in_orbit"])
        for lab, ri in [("A_center", rA), ("B_nocenter", rB)]:
            cc = cA if ri == rA else cB
            for k in sorted(cc):
                w.writerow([lab, ri, f"{rA:02d}/{rB:02d}", k[0], k[1],
                            len({p[k[1] * 7 + k[0]] for p in P7}), cc[k]])
    pf = Counter()
    for s in S7:
        st = stones(s, 49)
        for a in range(len(st)):
            for b in range(a + 1, len(st)):
                u, v = st[a], st[b]
                pf[(u, v)] += 1

    def pkey(u, v):
        c = []
        for p in P7:
            a, b = p[u], p[v]
            if a > b:
                a, b = b, a
            c.append((a % 7, a // 7, b % 7, b // 7))
        return min(c)

    fold = defaultdict(lambda: {"n": 0, "f": []})
    for (u, v), fr in pf.items():
        k = pkey(u, v)
        fold[k]["n"] += 1
        fold[k]["f"].append(fr)
    never = sorted(set(combinations(range(49), 2)) - set(pf.keys()))
    nf = Counter(pkey(u, v) for (u, v) in never)
    alw = [uv for uv, fr in pf.items() if fr == 16]
    with open(RES / "maxsafe_cell_pair_frequency_n7.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ax", "ay", "bx", "by", "num_cell_pairs_in_class",
                    "min_freq", "max_freq", "mean_freq",
                    "num_never_pairs_in_class", "num_always_pairs_in_class"])
        for k in sorted(set(fold) | set(nf)):
            frs = fold[k]["f"] if k in fold else []
            w.writerow([k[0], k[1], k[2], k[3], fold[k]["n"] if k in fold else 0,
                        min(frs) if frs else "", max(frs) if frs else "",
                        round(sum(frs) / len(frs), 4) if frs else "",
                        nf.get(k, 0),
                        sum(1 for uv in alw if pkey(*uv) == k)])
    S6 = load_sets("maxsafe_n6_K11.bin", 11, 36)
    assert len(S6) == 464
    P6 = d4_perms(6)
    C6 = [canon(s, P6) for s in S6]
    ex6 = list(csv.DictReader(open(RES / "maxsafe_exchange_n6.csv")))
    assert {f"{c:016x}" for c in set(C6)} == {r["canonical_key_hex"].lower() for r in ex6}
    orb6, o2i6 = orbit_index(C6)
    assert len(o2i6) == 58
    pairs6 = []
    for i, j in combinations(range(464), 2):
        a = (S6[i] & S6[j]).bit_count()
        d = 11 - a
        assert (S6[i] ^ S6[j]).bit_count() == 2 * d
        pairs6.append((i, j, a, 2 * d, d, 1 if orb6[i] == orb6[j] else 0))
    with open(RES / "maxsafe_pair_distance_n6.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["i", "j", "inter", "symdiff", "d", "same_d4_orbit",
                    "orbit_i", "orbit_j"])
        w.writerows(pairs6)
    sw6 = sweep(464, pairs6, list(range(1, 8)))
    with open(RES / "maxsafe_distance_components_n6.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["threshold_d_le", "num_components", "largest_component",
                    "size_histogram", "num_edges"])
        w.writerows(sw6)
    F = lambda h: "{" + ", ".join(f"{k}:{h[k]}" for k in sorted(h)) + "}"
    h7 = Counter(d for (*_, d, _) in pairs7)
    hx = Counter(d for (*_, d, so) in pairs7 if so == 0)
    hw = Counter(d for (*_, d, so) in pairs7 if so == 1)
    h6 = Counter(d for (*_, d, _) in pairs6)
    h6x = Counter(d for (*_, d, so) in pairs6 if so == 0)
    print(f"n7 dstar={min(d for (*_, d, so) in pairs7 if so==0)} "
          f"dstar_center={min(d for (i,j,_,_,d,_) in pairs7 if hc[i]!=hc[j])} "
          f"all={F(h7)} cross={F(hx)} within={F(hw)}")
    for r in sw7:
        print("N7SW", r)
    print(f"REPS rA={rA} corners={cA[cell_key(7,0,0)]} "
          f"rB={rB} corners={cB[cell_key(7,0,0)]}")
    print("PROFA " + str(dict(sorted(cA.items()))))
    print("PROFB " + str(dict(sorted(cB.items()))))
    print(f"COOCCUR classes={len(fold)} never={len(never)}/1176 always16={len(alw)}")
    print(f"n6 dstar={min(d for (*_, d, so) in pairs6 if so==0)} all={F(h6)} cross={F(h6x)}")
    for r in sw6:
        print("N6SW", r)
    print("WROTE 6 CSVS OK")


if __name__ == "__main__":
    main()


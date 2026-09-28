#!/usr/bin/env python3
"""Decode a few witness masks from round4_b371.bin into board coordinates and
re-derive their features, so the md can quote concrete configurations."""
import struct, sys, json, itertools

REPO = "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification"
N = 8

def det4(pts):
    a = pts
    m = [[x*x+y*y, x, y, 1] for (x, y) in a]
    tot = 0
    for i in range(4):
        mm = [[m[r][c] for c in range(1, 4)] for r in range(4) if r != i]
        d3 = (mm[0][0]*(mm[1][1]*mm[2][2]-mm[1][2]*mm[2][1])
              - mm[0][1]*(mm[1][0]*mm[2][2]-mm[1][2]*mm[2][0])
              + mm[0][2]*(mm[1][0]*mm[2][1]-mm[1][1]*mm[2][0]))
        tot += (1 if i % 2 == 0 else -1) * m[i][0] * d3
    return tot

def load(path):
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        return list(struct.unpack("<%dQ" % n, f.read(8 * n)))

def analyse(mask, verbose=False):
    ch = [i for i in range(64) if (mask >> i) & 1]
    pts = [(i % N, i // N) for i in ch]
    assert len(ch) == 8, len(ch)
    # safety
    for q in itertools.combinations(range(8), 4):
        if det4([pts[i] for i in q]) == 0:
            return None  # unsafe
    # maximality: every other point must complete a concyclic/collinear quad
    for p in range(64):
        if (mask >> p) & 1:
            continue
        blocked = False
        for q in itertools.combinations(range(8), 3):
            if det4([pts[i] for i in q] + [(p % N, p // N)]) == 0:
                blocked = True
                break
        if not blocked:
            return None
    ncol = 0
    dirs = set()
    for q in itertools.combinations(range(8), 3):
        a, b, c = [pts[i] for i in q]
        if (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]) == 0:
            ncol += 1
            dx, dy = b[0]-a[0], b[1]-a[1]
            g = 0
            for t in (abs(dx), abs(dy)):
                pass
            import math
            g = math.gcd(abs(dx), abs(dy)) or 1
            ux, uy = dx//g, dy//g
            if ux < 0 or (ux == 0 and uy < 0):
                ux, uy = -ux, -uy
            dirs.add((ux, uy))
    xs = [x for x, y in pts]; ys = [y for x, y in pts]
    sides = sum([min(xs) == 0, max(xs) == N-1, min(ys) == 0, max(ys) == N-1])
    corners = sum(1 for (x, y) in pts if x in (0, N-1) and y in (0, N-1))
    # one-stone deletion
    delmin = 10**9
    for i in range(8):
        rest = [pts[j] for j in range(8) if j != i]
        cnt = 0
        for p in range(64):
            if p in ch:
                continue
            if not any(det4([rest[j] for j in q] + [(p % N, p // N)]) == 0
                       for q in itertools.combinations(range(7), 3)):
                cnt += 1
        delmin = min(delmin, cnt)
    # b values
    b = {}
    for p in range(64):
        if (mask >> p) & 1:
            continue
        b[p] = sum(1 for q in itertools.combinations(range(8), 3)
                   if det4([pts[i] for i in q] + [(p % N, p // N)]) == 0)
    se = sum(1 for p, v in b.items() if v == 1 and (p % N in (0, N-1) or p // N in (0, N-1)))
    si = sum(1 for p, v in b.items() if v == 1 and not (p % N in (0, N-1) or p // N in (0, N-1)))
    return dict(ch=ch, pts=pts, ncol=ncol, ndir=len(dirs), dirs=sorted(dirs),
                sides=sides, corners=corners, delmin=delmin, sumb=sum(b.values()),
                se=se, si=si, minb=min(b.values()), maxb=max(b.values()))

if __name__ == "__main__":
    masks = load(REPO + "/round4_b371.bin")
    print("total maximal 8-sets in file:", len(masks))
    W = (1 << 0) | (1 << 1) | (1 << 6) | (1 << 20) | (1 << 24) | (1 << 32) | (1 << 34) | (1 << 60)
    print("witness W present in enumeration:", W in masks)
    r = analyse(W)
    print("W re-derived:", {k: v for k, v in r.items() if k != "pts"})
    # one witness per interesting class
    js = json.load(open(REPO + "/round4_b371.json"))
    for name, key in [("B372 (1 direction)", "witness_masks"),
                      ("B373 (<=1 side)", "witness_masks"),
                      ("B374 (no corner)", "witness_masks")]:
        pass
    for hid, tgt in [("b372", 0), ("b373", 0), ("b374", 0)]:
        for m in js[hid]["witness_masks"][:2]:
            r = analyse(m)
            if r:
                print(hid, {k: v for k, v in r.items() if k != "pts"}, "ch=", r["ch"])
    # check statistics over whole file
    n_nocol = n_dir1 = n_side1 = n_corner0 = n_del1 = 0
    ncolh, ndirh, sideh, cornh, delh = {}, {}, {}, {}, {}
    for m in masks:
        r = analyse(m)
        assert r, "file contains a non-maximal/unsafe set"
        n_nocol += r["ncol"] == 0
        n_dir1 += r["ndir"] <= 1
        n_side1 += r["sides"] <= 1
        n_corner0 += r["corners"] == 0
        n_del1 += r["delmin"] == 1
        ncolh[r["ncol"]] = ncolh.get(r["ncol"], 0) + 1
        ndirh[r["ndir"]] = ndirh.get(r["ndir"], 0) + 1
        sideh[r["sides"]] = sideh.get(r["sides"], 0) + 1
        cornh[r["corners"]] = cornh.get(r["corners"], 0) + 1
        delh[r["delmin"]] = delh.get(r["delmin"], 0) + 1
    print("independent python recount over the whole file:")
    print("  no-collinear:", n_nocol, " dir<=1:", n_dir1, " sides<=1:", n_side1,
          " no-corner:", n_corner0, " delmin==1:", n_del1)
    print("  ncol:", dict(sorted(ncolh.items())))
    print("  ndir:", dict(sorted(ndirh.items())))
    print("  sides:", dict(sorted(sideh.items())))
    print("  corners:", dict(sorted(cornh.items())))
    print("  delmin:", dict(sorted(delh.items())))

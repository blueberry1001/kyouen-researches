// Shared kyouen engine for the C++ (WSL) verification solvers.
//
// Board is a set of lattice points; a forbidden 4-set is one whose integer
// determinant det[x^2+y^2, x, y, 1] is 0 (concyclic or collinear). A safe set
// is a bitmask containing no forbidden 4-subset.
//
// Occupancy is one uint64 per board, so boards up to 64 points fit. Point
// index is y*n + x, matching kyouen_core.py.
#pragma once
#include <cstdint>
#include <vector>
#include <array>

namespace kc {

using u64 = uint64_t;

struct Board {
    int n = 0;          // side length for square boards
    int V = 0;          // number of points
    u64 full = 0;       // (1<<V) - 1
    // For every point p, the set of forbidden quads that contain p, encoded
    // as a mask of the *other three* points. Occupied if (occ & t) == t.
    std::vector<std::vector<u64>> triples_by_pt;
    std::vector<u64> quads;          // each forbidden quad as a 4-point mask
    std::vector<int> pt_x, pt_y;     // coordinates, for reporting
};

// Exact integer determinant of the 4x4 matrix rows, 0 iff concyclic/collinear.
inline long long det4(const long long r[4][4]) {
    long long total = 0;
    for (int i = 0; i < 4; ++i) {
        long long mm[3][3];
        int ri = 0;
        for (int r2 = 0; r2 < 4; ++r2) {
            if (r2 == i) continue;
            int ci = 0;
            for (int c2 = 1; c2 < 4; ++c2) mm[ri][ci++] = r[r2][c2];
            ++ri;
        }
        long long d3 = mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
                     - mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0])
                     + mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0]);
        total += (i % 2 == 0 ? 1 : -1) * r[i][0] * d3;
    }
    return total;
}

// Build geometry for the n x n square. n must satisfy n*n <= 64.
inline void build_square(Board& b, int n) {
    b.n = n;
    b.V = n * n;
    b.full = (b.V >= 64) ? ~u64(0) : ((u64(1) << b.V) - 1);
    b.triples_by_pt.assign(b.V, {});
    b.quads.clear();
    b.pt_x.assign(b.V, 0);
    b.pt_y.assign(b.V, 0);

    std::vector<std::array<long long, 4>> rows(b.V);
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int i = y * n + x;
            b.pt_x[i] = x;
            b.pt_y[i] = y;
            rows[i] = {(long long)x * x + (long long)y * y, x, y, 1};
        }

    for (int a = 0; a < b.V - 3; ++a)
    for (int c1 = a + 1; c1 < b.V - 2; ++c1)
    for (int c2 = c1 + 1; c2 < b.V - 1; ++c2)
    for (int d = c2 + 1; d < b.V; ++d) {
        int ids[4] = {a, c1, c2, d};
        long long m[4][4];
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j) m[i][j] = rows[ids[i]][j];
        if (det4(m) != 0) continue;
        u64 q = 0;
        for (int i = 0; i < 4; ++i) q |= u64(1) << ids[i];
        b.quads.push_back(q);
        for (int t = 0; t < 4; ++t) {
            u64 o = 0;
            for (int s = 0; s < 4; ++s)
                if (s != t) o |= u64(1) << ids[s];
            b.triples_by_pt[ids[t]].push_back(o);
        }
    }
}

// Legal moves from occ, as a point mask.
inline u64 legal_mask(const Board& b, u64 occ) {
    u64 out = 0;
    u64 empty = b.full & ~occ;
    while (empty) {
        int p = __builtin_ctzll(empty);
        empty &= empty - 1;
        bool ok = true;
        for (u64 t : b.triples_by_pt[p]) {
            if ((occ & t) == t) { ok = false; break; }
        }
        if (ok) out |= u64(1) << p;
    }
    return out;
}

inline bool can_add(const Board& b, u64 occ, int p) {
    if (occ & (u64(1) << p)) return false;
    for (u64 t : b.triples_by_pt[p]) {
        u64 q = t | (u64(1) << p);
        if ((occ & t) == t) return false;
    }
    return true;
}

inline bool is_maximal(const Board& b, u64 occ) { return legal_mask(b, occ) == 0; }

}  // namespace kc

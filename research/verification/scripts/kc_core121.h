// Shared kyouen engine, 2-word (128-bit) occupancy.
//
// This is the n>=9 sibling of kc_core.h. n=8 already fills a single uint64;
// n=9 (81 points), n=10 (100) and n=11 (121) do not. `1ULL << v` for v>=64 is
// undefined behaviour, so a 1-word board silently corrupts the top rows of
// the grid. Everything below therefore keeps the occupancy in {lo, hi}:
//
//   lo  holds points 0..63        (i.e. cell id p = y*n + x,  p < 64)
//   hi  holds points 64..120      (bit p-64)
//
// Point id is y*n + x, matching kyouen_core.py and kc_core.h.
//
// A forbidden 4-set is a set of 4 lattice points whose integer determinant
// det[x^2+y^2, x, y, 1] is 0 (concyclic or collinear). A safe set is a point
// set containing no forbidden 4-subset.
#pragma once
#include <algorithm>
#include <cstdint>
#include <vector>
#include <array>
#include <string>
#include <utility>

namespace kc {

using u64 = uint64_t;

// ---------------------------------------------------------------- occupancy
// Two-word point set. Supports up to 128 points; kc_core121.h is used with
// V <= 120, so no shift ever reaches 64 in the `hi` word and every shift is
// defined. (A 1-word board with n=11 would compute `1ULL << 64..120`.)
struct Bits {
    u64 lo = 0;   // points 0..63
    u64 hi = 0;   // points 64..120

    bool test(int p) const { return p < 64 ? ((lo >> p) & 1) : ((hi >> (p - 64)) & 1); }
    void set(int p) { if (p < 64) lo |= u64(1) << p; else hi |= u64(1) << (p - 64); }
    void clear(int p) { if (p < 64) lo &= ~(u64(1) << p); else hi &= ~(u64(1) << (p - 64)); }

    int count() const { return __builtin_popcountll(lo) + __builtin_popcountll(hi); }

    // Order: unsigned 128-bit integer with `hi` as the high word. This makes
    // the level lists a plain increasing sequence of 128-bit integers, which is
    // exactly what the v-max partition needs in order to come out sorted.
    bool operator<(const Bits& b) const { return hi != b.hi ? hi < b.hi : lo < b.lo; }
    bool operator==(const Bits& b) const { return lo == b.lo && hi == b.hi; }
    bool operator!=(const Bits& b) const { return !(*this == b); }
};

// ------------------------------------------------------------------- board
struct Board {
    int n = 0;          // side length for square boards
    int V = 0;          // number of points, n*n
    // For every point p, the forbidden quads that contain p, encoded as the
    // *other three* points. Occupied iff (occ & t) == t, i.e. t is a subset.
    std::vector<std::vector<Bits>> triples_by_pt;
    std::vector<Bits> quads;         // each forbidden quad as a 4-point set
    std::vector<int> pt_x, pt_y;     // coordinates, for reporting
    // Points 64..V-1 as a bit mask, so the outer loop over empty cells stays a
    // 64-bit ctz loop. lo_marks points >= 64.
    u64 hi_marks = 0;
    u64 full_lo = 0;    // points 0..min(V,64)-1
};

// True iff every point of `a` is occupied in `b`. (t is a "other three" mask.)
inline bool is_subset(const Bits& a, const Bits& b) {
    if (a.lo & ~b.lo) return false;
    if (a.hi & ~b.hi) return false;
    return true;
}

inline int cmp_bits(const Bits& a, const Bits& b) {
    if (a.hi != b.hi) return a.hi < b.hi ? -1 : 1;
    if (a.lo != b.lo) return a.lo < b.lo ? -1 : 1;
    return 0;
}

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

// Build geometry for the n x n square. n must satisfy n*n <= 128.
inline void build_square(Board& b, int n) {
    b.n = n;
    b.V = n * n;
    b.triples_by_pt.assign((size_t)b.V, {});
    b.quads.clear();
    b.pt_x.assign((size_t)b.V, 0);
    b.pt_y.assign((size_t)b.V, 0);
    b.hi_marks = (b.V > 64) ? ((b.V >= 128) ? ~u64(0) : ((u64(1) << (b.V - 64)) - 1)) : 0;
    b.full_lo = (b.V >= 64) ? ~u64(0) : ((u64(1) << b.V) - 1);

    std::vector<std::array<long long, 4>> rows((size_t)b.V);
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int i = y * n + x;
            b.pt_x[i] = x;
            b.pt_y[i] = y;
            rows[i] = {(long long)x * x + (long long)y * y, x, y, 1};
        }

    long long m[4][4];
    for (int a = 0; a < b.V - 3; ++a)
    for (int c1 = a + 1; c1 < b.V - 2; ++c1)
    for (int c2 = c1 + 1; c2 < b.V - 1; ++c2)
    for (int d = c2 + 1; d < b.V; ++d) {
        int ids[4] = {a, c1, c2, d};
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j) m[i][j] = rows[ids[i]][j];
        if (det4(m) != 0) continue;
        Bits q;
        for (int i = 0; i < 4; ++i) q.set(ids[i]);
        b.quads.push_back(q);
        for (int t = 0; t < 4; ++t) {
            Bits o;
            for (int s = 0; s < 4; ++s)
                if (s != t) o.set(ids[s]);
            b.triples_by_pt[ids[t]].push_back(o);
        }
    }
}

// Legal moves from occ, as a point set.
inline Bits legal_mask(const Board& b, const Bits& occ) {
    Bits out;
    u64 e = b.full_lo & ~occ.lo;
    while (e) {
        int p = __builtin_ctzll(e);
        e &= e - 1;
        bool ok = true;
        for (const Bits& t : b.triples_by_pt[(size_t)p])
            if (is_subset(t, occ)) { ok = false; break; }
        if (ok) out.lo |= u64(1) << p;
    }
    u64 eh = b.hi_marks & ~occ.hi;
    while (eh) {
        int p = 64 + __builtin_ctzll(eh);
        eh &= eh - 1;
        bool ok = true;
        for (const Bits& t : b.triples_by_pt[(size_t)p])
            if (is_subset(t, occ)) { ok = false; break; }
        if (ok) out.hi |= u64(1) << (p - 64);
    }
    return out;
}

inline bool can_add(const Board& b, const Bits& occ, int p) {
    if (occ.test(p)) return false;
    for (const Bits& t : b.triples_by_pt[(size_t)p])
        if (is_subset(t, occ)) return false;
    return true;
}

inline bool is_maximal(const Board& b, const Bits& occ) { return legal_mask(b, occ).count() == 0; }

// --------------------------------------------------------------- spill I/O
// Format: u64 count, then count records of {u64 lo, u64 hi} = 16 bytes/state.
// (The 1-word probe wrote raw u64 with no header; the header makes a truncated
// or stale file detectable instead of silently short.)
struct Spill {
    std::string dir;
    bool on = false;
    explicit Spill(std::string d) : dir(std::move(d)) { on = !dir.empty(); }
    std::string path(int k) const { return dir + "/level_" + std::to_string(k) + ".occ"; }

    void write(int k, const std::vector<Bits>& v) const {
        if (!on) return;
        std::string p = path(k);
        FILE* f = fopen(p.c_str(), "wb");
        if (!f) { fprintf(stderr, "spill open failed %s\n", p.c_str()); exit(9); }
        u64 cnt = (u64)v.size();
        std::vector<u64> buf;
        buf.reserve(2 * v.size());
        for (const Bits& b : v) { buf.push_back(b.lo); buf.push_back(b.hi); }
        bool ok = (fwrite(&cnt, 8, 1, f) == 1) &&
                  (buf.empty() || fwrite(buf.data(), 8, buf.size(), f) == buf.size());
        fclose(f);
        if (!ok) { fprintf(stderr, "spill write short %s\n", p.c_str()); exit(9); }
    }

    std::vector<Bits> read(int k) const {
        std::vector<Bits> v;
        if (!on) return v;
        std::string p = path(k);
        FILE* f = fopen(p.c_str(), "rb");
        if (!f) return v;
        u64 cnt = 0;
        if (fread(&cnt, 8, 1, f) != 1) { fclose(f); fprintf(stderr, "spill read no header %s\n", p.c_str()); exit(9); }
        v.resize((size_t)cnt);
        std::vector<u64> buf(2 * (size_t)cnt);
        size_t got = cnt ? fread(buf.data(), 8, buf.size(), f) : 0;
        fclose(f);
        if (got != buf.size()) { fprintf(stderr, "spill read short %s\n", p.c_str()); exit(9); }
        for (size_t i = 0; i < (size_t)cnt; ++i) { v[i].lo = buf[2 * i]; v[i].hi = buf[2 * i + 1]; }
        return v;
    }
};

// True iff v is strictly increasing, i.e. sorted and duplicate free.
inline bool is_sorted_unique(const std::vector<Bits>& v) {
    for (size_t i = 1; i < v.size(); ++i)
        if (!(v[i - 1] < v[i])) return false;
    return true;
}

}  // namespace kc

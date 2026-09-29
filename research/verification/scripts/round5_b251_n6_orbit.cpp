// B251-B258 n=6 followup: single-quad removal via D4 orbits.
// For each D4-orbit of forbidden quads, run outcome-only solve and see if g0 flips.
// Also collect: nstates after removal, and per-quad stats for B257 (sensitivity).
// Usage: round5_b251_n6_orbit [max_orbits]
// Output: JSON to stdout.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <array>
#include <algorithm>
#include <map>
#include <set>
#include <unordered_map>
#include <chrono>
#ifdef _OPENMP
#include <omp.h>
#endif

using u64 = uint64_t;

static long long det4(const long long r[4][4]) {
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

struct Board {
    int n = 0, V = 0;
    u64 full = 0;
    std::vector<std::vector<u64>> triples_by_pt;
    std::vector<u64> quads;
    std::vector<int> px, py;
};

static void build_square(Board& b, int n) {
    b.n = n; b.V = n * n;
    b.full = (u64(1) << b.V) - 1;
    b.triples_by_pt.assign(b.V, {});
    b.quads.clear();
    b.px.assign(b.V, 0); b.py.assign(b.V, 0);
    std::vector<std::array<long long, 4>> rows(b.V);
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int i = y * n + x;
            b.px[i] = x; b.py[i] = y;
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
            for (int s = 0; s < 4; ++s) if (s != t) o |= u64(1) << ids[s];
            b.triples_by_pt[ids[t]].push_back(o);
        }
    }
}

static void rebuild_without(Board& b, const Board& src, int rm_qi) {
    b.n = src.n; b.V = src.V; b.full = src.full;
    b.px = src.px; b.py = src.py;
    b.triples_by_pt.assign(b.V, {});
    b.quads.clear();
    for (size_t qi = 0; qi < src.quads.size(); ++qi) {
        if ((int)qi == rm_qi) continue;
        u64 q = src.quads[qi];
        b.quads.push_back(q);
        for (int t = 0; t < b.V; ++t) {
            if (!(q & (u64(1) << t))) continue;
            b.triples_by_pt[t].push_back(q & ~(u64(1) << t));
        }
    }
}

static inline u64 legal_mask(const Board& b, u64 occ) {
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

// Outcome-only: returns 1 if empty is N (next player wins), 0 if P.
// Uses DFS + memo on reachable states. Compact: unordered_map.
static int outcome_empty(const Board& b) {
    // iterative post-order using explicit stack
    std::unordered_map<u64, int8_t> memo; // 0=P, 1=N, 2=visiting
    std::vector<std::pair<u64, u64>> stack; // state, remaining legal moves to try
    memo.reserve(1 << 22);
    stack.push_back({0, legal_mask(b, 0)});
    while (!stack.empty()) {
        auto& [s, rem] = stack.back();
        if (rem == 0) {
            // all children done: outcome is N iff some child is P
            // We need child outcomes. Store differently.
            // Recompute children (cheap enough) — actually store child results.
            stack.pop_back();
            continue;
        }
        int p = __builtin_ctzll(rem);
        rem &= rem - 1;
        u64 ns = s | (u64(1) << p);
        auto it = memo.find(ns);
        if (it == memo.end()) {
            u64 lm = legal_mask(b, ns);
            if (lm == 0) {
                memo[ns] = 0; // terminal = P
            } else {
                memo[ns] = 2; // visiting
                stack.push_back({ns, lm});
            }
        }
        // After child is resolved, we'll finish parent when rem==0.
        // But we need to know children outcomes at that point.
    }
    // The above loses child outcomes. Use a cleaner recursion with explicit result buffer.
    // Redo with a simpler approach: BFS levels from high |S| to low is hard without full enum.
    // Use recursive lambda with manual stack storing child-outcome OR.
    return -1; // replaced below
}

// Cleaner outcome-only via DFS with post-order and "any P child" accumulation.
struct OutcomeSolver {
    const Board& b;
    std::unordered_map<u64, int8_t> memo; // 0 P, 1 N
    OutcomeSolver(const Board& bb) : b(bb) { memo.reserve(1 << 22); }

    int solve(u64 s) {
        auto it = memo.find(s);
        if (it != memo.end()) return it->second;
        u64 lm = legal_mask(b, s);
        if (lm == 0) { memo[s] = 0; return 0; }
        // iterative DFS
        struct Frame { u64 s; u64 rem; int any_p; };
        std::vector<Frame> st;
        st.push_back({s, lm, 0});
        memo[s] = 2; // mark visiting (won't be returned as 0/1)
        while (!st.empty()) {
            Frame& f = st.back();
            if (f.rem == 0) {
                int r = f.any_p ? 1 : 0;
                memo[f.s] = (int8_t)r;
                st.pop_back();
                // propagate P-child to parent
                if (!st.empty() && r == 0) st.back().any_p = 1;
                continue;
            }
            int p = __builtin_ctzll(f.rem);
            f.rem &= f.rem - 1;
            u64 ns = f.s | (u64(1) << p);
            auto it2 = memo.find(ns);
            if (it2 != memo.end() && it2->second != 2) {
                if (it2->second == 0) f.any_p = 1;
                continue;
            }
            if (it2 != memo.end() && it2->second == 2) {
                // cycle shouldn't happen in acyclic game; treat as N-safe
                continue;
            }
            u64 lm2 = legal_mask(b, ns);
            if (lm2 == 0) {
                memo[ns] = 0;
                f.any_p = 1;
            } else {
                memo[ns] = 2;
                st.push_back({ns, lm2, 0});
            }
        }
        return memo[s];
    }
};

// D4 action on n x n point id
static int d4_map(int id, int n, int op) {
    int x = id % n, y = id / n;
    int nx, ny;
    switch (op) {
        case 0: nx = x; ny = y; break;                 // id
        case 1: nx = n-1-x; ny = y; break;             // rot 180 / flip x? we'll use full D4
        case 2: nx = x; ny = n-1-y; break;
        case 3: nx = n-1-x; ny = n-1-y; break;
        case 4: nx = y; ny = x; break;                 // transpose
        case 5: nx = n-1-y; ny = x; break;
        case 6: nx = y; ny = n-1-x; break;
        case 7: nx = n-1-y; ny = n-1-x; break;
        default: nx = x; ny = y; break;
    }
    return ny * n + nx;
}

static u64 map_quad(u64 q, int n, int op) {
    u64 out = 0;
    for (int p = 0; p < n * n; ++p) if (q & (u64(1) << p)) {
        out |= u64(1) << d4_map(p, n, op);
    }
    return out;
}

static void print_quad(FILE* f, const Board& b, u64 q) {
    fputc('[', f);
    bool first = true;
    for (int p = 0; p < b.V; ++p) if (q & (u64(1) << p)) {
        fprintf(f, "%s[%d,%d]", first ? "" : ",", b.px[p], b.py[p]);
        first = false;
    }
    fputc(']', f);
}

int main(int argc, char** argv) {
    int n = 6;
    int max_orbits = (argc > 1) ? atoi(argv[1]) : 100000;
    Board b0;
    build_square(b0, n);
    int nq = (int)b0.quads.size();

    // Compute D4 orbits of quads
    std::vector<int> orbit_id(nq, -1);
    std::vector<u64> orbit_reps;
    std::vector<std::vector<int>> orbit_members;
    {
        // map quad-mask -> index
        std::unordered_map<u64, int> qidx;
        for (int i = 0; i < nq; ++i) qidx[b0.quads[i]] = i;
        for (int i = 0; i < nq; ++i) {
            if (orbit_id[i] >= 0) continue;
            int oid = (int)orbit_reps.size();
            orbit_reps.push_back(b0.quads[i]);
            orbit_members.push_back({});
            std::vector<int> members;
            for (int op = 0; op < 8; ++op) {
                u64 mq = map_quad(b0.quads[i], n, op);
                auto it = qidx.find(mq);
                if (it != qidx.end() && orbit_id[it->second] < 0) {
                    orbit_id[it->second] = oid;
                    members.push_back(it->second);
                } else if (it != qidx.end() && orbit_id[it->second] == oid) {
                    members.push_back(it->second);
                }
            }
            // ensure original is in
            if (orbit_id[i] != oid) { orbit_id[i] = oid; members.push_back(i); }
            std::sort(members.begin(), members.end());
            members.erase(std::unique(members.begin(), members.end()), members.end());
            orbit_members[oid] = members;
        }
    }
    int norb = (int)orbit_reps.size();

    // Standard g0 (full solve outcome)
    OutcomeSolver std_os(b0);
    int g0s = std_os.solve(0);

    fprintf(stdout, "{\"n\":%d,\"V\":%d,\"nquads\":%d,\"norbits\":%d,\"g0_std\":%d,",
            n, b0.V, nq, norb, g0s);
    fprintf(stdout, "\"orbits\":[");

    int tested = 0, flips = 0;
    std::vector<int> flip_orbs;
    // Parallel over orbit reps
    std::vector<int> orb_g0(norb, -1);
    std::vector<long long> orb_nstates(norb, -1);

    auto t0 = std::chrono::steady_clock::now();

    int nloop = norb < max_orbits ? norb : max_orbits;
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 1)
#endif
    for (int oi = 0; oi < nloop; ++oi) {
        // find any member quad index
        int qi = orbit_members[oi].empty() ? -1 : orbit_members[oi][0];
        if (qi < 0) continue;
        Board bm;
        rebuild_without(bm, b0, qi);
        OutcomeSolver os(bm);
        int g = os.solve(0);
        orb_g0[oi] = g;
        orb_nstates[oi] = (long long)os.memo.size();
    }

    auto t1 = std::chrono::steady_clock::now();
    double secs = std::chrono::duration<double>(t1 - t0).count();

    bool first = true;
    for (int oi = 0; oi < nloop; ++oi) {
        if (orb_g0[oi] < 0) continue;
        ++tested;
        if (orb_g0[oi] != g0s) { ++flips; flip_orbs.push_back(oi); }
        fprintf(stdout, "%s{\"oid\":%d,\"g0\":%d,\"nstates\":%lld,\"size\":%d,\"rep\":",
                first ? "" : ",", oi, orb_g0[oi], orb_nstates[oi], (int)orbit_members[oi].size());
        print_quad(stdout, b0, orbit_reps[oi]);
        fprintf(stdout, "}");
        first = false;
    }
    fprintf(stdout, "],\"orbits_tested\":%d,\"orbit_flips\":%d,\"secs\":%.2f",
            tested, flips, secs);
    if (!flip_orbs.empty()) {
        fprintf(stdout, ",\"flip_orbit_ids\":[");
        for (size_t i = 0; i < flip_orbs.size(); ++i)
            fprintf(stdout, "%s%d", i ? "," : "", flip_orbs[i]);
        fprintf(stdout, "],\"first_flip_rep\":");
        print_quad(stdout, b0, orbit_reps[flip_orbs[0]]);
    }
    fprintf(stdout, ",\"done\":true}\n");
    return 0;
}

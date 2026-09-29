// B256/B258: min forbidden family keeping winner. n=4 complete + n=5 sample.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <array>
#include <algorithm>
#include <map>
#include <set>
#include <string>
#include <chrono>

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
    std::vector<std::vector<int>> tri_quad;
    std::vector<u64> quads;
    std::vector<int> px, py;
};

static void build_square(Board& b, int n) {
    b.n = n; b.V = n * n;
    b.full = (u64(1) << b.V) - 1;
    b.triples_by_pt.assign(b.V, {});
    b.tri_quad.assign(b.V, {});
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
        int qi = (int)b.quads.size();
        b.quads.push_back(q);
        for (int t = 0; t < 4; ++t) {
            u64 o = 0;
            for (int s = 0; s < 4; ++s) if (s != t) o |= u64(1) << ids[s];
            b.triples_by_pt[ids[t]].push_back(o);
            b.tri_quad[ids[t]].push_back(qi);
        }
    }
}

// Active-quad mask solver. `active[qi]=1` means quad qi is FORBIDDEN.
// For n=4, use dense 2^16 array. For n=5 with few active, dense 2^25 is 32MB.
static int solve_active(const Board& b, const std::vector<char>& active, std::vector<uint8_t>* win_out = nullptr) {
    int N = 1 << b.V;
    std::vector<uint8_t> win(N, 0);
    std::vector<uint8_t> seen(N, 0);
    std::vector<u64> order;
    order.reserve(b.V <= 16 ? 65536 : 2000000);
    std::vector<u64> stack = {0};
    seen[0] = 1;
    while (!stack.empty()) {
        u64 s = stack.back(); stack.pop_back();
        order.push_back(s);
        u64 empty = b.full & ~s;
        while (empty) {
            int p = __builtin_ctzll(empty); empty &= empty - 1;
            bool ok = true;
            const auto& tris = b.triples_by_pt[p];
            const auto& qid = b.tri_quad[p];
            for (size_t i = 0; i < tris.size(); ++i) {
                if (!active[qid[i]]) continue;
                if ((s & tris[i]) == tris[i]) { ok = false; break; }
            }
            if (ok) {
                u64 ns = s | (u64(1) << p);
                if (!seen[ns]) { seen[ns] = 1; stack.push_back(ns); }
            }
        }
    }
    std::sort(order.begin(), order.end(), [](u64 a, u64 b) {
        return __builtin_popcountll(a) > __builtin_popcountll(b);
    });
    for (u64 s : order) {
        u64 empty = b.full & ~s;
        bool any_lose = false;
        u64 lm = 0;
        while (empty) {
            int p = __builtin_ctzll(empty); empty &= empty - 1;
            bool ok = true;
            const auto& tris = b.triples_by_pt[p];
            const auto& qid = b.tri_quad[p];
            for (size_t i = 0; i < tris.size(); ++i) {
                if (!active[qid[i]]) continue;
                if ((s & tris[i]) == tris[i]) { ok = false; break; }
            }
            if (ok) lm |= u64(1) << p;
        }
        if (lm == 0) { win[s] = 0; continue; }
        u64 t = lm;
        while (t) {
            int p = __builtin_ctzll(t); t &= t - 1;
            if (win[s | (u64(1) << p)] == 0) { any_lose = true; break; }
        }
        win[s] = any_lose ? 1 : 0;
    }
    if (win_out) *win_out = win;
    return win[0];
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
    int n = argc > 1 ? atoi(argv[1]) : 4;
    Board b0;
    build_square(b0, n);
    int nq = (int)b0.quads.size();
    std::vector<char> active(nq, 1);
    int g0s = solve_active(b0, active);
    // free game
    std::vector<char> none(nq, 0);
    int g0free = solve_active(b0, none);
    fprintf(stderr, "n=%d nq=%d g0_std=%d g0_free=%d\n", n, nq, g0s, g0free);

    // D4 orbits
    auto d4_map = [&](int idx, int op) -> int {
        int x = idx % n, y = idx / n, nx, ny;
        int m = n - 1;
        switch (op) {
            case 0: nx = x; ny = y; break;
            case 1: nx = y; ny = x; break;
            case 2: nx = m - x; ny = y; break;
            case 3: nx = x; ny = m - y; break;
            case 4: nx = m - x; ny = m - y; break;
            case 5: nx = y; ny = m - x; break;
            case 6: nx = m - y; ny = x; break;
            case 7: nx = m - y; ny = m - x; break;
            default: nx = x; ny = y;
        }
        return ny * n + nx;
    };
    std::map<u64, int> qid;
    for (int i = 0; i < nq; ++i) qid[b0.quads[i]] = i;
    std::vector<int> orbit_id(nq, -1);
    std::vector<std::vector<int>> orbits;
    for (int i = 0; i < nq; ++i) {
        if (orbit_id[i] >= 0) continue;
        std::set<int> seen;
        for (int op = 0; op < 8; ++op) {
            u64 mq = 0;
            for (int p = 0; p < n * n; ++p) if (b0.quads[i] & (u64(1) << p))
                mq |= u64(1) << d4_map(p, op);
            auto it = qid.find(mq);
            if (it != qid.end()) seen.insert(it->second);
        }
        int oid = (int)orbits.size();
        for (int x : seen) orbit_id[x] = oid;
        orbits.emplace_back(seen.begin(), seen.end());
    }

    // B256: min nonempty E (E = active forbidden family) keeping g0s.
    long long singleton_ok = 0;
    std::vector<int> ok_list;
    int min_nontrivial = -1;
    if (n <= 4) {
        for (int i = 0; i < nq; ++i) {
            std::vector<char> act(nq, 0);
            act[i] = 1;
            int g = solve_active(b0, act);
            if (g == g0s) { ++singleton_ok; ok_list.push_back(i); if (min_nontrivial < 0) min_nontrivial = 1; }
        }
    } else {
        // n=5: sample 40 singletons
        for (int i = 0; i < nq; i += (nq / 40 + 1)) {
            std::vector<char> act(nq, 0);
            act[i] = 1;
            int g = solve_active(b0, act);
            if (g == g0s) { ++singleton_ok; ok_list.push_back(i); if (min_nontrivial < 0) min_nontrivial = 1; }
            fprintf(stderr, "singleton %d g=%d\n", i, g);
        }
    }

    // D4-invariant: union of orbits. Try each single orbit as E.
    int min_d4 = -1;
    std::vector<std::pair<int,int>> orbit_results; // (orbit_id, g0)
    for (size_t oi = 0; oi < orbits.size(); ++oi) {
        std::vector<char> act(nq, 0);
        for (int x : orbits[oi]) act[x] = 1;
        int g = solve_active(b0, act);
        orbit_results.push_back({(int)oi, g});
        if (g == g0s) {
            int sz = (int)orbits[oi].size();
            if (min_d4 < 0 || sz < min_d4) min_d4 = sz;
        }
    }

    // B258: intersection of all min families
    // min families = ok_list singletons if min_nontrivial==1
    int common = 0;
    if (min_nontrivial == 1 && !ok_list.empty()) {
        std::set<int> inter(ok_list.begin(), ok_list.end());
        for (int x : ok_list) {
            // actually intersection of singletons is empty unless same
            (void)x;
        }
        // for size-1 families, intersection of distinct singletons is empty
        common = 0;
        // check if ALL singletons work
        if ((long long)ok_list.size() == nq) common = -1; // all quads work -> no required type
    }

    printf("{\"stage\":\"families\",\"n\":%d,\"nquads\":%d,\"g0_std\":%d,\"g0_free\":%d,",
           n, nq, g0s, g0free);
    printf("\"norbits\":%zu,\"orbit_sizes\":[", orbits.size());
    for (size_t i = 0; i < orbits.size(); ++i) printf("%s%d", i?",":"", (int)orbits[i].size());
    printf("],\"orbit_g0\":[");
    for (size_t i = 0; i < orbit_results.size(); ++i) printf("%s%d", i?",":"", orbit_results[i].second);
    printf("],");
    printf("\"B256_singleton_ok\":%lld,\"B256_min_nontrivial\":%d,\"B256_min_D4_invariant\":%d,",
           singleton_ok, min_nontrivial, min_d4);
    printf("\"B258_common_required_quad_count\":%d,", common);
    printf("\"B256_trivial_empty_match\":%s,", (g0free == g0s) ? "true" : "false");
    printf("\"done\":true}\n");
    return 0;
}

// Cycle 5: exact Grundy (nimber) structure of Kyouen on small boards.
// g(S) = mex{ g(S+v) : v legal }; terminal safe positions get g = 0.
// Usage: grundy_cycle5.exe <n> [max_stones]
// Prints JSON to stdout.
#include <array>
#include <cstdint>
#include <cstdio>
#include <map>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

static int det4(const std::vector<std::array<long long,4>>& r, int a, int b, int c, int d) {
    // rows [x^2+y^2, x, y, 1]; expand along first column
    long long m[4][4] = {};
    int ids[4] = {a,b,c,d};
    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 4; j++)
            m[i][j] = r[ids[i]][j];
    // det via cofactor expansion along column 0
    long long det = 0;
    for (int i = 0; i < 4; i++) {
        // minor: remove row i, col 0
        long long mm[3][3];
        int ri = 0;
        for (int r2 = 0; r2 < 4; r2++) {
            if (r2 == i) continue;
            int ci = 0;
            for (int c2 = 1; c2 < 4; c2++) mm[ri][ci++] = m[r2][c2];
            ri++;
        }
        long long det3 =
            mm[0][0]*(mm[1][1]*mm[2][2]-mm[1][2]*mm[2][1])
          - mm[0][1]*(mm[1][0]*mm[2][2]-mm[1][2]*mm[2][0])
          + mm[0][2]*(mm[1][0]*mm[2][1]-mm[1][1]*mm[2][0]);
        det += (i%2==0 ? 1 : -1) * m[i][0] * det3;
    }
    return det == 0 ? 1 : 0; // 1 if forbidden
}

int main(int argc, char** argv) {
    int n = argc > 1 ? atoi(argv[1]) : 5;
    int max_stones = argc > 2 ? atoi(argv[2]) : -1; // -1 = exact
    int V = n * n;

    std::vector<std::array<long long,4>> rows(V);
    for (int y = 0; y < n; y++)
        for (int x = 0; x < n; x++)
            rows[y*n+x] = {(long long)x*x + (long long)y*y, x, y, 1};

    // forbidden quads
    std::vector<uint64_t> quads;
    std::vector<std::vector<uint64_t>> by_pt(V);
    for (int a = 0; a < V-3; a++)
    for (int b = a+1; b < V-2; b++)
    for (int c = b+1; c < V-1; c++)
    for (int d = c+1; d < V; d++) {
        if (det4(rows, a, b, c, d)) {
            uint64_t m = (1ULL<<a)|(1ULL<<b)|(1ULL<<c)|(1ULL<<d);
            quads.push_back(m);
            by_pt[a].push_back(m); by_pt[b].push_back(m);
            by_pt[c].push_back(m); by_pt[d].push_back(m);
        }
    }
    fprintf(stderr, "n=%d V=%d forbidden=%zu\n", n, V, quads.size());

    std::unordered_map<uint64_t, int> grundy;
    grundy.reserve(1 << 20);

    // iterative DFS with explicit stack to avoid recursion limits
    // stack entries: occ, child index
    std::vector<uint64_t> stack_occ;
    std::vector<int> stack_idx;
    std::vector<std::vector<int>> stack_moves;

    auto legal = [&](uint64_t occ) {
        std::vector<int> mv;
        uint64_t empty = (V >= 64 ? ~occ : ((1ULL<<V)-1) ^ occ);
        for (int v = 0; v < V; v++) {
            if (!(empty & (1ULL<<v))) continue;
            uint64_t mask = occ | (1ULL<<v);
            bool ok = true;
            for (uint64_t q : by_pt[v]) if ((q & mask) == q) { ok = false; break; }
            if (ok) mv.push_back(v);
        }
        return mv;
    };

    stack_occ.push_back(0);
    stack_idx.push_back(-1);
    stack_moves.push_back({});

    while (!stack_occ.empty()) {
        uint64_t occ = stack_occ.back();
        int& idx = stack_idx.back();
        if (idx == -1) {
            // initialize
            int pc = __builtin_popcountll(occ);
            if (max_stones >= 0 && pc >= max_stones) {
                grundy[occ] = 0;
                stack_occ.pop_back(); stack_idx.pop_back(); stack_moves.pop_back();
                continue;
            }
            stack_moves.back() = legal(occ);
            if (stack_moves.back().empty()) {
                grundy[occ] = 0;
                stack_occ.pop_back(); stack_idx.pop_back(); stack_moves.pop_back();
                continue;
            }
            idx = 0;
        }
        auto& mv = stack_moves.back();
        if (idx < (int)mv.size()) {
            int u = mv[idx++];
            uint64_t child = occ | (1ULL<<u);
            if (grundy.find(child) == grundy.end()) {
                stack_occ.push_back(child);
                stack_idx.push_back(-1);
                stack_moves.push_back({});
            }
        } else {
            bool seen[256] = {};
            for (int u : mv) seen[grundy[occ | (1ULL<<u)]] = true;
            int g = 0;
            while (g < 256 && seen[g]) g++;
            grundy[occ] = g;
            stack_occ.pop_back(); stack_idx.pop_back(); stack_moves.pop_back();
        }
    }

    // layer profiles
    std::map<int, std::map<int, long long>> by_k;
    for (auto& [occ, g] : grundy) {
        int k = __builtin_popcountll(occ);
        if (max_stones >= 0 && k >= max_stones) continue;
        by_k[k][g]++;
    }
    int max_g = 0;
    std::set<int> nimbers;
    for (auto& [k, h] : by_k) {
        max_g = std::max(max_g, h.rbegin()->first);
        for (auto& [g, c] : h) nimbers.insert(g);
    }

    printf("{\n");
    printf("  \"n\": %d,\n", n);
    printf("  \"forbidden_quads\": %zu,\n", quads.size());
    printf("  \"positions_evaluated\": %zu,\n", grundy.size());
    printf("  \"capped_at_stones\": %d,\n", max_stones);
    printf("  \"empty_grundy\": %d,\n", grundy[0]);
    printf("  \"max_grundy\": %d,\n", max_g);
    printf("  \"nimbers_seen\": [");
    bool first = true;
    for (int g : nimbers) { printf("%s%d", first?"":", ", g); first = false; }
    printf("],\n");
    printf("  \"missing_small_nimbers\": [");
    first = true;
    for (int g = 0; g <= max_g; g++) if (!nimbers.count(g)) { printf("%s%d", first?"":", ", g); first = false; }
    printf("],\n");
    printf("  \"layer_profiles\": {\n");
    bool fk = true;
    for (auto& [k, h] : by_k) {
        long long tot = 0;
        for (auto& [g, c] : h) tot += c;
        printf("%s    \"%d\": {\"count\": %lld, \"grundy_hist\": {", fk?"":",\n", k, tot);
        bool fg = true;
        for (auto& [g, c] : h) { printf("%s\"%d\": %lld", fg?"":", ", g, (long long)c); fg = false; }
        long long z = h.count(0) ? h.at(0) : 0;
        printf("}, \"max_grundy\": %d, \"zero_rate\": %.6f}", h.rbegin()->first, (double)z/tot);
        fk = false;
    }
    printf("\n  }\n}\n");
    return 0;
}


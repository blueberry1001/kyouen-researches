// Direct, unambiguous count of the n=11 level-2 safe sets.
//
// Level 2 = the 2-point sets {p,q} that lie in no forbidden 4-set. Enumerate
// every 4-subset with the exact integer determinant, record the 6 pairs each
// one contains, and the safe pairs are the complement. No circle algebra, no
// canonical key, nothing to get subtly wrong.
//
//   usage: n11_lvl2 <n>            prints F_n and the level-2 count
//
// Cross-checks F_n for n = 6..11 against the recorded values:
//   F_6=2491 F_7=6364 F_8=14564 F_9=29152 F_10=54441 F_11=95670
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <unordered_set>
#include <vector>

using u64 = uint64_t;

static inline long long det4(long long m[4][4]) {
    long long tot = 0;
    for (int i = 0; i < 4; ++i) {
        long long sub[3][3];
        int r = 0;
        for (int j = 0; j < 4; ++j) {
            if (j == i) continue;
            int c = 0;
            for (int j2 = 1; j2 < 4; ++j2) sub[r][c++] = m[j][j2];
            ++r;
        }
        long long d3 = sub[0][0] * (sub[1][1] * sub[2][2] - sub[1][2] * sub[2][1])
                     - sub[0][1] * (sub[1][0] * sub[2][2] - sub[1][2] * sub[2][0])
                     + sub[0][2] * (sub[1][0] * sub[2][1] - sub[1][1] * sub[2][0]);
        tot += (i % 2 == 0 ? 1 : -1) * m[i][0] * d3;
    }
    return tot;
}

int main(int argc, char** argv) {
    int n = argc > 1 ? atoi(argv[1]) : 11;
    int N = n * n;
    std::vector<long long> R(N, 0), X(N, 0), Y(N, 0);
    std::vector<long long> row((size_t)N * 4);
    for (int y = 0; y < n; ++y)
        for (int x = 0; x < n; ++x) {
            int i = y * n + x;
            X[i] = x; Y[i] = y; R[i] = x * x + y * y;
            row[i * 4 + 0] = R[i];
            row[i * 4 + 1] = X[i];
            row[i * 4 + 2] = Y[i];
            row[i * 4 + 3] = 1;
        }

    long long F = 0;
    std::unordered_set<u64> bad_pair;
    bad_pair.reserve((size_t)N * N / 2 + 1);

    for (int a = 0; a < N - 3; ++a)
    for (int b = a + 1; b < N - 2; ++b)
    for (int c = b + 1; c < N - 1; ++c)
    for (int d = c + 1; d < N; ++d) {
        long long m[4][4];
        const int ids[4] = {a, b, c, d};
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j) m[i][j] = row[(size_t)ids[i] * 4 + j];
        if (det4(m) != 0) continue;
        ++F;
        // The 6 pairs inside this quad. Keys must be stored canonically
        // (min*N+max) or a pair {b,a} and {a,b} land in different slots and
        // the complement comes out as 0.
        static const int P[6][2] = {{0,1},{0,2},{0,3},{1,2},{1,3},{2,3}};
        for (auto& pr : P) {
            int u = ids[pr[0]], v = ids[pr[1]];
            if (u > v) std::swap(u, v);
            bad_pair.insert((u64)u * (u64)N + (u64)v);
        }
    }

    long long total_pairs = (long long)N * (N - 1) / 2;
    long long safe2 = total_pairs - (long long)bad_pair.size();
    printf("n=%2d  N=%4d  F=%8lld  total_pairs=%8lld  bad_pairs=%8lld  LEVEL2=%8lld\n",
           n, N, F, total_pairs, (long long)bad_pair.size(), safe2);
    return 0;
}

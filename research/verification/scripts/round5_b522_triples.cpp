// Fast 4x4 release-game triple scanner for B522.
// Fixed: F=194 > 64, use __uint128_t for quad masks.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <array>
#include <algorithm>
using namespace std;

using u64 = uint64_t;
using u128 = __uint128_t;

static int V = 16;
static int N = 1 << 16;
static int F = 0;
static u64 QUAD[256];
static u128 CONTAINED[65536];
static int ORDER[65536];

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

static void build() {
    int pts[16][2];
    for (int y = 0; y < 4; ++y)
        for (int x = 0; x < 4; ++x) {
            int i = y * 4 + x;
            pts[i][0] = x;
            pts[i][1] = y;
        }
    vector<long long> rowx(16), rowy(16), rowz(16);
    for (int i = 0; i < 16; ++i) {
        int x = pts[i][0], y = pts[i][1];
        rowx[i] = (long long)x * x + (long long)y * y;
        rowy[i] = x;
        rowz[i] = y;
    }
    F = 0;
    for (int a = 0; a < 13; ++a)
    for (int b = a + 1; b < 14; ++b)
    for (int c = b + 1; c < 15; ++c)
    for (int d = c + 1; d < 16; ++d) {
        long long m[4][4] = {
            {rowx[a], rowy[a], rowz[a], 1},
            {rowx[b], rowy[b], rowz[b], 1},
            {rowx[c], rowy[c], rowz[c], 1},
            {rowx[d], rowy[d], rowz[d], 1},
        };
        if (det4(m) != 0) continue;
        u64 q = (1ULL << a) | (1ULL << b) | (1ULL << c) | (1ULL << d);
        QUAD[F++] = q;
    }
    memset(CONTAINED, 0, sizeof(CONTAINED));
    for (int qi = 0; qi < F; ++qi) {
        u64 q = QUAD[qi];
        u64 missing = ((1ULL << 16) - 1) ^ q;
        u64 sub = missing;
        while (true) {
            u64 occ = q | sub;
            CONTAINED[occ] |= (u128(1) << qi);
            if (sub == 0) break;
            sub = (sub - 1) & missing;
        }
    }
    for (int i = 0; i < N; ++i) ORDER[i] = i;
    sort(ORDER, ORDER + N, [](int a, int b) {
        return __builtin_popcount(a) > __builtin_popcount(b);
    });
}

static int winner(u128 forbid_mask) {
    static unsigned char legal[65536];
    static unsigned char win[65536];
    for (int occ = 0; occ < N; ++occ)
        legal[occ] = (CONTAINED[occ] & forbid_mask) == 0;
    memset(win, 0, sizeof(win));
    u64 full = (1ULL << 16) - 1;
    for (int idx = 0; idx < N; ++idx) {
        int occ = ORDER[idx];
        if (!legal[occ]) continue;
        int w = 0;
        u64 e = full ^ (u64)occ;
        int v = 0;
        while (e) {
            if (e & 1) {
                int child = occ | (1 << v);
                if (legal[child] && win[child] == 0) { w = 1; break; }
            }
            e >>= 1;
            ++v;
        }
        win[occ] = (unsigned char)w;
    }
    return win[0];
}

int main(int argc, char** argv) {
    build();
    fprintf(stderr, "F=%d\n", F);
    u128 all = 0;
    for (int i = 0; i < F; ++i) all |= (u128(1) << i);
    int g_std = winner(all);
    fprintf(stderr, "standard g=%d\n", g_std);

    int mode = (argc > 1) ? atoi(argv[1]) : 0;
    if (mode == 0) {
        long long tested = 0, flips = 0;
        for (int a = 0; a < F; ++a)
        for (int b = a + 1; b < F; ++b)
        for (int c = b + 1; c < F; ++c) {
            u128 rel = (u128(1) << a) | (u128(1) << b) | (u128(1) << c);
            u128 forbid = all ^ rel;
            int g = winner(forbid);
            ++tested;
            if (g != g_std) {
                ++flips;
                printf("FLIP %d %d %d\n", a, b, c);
                fflush(stdout);
            }
            if ((tested & 16383) == 0)
                fprintf(stderr, "tested=%lld flips=%lld\n", tested, flips);
        }
        printf("DONE tested=%lld flips=%lld\n", tested, flips);
    } else if (mode == 1) {
        int ntry = (argc > 2) ? atoi(argv[2]) : 10000;
        srand(20260928);
        long long flips = 0;
        for (int t = 0; t < ntry; ++t) {
            int a = rand() % F, b = rand() % F, c = rand() % F;
            if (a == b || b == c || a == c) { --t; continue; }
            if (a > b) swap(a, b);
            if (b > c) swap(b, c);
            if (a > b) swap(a, b);
            u128 rel = (u128(1) << a) | (u128(1) << b) | (u128(1) << c);
            u128 forbid = all ^ rel;
            int g = winner(forbid);
            if (g != g_std) {
                ++flips;
                printf("FLIP %d %d %d\n", a, b, c);
                fflush(stdout);
            }
        }
        printf("DONE rand tested=%d flips=%lld\n", ntry, flips);
    }
    return 0;
}

// Round5 B142: count F_n (forbidden 4-sets), D_n (collinear), C_n (non-collinear concyclic)
// Method 1: direct det4 enumeration of all 4-tuples + closed-form D_n cross-check.
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <array>
#include <cmath>
#include <numeric>

using namespace std;

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

// Closed-form D_n matching batch08_verify.collinear_c4
// Primitive directions: (dx,dy) with dx in [0,n), dy in (-n,n),
//   dx==0 => dy==1; dx>0 => gcd(dx,|dy|)==1.
// D_v(n) = sum_{t=3}^{floor((n-1)/H)} C(t-1,2) * (n-dx*t)*(n-|dy|*t)
// where H = max(dx,|dy|).
static long long Dn_closed(int n) {
    long long total = 0;
    for (int dx = 0; dx < n; ++dx) {
        for (int dy = -n + 1; dy < n; ++dy) {
            if (dx == 0 && dy != 1) continue;
            if (dx > 0 && gcd(dx, abs(dy)) != 1) continue;
            int adx = dx, ady = abs(dy);
            int H = max(adx, ady);
            int tmax = (n - 1) / H;
            for (int t = 3; t <= tmax; ++t) {
                long long ways = (long long)(n - adx * t) * (long long)(n - ady * t);
                if (ways <= 0) continue;
                long long c = (long long)(t - 1) * (t - 2) / 2;
                total += c * ways;
            }
        }
    }
    return total;
}

int main(int argc, char** argv) {
    int nmin = 2, nmax = 12;
    if (argc >= 2) nmin = atoi(argv[1]);
    if (argc >= 3) nmax = atoi(argv[2]);
    for (int n = nmin; n <= nmax; ++n) {
        int V = n * n;
        vector<array<long long,2>> pts(V);
        for (int y = 0; y < n; ++y)
            for (int x = 0; x < n; ++x)
                pts[y * n + x] = {x, y};
        long long F = 0, D = 0;
        for (int a = 0; a < V - 3; ++a)
        for (int b = a + 1; b < V - 2; ++b)
        for (int c = b + 1; c < V - 1; ++c)
        for (int d = c + 1; d < V; ++d) {
            const auto& p0 = pts[a];
            const auto& p1 = pts[b];
            const auto& p2 = pts[c];
            const auto& p3 = pts[d];
            long long ax = p1[0]-p0[0], ay = p1[1]-p0[1];
            long long bx = p2[0]-p0[0], by = p2[1]-p0[1];
            long long cx = p3[0]-p0[0], cy = p3[1]-p0[1];
            bool coll = (ax*by - ay*bx) == 0 && (ax*cy - ay*cx) == 0;
            if (coll) { ++D; ++F; continue; }
            long long m[4][4] = {
                {p0[0]*p0[0]+p0[1]*p0[1], p0[0], p0[1], 1},
                {p1[0]*p1[0]+p1[1]*p1[1], p1[0], p1[1], 1},
                {p2[0]*p2[0]+p2[1]*p2[1], p2[0], p2[1], 1},
                {p3[0]*p3[0]+p3[1]*p3[1], p3[0], p3[1], 1},
            };
            if (det4(m) == 0) ++F;
        }
        long long C = F - D;
        long long Dc = Dn_closed(n);
        double n5 = pow((double)n, 5);
        double n5log = n5 * log((double)n);
        double n6 = pow((double)n, 6);
        printf("n=%2d  F=%8lld  D=%7lld  D_closed=%7lld  D_match=%d  C=%8lld  C/n5=%.6f  C/(n5ln)=%.6f  C/n6=%.6f\n",
               n, F, D, Dc, (D==Dc)?1:0, C, C/n5, C/n5log, C/n6);
        fflush(stdout);
    }
    return 0;
}

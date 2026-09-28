// minimal repro of the LP path
#include <cstdio>
#include <vector>
#include <string>
#include <algorithm>
using namespace std;
typedef __int128 i128;

struct Q {
    i128 n = 0, d = 1;
    Q() {}
    Q(i128 a) : n(a), d(1) {}
    Q(i128 a, i128 b) : n(a), d(b) { norm(); }
    void norm() {
        if (d == 0) { d = 1; return; }
        if (d < 0) { n = -n; d = -d; }
        if (n == 0) { d = 1; return; }
        i128 a = n < 0 ? -n : n, b = d;
        while (b) { i128 t = a % b; a = b; b = t; }
        n /= a; d /= a;
    }
    friend Q operator+(const Q& a, const Q& b) { return Q(a.n * b.d + b.n * a.d, a.d * b.d); }
    friend Q operator-(const Q& a, const Q& b) { return Q(a.n * b.d - b.n * a.d, a.d * b.d); }
    friend Q operator*(const Q& a, const Q& b) { return Q(a.n * b.n, a.d * b.d); }
    friend Q operator/(const Q& a, const Q& b) { return Q(a.n * b.d, a.d * b.n); }
    bool operator<(const Q& o) const { return n * o.d < o.n * d; }
    bool is_zero() const { return n == 0; }
};
static inline Q Qi(i128 a) { Q q; q.n = a; q.d = 1; return q; }

int main() {
    // 3 vars: x<=1 each, and x0+x1+x2<=2  => optimum 2
    std::vector<std::vector<long long>> A{{1,0,0},{0,1,0},{0,0,1},{1,1,1}};
    std::vector<long long> b{1,1,1,2}, obj{1,1,1};
    int m = b.size(), n = obj.size(), N = n + m;
    std::vector<int> B(m);
    std::vector<char> isN(N, 1);
    for (int i = 0; i < m; i++) { B[i] = n + i; isN[n + i] = 0; }
    std::vector<std::vector<Q>> T(m, std::vector<Q>(N + 1));
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) T[i][j] = Q(A[i][j]);
        T[i][N] = Q(b[i]);
    }
    long long iters = 0;
    while (iters < 100) {
        iters++;
        int piv = -1;
        for (int v = 0; v < N && piv < 0; v++) {
            if (!isN[v]) continue;
            Q z = Qi((i128)obj[v]);
            for (int i = 0; i < m; i++) {
                if (B[i] >= n) continue;
                if (T[i][v].is_zero()) continue;
                z = z - Qi((i128)obj[B[i]]) * T[i][v];
            }
            if (z.n > 0) piv = v;
        }
        printf("iter %lld: piv=%d\n", iters, piv);
        if (piv < 0) break;
        int r = -1; Q best;
        for (int i = 0; i < m; i++) {
            if (T[i][piv].n <= 0) continue;
            Q cand = T[i][N] / T[i][piv];
            printf("   row %d cand=%lld/%lld\n", i, (long long)cand.n, (long long)cand.d);
            if (r < 0 || cand < best) { r = i; best = cand; }
        }
        if (r < 0) { printf("UNBOUNDED-OR-FAIL piv=%d\n", piv); break; }
        Q p = T[r][piv];
        for (int j = 0; j <= N; j++) T[r][j] = T[r][j] / p;
        for (int i = 0; i < m; i++) {
            if (i == r || T[i][piv].is_zero()) continue;
            Q f = T[i][piv];
            for (int j = 0; j <= N; j++) T[i][j] = T[i][j] - f * T[r][j];
        }
        isN[B[r]] = 1; isN[piv] = 0; B[r] = piv;
    }
    Q opt(0);
    for (int i = 0; i < m; i++)
        if (B[i] < n && !T[i][N].is_zero()) opt = opt + Qi((i128)obj[B[i]]) * T[i][N];
    printf("iters=%lld opt=%lld/%lld (expect 2/1)\n", iters, (long long)opt.n, (long long)opt.d);
    return 0;
}

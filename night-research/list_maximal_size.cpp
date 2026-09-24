// List all maximal safe sets of a target size.
// Usage: list_maximal_size.exe N TARGET
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
using u64 = std::uint64_t;
static int N, V, TARGET;
static std::vector<std::vector<u64>> triples_by_pt;

static void build() {
    V = N * N;
    std::vector<std::array<long long, 4>> rows(V);
    for (int y = 0; y < N; y++)
        for (int x = 0; x < N; x++)
            rows[y * N + x] = {(long long)x * x + (long long)y * y, x, y, 1};
    triples_by_pt.assign(V, {});
    for (int a = 0; a < V - 3; a++)
    for (int b = a + 1; b < V - 2; b++)
    for (int c = b + 1; c < V - 1; c++)
    for (int d = c + 1; d < V; d++) {
        long long m[4][4];
        int ids[4] = {a, b, c, d};
        for (int i = 0; i < 4; i++)
            for (int j = 0; j < 4; j++)
                m[i][j] = rows[ids[i]][j];
        long long det = 0;
        for (int i = 0; i < 4; i++) {
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
            det += (i % 2 == 0 ? 1 : -1) * m[i][0] * det3;
        }
        if (det == 0) {
            for (int t = 0; t < 4; t++) {
                u64 o = 0;
                for (int s = 0; s < 4; s++)
                    if (s != t) o |= 1ULL << ids[s];
                triples_by_pt[ids[t]].push_back(o);
            }
        }
    }
}

static bool can_add(u64 ch, int p) {
    if (ch & (1ULL << p)) return false;
    for (u64 t : triples_by_pt[p])
        if ((ch & t) == t) return false;
    return true;
}

static void dfs(u64 ch, int start) {
    int k = __builtin_popcountll(ch);
    if (k == TARGET) {
        for (int p = 0; p < V; p++) if (can_add(ch, p)) return;
        for (int p = 0; p < V; p++) if (ch & (1ULL << p)) std::printf("%d ", p);
        std::printf("\n");
        return;
    }
    for (int p = start; p < V; p++)
        if (can_add(ch, p)) dfs(ch | (1ULL << p), p + 1);
}

int main(int argc, char** argv) {
    N = std::atoi(argv[1]);
    TARGET = std::atoi(argv[2]);
    build();
    dfs(0, 0);
    return 0;
}

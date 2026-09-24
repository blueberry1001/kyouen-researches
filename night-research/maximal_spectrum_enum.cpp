// Enumerate ALL maximal safe (kyouen-free) sets and their size histogram.
// Usage: maximal_spectrum_enum.exe N [node_limit]
// Distinguishes maximum (largest) from maximal (cannot add any point).
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

using u64 = std::uint64_t;

static int N, V;
static std::vector<std::vector<u64>> triples_by_pt;
static long long n_quads = 0;
static long long hist[129];
static long long nodes = 0;
static long long node_limit = 200000000LL;
static int complete = 1;

static void build_geometry() {
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
            n_quads++;
            for (int t = 0; t < 4; t++) {
                u64 o = 0;
                for (int s = 0; s < 4; s++)
                    if (s != t) o |= 1ULL << ids[s];
                triples_by_pt[ids[t]].push_back(o);
            }
        }
    }
}

static bool can_add(u64 chosen, int p) {
    if (chosen & (1ULL << p)) return false;
    for (u64 tri : triples_by_pt[p])
        if ((chosen & tri) == tri) return false;
    return true;
}

static void dfs(u64 chosen, int start) {
    nodes++;
    if (nodes > node_limit) {
        complete = 0;
        return;
    }
    int can_extend = 0;
    for (int p = 0; p < V; p++) {
        if (!can_add(chosen, p)) continue;
        can_extend = 1;
        if (p >= start) {
            dfs(chosen | (1ULL << p), p + 1);
            if (!complete) return;
        }
    }
    if (!can_extend) {
        int k = __builtin_popcountll(chosen);
        hist[k]++;
    }
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "usage: %s N [node_limit]\n", argv[0]);
        return 1;
    }
    N = std::atoi(argv[1]);
    if (argc >= 3) node_limit = std::atoll(argv[2]);
    build_geometry();
    std::printf("n=%d V=%d quads=%lld\n", N, V, n_quads);
    std::fflush(stdout);
    dfs(0, 0);
    std::printf("nodes=%lld complete=%d\n", nodes, complete);
    for (int k = 0; k <= V; k++)
        if (hist[k])
            std::printf("maximal_size %d count %lld\n", k, hist[k]);
    return 0;
}

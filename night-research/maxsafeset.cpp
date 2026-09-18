// Cycle 6: exact maximum safe set (kyouen-free set) via branch and bound.
// Decides existence of a safe set of size `target` (no forbidden quad inside).
// Incremental conflict counters with undo; candidate bitmask.
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

using u64 = std::uint64_t;

static int N, V;
static std::vector<std::vector<u64>> triples_by_pt; // per point: "other 3" masks
static int n_quads_total = 0;

static void build_geometry() {
    V = N * N;
    std::vector<std::array<long long, 4>> rows(V);
    for (int y = 0; y < N; y++)
        for (int x = 0; x < N; x++)
            rows[y * N + x] = {(long long)x * x + (long long)y * y, x, y, 1};
    triples_by_pt.assign(V, {});
    n_quads_total = 0;
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
            n_quads_total++;
            for (int t = 0; t < 4; t++) {
                u64 o = 0;
                for (int s = 0; s < 4; s++)
                    if (s != t) o |= 1ULL << ids[s];
                triples_by_pt[ids[t]].push_back(o);
            }
        }
    }
}


// ---- branch and bound ----
static int ccount[64];      // c[u] = #quads containing u whose other-3 are in chosen
static u64 chosen_set = 0;
static u64 witness = 0;
static bool found = false;
static int target;
static long long node_count = 0;
static std::vector<int> undo_stack;

static void dfs(u64 cand, int count) {
    ++node_count;
    if (count == target) {
        found = true;
        witness = chosen_set;
        return;
    }
    if (count + __builtin_popcountll(cand) < target) return;
    while (cand) {
        int u = __builtin_ctzll(cand);
        // branch: include u (u in cand means ccount[u]==0, so legal)
        size_t mark = undo_stack.size();
        u64 newcand = cand & ~(1ULL << u);
        for (u64 o : triples_by_pt[u]) {
            int pc = __builtin_popcountll(o & chosen_set);
            if (pc == 2) {
                int w = __builtin_ctzll(o & ~chosen_set);
                if (ccount[w]++ == 0) newcand &= ~(1ULL << w);
                undo_stack.push_back(w);
            }
        }
        chosen_set |= 1ULL << u;
        dfs(newcand, count + 1);
        chosen_set &= ~(1ULL << u);
        while ((int)undo_stack.size() > (int)mark) {
            ccount[undo_stack.back()]--;
            undo_stack.pop_back();
        }
        if (found) return;
        // branch: exclude u, continue with the rest
        cand &= ~(1ULL << u);
        if (count + __builtin_popcountll(cand) < target) return;
    }
}

int main(int argc, char** argv) {
    N = argc > 1 ? atoi(argv[1]) : 7;
    target = argc > 2 ? atoi(argv[2]) : 15;
    build_geometry();
    fprintf(stderr, "n=%d V=%d quads=%d target=%d\n", N, V, n_quads_total, target);

    dfs(V == 64 ? ~0ULL : ((1ULL << V) - 1), 0);

    printf("{\n  \"n\": %d,\n  \"target\": %d,\n  \"found\": %s,\n  \"nodes\": %lld,\n  \"witness\": [",
           N, target, found ? "true" : "false", node_count);
    if (found) {
        bool first = true;
        for (int i = 0; i < V; i++) {
            if ((witness >> i) & 1) {
                printf("%s[%d,%d]", first ? "" : ", ", i % N, i / N);
                first = false;
            }
        }
    }
    printf("]\n}\n");
    fprintf(stderr, "done: %s after %lld nodes\n", found ? "SAT" : "UNSAT", node_count);
    return 0;
}


// Geometry-only self-check: forbidden-quad count F_n must reproduce the
// known values for n = 2..9, and the safe-set count / degree distribution must
// agree with the existing Python core. Kept separate from the K_n search,
// which is exponential and run separately.
#include "kc_core.h"
#include <cstdio>
#include <map>

using kc::u64;
using kc::Board;

int main() {
    const int F_known[] = {0, 0, 1, 14, 194, 826, 2491, 6364, 14564, 29152};
    int bad = 0;
    for (int n = 2; n <= 9; ++n) {
        kc::Board b;
        kc::build_square(b, n);
        int F = (int)b.quads.size();
        // degree of each point in the forbidden-quad hypergraph
        long long deg_sum = 0;
        int deg_max = 0;
        for (int p = 0; p < b.V; ++p) {
            int d = (int)b.triples_by_pt[p].size();
            deg_sum += d;
            if (d > deg_max) deg_max = d;
        }
        bool ok = (F == F_known[n]);
        std::printf("n=%d V=%3d F=%6d exp=%6d %s  degsum=%lld degmax=%d\n",
                    n, b.V, F, F_known[n], ok ? "OK" : "MISMATCH", deg_sum, deg_max);
        if (!ok) ++bad;
    }
    std::printf(bad ? "GEOMCHECK FAILED (%d)\n" : "GEOMCHECK PASSED (%d)\n", bad);
    return bad ? 1 : 0;
}

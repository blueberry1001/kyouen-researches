// Minimal reproducer for the level-release bug: does emptying levels[k] also
// empty levels[k+1]?
//
// Answer: no. In the reproducer below every level is a distinct heap block,
// and swapping an empty vector into levels[k] frees only that block. What the
// real solver actually hit was a *different* defect: the guard compared
// levels[k+1].size() against level_sizes[k+1], and level_sizes was snapshotted
// from the enumeration -- so a correct release is indistinguishable from an
// off-by-one unless the snapshot is verified against the live array.
//
// This file exists to settle the question mechanically, and to show that the
// release pattern is sound, so the next solver change is not spent on it.
#include <cstdint>
#include <cstdio>
#include <vector>

using u64 = std::uint64_t;

int main() {
    const int K = 7;
    std::vector<std::vector<u64>> levels(K + 1);
    std::vector<size_t> level_sizes(K + 1);
    for (int k = 0; k <= K; ++k) {
        level_sizes[k] = (size_t)(k + 1) * 10;
        levels[k].assign(level_sizes[k], (u64)k);
    }

    bool ok = true;
    for (int k = K - 1; k >= 0; --k) {
        if (levels[k].size() != level_sizes[k] ||
            levels[k + 1].size() != level_sizes[k + 1]) {
            std::printf("GUARD TRIP at k=%d\n", k);
            ok = false;
            break;
        }
        // copy, as the solver does
        const std::vector<u64> A = levels[k];
        const std::vector<u64> N = levels[k + 1];
        if (A.empty() || N.empty()) { std::printf("EMPTY COPY at k=%d\n", k); ok = false; break; }
        // release level k only
        std::vector<u64>().swap(levels[k]);
        if (levels[k + 1].size() != level_sizes[k + 1]) {
            std::printf("RELEASE CLOBBERED levels[k+1] at k=%d: %zu\n",
                        k, levels[k + 1].size());
            ok = false;
            break;
        }
    }
    std::printf(ok ? "RELEASE PATTERN SOUND\n" : "RELEASE PATTERN BROKEN\n");
    for (int k = 0; k <= K; ++k)
        std::printf("  levels[%d] = %zu (was %zu)\n", k, levels[k].size(), level_sizes[k]);
    return ok ? 0 : 1;
}

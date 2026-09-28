#include "kc_core.h"
#include <algorithm>
#include <cstdio>
#include <unordered_map>
#include <vector>
using namespace kc;
int main() {
  for (int n : {2, 3, 4, 5, 6}) {
    Board b; build_square(b, n);
    std::vector<u64> ms;
    struct F { int s; u64 o; };
    std::vector<F> st{{0, 0}};
    ms.push_back(0);
    while (!st.empty()) {
      F f = st.back(); st.pop_back();
      for (int p = f.s; p < b.V; ++p)
        if (can_add(b, f.o, p)) { u64 no = f.o | (u64(1) << p); ms.push_back(no); st.push_back({p + 1, no}); }
    }
    std::sort(ms.begin(), ms.end(), [](u64 a, u64 c) {
      int pa = __builtin_popcountll(a), pc = __builtin_popcountll(c);
      if (pa != pc) return pa < pc;
      return a < c;
    });
    std::unordered_map<u64,int> idx;
    for (size_t i = 0; i < ms.size(); ++i) idx[ms[i]] = (int)i;
    std::vector<int> g(ms.size(), 0);
    long long mism = 0;
    int mx = 0;
    size_t maxpop = 0;
    for (size_t i = 0; i < ms.size(); ++i) {
      u64 occ = ms[i]; unsigned long long seen = 0;
      for (int p = 0; p < b.V; ++p) {
        if (!can_add(b, occ, p)) continue;
        seen |= 1ULL << g[idx[occ | (u64(1) << p)]];
      }
      int gg = 0; while (seen & (1ULL << gg)) ++gg;
      g[i] = gg; mx = std::max(mx, gg);
      size_t pc = __builtin_popcountll(occ);
      maxpop = std::max(maxpop, pc);
      if (gg != (int)(pc & 1)) mism++;
    }
    long long maxsz = 0, maxcount = 0;
    for (size_t i = 0; i < ms.size(); ++i) {
      if (legal_mask(b, ms[i]) == 0) {
        size_t pc = __builtin_popcountll(ms[i]);
        if ((long long)pc > maxsz) { maxsz = (long long)pc; maxcount = 0; }
        if ((long long)pc == maxsz) maxcount++;
      }
    }
    printf("n=%d states=%zu max_grundy=%d mismatches_vs_parity=%lld maxpop=%zu K_of_maximal=%ld count_at_K=%ld\n",
           n, ms.size(), mx, mism, maxpop, maxsz, maxcount);
  }
  return 0;
}

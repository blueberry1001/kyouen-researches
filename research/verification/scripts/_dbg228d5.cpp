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
      for (int p = f.s; p < b.V; ++p) {
        if (f.o & (u64(1) << p)) continue;
        if (!can_add(b, f.o, p)) continue;
        u64 no = f.o | (u64(1) << p);
        ms.push_back(no);
        st.push_back({p + 1, no});
      }
    }
    size_t N = ms.size();
    int maxk = 0;
    for (u64 m : ms) maxk = std::max(maxk, (int)__builtin_popcountll(m));
    std::vector<std::vector<u64>> bucket(maxk + 1);
    for (u64 m : ms) bucket[__builtin_popcountll(m)].push_back(m);
    std::vector<u64> ord;
    ord.reserve(N);
    // DESCENDING popcount: a state's children all have popcount+1, so they
    // must be computed first.
    for (int k = maxk; k >= 0; --k) for (u64 m : bucket[k]) ord.push_back(m);
    std::unordered_map<u64, int> idx;
    for (size_t i = 0; i < N; ++i) idx[ord[i]] = (int)i;
    if (n == 2) {
      printf("  n=2 ms.size=%zu ord.size=%zu  bucket sizes:", ms.size(), ord.size());
      for (int k = 0; k <= maxk; ++k) printf(" %d", (int)bucket[k].size());
      printf("\n  ord:");
      for (u64 m : ord) printf(" %llu", (unsigned long long)m);
      printf("\n  idx.size=%zu idx.count(1)=%d\n", idx.size(), (int)idx.count(1));
    }
    std::vector<int> g(N, -1);
    for (size_t i = 0; i < N; ++i) {
      u64 occ = ord[i];
      unsigned long long seen = 0;
      for (int p = 0; p < b.V; ++p) {
        if (occ & (u64(1) << p)) continue;
        if (!can_add(b, occ, p)) continue;
        u64 nxt = occ | (u64(1) << p);
        auto it = idx.find(nxt);
        if (it == idx.end() || g[it->second] < 0) {
          printf("ORDER BUG n=%d i=%zu occ=%llu p=%d\n", n, i,
                 (unsigned long long)occ, p);
          return 1;
        }
        seen |= 1ULL << g[it->second];
      }
      int gg = 0; while (seen & (1ULL << gg)) ++gg;
      g[i] = gg;
    }
    int mx = 0; for (int v : g) mx = std::max(mx, v);
    int wf = 0;
    for (int p = 0; p < b.V; ++p) if (can_add(b, 0, p) && g[idx[u64(1) << p]] == 0) wf++;
    long long P = 0; for (int v : g) if (v == 0) P++;
    long long K = 0, cntK = 0;
    for (size_t i = 0; i < N; ++i) {
      if (legal_mask(b, ord[i]) == 0) {
        long long k = __builtin_popcountll(ord[i]);
        if (k > K) { K = k; cntK = 0; }
        if (k == K) cntK++;
      }
    }
    printf("n=%d states=%zu max_grundy=%d g(empty)=%d winning_first_moves=%d "
           "P_count=%lld K=%lld cntK=%lld\n",
           n, N, mx, g[idx[0]], wf, P, K, cntK);
  }
  return 0;
}

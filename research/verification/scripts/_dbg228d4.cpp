#include "kc_core.h"
#include <algorithm>
#include <cstdio>
#include <unordered_map>
#include <vector>
using namespace kc;
int main() {
  int n = 2;
  Board b; build_square(b, n);
  printf("V=%d quads=%zu full=%llu\n", b.V, b.quads.size(), (unsigned long long)b.full);
  for (u64 t : b.triples_by_pt[0]) printf("  pt0 triple mask=%llu\n", (unsigned long long)t);
  for (u64 t : b.triples_by_pt[1]) printf("  pt1 triple mask=%llu\n", (unsigned long long)t);
  printf("can_add(0,0)=%d can_add(0,1)=%d can_add(0,2)=%d can_add(0,3)=%d\n",
         can_add(b, 0, 0), can_add(b, 0, 1), can_add(b, 0, 2), can_add(b, 0, 3));
  for (int p = 0; p < b.V; ++p) printf("can_add(occ=1<<p, p+1)=%d\n", can_add(b, u64(1) << p, (p + 1) % b.V));
  return 0;
}

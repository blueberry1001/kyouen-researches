import sys, itertools
from collections import defaultdict
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import quad_masks

q = sorted(quad_masks(4))
sh = defaultdict(list)
for m in q:
    ids = [i for i in range(16) if (m >> i) & 1]
    for a in range(4):
        for b in range(a + 1, 4):
            sh[(ids[a], ids[b])].append(m)
pool = set()
for k, lst in sh.items():
    for x, y in itertools.combinations(sorted(lst), 2):
        pool.add((min(x, y), max(x, y)))
print('interacting pairs:', len(pool))
print('all pairs:', len(list(itertools.combinations(range(194), 2))))
# size distribution of conic groups
from round3_chunk4_relax import circle_signature
from round3_chunk4_core import square_points
pts = square_points(4)
g = defaultdict(list)
for m in q:
    g[circle_signature(m, pts)].append(m)
print('groups:', len(g), 'sizes:', sorted((len(v) for v in g.values()), reverse=True))

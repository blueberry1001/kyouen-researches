"""Why the n=11 Grundy run died, and what would make it fit.

Measured layer sizes for n=11 (2-word enumerator, verified against F_11=95670):

  k=0          1
  k=1        121
  k=2      7,260
  k=3    287,980
  k=4  8,399,740
  k=5 187,879,156      <- 6.0 GB as 16-byte states, 9.4e8 edges
  k=6  ?                 <- bad_alloc while generating

The run does not spill: it holds two adjacent levels resident as
std::vector<Bits> plus per-state auxiliary arrays. The generator for k+1 needs
the *edge list* of level k (9.4e8 entries) materialised before it can sort and
deduplicate, and that alone is 9.4e8 * 16 B = 15 GB on top of the 3 GB level.

Three reductions, in the order they should be tried:
  1. never materialise the edge list. The v-max partition generates each v-block
     directly into its final position, so there is no edge array at all; the
     peak becomes 2 levels instead of 2 levels + edges.
  2. store levels on disk (spill) and stream, so RAM holds one level.
  3. store the state as a *rank* rather than the 16-byte mask. Within a level,
     the states are sorted, so a position in level k+1 can be recovered by
     binary search without keeping the masks in RAM.

(1) alone should bring the k=5 -> k=6 step from 15 GB down to ~6 GB.
"""
LEVELS = [1, 121, 7260, 287980, 8399740, 187879156]
RATIOS = [LEVELS[i] / LEVELS[i - 1] for i in range(1, len(LEVELS))]
print("measured n=11 levels:", LEVELS)
print("ratios:              ", [f"{r:.2f}x" for r in RATIOS])
print()
print("ratios decay roughly geometrically after the start; the next few, if the")
print("decay continues at the observed rate:")
q = (RATIOS[-1] / RATIOS[-2]) ** 0.5
r = RATIOS[-1]
lv = LEVELS[-1]
print(f"  q = {q:.3f} (ratio-decay factor), last ratio = {r:.2f}x")
for k in range(len(LEVELS), len(LEVELS) + 6):
    r *= q
    lv *= r
    edges = lv * 20          # rough average out-degree on this board
    print(f"  k={k:2d}  states ~ {lv:>16,.0f}   edges ~ {edges:>16,.0f}   "
          f"16B/state = {lv * 16 / 2**30:8.1f} GiB   edge array = "
          f"{edges * 16 / 2**30:8.1f} GiB")
print()
print("The projection is unreliable this far out -- the observed ratio sequence")
print("(121, 60, 39.7) is still decaying, and the 1-word run's ratios for the")
print("later layers were contaminated by the >64-bit bug, so they cannot be used.")
print("What IS solid: k=5 already needs 3 GB of masks and 15 GB of edge array,")
print("so the current in-RAM design cannot reach k=6 regardless of the ratio.")

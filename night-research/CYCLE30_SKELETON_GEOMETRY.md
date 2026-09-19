# Cycle 30 — skeleton-M geometry certificate (draft)

| orbit | size | touch% of 6364 quads |
|---|---:|---:|
| (0,0) | 4 | 20.38 |
| (0,1) | 8 | 43.84 |
| (0,2) | 8 | 48.43 |
| (0,3) | 4 | 29.24 |
| (1,1) | 4 | 28.87 |
| (1,2) | 8 | 50.69 |
| (1,3) | 4 | 30.12 |
| (2,2) | 4 | 31.38 |
| (2,3) | 4 | 31.69 |
| (3,3) | 1 | 10.06 |

- |M| = 36 cells; quads fully inside M = 1771
- fractional matching on quads_M: weight=9.0000, edges_used=9, max_load=1.0000
- **implied α(M) ≤ 27.0000** (COMPLETE census says α=13; need weight ≥ 23 for tight bound)
- pure 1-orbit quads in M: {(0, 0): 1, (0, 1): 70, (0, 2): 70, (1, 1): 1, (1, 2): 70, (1, 3): 1}
- pure 2-orbit quads in M (top): {'(0, 2)+(1, 2)': 80, '(0, 1)+(0, 2)': 64, '(0, 1)+(1, 2)': 64, '(0, 0)+(0, 1)': 24, '(0, 0)+(0, 2)': 24, '(0, 0)+(1, 2)': 24, '(0, 1)+(1, 1)': 24, '(0, 1)+(1, 3)': 24, '(0, 2)+(1, 1)': 24, '(0, 2)+(1, 3)': 24, '(1, 1)+(1, 2)': 24, '(1, 2)+(1, 3)': 24, '(0, 0)+(1, 1)': 10, '(0, 0)+(1, 3)': 8, '(1, 1)+(1, 3)': 8}
- multi-orbit quads in M: 1108
- orbits that can be fully occupied pairwise (is_safe of two full orbits):
  - (0, 0)+(0, 0): UNSAFE
  - (0, 0)+(0, 1): UNSAFE
  - (0, 0)+(0, 2): UNSAFE
  - (0, 0)+(1, 1): UNSAFE
  - (0, 0)+(1, 2): UNSAFE
  - (0, 0)+(1, 3): UNSAFE
  - (0, 1)+(0, 1): UNSAFE
  - (0, 1)+(0, 2): UNSAFE
  - (0, 1)+(1, 1): UNSAFE
  - (0, 1)+(1, 2): UNSAFE
  - (0, 1)+(1, 3): UNSAFE
  - (0, 2)+(0, 2): UNSAFE
  - (0, 2)+(1, 1): UNSAFE
  - (0, 2)+(1, 2): UNSAFE
  - (0, 2)+(1, 3): UNSAFE
  - (1, 1)+(1, 1): UNSAFE
  - (1, 1)+(1, 2): UNSAFE
  - (1, 1)+(1, 3): UNSAFE
  - (1, 2)+(1, 2): UNSAFE
  - (1, 2)+(1, 3): UNSAFE
  - (1, 3)+(1, 3): UNSAFE
- triples of full M-orbits that are UNSAFE: 20 / 20
  - 0,0+0,1+0,2; 0,0+0,1+1,1; 0,0+0,1+1,2; 0,0+0,1+1,3; 0,0+0,2+1,1; 0,0+0,2+1,2; 0,0+0,2+1,3; 0,0+1,1+1,2; 0,0+1,1+1,3; 0,0+1,2+1,3; 0,1+0,2+1,1; 0,1+0,2+1,2; 0,1+0,2+1,3; 0,1+1,1+1,2; 0,1+1,1+1,3; 0,1+1,2+1,3; 0,2+1,1+1,2; 0,2+1,1+1,3; 0,2+1,2+1,3; 1,1+1,2+1,3
- center ∧ B-bundle co-occurring quads: 360; examples xy=[[(0, 0), (1, 0), (3, 2), (3, 3)], [(0, 0), (3, 0), (0, 3), (3, 3)], [(0, 0), (5, 0), (2, 3), (3, 3)], [(0, 0), (0, 1), (2, 3), (3, 3)]]
- A-core center blockers = 0 (phase A lifts free); B-core center blockers = 1
- A-core M-occupancy patterns: {'(2, 3, 2, 1, 3, 2)': 8}
- B-core M-occupancy patterns: {'(3, 1, 2, 1, 3, 1)': 8}

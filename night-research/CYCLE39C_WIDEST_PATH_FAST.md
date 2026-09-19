# Cycle 39c — widest A–B path on A0∪B0 (fast restricted)

- |A∪B| = 19; quads inside union = 59
- **restricted widest width = 11** (COMPLETE on union graph)
- bottleneck states: 1763
- uses (2,2) rate: 0.0
- uses center rate: 0.3040272263187748

| bottleneck occ | (2,2) | center |
|---|---|---|
| [0, 2, 2, 0, 1, 3, 2, 0, 0, 1] | False | True |
| [1, 1, 2, 0, 1, 3, 2, 0, 0, 1] | False | True |
| [1, 1, 2, 0, 1, 3, 2, 0, 0, 1] | False | True |
| [1, 2, 2, 0, 0, 3, 2, 0, 0, 1] | False | True |
| [1, 2, 2, 0, 1, 2, 2, 0, 0, 1] | False | True |
| [1, 2, 2, 0, 1, 2, 2, 0, 0, 1] | False | True |
| [1, 2, 1, 0, 1, 3, 2, 0, 0, 1] | False | True |
| [1, 2, 2, 0, 1, 3, 2, 0, 0, 0] | False | False |
| [1, 2, 2, 0, 1, 3, 1, 0, 0, 1] | False | True |
| [1, 2, 1, 0, 1, 3, 2, 0, 0, 1] | False | True |
| [1, 2, 2, 0, 1, 3, 1, 0, 0, 1] | False | True |
| [1, 2, 2, 0, 1, 2, 2, 0, 0, 1] | False | True |

Artifact: `cycle39c_widest_path_fast.json`

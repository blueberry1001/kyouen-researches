# Below-root memo instrumentation — mechanism analysis

### OVERALL (12 parents, visited=225422484)
- entry: lookups=225422484 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=858168427 hits=204133384 (WIN=98090122 LOSS=106043262) rate=23.79%
- recursion omission: cached=121051417 consumed=346473889 omission=34.94% (fromWIN=40340829 fromLOSS=80710588 recursive=225422472)
- ordering: nonterm=193606274 first-change=41677154 (21.53%) full-change=65256722 (33.71%)
- cached-LOSS first: actual=80710588 (41.69%) fallback=60736764 (31.37%)
- WIN shortcut: 80710588/153066536 solved-WIN = 52.73%

## Per-parent

| parent | outcome | visited | entry hit | prefetch hit | omission | firstΔ | fullΔ | shortcut |
|---|---|---|---|---|---|---|---|---|
| 0,11,35 | WIN | 85311102 | 0.00% | 23.16% | 33.93% | 20.89% | 33.00% | 51.94% |
| 11,38,44 | WIN | 17051435 | 0.00% | 23.78% | 34.95% | 21.54% | 33.79% | 52.85% |
| 11,78,87 | WIN | 9928498 | 0.00% | 23.21% | 34.29% | 20.79% | 32.31% | 51.77% |
| 12,24,68 | WIN | 11677827 | 0.00% | 24.18% | 35.62% | 21.91% | 34.05% | 53.25% |
| 12,32,55 | WIN | 7106990 | 0.00% | 23.85% | 35.06% | 21.42% | 33.37% | 52.73% |
| 13,52,57 | WIN | 11651703 | 0.00% | 24.68% | 36.35% | 22.61% | 35.33% | 54.23% |
| 14,64,74 | WIN | 4342654 | 0.00% | 24.95% | 36.75% | 22.70% | 35.10% | 54.10% |
| 23,44,45 | WIN | 7188933 | 0.00% | 24.75% | 36.35% | 22.58% | 35.22% | 54.10% |
| 3,47,63 | WIN | 5711578 | 0.00% | 24.01% | 35.30% | 21.68% | 33.72% | 52.83% |
| 3,53,84 | WIN | 7184954 | 0.00% | 23.97% | 35.27% | 21.55% | 33.40% | 52.68% |
| 4,24,26 | WIN | 51289701 | 0.00% | 24.25% | 35.64% | 22.03% | 34.31% | 53.31% |
| 4,42,54 | WIN | 6977109 | 0.00% | 24.35% | 35.74% | 22.07% | 34.43% | 53.40% |

## Per-depth (all parents)

| depth | miss | entry hit | prefetch hit | omission | firstΔ | fullΔ | shortcut |
|---|---|---|---|---|---|---|---|
| 3 | 12 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| 4 | 25 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| 5 | 1067 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| 6 | 4616 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| 7 | 90945 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| 8 | 673646 | 0.00% | 21.68% | 30.86% | 55.89% | 86.72% | 56.70% |
| 9 | 2814437 | 0.00% | 10.70% | 12.39% | 45.05% | 79.37% | 35.88% |
| 10 | 10424278 | 0.00% | 14.04% | 16.97% | 38.61% | 72.35% | 38.74% |
| 11 | 31110363 | 0.00% | 16.58% | 24.32% | 32.57% | 57.17% | 42.98% |
| 12 | 55037277 | 0.00% | 23.17% | 33.21% | 26.57% | 40.74% | 47.38% |
| 13 | 64391047 | 0.00% | 38.71% | 44.76% | 15.79% | 21.33% | 56.39% |
| 14 | 44869441 | 0.00% | 58.91% | 59.73% | 7.19% | 8.31% | 66.06% |
| 15 | 14268523 | 0.00% | 73.13% | 72.72% | 2.57% | 2.70% | 75.02% |
| 16 | 1671795 | 0.00% | 81.51% | 81.45% | 0.72% | 0.73% | 82.02% |
| 17 | 60906 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| 18 | 4066 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| 19 | 40 | 0.00% | n/a | n/a | n/a | n/a | n/a |

### parent 0,11,35
- entry: lookups=85311102 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=320514469 hits=74226099 (WIN=34966046 LOSS=39260053) rate=23.16%
- recursion omission: cached=43809860 consumed=129120961 omission=33.93% (fromWIN=13884784 fromLOSS=29925076 recursive=85311101)
- ordering: nonterm=72394827 first-change=15125302 (20.89%) full-change=23888616 (33.00%)
- cached-LOSS first: actual=29925076 (41.34%) fallback=22580469 (31.19%)
- WIN shortcut: 29925076/57618089 solved-WIN = 51.94%

### parent 11,38,44
- entry: lookups=17051435 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=65245025 hits=15513572 (WIN=7470492 LOSS=8043080) rate=23.78%
- recursion omission: cached=9162864 consumed=26214298 omission=34.95% (fromWIN=3039203 fromLOSS=6123661 recursive=17051434)
- ordering: nonterm=14646687 first-change=3155522 (21.54%) full-change=4948465 (33.79%)
- cached-LOSS first: actual=6123661 (41.81%) fallback=4602805 (31.43%)
- WIN shortcut: 6123661/11587548 solved-WIN = 52.85%

### parent 11,78,87
- entry: lookups=9928498 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=37318985 hits=8660423 (WIN=4123338 LOSS=4537085) rate=23.21%
- recursion omission: cached=5180698 consumed=15109195 omission=34.29% (fromWIN=1713138 fromLOSS=3467560 recursive=9928497)
- ordering: nonterm=8492740 first-change=1765366 (20.79%) full-change=2743782 (32.31%)
- cached-LOSS first: actual=3467560 (40.83%) fallback=2636631 (31.05%)
- WIN shortcut: 3467560/6698029 solved-WIN = 51.77%

### parent 12,24,68
- entry: lookups=11677827 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=44809416 hits=10835938 (WIN=5268901 LOSS=5567037) rate=24.18%
- recursion omission: cached=6459927 consumed=18137753 omission=35.62% (fromWIN=2222328 fromLOSS=4237599 recursive=11677826)
- ordering: nonterm=10121026 first-change=2217785 (21.91%) full-change=3445772 (34.05%)
- cached-LOSS first: actual=4237599 (41.87%) fallback=3191667 (31.54%)
- WIN shortcut: 4237599/7957713 solved-WIN = 53.25%

### parent 12,32,55
- entry: lookups=7106990 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=27063401 hits=6454144 (WIN=3114249 LOSS=3339895) rate=23.85%
- recursion omission: cached=3836274 consumed=10943263 omission=35.06% (fromWIN=1291838 fromLOSS=2544436 recursive=7106989)
- ordering: nonterm=6118637 first-change=1310414 (21.42%) full-change=2041539 (33.37%)
- cached-LOSS first: actual=2544436 (41.59%) fallback=1916560 (31.32%)
- WIN shortcut: 2544436/4825713 solved-WIN = 52.73%

### parent 13,52,57
- entry: lookups=11651703 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=45738916 hits=11289167 (WIN=5565169 LOSS=5723998) rate=24.68%
- recursion omission: cached=6654980 consumed=18306682 omission=36.35% (fromWIN=2320439 fromLOSS=4334541 recursive=11651702)
- ordering: nonterm=10151922 first-change=2295773 (22.61%) full-change=3586657 (35.33%)
- cached-LOSS first: actual=4334541 (42.70%) fallback=3227003 (31.79%)
- WIN shortcut: 4334541/7993122 solved-WIN = 54.23%

### parent 14,64,74
- entry: lookups=4342654 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=17104454 hits=4267210 (WIN=2142235 LOSS=2124975) rate=24.95%
- recursion omission: cached=2522752 consumed=6865405 omission=36.75% (fromWIN=912386 fromLOSS=1610366 recursive=4342653)
- ordering: nonterm=3799245 first-change=862545 (22.70%) full-change=1333636 (35.10%)
- cached-LOSS first: actual=1610366 (42.39%) fallback=1199448 (31.57%)
- WIN shortcut: 1610366/2976510 solved-WIN = 54.10%

### parent 23,44,45
- entry: lookups=7188933 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=28046955 hits=6942298 (WIN=3425898 LOSS=3516400) rate=24.75%
- recursion omission: cached=4105000 consumed=11293932 omission=36.35% (fromWIN=1439619 fromLOSS=2665381 recursive=7188932)
- ordering: nonterm=6262081 first-change=1413877 (22.58%) full-change=2205580 (35.22%)
- cached-LOSS first: actual=2665381 (42.56%) fallback=1985815 (31.71%)
- WIN shortcut: 2665381/4927157 solved-WIN = 54.10%

### parent 3,47,63
- entry: lookups=5711578 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=21807553 hits=5236726 (WIN=2542376 LOSS=2694350) rate=24.01%
- recursion omission: cached=3116032 consumed=8827609 omission=35.30% (fromWIN=1065734 fromLOSS=2050298 recursive=5711577)
- ordering: nonterm=4925507 first-change=1068060 (21.68%) full-change=1660660 (33.72%)
- cached-LOSS first: actual=2050298 (41.63%) fallback=1542761 (31.32%)
- WIN shortcut: 2050298/3880938 solved-WIN = 52.83%

### parent 3,53,84
- entry: lookups=7184954 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=27128280 hits=6502618 (WIN=3131572 LOSS=3371046) rate=23.97%
- recursion omission: cached=3915009 consumed=11099962 omission=35.27% (fromWIN=1345441 fromLOSS=2569568 recursive=7184953)
- ordering: nonterm=6209967 first-change=1338457 (21.55%) full-change=2074379 (33.40%)
- cached-LOSS first: actual=2569568 (41.38%) fallback=1938351 (31.21%)
- WIN shortcut: 2569568/4877261 solved-WIN = 52.68%

### parent 4,24,26
- entry: lookups=51289701 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=196535939 hits=47665077 (WIN=23142805 LOSS=24522272) rate=24.25%
- recursion omission: cached=28407237 consumed=79696937 omission=35.64% (fromWIN=9766830 fromLOSS=18640407 recursive=51289700)
- ordering: nonterm=44441315 first-change=9790717 (22.03%) full-change=15247121 (34.31%)
- cached-LOSS first: actual=18640407 (41.94%) fallback=14008937 (31.52%)
- WIN shortcut: 18640407/34965054 solved-WIN = 53.31%

### parent 4,42,54
- entry: lookups=6977109 hits=0 (WIN=0 LOSS=0) rate=0.00%
- prefetch: calls=26855034 hits=6540112 (WIN=3197041 LOSS=3343071) rate=24.35%
- recursion omission: cached=3880784 consumed=10857892 omission=35.74% (fromWIN=1339089 fromLOSS=2541695 recursive=6977108)
- ordering: nonterm=6042320 first-change=1333336 (22.07%) full-change=2080515 (34.43%)
- cached-LOSS first: actual=2541695 (42.06%) fallback=1906317 (31.55%)
- WIN shortcut: 2541695/4759402 solved-WIN = 53.40%


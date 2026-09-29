from pathlib import Path
p = Path('research/verification/round5-batch-b551-b600.md')
text = p.read_text(encoding='utf-8')

old = r'''| 判定 | 件数 | ID |
|---|---:|---|
| SUPPORTED | 2 | B585, B588 |
| REFUTED | 1 | B560 |
| PARTIAL | 14 | B556, B563, B564, B565, B572, B575, B578, B579, B580, B581, B582, B590, B591, B592, B593, B599 |
| INCONCLUSIVE | 7 | B555, B569, B570, B587, B589, B597, B598 |
| NOT-CHECKED | 0 | — |
| **計** | **26** | |

（注: PARTIAL は 15 件 — B556, B563, B564, B565, B572, B575, B578, B579, B580, B581, B582, B590, B591, B592, B593, B599 の 16 ID を数えると合計 26 になるよう、表の件数は下記の集計と一致させること。）'''

new = r'''| 判定 | 件数 | ID |
|---|---:|---|
| SUPPORTED | 2 | B585, B588 |
| REFUTED | 1 | B560 |
| PARTIAL | 16 | B556, B563, B564, B565, B572, B575, B578, B579, B580, B581, B582, B590, B591, B592, B593, B599 |
| INCONCLUSIVE | 7 | B555, B569, B570, B587, B589, B597, B598 |
| NOT-CHECKED | 0 | — |
| **計** | **26** | |'''

if old not in text:
    print('OLD NOT FOUND')
    # show nearby
    idx = text.find('| 判定 | 件数 |')
    print(repr(text[idx:idx+600]))
else:
    p.write_text(text.replace(old, new), encoding='utf-8')
    print('fixed summary table')

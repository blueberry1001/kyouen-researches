"""Collect previous round-2 individual notes for chunk8 IDs (helper, run once)."""
import re
import os

IDS = "B520 B521 B522 B523 B524 B527 B528 B529 B530 B536 B542 B546 B550 B555 B556 B560 B563 B564 B565 B569 B570 B572 B575 B578 B579 B580 B581 B582 B585 B587 B588 B589 B590 B593 B596 B597 B598 B599".split()
FILES = [
    'research/verification/round2-batch-b501.md',
    'research/verification/round2-batch-b531.md',
    'research/verification/round2-batch-b561.md',
    'research/verification/round2-batch-b591.md',
]
OUT = os.environ['COMMANDCODE_SCRATCHPAD'] + '/prev.md'

out = []
for f in FILES:
    t = open(f, encoding='utf-8').read()
    out.append('#' * 100)
    out.append('FILE %s len=%d' % (f, len(t)))
    heads = [(m.start(), m.group(0)) for m in re.finditer(r'(?m)^#+ .*$', t)]
    for idx, (st, h) in enumerate(heads):
        for i in IDS:
            if re.search(r'\b' + i + r'\b', h):
                en = heads[idx + 1][0] if idx + 1 < len(heads) else len(t)
                out.append(t[st:en])
                break
open(OUT, 'w', encoding='utf-8').write('\n'.join(out))
print('wrote', OUT, len('\n'.join(out)))

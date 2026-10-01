# -*- coding: utf-8 -*-
"""Report any character that is neither ASCII nor Japanese text/punctuation.

Catches the stray fragments (Korean/Arabic/Chinese filler words) and
non-breaking spaces that creep into these files.
"""
import io
import sys

def scan(path):
    bad = 0
    lines = io.open(path, encoding='utf-8').read().split('\n')
    for ln, line in enumerate(lines, 1):
        offenders = []
        for c in line:
            o = ord(c)
            if o < 128:
                continue
            if 0x3000 <= o <= 0x30FF:      # CJK punct + kana
                continue
            if 0x4E00 <= o <= 0x9FFF:      # kanji
                continue
            if 0xFF00 <= o <= 0xFF65:      # fullwidth
                continue
            if o in (0x2010, 0x2013, 0x2014, 0x2018, 0x2019,
                     0x201C, 0x201D, 0x2026, 0x00D7, 0x2192, 0x00A0):
                if o == 0x00A0:
                    offenders.append('NBSP')
                continue
            if o in (0x03A3,   # Sigma
                     0x2248,   # almost equal to
                     0x2212,   # minus sign
                     0x2208,   # element of
                     0x2203,   # there exists
                     0x2200,   # for all
                     0x00AC,   # logical not
                     0x2264, 0x2265, 0x2260, 0x2261):
                continue
            offenders.append('U+%04X(%s)' % (o, c))
        if offenders:
            bad += 1
            print('%s L%d %s' % (path.split('/')[-1], ln, ' '.join(offenders)))
            print('    %r' % line)
    return bad

if __name__ == '__main__':
    total = 0
    for p in sys.argv[1:]:
        total += scan(p)
    print('SCAN_CLEAN' if total == 0 else 'SCAN_FOUND %d' % total)
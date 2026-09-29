#!/usr/bin/env python3
# Compare [done] outcomes across eviction-stress memo powers.
# Usage: python3 dfpn_evict_compare.py 6  (or 7)
import re, sys
n = sys.argv[1]
base = "/mnt/d/ghq/build11/xcheck-logs/"
ref = {}
for pow in (24, 20, 16, 12):
    path = "%sevict%s-p%d.log" % (base, n, pow)
    try:
        lines = open(path).read().splitlines()
    except FileNotFoundError:
        print("missing", path)
        continue
    cur = {}
    for ln in lines:
        m = re.match(r"\[done\] \[(roots\{[^]]*\}|empty|v=\d+)\] (WIN|LOSS|TIMEOUT)", ln)
        if m:
            cur[m.group(1)] = m.group(2)
    print("memo=2^%d: %d roots" % (pow, len(cur)))
    if pow == 24:
        ref = cur
    else:
        bad = 0
        for k, v in ref.items():
            if k in cur and cur[k] != v:
                print("  MISMATCH %s ref=%s pow%d=%s" % (k, v, pow, cur[k]))
                bad += 1
        print("  mismatches vs memo=24: %d" % bad)

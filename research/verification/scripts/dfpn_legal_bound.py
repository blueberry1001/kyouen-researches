import io, sys, collections

# How many legal moves does a position with k stones have on 11x11?
# Upper bound: 121 - k occupied - completion-forbidden points.
# The exact frontier therefore cannot be reached for small k by
# raising --exact-legal past what the position actually has.
N = 11
V = N * N
print('n=11, V=%d' % V)
print()
print('  stones   max legal (121 - k)   frontier needs L >= that')
for k in range(0, 13):
    print('  %6d   %19d   %22d' % (k, V - k, V - k))
print()
print('So for a position with 5 stones the most legal moves it can have')
print('is 116, and for 6 stones 115. A threshold of 72 fires readily.')
print('To hand off an s7 position the threshold would have to be at')
print('least 114, by which point s5 and s6 positions are also being')
print('handed off, and at L>=114 the search spends its budget on the')
print('shallow layers instead.')
print()
# Cross-check against the recorded data: what legal counts actually appear?
for path in sys.argv[1:]:
    c = collections.Counter()
    mx = {}
    for line in io.open(path, encoding='utf-8', errors='replace'):
        if line.startswith('#') or not line.strip():
            continue
        f = line.split(',')
        if len(f) < 11:
            continue
        try:
            stones = int(f[2]); legal = int(f[5])
        except ValueError:
            continue
        c[stones] += 1
        mx[stones] = max(mx.get(stones, 0), legal)
    if not c:
        continue
    print('%s' % path.split('/')[-1])
    for s in sorted(c):
        print('  s%-3d n=%-4d max legal seen=%d' % (s, c[s], mx[s]))
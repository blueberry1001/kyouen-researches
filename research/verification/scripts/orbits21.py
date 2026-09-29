reps = [60, 0] + [y * 11 + x for x in range(6) for y in range(x + 1)
                if y * 11 + x not in (60, 0)]
print(len(reps))
print(reps)
for v in reps:
    print(v, (v % 11, v // 11))

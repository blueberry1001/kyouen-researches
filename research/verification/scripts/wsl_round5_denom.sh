#!/usr/bin/env bash
# Does the per-level lcm Lk fit in 64 bits?  (round5 tracked it as
# `unsigned long long`, which silently overflows for n>=6.)
python3 - <<'EOF'
import math
# counts are child counts (<= 64); Lk = lcm of the counts present at a level.
# We only know the REDUCED denominators from the references, so reconstruct the
# unreduced D_0 = prod_{j=0}^{K-1} Lk at least in lower bound form: the reduced
# D_0 divides the unreduced D_0, so bits(unreduced D_0) >= bits(reduced D_0).
ref = {
 4: [10,11,10,9,7,3,1,1],
 5: [19,34,33,32,26,18,10,3,1,1],
 6: [35,64,62,61,56,43,30,18,9,3,1,1],
 7: [54,112,110,109,100,84,66,49,32,19,9,4,1,1,1],
}
for n,ds in ref.items():
    mx = max(ds)
    print(f"n={n}: max reduced D digits = {mx} -> {mx*math.log2(10):.0f} bits;"
          f" needs ceil(bits/61) = {-(-mx*math.log2(10)//61):.0f} primes for exactness")
EOF

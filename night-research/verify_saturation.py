#!/usr/bin/env python3
"""Verify the Grundy-ceiling saturation on n=4,5,6 from Cycle 5 data.

For each board, find sigma = min{ k : max_g(k) == K - k } and check
that all deeper layers are also saturated (deficit stays 0).
Also print the full deficit profile D(k) = K - k - max_g(k).
"""

import json
import sys

K = {4: 7, 5: 9, 6: 11}
FILES = {
    4: "night-research/cycle5-grundy-n4.json",
    5: "night-research/cycle5-grundy-n5.json",
    6: "night-research/cycle5-grundy-n6-cap14.json",
}

out = {}
for n, path in FILES.items():
    j = json.load(open(path))
    layers = {int(k): v for k, v in j["layer_profiles"].items()}
    deficits = {}
    sigma = None
    for k in sorted(layers):
        ceiling = K[n] - k
        if ceiling < 0:
            continue
        d = ceiling - layers[k]["max_grundy"]
        deficits[k] = d
        if d == 0 and sigma is None:
            sigma = k
    # verify deficit non-increasing
    ks = sorted(deficits)
    non_incr = all(deficits[ks[i]] >= deficits[ks[i + 1]] for i in range(len(ks) - 1))
    post_sigma_zero = all(deficits[k] == 0 for k in ks if sigma is not None and k >= sigma)
    out[n] = {
        "K": K[n],
        "sigma": sigma,
        "deficits": {str(k): deficits[k] for k in ks},
        "deficit_nonincreasing": non_incr,
        "all_layers_after_sigma_saturated": post_sigma_zero,
    }
    print(f"n={n} K={K[n]} sigma={sigma} deficits={ {k: deficits[k] for k in ks} } "
          f"non_incr={non_incr} post_sigma_zero={post_sigma_zero}")

json.dump(out, open("night-research/cycle6-saturation-verify.json", "w"), indent=2)
print("wrote night-research/cycle6-saturation-verify.json")

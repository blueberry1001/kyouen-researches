#!/usr/bin/env python3
"""Scan DP binary files and produce p_rand summary JSON."""
import struct, sys, os, json, math

SPILL = "/home/yuubi/spill8"
N = 8
SCALE = 1 << 30

# Known level sizes from enumeration
LEVEL_SIZES = [1, 64, 2016, 41664, 620812, 6784816, 53020968, 281902248,
               956468384, 1921019144, 2092205428, 1112723392, 254143028,
               21240760, 535844, 3368]
K = len(LEVEL_SIZES) - 1
TOTAL_STATES = sum(LEVEL_SIZES)

def main():
    total_P = 0
    total_N = 0
    cnt_gt_1_2 = 0
    cnt_gt_2_3 = 0
    cnt_gt_3_4 = 0
    global_best = 0.0
    global_best_k = -1
    global_best_count = 0
    per_level = []

    for k in range(K + 1):
        path = f"{SPILL}/dp_{k}.bin"
        sz = os.path.getsize(path)
        expected = LEVEL_SIZES[k] * 5
        if sz != expected:
            print(f"WARNING: dp_{k}.bin size {sz} != expected {expected}")
            # Adjust level size to match file
            n_states = sz // 5
        else:
            n_states = LEVEL_SIZES[k]

        np_cnt = 0
        nn_cnt = 0
        best_p = 0
        best_count = 0

        with open(path, "rb") as f:
            # Read in chunks for large files
            CHUNK = 10_000_000  # 10M states per chunk
            for start in range(0, n_states, CHUNK):
                count = min(CHUNK, n_states - start)
                data = f.read(count * 5)
                for i in range(count):
                    g, p = struct.unpack_from("<bI", data, i * 5)
                    if g != 0:
                        nn_cnt += 1
                        continue
                    np_cnt += 1
                    # Threshold counts (exact u32 comparison)
                    if p > SCALE // 2:
                        cnt_gt_1_2 += 1
                    if p * 3 > SCALE * 2:
                        cnt_gt_2_3 += 1
                    if p * 4 > SCALE * 3:
                        cnt_gt_3_4 += 1
                    fv = p / SCALE
                    if fv > best_p:
                        best_p = fv
                        best_count = 1
                    elif fv == best_p and fv > 0:
                        best_count += 1

        total_P += np_cnt
        total_N += nn_cnt

        if best_p > global_best:
            global_best = best_p
            global_best_k = k
            global_best_count = best_count
        elif best_p == global_best and best_p > 0:
            global_best_count += best_count

        per_level.append({
            "k": k,
            "size": n_states,
            "n_P": np_cnt,
            "n_N": nn_cnt,
            "best_filter": best_p,
            "best_count": best_count,
        })
        print(f"  k={k:2d} size={n_states:12d} P={np_cnt:10d} N={nn_cnt:10d} best={best_p:.12f} x{best_count}")

    print(f"\n=== n={N} p_rand SUMMARY ===")
    print(f"  total P={total_P} N={total_N}")
    print(f"  P_max ≈ {global_best:.12f} at level {global_best_k} x{global_best_count}")
    print(f"  P>1/2: {cnt_gt_1_2}  P>2/3: {cnt_gt_2_3}  P>3/4: {cnt_gt_3_4}")

    result = {
        "n": N,
        "V": 64,
        "F": 14564,
        "method": "streaming DP: grundy(u8)+p_rand(u32 fixed-point) 5B/state, "
                  "child masks via mmap, parent streamed in chunks, legal_one via 3-subset table",
        "n_safe_subsets": TOTAL_STATES,
        "level_sizes": LEVEL_SIZES,
        "max_safe_size": K,
        "n_P": total_P,
        "n_N": total_N,
        "P_max_filter_value": f"{global_best:.12f}",
        "P_max_level": global_best_k,
        "P_max_n_attaining": global_best_count,
        "P_gt_1_2": cnt_gt_1_2,
        "P_gt_2_3": cnt_gt_2_3,
        "P_gt_3_4": cnt_gt_3_4,
        "levels": per_level,
    }

    outpath = sys.argv[1] if len(sys.argv) > 1 else "/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/round5_prand_n8.json"
    with open(outpath, "w") as f:
        json.dump(result, f, indent=2)
    print(f"wrote {outpath}")

if __name__ == "__main__":
    main()

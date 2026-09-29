# delta_K(5): find min deletion that drops K(5)=9
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from kyouen_core import board_square, board_square_minus

OUT = Path(__file__).resolve().parent.parent / "round5_b401_fu_delta_k.json"

def main():
    t0 = time.time()
    n = 5
    b = board_square(n)
    K0 = b.max_safe_size()
    print(f"n={n} V={b.V} F={len(b.quads)} K0={K0}", flush=True)

    V = b.V
    # size 1
    drops1 = []
    for i in range(V):
        b2 = board_square_minus(n, [(i % n, i // n)])
        K = b2.max_safe_size()
        if K < K0:
            drops1.append({"pt": i, "xy": (i % n, i // n), "K": K})
        if (i+1) % 5 == 0:
            print(f"  size1 {i+1}/{V}", flush=True)
    print(f"size1 drops: {len(drops1)}", flush=True)

    # size 2
    drops2 = []
    total2 = V*(V-1)//2
    done = 0
    for i in range(V):
        for j in range(i+1, V):
            b2 = board_square_minus(n, [(i % n, i // n), (j % n, j // n)])
            K = b2.max_safe_size()
            if K < K0:
                drops2.append({"pts": [i, j], "xys": [(i%n,i//n),(j%n,j//n)], "K": K})
            done += 1
            if done % 50 == 0:
                print(f"  size2 {done}/{total2}", flush=True)
    print(f"size2 drops: {len(drops2)}", flush=True)

    result = {
        "n": n, "K0": K0,
        "size1": {"tested": V, "n_drops": len(drops1), "drops": drops1},
        "size2": {"tested": total2, "n_drops": len(drops2), "drops": drops2[:50]},
    }
    if drops1:
        result["delta_K"] = 1
        result["witness"] = drops1[0]
    elif drops2:
        result["delta_K"] = 2
        result["witness"] = drops2[0]
    else:
        result["delta_K"] = ">=3"
    result["elapsed"] = time.time() - t0
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(f"delta_K({n}) = {result['delta_K']}  ({result['elapsed']:.1f}s)", flush=True)

if __name__ == "__main__":
    main()

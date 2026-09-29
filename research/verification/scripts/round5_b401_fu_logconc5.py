# B563: log-concavity with 1 stone fixed, n=5 sample
# B593/B597/B598: near-max analysis reflecting delta_K(7)=2
import sys, json, time, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from kyouen_core import Board, board_square

OUT = Path(__file__).resolve().parent.parent / "round5_b401_fu_logconc5.json"

def f_vector(board, S_mask, max_r=None):
    """f_S(r) = number of r-point sets that can be legally added to S."""
    V = board.V
    empty = board.full & ~S_mask
    # enumerate subsets of empty that are safe when added
    # for small V this is OK
    # We'll do DFS
    f = [0] * (V + 1)
    # candidates: points not in S
    cands = []
    e = empty
    while e:
        b = e & -e
        cands.append(b.bit_length() - 1)
        e ^= b
    # recursive enumeration of safe supersets
    def dfs(idx, occ, size):
        f[size] += 1
        for j in range(idx, len(cands)):
            bit = 1 << cands[j]
            new_occ = occ | bit
            if board.is_safe(new_occ):
                dfs(j + 1, new_occ, size + 1)
    dfs(0, S_mask, 0)  # counts S itself as f(0)=1
    return f

def is_logconcave(f):
    for r in range(1, len(f) - 1):
        if f[r] == 0:
            continue
        # f(r)^2 >= f(r-1)*f(r+1)
        if f[r] * f[r] < f[r-1] * f[r+1]:
            return False, r
    return True, None

def main():
    t0 = time.time()
    n = 5
    board = board_square(n)
    V = board.V
    print(f"n={n} V={V} F={len(board.quads)}", flush=True)

    # f_empty
    f0 = f_vector(board, 0)
    ok0, r0 = is_logconcave(f0)
    print(f"f_empty log-concave: {ok0} (viol at r={r0})", flush=True)
    print(f"f_empty = {f0[:20]}", flush=True)

    # Sample: 20 random points, compute f_p
    rng = random.Random(42)
    results = []
    n_viol = 0
    for trial in range(20):
        p = rng.randrange(V)
        S = 1 << p
        if not board.is_safe(S):
            continue
        f = f_vector(board, S)
        ok, rv = is_logconcave(f)
        results.append({"p": p, "xy": (p % n, p // n), "logconcave": ok, "viol_r": rv})
        if not ok:
            n_viol += 1
            print(f"  VIOLATION at p={p} ({p%n},{p//n}) r={rv}", flush=True)
        if (trial + 1) % 5 == 0:
            print(f"  sample {trial+1}/20", flush=True)
    print(f"n=5 single-stone: {20 - n_viol}/20 log-concave, violations={n_viol}", flush=True)

    # Also sample 2-stone fixed
    n_viol2 = 0
    results2 = []
    for trial in range(10):
        p = rng.randrange(V)
        q = rng.randrange(V)
        if p == q:
            continue
        S = (1 << p) | (1 << q)
        if not board.is_safe(S):
            continue
        f = f_vector(board, S)
        ok, rv = is_logconcave(f)
        results2.append({"pq": [p, q], "logconcave": ok, "viol_r": rv})
        if not ok:
            n_viol2 += 1
            print(f"  VIOLATION 2-stone at ({p},{q}) r={rv}", flush=True)
    print(f"n=5 two-stone: {10 - n_viol2}/10 log-concave, violations={n_viol2}", flush=True)

    result = {
        "n": n, "f_empty": f0[:30], "f_empty_logconcave": ok0,
        "single_stone": results, "single_violations": n_viol,
        "two_stone": results2, "two_violations": n_viol2,
    }
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(f"done in {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()

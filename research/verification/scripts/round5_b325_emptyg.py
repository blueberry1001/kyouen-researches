import sys
sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import board_square

for n in range(2, 6):
    B = board_square(n)
    g = B.solve_grundy()
    empty_g = g.get(0, "missing")
    print(f"n={n} empty_grundy={empty_g} n_states={len(g)} K={B.max_safe_size()}", flush=True)

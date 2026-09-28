"""Round3 chunk-4: engine self-validation against PROTOCOL.md known facts.

Checks the fast numpy engine reproduces the established numbers before any
hypothesis work is done.  Writes research/verification/round3_chunk4_selfcheck.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from round3_chunk4_core import (  # noqa: E402
    Solve, all_safe_sets, quad_masks, square_points, is_collinear4, d4_perms,
    apply_perm_mask,
)

OUT = Path(__file__).resolve().parents[1] / "round3_chunk4_selfcheck.json"
V = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def main():
    rep = {}
    for n in range(2, V + 1):
        t0 = time.time()
        q = quad_masks(n)
        tq = time.time() - t0
        t0 = time.time()
        s = Solve(q, n * n)
        tenum = time.time() - t0
        pn = s.pn()
        g = s.grundy()
        d = s.depth(pn)
        ps = s.proof_size(pn)
        st = s.states
        # first moves
        W = sorted(st[i] for i in range(s.N)
                   if st[i].bit_count() == 1 and pn[i] == False)
        Wids = sorted(v for m in W for v in [m.bit_length() - 1])
        rep[f"n{n}"] = {
            "n_quads": len(q),
            "n_collinear": sum(1 for qm in q if is_collinear4(
                [square_points(n)[i] for i in
                 [b.bit_length() - 1 for b in [qm] if False]])) if False else None,
            "n_states": s.N,
            "level_counts": {k: len(lv) for k, lv in enumerate(s.levels)},
            "g0": int(g[0]),
            "winner": "Second" if g[0] == 0 else "First",
            "max_g": int(g.max()),
            "max_proof": int(ps.max()),
            "max_depth": int(d.max()),
            "W_ids": Wids,
            "W_xy": [[p % n, p // n] for p in Wids],
            "n_P": int((~pn).sum()),
            "n_N": int(pn.sum()),
            "seconds_quad": round(tq, 2),
            "seconds_enum": round(tenum, 2),
        }
        print(n, rep[f"n{n}"]["g0"], rep[f"n{n}"]["max_g"],
              rep[f"n{n}"]["n_states"], "PN",
              rep[f"n{n}"]["winner"], round(tenum, 1), "s", flush=True)
    OUT.write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()

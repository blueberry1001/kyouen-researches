#!/usr/bin/env python3
"""9×9 の初手14クラス (D4軌道) の勝敗を exact solver で分類する。

kyouen_solver_9 <first_id> <memo_power> を6並列で実行し、結果を
scratch/first-moves-9x9.csv に保存する (再開可能)。

結果の解釈:
  "first move (a,b) leaves LOSS for player to move" -> 先手必勝
  "first move (a,b) leaves WIN for player to move"  -> 先手必敗
"""
import csv
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOLVER = ROOT / "cpp" / "solvers" / "kyouen_solver_9.exe"
OUT = ROOT / "scratch" / "first-moves-9x9.csv"
MEMO_POWER = 28
PARALLEL = 6

# (a,b) 代表クラス (0<=a<=b<=4, 中央(4,4)は既知なので除く)
CLASSES = [
    (0, 0), (0, 1), (0, 2), (0, 3), (0, 4),
    (1, 1), (1, 2), (1, 3), (1, 4),
    (2, 2), (2, 3), (2, 4),
    (3, 3), (3, 4),
]


def first_id(a: int, b: int) -> int:
    return b * 9 + a


def load_done() -> set[tuple[int, int]]:
    done = set()
    if OUT.exists():
        with open(OUT, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                done.add((int(row["a"]), int(row["b"])))
    return done


def run_one(a: int, b: int) -> dict:
    fid = first_id(a, b)
    p = subprocess.run(
        [str(SOLVER), str(fid), str(MEMO_POWER)],
        capture_output=True, text=True, timeout=900,
    )
    out = p.stdout
    verdict = None
    for line in out.splitlines():
        if line.startswith("first move"):
            if "leaves LOSS" in line:
                verdict = "FIRST_WIN"   # 後手が負ける
            elif "leaves WIN" in line:
                verdict = "FIRST_LOSS"  # 後手が勝つ
    stats = {}
    for line in out.splitlines():
        if "visited=" in line:
            for token in line.split():
                if "=" in token:
                    k, v = token.split("=", 1)
                    stats[k] = v
    return {
        "a": a, "b": b, "first_id": fid,
        "verdict": verdict, "rc": p.returncode,
        **stats,
    }


def main() -> None:
    done = load_done()
    todo = [c for c in CLASSES if c not in done]
    print(f"完了済み {len(done)}/{len(CLASSES)}、残り {len(todo)}")
    if not todo:
        return
    newfile = not OUT.exists()
    with open(OUT, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if newfile:
            w.writerow(["a", "b", "first_id", "verdict", "rc",
                        "visited", "memo", "maxdepth", "seconds"])
        with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
            futs = {ex.submit(run_one, a, b): (a, b) for a, b in todo}
            for fut in as_completed(futs):
                a, b = futs[fut]
                try:
                    r = fut.result()
                except Exception as e:
                    r = {"a": a, "b": b, "first_id": first_id(a, b),
                         "verdict": f"ERROR:{e}", "rc": -1}
                w.writerow([r["a"], r["b"], r["first_id"], r["verdict"], r["rc"],
                            r.get("visited", ""), r.get("memo", ""),
                            r.get("maxdepth", ""), r.get("seconds", "")])
                f.flush()
                print(f"  ({r['a']},{r['b']}) id={r['first_id']} -> {r['verdict']} "
                      f"visited={r.get('visited','')} maxdepth={r.get('maxdepth','')} "
                      f"seconds={r.get('seconds','')}", flush=True)


if __name__ == "__main__":
    main()
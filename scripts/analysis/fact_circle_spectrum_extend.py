#!/usr/bin/env python3
"""n=6,7,11 の円スペクトルでサイズ数の経験則を検証する。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from fact_circle_spectrum_compare import spectrum  # noqa: E402

OUT = ROOT / "research" / "exploration"


def main() -> None:
    rows = []
    for n in (6, 7, 11):
        print(f"n={n}...", flush=True)
        r = spectrum(n)
        print(r, flush=True)
        rows.append(r)
    path = OUT / "fact_circle_spectrum_n6_n7_n11.json"
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()

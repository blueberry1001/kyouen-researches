#!/usr/bin/env python3
"""Reproduce the small-board/abstract classification; optionally verify all 8x8 moves."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
DATA = HERE.parent
PREFIX = "game_structure_20261003"


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k not in ("source_sha256", "sha256")}
    if isinstance(value, list):
        return list(map(stable, value))
    return value


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-eight", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="kyouen-game-check-") as tmp:
        work = Path(tmp)
        subprocess.run([sys.executable, str(HERE / (PREFIX + "_reproduce.py")),
                        "--work-dir", str(work / "small"), "--output-dir", str(work / "results")], check=True)
        for suffix in ("boards", "complexes", "residuals"):
            name = PREFIX + "_" + suffix + ".json"
            assert stable(read(work / "results" / name)) == stable(read(DATA / name)), name
        if args.full_eight:
            output = work / "eight.json"
            subprocess.run([sys.executable, str(HERE / (PREFIX + "_eight_reproduce.py")),
                            "--work-dir", str(work / "eight"), "--output", str(output)], check=True)
            observed = read(output)
            expected = read(DATA / (PREFIX + "_eight.json"))
            assert observed["independent_check"] == expected["independent_check"]
        else:
            # Keep both independently implemented large-board programs buildable
            # in ordinary CI; full proof generation/checking is a manual option.
            for suffix in ("_eight", "_eight_check"):
                subprocess.run(["g++", "-O3", "-std=c++17", "-Wall", "-Wextra",
                                str(HERE / (PREFIX + suffix + ".cpp")), "-o", str(work / suffix)], check=True)
        print("All requested game-structure certificates reproduced")


if __name__ == "__main__":
    main()

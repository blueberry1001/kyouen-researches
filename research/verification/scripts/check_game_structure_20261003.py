#!/usr/bin/env python3
"""Check game research, including 9x9 primitives but never its heavy root search."""
import argparse
import hashlib
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


def check_nine(work):
    """Exercise 81-bit geometry/endgames without allocating the root-search memo."""
    binary = work / "nine"
    subprocess.run(["g++", "-O3", "-std=c++17", "-Wall", "-Wextra",
                    str(HERE / (PREFIX + "_nine.cpp")), "-o", str(binary)], check=True)
    probes, checked = work / "nine-probes.jsonl", work / "nine-checked.json"
    with probes.open("w") as out:
        subprocess.run([str(binary), "--probe", "1000"], stdout=out, check=True)
    with checked.open("w") as out:
        subprocess.run([sys.executable, str(HERE / (PREFIX + "_nine_validate.py")),
                        str(probes)], stdout=out, check=True)
    observed = read(checked)
    probe_hash = hashlib.sha256(probes.read_bytes()).hexdigest()
    for opening in ("center", "corner"):
        expected = read(DATA / (PREFIX + "_nine_" + opening + ".json"))
        assert expected["root_status"] == "UNKNOWN"
        assert expected["search"]["winner"] == "UNKNOWN"
        assert expected["search"]["complete"] is False
        assert observed == expected["primitive_validation"], opening
        assert probe_hash == expected["probe_sha256"], opening
        for name, expected_hash in expected["source_sha256"].items():
            assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected_hash, name
    print("9x9 primitives verified; the empty-board winner remains UNKNOWN", flush=True)


def main():
    if not __debug__:
        raise SystemExit("Run without -O: these checks require assertions.")
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--full-eight", action="store_true")
    mode.add_argument("--nine-only", action="store_true",
                      help="only run the light 9x9 primitive checks; no root search")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="kyouen-game-check-") as tmp:
        work = Path(tmp)
        check_nine(work)
        if args.nine_only:
            return
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
        print("All requested game-structure checks passed")


if __name__ == "__main__":
    main()

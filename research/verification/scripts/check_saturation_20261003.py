#!/usr/bin/env python3
"""Check saturation witnesses, direction bounds and completed finite exclusions."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k != "seconds"}
    if isinstance(value, list):
        return list(map(stable, value))
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-exclusion", action="store_true",
                        help="Also repeat the 1.5 billion-node seven-stone exclusion")
    args = parser.parse_args()
    certificate = HERE / "saturation_20261003_verified.json"
    saved = json.loads(certificate.read_text())
    subprocess.run([sys.executable, str(HERE / "saturation_20261003_verify.py")], check=True)
    assert json.loads(certificate.read_text()) == saved
    expected = json.loads((HERE / "saturation_20261003_exact_results.json").read_text())["results"]
    with tempfile.TemporaryDirectory(prefix="kyouen-saturation-check-") as tmp:
        binary = str(Path(tmp) / "exact")
        subprocess.run(["g++", "-O3", "-std=c++17", str(HERE / "saturation_20261003_exact.cpp"),
                        "-o", binary], check=True)
        for case in expected:
            if case["k"] == 7 and not args.full_exclusion:
                continue
            observed = json.loads(subprocess.check_output([binary, "11", str(case["k"])], text=True))
            assert stable(observed) == stable(case)
            print(f"11x11, {case['k']} stones: full exclusion reproduced", flush=True)
    print("Saturation certificates and direction bounds verified")


if __name__ == "__main__":
    main()

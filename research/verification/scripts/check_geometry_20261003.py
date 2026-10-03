#!/usr/bin/env python3
"""Reproduce strip/radius certificates and independently check the circle census."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPTS = Path(__file__).resolve().parent
DATA = SCRIPTS.parent


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-census", action="store_true",
                        help="Repeat all 4.4 billion anchor pairs through side 112")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="kyouen-geometry-check-") as tmp:
        work = Path(tmp)
        for stem in ("geometry_20261003_strip", "geometry_20261003_scale",
                     "theory_audit_20261003_q6", "theory_audit_20261003_checks"):
            script = stem.replace("_checks", "_verify")
            out = work / (stem + ".json")
            command = [sys.executable, str(SCRIPTS / (script + ".py")), "--output", str(out)]
            if stem.endswith("_checks"):
                command += ["--census", str(DATA / "theory_audit_20261003_circles.json")]
            subprocess.run(command, check=True)
            assert read(out) == read(DATA / out.name), stem
        census = read(DATA / "theory_audit_20261003_circles.json")
        previous = read(DATA / "theory_audit_20261003_circles_100.json")
        for old, new in zip(previous["results"], census["results"]):
            assert old["n"] == new["n"]
            for key in ("all", "nonhalf"):
                assert old[key]["count"] == new[key]["count"]
        binary = work / "circle-census"
        subprocess.run(["g++", "-O3", "-std=c++20", "-Wall", "-Wextra",
                        str(SCRIPTS / "theory_audit_20261003_circles.cpp"), "-o", str(binary)], check=True)
        side = 112 if args.full_census else 8
        observed = json.loads(subprocess.check_output([str(binary), str(side)], text=True))
        for small, saved in zip(observed["results"], census["results"]):
            assert small["n"] == saved["n"]
            for key in ("all", "nonhalf"):
                assert small[key]["count"] == saved[key]["count"]
        if args.full_census:
            assert observed == census
        print("All geometry certificates match; all-center census checked through", side)


if __name__ == "__main__":
    main()

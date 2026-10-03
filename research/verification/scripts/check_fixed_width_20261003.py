#!/usr/bin/env python3
"""Recompute the fixed-width discoveries and compare exact saved results.

Default: independent determinant audits, all Grundy values for 3xm q5 (m4..11),
the q4 exceptional-complex solution (m7..23), four-row threshold proofs,
reflection strategy and general packing inequalities. --full-exclusion also
repeats every q5 (m12..40) and q4 (m24..68) support exclusion.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "research/verification/scripts"
RESULTS = ROOT / "research/verification"


def run(*command):
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout


def stable(value):
    if isinstance(value, dict):
        return {key: stable(item) for key, item in value.items()
                if key not in ("seconds", "census_seconds")}
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


def load(name):
    return json.loads((RESULTS / name).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-exclusion", action="store_true")
    args = parser.parse_args()
    for stem in ("curve_packing_fixed_width", "q48_exact_threshold", "q48_nearby_q7_threshold",
                 "q48_pell_family", "q48_nearby_q6_bounds", "q48_odd_q_reflection"):
        expected = load(stem + ".json")
        observed = json.loads(run(sys.executable, str(SCRIPTS / (stem + ".py"))))
        assert stable(observed) == stable(expected), stem
        print(stem + ": exact result reproduced", flush=True)
    with tempfile.TemporaryDirectory(prefix="kyouen-fixed-width-") as directory:
        for stem in ("q35_independent_audit", "q35_full_grundy"):
            binary = str(Path(directory) / stem)
            run("g++", "-O3", "-std=c++17", str(SCRIPTS / (stem + ".cpp")), "-o", binary)
            if stem.endswith("audit"):
                observed = json.loads(run(binary))
                assert observed == load("q35_audit.json"), stem
            else:
                observed = [json.loads(line) for line in run(binary, "4", "11").splitlines()]
                expected = load("q35_full_grundy.json")["cases"]
                assert stable(observed) == stable(expected), stem
                # Independent generic subset DP vs optimized row-state DP.
                for direct, row in zip(load("q35_audit.json")["independent_full_grundy"], observed):
                    for key in ("safe_states", "empty_grundy", "max_grundy", "safe_by_size", "grundy_histogram"):
                        assert direct[key] == row[key], (direct["m"], key)
                    terminal = [row["terminal_counts"].get(str(k), 0) for k in range(13)]
                    assert direct["terminal_by_size"] == terminal
            print(stem + ": exact result reproduced", flush=True)
        programs = {}
        for stem in ("q34_independent_audit", "q34_exceptional_grundy", "q34_exceptional_audit"):
            binary = str(Path(directory) / stem)
            run("g++", "-O3", "-std=c++17", str(SCRIPTS / (stem + ".cpp")), "-o", binary)
            programs[stem] = binary
        assert json.loads(run(programs["q34_independent_audit"])) == load("q34_audit.json")
        observed = [json.loads(line) for line in run(programs["q34_exceptional_grundy"], "7", "23").splitlines()]
        assert stable(observed) == stable(load("q34_exceptional_grundy.json")["cases"])
        prefix = str(Path(directory) / "q34_certificate")
        for length in (7, 23):
            run(programs["q34_exceptional_grundy"], str(length), str(length), prefix)
        checked = json.loads(run(programs["q34_exceptional_audit"], prefix + "_7.txt", prefix + "_23.txt"))
        assert checked == load("q34_exceptional_audit.json")
        print("q34: all exceptional-complex values and independent audits reproduced", flush=True)
        for stem in ("q36_full_grundy", "q36_independent_audit"):
            binary = str(Path(directory) / stem)
            run("g++", "-O3", "-std=c++17", str(SCRIPTS / (stem + ".cpp")), "-o", binary)
            programs[stem] = binary
        observed = [json.loads(line) for line in run(programs["q36_full_grundy"], "1", "9").splitlines()]
        assert stable(observed) == stable(load("q36_full_grundy.json")["cases"])
        direct = json.loads(run(programs["q36_independent_audit"]))
        assert direct == load("q36_audit.json")
        for full, row in zip(direct["direct_full_grundy"], observed):
            for key in ("safe_states", "empty_grundy", "max_grundy", "safe_by_size", "grundy_histogram"):
                assert full[key] == row[key], (full["m"], key)
            assert full["terminal_by_size"] == [row["terminal_counts"].get(str(k), 0) for k in range(16)]
        print("q36: all row-state and independent subset Grundy values reproduced", flush=True)
        if args.full_exclusion:
            binary = str(Path(directory) / "q35_support")
            run("g++", "-O3", "-std=c++17", str(SCRIPTS / "q35_support_exclusion.cpp"), "-o", binary)
            observed = [json.loads(line) for line in run(binary, "12", "40").splitlines()]
            assert stable(observed) == stable(load("q35_exact_threshold.json")["cases"])
            print("q35_support_exclusion: all lengths 12..40 reproduced", flush=True)
            binary = str(Path(directory) / "q34_support")
            run("g++", "-O3", "-std=c++17", str(SCRIPTS / "q34_support_exclusion.cpp"), "-o", binary)
            observed = [json.loads(line) for line in run(binary, "24", "68").splitlines()]
            assert stable(observed) == stable(load("q34_exact_threshold.json")["cases"])
            print("q34_support_exclusion: all lengths 24..68 reproduced", flush=True)


if __name__ == "__main__":
    main()

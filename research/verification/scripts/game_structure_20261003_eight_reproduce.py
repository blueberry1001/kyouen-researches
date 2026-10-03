#!/usr/bin/env python3
"""Reproduce and independently verify the 8x8 misere classification.

The search uses about 1.3 GB and can take several minutes. A node-cap stop is
reported as UNKNOWN, never as a win/loss certificate. Raw proof bytes remain
in --work-dir; --output receives only compact evidence and hashes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

PREFIX = "game_structure_20261003_eight"
SOURCE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root-only", action="store_true")
    parser.add_argument("--node-cap", type=int, default=145000000)
    parser.add_argument("--verify-existing", action="store_true",
                        help="verify existing proof.bin and search.json in --work-dir")
    args = parser.parse_args()
    work = args.work_dir or Path(tempfile.mkdtemp(prefix="kyouen-eight-misere-"))
    work.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    search, check = work / "search", work / "check"
    for suffix, executable in (("", search), ("_check", check)):
        subprocess.run(["g++", "-O3", "-std=c++17", "-Wall", "-Wextra",
                        str(SOURCE / (PREFIX + suffix + ".cpp")), "-o", str(executable)], check=True)
    certificate, search_json = work / "proof.bin", work / "search.json"
    if not args.verify_existing:
        with search_json.open("w") as output:
            result = subprocess.run([str(search), str(certificate), str(args.node_cap),
                                     "27", "root" if args.root_only else "all"], stdout=output)
        if result.returncode:
            raise SystemExit("Search incomplete: UNKNOWN. No verified outcome was written.")
    result = json.loads(search_json.read_text())
    assert result["complete"] is True
    if not args.root_only:
        assert result["all_first_moves_classified"] is True
    with (work / "checked.json").open("w") as output:
        subprocess.run([str(check), "8", "pn", str(certificate)], stdout=output, check=True)
    checked = json.loads((work / "checked.json").read_text())
    assert checked["verified"] is True
    assert checked["empty_misere"] == result["misere_first_wins"]
    assert checked["records"] == result["proof_size"]
    assert checked["first_move_child_outcomes"] == result["first_move_child_outcomes"]
    assert checked["all_first_moves_classified"] == result["all_first_moves_classified"]
    sources = [SOURCE / (PREFIX + suffix) for suffix in (".cpp", "_check.cpp", "_reproduce.py")]
    evidence = dict(search=result, independent_check=checked,
                    certificate=dict(bytes=certificate.stat().st_size,
                                     sha256=hashlib.sha256(certificate.read_bytes()).hexdigest()),
                    source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Verified; raw certificate remains in {certificate}")


if __name__ == "__main__":
    main()

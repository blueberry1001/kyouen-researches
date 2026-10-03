#!/usr/bin/env python3
"""Recompute the fixed-width discoveries and compare exact saved results.

Default: independent determinant audits, the three-row Grundy solutions,
four-row threshold certificates and boundary nimbers, both q6 pair-graph
implementations, the star refinement, and the q6 deficient-row search at m16.
--full-exclusion also repeats every q5 (m12..40), q4 (m24..68), and four-row
q6 (m16..35, both target-row orbits) exclusion.
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


def run(*command, expected_returncode=0):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="", flush=True)
    if result.returncode != expected_returncode:
        if result.stdout:
            print(result.stdout, file=sys.stderr, end="", flush=True)
        is_unknown = result.returncode == 4 and Path(command[0]).name == "q48_q6_exclusion"
        detail = " (UNKNOWN is not an exclusion certificate)" if is_unknown else ""
        raise RuntimeError(f"{command[0]} exited {result.returncode}, expected "
                           f"{expected_returncode}{detail}")
    return result.stdout


def compile_program(directory, stem):
    binary = str(Path(directory) / stem)
    # Fixed flags keep warnings visible and C++ assertions enabled.  Do not
    # inherit CXXFLAGS, which could silently introduce -DNDEBUG.
    run("g++", "-O3", "-std=c++17", "-Wall", "-Wextra", "-UNDEBUG",
        str(SCRIPTS / (stem + ".cpp")), "-o", binary)
    return binary


def json_lines(output):
    return [json.loads(line) for line in output.splitlines() if line.strip()]


def stable(value):
    if isinstance(value, dict):
        return {key: stable(item) for key, item in value.items()
                if key not in ("seconds", "census_seconds")}
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


def load(name):
    return json.loads((RESULTS / name).read_text())


def check_q46(directory):
    primary = compile_program(directory, "q46_pair_upper_bound")
    observed = json.loads(run(primary))
    assert observed == load("q46_pair_upper_bound.json")

    independent = compile_program(directory, "q46_pair_independent_bound")
    expected = load("q46_pair_independent_bound.json")
    rows = json_lines(run(independent))
    assert rows == expected["rows"]
    assert expected["status"] == "passed"
    assert expected["horizontal_diameter_bound"] == observed["maximum_horizontal_span"] == 67
    assert expected["shape_order_target_then_external_rows"] == [
        [row["target_row"], *row["exterior_rows"]] for row in observed["shapes"]]
    assert sum(row["normalized_B_sets"] for row in rows) == expected["total_normalized_B_sets_checked"]
    bounds = [row["universal_upper_bound"] for row in rows]
    assert bounds == [
        row["circle_count_upper_bound"] for row in observed["shapes"]]
    assert expected["three_row_blocker_upper_bound_outer_target"] == sum(bounds[:3]) == 19
    assert expected["three_row_blocker_upper_bound_inner_target"] == bounds[3] + bounds[4] + bounds[0] == 19
    small = json_lines(run(independent, "35", "0"))
    assert small == [expected["small_diameter_refinement"]]
    small_primary = json.loads(run(primary, "35", "0"))["shapes"]
    assert len(small_primary) == 1
    assert small_primary[0]["circle_count_upper_bound"] == small[0]["universal_upper_bound"] == 5
    assert small_primary[0]["profile_count"] == small[0]["profiles"] == 16

    star = compile_program(directory, "q46_pair_independent_star")
    records = json_lines(run(star))
    assert all(row["type"] in ("candidate", "shape_summary") for row in records)
    candidates = [row for row in records if row["type"] == "candidate"]
    summaries = [row for row in records if row["type"] == "shape_summary"]
    expected_star = load("q46_pair_independent_star.json")
    assert candidates == expected_star["all_seven_edge_candidates"]
    assert summaries == expected_star["shape_summaries"]
    assert expected_star["status"] == "passed" and expected_star["D"] == 67
    assert sum(row["normalized_B_sets"] for row in summaries) == expected_star["total_B_sets_checked"]
    assert sum(row["seven_weight_five_vertex_candidates"] for row in summaries) == len(candidates) == 14
    assert all(row["star_candidates"] == 0 and
               row["blocker_upper_bound_with_four_target_stones"] == 6 for row in summaries)
    assert expected_star["three_row_blocker_upper_bound"] == 3 * 6 == 18
    assert expected_star["resulting_q6_tail_start_using_local_four_row_profiles"] == 18 + 12 + 4 + 1
    assert expected["three_row_blocker_upper_bound_at_D_35_after_target_star_refinement"] == 5 + 6 + 6
    assert expected["resulting_tail_start_after_target_star_refinement"] == 17 + 12 + 4 + 1
    for stem in ("q46_pair_counterexamples", "q46_pair_star_audit"):
        observed = json.loads(run(sys.executable, str(SCRIPTS / (stem + ".py"))))
        assert observed == load(stem + ".json"), stem
    print("q46: both pair-graph bounds, small-span refinement, and all star audits reproduced", flush=True)


def check_q6_exclusion(directory, full):
    audit = compile_program(directory, "geometry_q6_exclusion_review")
    assert json.loads(run(audit)) == load("geometry_q6_exclusion_review.json")
    binary = compile_program(directory, "q48_q6_exclusion")
    expected = load("q48_q6_finite_exclusions.json")
    assert expected["complete"] is True and expected["verified_interval"] == [16, 35]
    assert expected["required_cases"] == len(expected["cases"]) == 40
    assert [(row["m"], row["target_row"]) for row in expected["cases"]] == [
        (m, target) for m in range(16, 36) for target in (0, 1)]
    assert all(row["unknown_subsets"] == 0 and row["found_witness"] is False
               for row in expected["cases"])

    # Exercise the failure contract with an intentionally inadequate cap.
    # Exit 4 and a positive UNKNOWN count must never be accepted as a proof.
    incomplete = json_lines(run(binary, "16", "16", "1", expected_returncode=4))
    assert len(incomplete) == 2 and any(row["unknown_subsets"] > 0 for row in incomplete)
    assert all(row["found_witness"] is False for row in incomplete)

    last = 35 if full else 16
    observed = json_lines(run(binary, "16", str(last), str(expected["per_subset_node_cap"])))
    assert all(row["unknown_subsets"] == 0 and row["found_witness"] is False for row in observed)
    # These counters vary with safe search-order improvements and are omitted
    # from the saved certificate.  Keep every mathematical/completion field.
    performance_fields = {"seconds", "visited_states", "disjoint_support_prunes"}
    semantic = [{key: value for key, value in row.items() if key not in performance_fields}
                for row in observed]
    selected = [row for row in expected["cases"] if row["m"] <= last]
    assert semantic == selected, "q48_q6_exclusion semantic certificate"
    print(f"q48 q6: independent geometry audit, UNKNOWN exit 4, and {len(selected)} "
          f"complete exclusion cases (m16..{last}) reproduced", flush=True)


def main():
    if not __debug__:
        raise SystemExit("Assertions must remain enabled; do not run with python -O/PYTHONOPTIMIZE.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-exclusion", action="store_true")
    args = parser.parse_args()
    for stem in ("curve_packing_fixed_width", "q48_exact_threshold", "q48_nearby_q7_threshold",
                 "q48_pell_family", "q48_nearby_q6_bounds", "q48_odd_q_reflection",
                 "q48_boundary_nimbers"):
        expected = load(stem + ".json")
        observed = json.loads(run(sys.executable, str(SCRIPTS / (stem + ".py"))))
        assert stable(observed) == stable(expected), stem
        print(stem + ": exact result reproduced", flush=True)
    with tempfile.TemporaryDirectory(prefix="kyouen-fixed-width-") as directory:
        for stem in ("q35_independent_audit", "q35_full_grundy"):
            binary = compile_program(directory, stem)
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
            binary = compile_program(directory, stem)
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
            binary = compile_program(directory, stem)
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
        check_q46(directory)
        check_q6_exclusion(directory, args.full_exclusion)
        if args.full_exclusion:
            binary = compile_program(directory, "q35_support_exclusion")
            observed = [json.loads(line) for line in run(binary, "12", "40").splitlines()]
            assert stable(observed) == stable(load("q35_exact_threshold.json")["cases"])
            print("q35_support_exclusion: all lengths 12..40 reproduced", flush=True)
            binary = compile_program(directory, "q34_support_exclusion")
            observed = [json.loads(line) for line in run(binary, "24", "68").splitlines()]
            assert stable(observed) == stable(load("q34_exact_threshold.json")["cases"])
            print("q34_support_exclusion: all lengths 24..68 reproduced", flush=True)


if __name__ == "__main__":
    main()

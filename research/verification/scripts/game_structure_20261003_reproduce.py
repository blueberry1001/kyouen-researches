#!/usr/bin/env python3
"""Reproduce the normal/misere census and sharp six-vertex obstruction census.

Requires Python 3.10+ and g++ (C++17). Raw certificates stay in --work-dir;
only compact JSON evidence is written to --output-dir. Approximate peak memory
is below 1 GB. No depth truncation or heuristic verdict is used.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from functools import cache
import hashlib
from itertools import combinations, permutations
import json
from pathlib import Path
import struct
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parent
PREFIX = "game_structure_20261003"
PERMS = list(permutations(range(6)))
TRANSFORMS = [tuple(sum(1 << perm[i] for i in range(6) if s >> i & 1)
                    for s in range(64)) for perm in PERMS]


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def execute(command, output):
    print(" ".join(map(str, command)), flush=True)
    with output.open("w") as stream:
        subprocess.run(list(map(str, command)), stdout=stream, check=True)
    return json.loads(output.read_text())


def canonical(safe):
    subsets = [s for s in range(64) if safe >> s & 1]
    return min(sum(1 << table[s] for s in subsets) for table in TRANSFORMS)


def edges_of(safe):
    return [e for e in range(64) if not safe >> e & 1 and
            all(safe >> (e ^ (1 << p)) & 1 for p in range(6) if e >> p & 1)]


def solve_complex(safe, vertices=6):
    @cache
    def solve(s):
        options = [solve(s | (1 << p)) for p in range(vertices)
                   if not s >> p & 1 and safe >> (s | (1 << p)) & 1]
        if not options:
            return 0, 1
        result = []
        for dimension in range(2):
            seen = {o[dimension] for o in options}
            g = 0
            while g in seen:
                g += 1
            result.append(g)
        return tuple(result)
    return solve


def graph_name(edges):
    adjacency = [set() for _ in range(6)]
    for edge in edges:
        a, b = [p for p in range(6) if edge >> p & 1]
        adjacency[a].add(b)
        adjacency[b].add(a)
    assert max(map(len, adjacency)) <= 2
    components, remaining = [], set(range(6))
    while remaining:
        todo = [min(remaining)]
        component = set(todo)
        while todo:
            for p in adjacency[todo.pop()]:
                if p not in component:
                    component.add(p)
                    todo.append(p)
        remaining -= component
        kind = "C" if all(len(adjacency[p]) == 2 for p in component) else "P"
        components.append(f"{kind}{len(component)}")
    return " + ".join(sorted(components))


def verify_and_describe_classes(result):
    # Independent Python orbit exhaustion: pairwise disjoint orbits, canonical
    # representatives, true (0,0) labels, and total 69,940 prove completeness
    # after the deletion/link checker independently counts 69,940 exceptions.
    orbit_union = set()
    graph_profiles = defaultdict(lambda: {"classes": 0, "labelings": 0})
    edge_profiles, child_profiles = Counter(), Counter()
    for cls in result["exception_isomorphism_classes"]:
        safe = int(cls["safe_mask"])
        f = solve_complex(safe)
        assert f(0) == (0, 0)
        subsets = [s for s in range(64) if safe >> s & 1]
        orbit = {sum(1 << table[s] for s in subsets) for table in TRANSFORMS}
        assert min(orbit) == safe
        assert len(orbit) == cls["labelings"]
        assert not orbit_union.intersection(orbit)
        orbit_union.update(orbit)
        edges = edges_of(safe)
        profile = [sum(e.bit_count() == k for e in edges) for k in range(2, 7)]
        children = sorted(f(1 << p)[0] for p in range(6))
        cls.update(minimal_forbidden=edges, edge_size_counts_2_through_6=profile,
                   child_normal_values=children)
        graph = graph_name([e for e in edges if e.bit_count() == 2])
        cls["pair_graph"] = graph
        graph_profiles[graph]["classes"] += 1
        graph_profiles[graph]["labelings"] += len(orbit)
        edge_profiles[tuple(profile)] += 1
        child_profiles[tuple(children)] += 1
    assert len(orbit_union) == result["anomalies"] == 69940
    assert len(result["exception_isomorphism_classes"]) == 169
    result["independent_orbit_verification"] = {
        "verified": True, "disjoint_labeled_exceptions": len(orbit_union)}
    result["pair_graph_profiles"] = dict(sorted(graph_profiles.items()))
    result["edge_size_profiles"] = [dict(counts=list(p), classes=c)
                                    for p, c in sorted(edge_profiles.items())]
    result["child_value_profiles"] = [dict(values=list(p), classes=c)
                                      for p, c in sorted(child_profiles.items())]


def forbidden_quads(n):
    answer = []
    for ids in combinations(range(n * n), 4):
        d = ids[3]
        ax, ay, bx, by, cx, cy = [coordinate for p in ids[:3]
            for coordinate in (p % n - d % n, p // n - d // n)]
        determinant = ((ax * ax + ay * ay) * (bx * cy - by * cx)
                       - (bx * bx + by * by) * (ax * cy - ay * cx)
                       + (cx * cx + cy * cy) * (ax * by - ay * bx))
        if determinant == 0:
            answer.append(sum(1 << p for p in ids))
    return answer


def residual_census(n, certificate, known_classes):
    full, quads = (1 << (n * n)) - 1, forbidden_quads(n)
    counts, legal_hist, witnesses = Counter(), Counter(), {}
    for occupied, g, gm in struct.iter_unpack("<QBB", certificate.read_bytes()):
        if (g, gm) != (0, 0):
            continue
        remainder = [q & (full ^ occupied) for q in quads]
        blocked = 0
        for edge in remainder:
            if edge.bit_count() == 1:
                blocked |= edge
        legal = full & ~occupied & ~blocked
        legal_hist[legal.bit_count()] += 1
        assert legal.bit_count() >= 6
        if legal.bit_count() != 6:
            continue
        ids = [p for p in range(n * n) if legal >> p & 1]
        edges = {sum(1 << i for i, p in enumerate(ids) if edge >> p & 1)
                 for edge in remainder if not edge & ~legal}
        edges = {e for e in edges if not any(f != e and f & e == f for f in edges)}
        safe = sum(1 << s for s in range(64) if all(s & e != e for e in edges))
        assert solve_complex(safe)(0) == (0, 0)
        key = str(canonical(safe))
        assert key in known_classes
        counts[key] += 1
        witnesses.setdefault(key, dict(occupied=occupied, legal_points=ids,
                                       minimal_forbidden=sorted(edges)))
    return dict(n=n, double_p_by_legal_count=dict(sorted(legal_hist.items())),
                six_legal_classes=[dict(safe_mask=key, count=counts[key],
                    pair_graph=known_classes[key]["pair_graph"], witness=witnesses[key])
                    for key in sorted(counts, key=int)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    work = args.work_dir or Path(tempfile.mkdtemp(prefix="kyouen-game-structure-"))
    work.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    programs = {}
    for suffix in ("", "_check", "_complexes", "_complexes_check"):
        binary = work / (PREFIX + suffix)
        subprocess.run(["g++", "-O3", "-std=c++17", "-Wall", "-Wextra",
                        str(SOURCE / (PREFIX + suffix + ".cpp")), "-o", str(binary)], check=True)
        programs[suffix] = binary
    boards, board_checks, certificates = [], [], []
    for n in range(1, 8):
        certificate = work / f"board{n}.bin"
        mode = "pairs" if n <= 6 else "pn"
        command = [programs[""], n, certificate] if n <= 6 else [programs[""], n, "pn", certificate]
        boards.append(execute(command, work / f"board{n}.json"))
        board_checks.append(execute([programs["_check"], n, mode, certificate],
                                    work / f"board{n}_checked.json"))
        certificates.append(dict(n=n, mode=mode, bytes=certificate.stat().st_size,
            sha256=hashlib.sha256(certificate.read_bytes()).hexdigest()))
    complexes = [execute([programs["_complexes"], n], work / f"complexes{n}.json")
                 for n in range(1, 7)]
    independent = execute([programs["_complexes_check"]], work / "complexes_checked.json")
    assert independent["families_on_six"] == complexes[-1]["families"]
    assert independent["pair_histogram"] == complexes[-1]["pair_histogram"]
    assert all(c["anomalies"] == 0 for c in complexes[:-1])
    verify_and_describe_classes(complexes[-1])
    known = {c["safe_mask"]: c for c in complexes[-1]["exception_isomorphism_classes"]}
    residuals = [residual_census(n, work / f"board{n}.bin", known) for n in (5, 6)]
    source_files = [SOURCE / (PREFIX + suffix) for suffix in (
        ".cpp", "_check.cpp", "_complexes.cpp", "_complexes_check.cpp", "_reproduce.py")]
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    dump(args.output_dir / (PREFIX + "_boards.json"),
         dict(boards=boards, independent_checks=board_checks, certificates=certificates,
              source_sha256=sources))
    dump(args.output_dir / (PREFIX + "_complexes.json"),
         dict(censuses=complexes, independent_deletion_link_check=independent))
    dump(args.output_dir / (PREFIX + "_residuals.json"), dict(censuses=residuals))
    print(f"Complete; raw certificates remain in {work}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Regression gate for the cache-aware vs cache-blind below-root benchmark.

Prereg guard, runs before the 12-parent B cohort and before manifest freeze.

Checks on short exactly-solvable states
  ("13,52,57,76", 4), ("4,24,26,67", 4), ("14,64,74", 3):
  1. A parity: frozen tmp-kb/parent_bench_native == new binary default
     == new binary explicit --below-root-order cache-aware, on outcome,
     visited, memo_used, maxdepth and root diagnostics
     (bench_root unique/entered/first/witness).
  2. B semantics: --below-root-order cache-blind keeps outcome and full
     root diagnostics identical to A; memo lookup/reuse stays alive
     (prefetch hits, cached child evaluations, cached-LOSS WIN shortcut);
     ordering-change counters are exactly 0 (actual order IS the blind
     fallback order, proving the cached-outcome key is ignored).
  3. Counter identities hold in both modes.

Child-set equality A vs B holds by construction: the diff touches only the
sort comparator branch, the blind flag, and CLI plumbing; child generation,
dedup, prefetch (Child.cached population) and cached-outcome consumption
are byte-identical. Root unique/entered/first equality additionally pins
the shared root child set observationally.

Must run under WSL/Linux (ELF solver binaries).
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_BIN = REPO_ROOT / "tmp-kb" / "parent_bench_native"
NEW_BIN = REPO_ROOT / "tmp-kb" / "order_ab_native"

# (comma state, root-diag depth); same three states as the memo-instr gate.
STATES = [("13,52,57,76", 4), ("4,24,26,67", 4), ("14,64,74", 3)]

EXACT_FIELDS = ("outcome", "visited", "maxdepth", "memo")
ROOT_FIELDS = ("unique", "entered", "first_lo", "first_hi", "witness",
               "outcome")


def run_exact(binary: Path, state: str, depth: int,
              extra: list[str], instr: Path | None
              ) -> tuple[dict[str, str], dict[str, str],
                         list[dict[str, str]], str]:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write(state + "\n")
        tmp_path = tmp.name
    try:
        cmd = [str(binary), tmp_path, "0", "90", "0", "0",
               "--root-depth", str(depth), *extra]
        if instr is not None:
            cmd += ["--memo-instr-out", str(instr)]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True,
                              capture_output=True, timeout=3600)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    if proc.returncode != 0:
        raise AssertionError(f"{binary.name} {state} {extra} "
                             f"rc={proc.returncode}\n{proc.stderr[-600:]}")
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    assert len(rows) == 1, (state, extra, proc.stdout[-200:])
    bench: dict[str, str] = {}
    for line in proc.stderr.splitlines():
        if line.startswith("bench_root "):
            for tok in line.split()[1:]:
                k, v = tok.split("=", 1)
                bench[k] = v
    assert bench, f"no bench_root for {state} {extra}:\n{proc.stderr[-600:]}"
    drows: list[dict[str, str]] = []
    if instr is not None:
        with instr.open(newline="", encoding="utf-8") as f:
            drows = list(csv.DictReader(f))
    return rows[0], bench, drows, proc.stderr


def check_identities(drows: list[dict[str, str]]) -> None:
    for d in drows:
        v = {k: int(d[k]) for k in d if k != "depth"}
        assert v["entry_lookup_calls"] == (
            v["entry_hit_win"] + v["entry_hit_loss"] + v["entry_miss"]), d
        assert v["prefetch_calls"] == (
            v["prefetch_hit_win"] + v["prefetch_hit_loss"]
            + v["prefetch_miss"]), d
        assert v["put_win"] + v["put_loss"] == v["entry_miss"], d
        consumed = (v["child_eval_from_cache_win"]
                    + v["child_eval_from_cache_loss"]
                    + v["child_eval_recursive"])
        assert consumed <= v["prefetch_calls"], d


def totals(drows: list[dict[str, str]]) -> dict[str, int]:
    tot: dict[str, int] = {}
    for d in drows:
        for k, val in d.items():
            if k == "depth":
                continue
            tot[k] = tot.get(k, 0) + int(val)
    return tot


def main() -> int:
    assert FROZEN_BIN.exists(), f"missing {FROZEN_BIN}"
    assert NEW_BIN.exists(), f"missing {NEW_BIN}; build it first"
    for state, depth in STATES:
        fz, fzb, _, _ = run_exact(FROZEN_BIN, state, depth, [], None)
        ad, adb, _, _ = run_exact(NEW_BIN, state, depth, [], None)
        ae, aeb, _, _ = run_exact(
            NEW_BIN, state, depth, ["--below-root-order", "cache-aware"],
            None)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                         encoding="utf-8") as itmp:
            a_instr = Path(itmp.name)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                         encoding="utf-8") as itmp:
            b_instr = Path(itmp.name)
        try:
            a, ab, arows, _ = run_exact(
                NEW_BIN, state, depth,
                ["--below-root-order", "cache-aware"], a_instr)
            b, bb, brows, berr = run_exact(
                NEW_BIN, state, depth,
                ["--below-root-order", "cache-blind"], b_instr)
        finally:
            a_instr.unlink(missing_ok=True)
            b_instr.unlink(missing_ok=True)
        assert "below_root_order=cache-blind" in berr, berr[-300:]

        # 1. A parity: frozen == default == explicit cache-aware.
        for tag, row, bench in (("default", ad, adb), ("aware", a, ab),
                                ("aware-explicit", ae, aeb)):
            for c in EXACT_FIELDS:
                assert row[c] == fz[c], (state, tag, c, row[c], fz[c])
            for c in ROOT_FIELDS:
                assert bench[c] == fzb[c], (state, tag, c, bench[c], fzb[c])
        check_identities(arows)
        check_identities(brows)

        # 2. B semantics: outcome + root identical to A.
        for c in EXACT_FIELDS[:1]:
            assert b[c] == a[c], (state, "B outcome", b[c], a[c])
        for c in ROOT_FIELDS:
            assert bb[c] == ab[c], (state, "B root", c, bb[c], ab[c])

        # Memo reuse alive in B.
        bt = totals(brows)
        assert bt["prefetch_calls"] > 0, (state, bt)
        assert (bt["prefetch_hit_win"] + bt["prefetch_hit_loss"]) > 0, \
            (state, "B has no prefetch hits; memo reuse dead?", bt)
        assert (bt["child_eval_from_cache_win"]
                + bt["child_eval_from_cache_loss"]) > 0, \
            (state, "B consumes no cached children?", bt)
        at = totals(arows)
        if at["win_return_from_cached_loss_child"] > 0:
            assert bt["win_return_from_cached_loss_child"] > 0, \
                (state, "B lost the cached-LOSS WIN shortcut", bt)

        # Blind ordering provably active: actual order == blind fallback.
        assert bt["nodes_cache_changes_first_child"] == 0, (state, bt)
        assert bt["nodes_cache_changes_full_order"] == 0, (state, bt)

        print(f"  {state}: A parity frozen==default==aware "
              f"({a['outcome']} visited={a['visited']} "
              f"maxdepth={a['maxdepth']} memo={a['memo']}) "
              f"B outcome={b['outcome']} visited={b['visited']} "
              f"cached_evals={bt['child_eval_from_cache_win'] + bt['child_eval_from_cache_loss']} "
              f"shortcut={bt['win_return_from_cached_loss_child']} "
              f"orderΔ=0 ok", flush=True)
    print("ALL ORDER A/B REGRESSION TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

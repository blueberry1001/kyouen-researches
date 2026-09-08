#!/usr/bin/env python3
"""Fail-closed source audit for the capacity-rescued C2 rerun.

This audit is intentionally independent of solver outputs.  It proves that,
relative to the historical C2 endpoint commit, the solver implementation
changed only the preregistered MultiDepthMemo100 physical table powers for
D12--D16.  Tooling/docs/results may evolve on the rerun branch, but no other
solver source/include is allowed to differ before execution sealing.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "5b501588d0e71807977ef69850ad78758295b031"
TARGET = "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_1.inc"
SOLVER_PATHS = [
    "scripts/probe_cert_solver.cpp",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_0.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_1.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_3.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_witness_log.inc",
]

OLD = "MultiDepthMemo100(unsigned shrink,unsigned load):d9_(41,p(23,shrink),load),d10_(44,p(25,shrink),load),d11_(48,p(26,shrink),load),d11b_(48,p(24,shrink),load),d12a_(50,p(27,shrink),load),d12b_(50,p(24,shrink),load),d13a_(53,p(27,shrink>0?shrink-1:0),load),d13b_(53,p(25,shrink>0?shrink-1:0),load),d14a_(56,p(27,shrink),load),d14b_(56,p(24,shrink),load),d15_(58,p(26,shrink),load),d16_(61,p(23,shrink),load),d17_(p(19,shrink),load){build();}"
NEW = "MultiDepthMemo100(unsigned shrink,unsigned load):d9_(41,p(23,shrink),load),d10_(44,p(25,shrink),load),d11_(48,p(26,shrink),load),d11b_(48,p(24,shrink),load),d12a_(50,p(28,shrink),load),d12b_(50,p(25,shrink),load),d13a_(53,p(28,shrink>0?shrink-1:0),load),d13b_(53,p(26,shrink>0?shrink-1:0),load),d14a_(56,p(28,shrink),load),d14b_(56,p(25,shrink),load),d15_(58,p(27,shrink),load),d16_(61,p(24,shrink),load),d17_(p(19,shrink),load){build();}"


def git_show(path: str) -> bytes:
    p = subprocess.run(
        ["git", "show", f"{BASE}:{path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        raise SystemExit(
            f"SOURCE AUDIT FAIL: cannot read {BASE}:{path}\n"
            + p.stderr.decode("utf-8", errors="replace")
        )
    return p.stdout


def main() -> None:
    # All solver translation/includes except the one frozen capacity line must
    # remain byte-identical to historical C2.
    for path in SOLVER_PATHS:
        current_path = ROOT / path
        if not current_path.is_file():
            raise SystemExit(f"SOURCE AUDIT FAIL: missing {path}")
        old = git_show(path)
        cur = current_path.read_bytes()
        if path != TARGET:
            if cur != old:
                raise SystemExit(
                    f"SOURCE AUDIT FAIL: unauthorized solver change in {path}"
                )
            continue

        try:
            old_text = old.decode("utf-8")
            cur_text = cur.decode("utf-8")
        except UnicodeDecodeError as e:
            raise SystemExit(f"SOURCE AUDIT FAIL: non-UTF8 target source: {e}")

        if old_text.count(OLD) != 1:
            raise SystemExit(
                f"SOURCE AUDIT FAIL: frozen old constructor count={old_text.count(OLD)}"
            )
        expected = old_text.replace(OLD, NEW, 1)
        if expected != cur_text:
            raise SystemExit(
                "SOURCE AUDIT FAIL: target differs by more than the exact "
                "preregistered D12--D16 capacity replacement"
            )
        if cur_text.count(NEW) != 1 or OLD in cur_text:
            raise SystemExit("SOURCE AUDIT FAIL: constructor replacement is not unique")

    print("SOURCE AUDIT PASS")
    print(f"base={BASE}")
    print("solver_paths_checked=7")
    print("authorized_solver_diff=exact MultiDepthMemo100 D12--D16 power +1 only")


if __name__ == "__main__":
    main()

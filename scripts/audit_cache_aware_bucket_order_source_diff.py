#!/usr/bin/env python3
"""Fail closed unless the bucket-order experiment changes exactly the preregistered solver text.

Expected relative to base e9d0460:
  * resume_2.inc: OLD2 -> NEW2 exactly once
  * resume_4.inc: OLD4A -> NEW4A and OLD4B -> NEW4B exactly once
  * all other solver translation/includes: byte-identical

This intentionally imports the patcher's frozen OLD/NEW literals so the patching and
audit definitions cannot silently drift apart.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_cache_aware_bucket_order_implementation as patch  # noqa: E402

BASE = "e9d0460b55b7f058379da2a843ecea33525b86ea"
P2 = "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc"
P4 = "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc"
SOLVER_PATHS = [
    "scripts/probe_cert_solver.cpp",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_0.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_1.inc",
    P2,
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_3.inc",
    P4,
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_witness_log.inc",
]


def git_show(path: str) -> bytes:
    p = subprocess.run(
        ["git", "show", f"{BASE}:{path}"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if p.returncode:
        raise SystemExit(
            f"SOURCE AUDIT FAIL: cannot read {BASE}:{path}\n"
            + p.stderr.decode("utf-8", errors="replace")
        )
    return p.stdout


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(
            f"SOURCE AUDIT FAIL: base {label} old-text count={text.count(old)}, want 1"
        )
    if new in text:
        raise SystemExit(f"SOURCE AUDIT FAIL: base unexpectedly already contains {label} new text")
    return text.replace(old, new, 1)


def expected_for(path: str, old: bytes) -> bytes:
    if path not in (P2, P4):
        return old
    try:
        text = old.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SystemExit(f"SOURCE AUDIT FAIL: non-UTF8 solver source {path}: {e}")
    if path == P2:
        text = replace_once(text, patch.OLD2, patch.NEW2, "resume_2")
    else:
        text = replace_once(text, patch.OLD4A, patch.NEW4A, "resume_4 CLI")
        text = replace_once(text, patch.OLD4B, patch.NEW4B, "resume_4 wiring")
    return text.encode("utf-8")


def main() -> None:
    for path in SOLVER_PATHS:
        cur_path = ROOT / path
        if not cur_path.is_file():
            raise SystemExit(f"SOURCE AUDIT FAIL: missing {path}")
        base = git_show(path)
        expected = expected_for(path, base)
        current = cur_path.read_bytes()
        if current != expected:
            if path in (P2, P4):
                hint = "authorized replacement missing, partial, or extra solver edit present"
            else:
                hint = "unauthorized solver edit outside the two allowed files"
            raise SystemExit(f"SOURCE AUDIT FAIL: {path}: {hint}")

    print("SOURCE AUDIT PASS")
    print(f"base={BASE}")
    print("solver_paths_checked=7")
    print("authorized_delta=resume_2 OLD2->NEW2; resume_4 OLD4A->NEW4A and OLD4B->NEW4B only")


if __name__ == "__main__":
    main()

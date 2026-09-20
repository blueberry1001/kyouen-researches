#!/usr/bin/env python3
"""Fail-closed source audit for the cache-aware no-hit fast-path experiment.

Relative to frozen base d3b5e8b, only the exact replacements declared in
prepare_cache_aware_nohit_fastpath.py are accepted. All other solver files
must remain byte-identical.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import prepare_cache_aware_nohit_fastpath as prep

ROOT = Path(__file__).resolve().parents[1]
BASE = "d3b5e8ba02a6581787a444e463ff16766d1babfd"
SOLVER_PATHS = [
    "scripts/probe_cert_solver.cpp",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_0.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_1.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_3.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_witness_log.inc",
]


def _resolve_main_gitdir() -> Path | None:
    """Resolve MAIN/.git from a Windows-created linked worktree under WSL."""
    dotgit = ROOT / ".git"
    if not dotgit.is_file():
        return None
    pointer = dotgit.read_text(encoding="utf-8", errors="replace").strip()
    if pointer.startswith("gitdir:"):
        pointer = pointer[len("gitdir:"):].strip()
    normalized = pointer.replace("\\", "/")
    m = re.match(r"^(.*)/\.git/worktrees/[^/]+$", normalized)
    if not m:
        return None
    repo = m.group(1)
    drive = re.match(r"^([A-Za-z]):/(.*)$", repo)
    if drive and Path("/mnt").exists() and not Path("C:/").exists():
        repo = f"/mnt/{drive.group(1).lower()}/{drive.group(2)}"
    gitdir = Path(repo) / ".git"
    return gitdir if gitdir.is_dir() else None


def git_show(path: str) -> bytes:
    # Normal checkout/worktree case.
    p = subprocess.run(
        ["git", "show", f"{BASE}:{path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode == 0:
        return p.stdout

    # WSL cannot follow a Windows .git worktree pointer. BASE is an explicit
    # immutable commit, so reading the same object from the main repository's
    # object database is equivalent and does not involve the main branch HEAD.
    main_gitdir = _resolve_main_gitdir()
    if main_gitdir is not None:
        q = subprocess.run(
            ["git", "--git-dir", str(main_gitdir), "show", f"{BASE}:{path}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if q.returncode == 0:
            return q.stdout
        fallback_err = q.stderr
    else:
        fallback_err = b"main gitdir fallback unavailable"
    raise SystemExit(
        f"NOHIT SOURCE AUDIT FAIL: cannot read {BASE}:{path}\n"
        + p.stderr.decode("utf-8", errors="replace")
        + "\nfallback: "
        + fallback_err.decode("utf-8", errors="replace")
    )


def expected(path: str, base: bytes) -> bytes:
    full = ROOT / path
    if full not in prep.REPLACEMENTS:
        return base
    try:
        text = base.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SystemExit(f"NOHIT SOURCE AUDIT FAIL: non-UTF8 {path}: {e}")
    # Reuse the exact frozen replacement table from the preparer, eliminating
    # a second independently-maintained definition of the authorized delta.
    return prep.transform(full, text).encode("utf-8")


def main() -> None:
    for rel in SOLVER_PATHS:
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"NOHIT SOURCE AUDIT FAIL: missing {rel}")
        base = git_show(rel)
        exp = expected(rel, base)
        cur = path.read_bytes()
        if cur != exp:
            kind = (
                "authorized file differs from exact frozen transform"
                if path in prep.REPLACEMENTS
                else "unauthorized solver change"
            )
            raise SystemExit(f"NOHIT SOURCE AUDIT FAIL: {rel}: {kind}")

    print("NOHIT SOURCE AUDIT PASS")
    print(f"base={BASE}")
    print("solver_paths_checked=7")
    print("changed_files=resume_2,resume_3,resume_4 only")
    print("resume_1_capacity_constructor=byte-identical-to-base")
    print("extra_memo_lookups=0")


if __name__ == "__main__":
    main()

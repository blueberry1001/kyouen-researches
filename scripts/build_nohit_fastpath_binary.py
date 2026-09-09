#!/usr/bin/env python3
"""Fail-closed endpoint build for 10x10 cache-aware no-hit fastpath.

The build is deliberately separate from the completed bucket experiment.
It refuses to build unless the dedicated no-hit source-diff audit passes,
deletes any stale target first, compiles once, and seals source/compiler/
binary provenance into build_receipt.json.  The resulting single binary is
used for both preregistered implementations:
  S: --cache-aware-order-impl sort
  F: --cache-aware-order-impl nohit
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-nohit-fastpath"
BIN = ROOT / "tmp-kb" / "nohit_fastpath_ab_native"
AUDIT = ROOT / "scripts" / "audit_cache_aware_nohit_fastpath_source_diff.py"
SOURCES = ["scripts/probe_cert_solver.cpp"] + sorted(
    str(p.relative_to(ROOT)) for p in (ROOT / "scripts" / "probe_parts").glob("*.inc")
)
FLAGS = ["-O2", "-std=c++20"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def git_head() -> str:
    p = run(["git", "rev-parse", "HEAD"])
    if p.returncode == 0 and p.stdout.strip():
        return p.stdout.strip()
    # WSL worktree fallback: resolve the Windows worktree gitdir pointer.
    import re
    dotgit = ROOT / ".git"
    if dotgit.is_file():
        pointer = dotgit.read_text(encoding="utf-8", errors="replace").strip()
        if pointer.startswith("gitdir:"):
            pointer = pointer[len("gitdir:"):].strip()
        m = re.match(r"(.*)[/\\]\.git[/\\]worktrees[/\\](.+)$", pointer)
        if m:
            repo = m.group(1)
            mm = re.match(r"^([A-Za-z]):[/\\](.*)$", repo)
            if mm and Path("/mnt").exists() and not Path("C:/").exists():
                repo = "/mnt/" + mm.group(1).lower() + "/" + mm.group(2).replace("\\", "/")
            main_git = Path(repo) / ".git"
            wt_head = main_git / "worktrees" / m.group(2) / "HEAD"
            if wt_head.is_file():
                line = wt_head.read_text(encoding="utf-8", errors="replace").strip()
                if line.startswith("ref: "):
                    ref = line[5:].strip()
                    ref_file = main_git / ref
                    if ref_file.is_file():
                        return ref_file.read_text(encoding="utf-8", errors="replace").strip()
                elif line:
                    return line
    raise SystemExit("BUILD FAIL: cannot resolve git HEAD")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cxx", default=os.environ.get("CXX", "g++"))
    args = ap.parse_args()

    # The implementation must already have been applied.  An unpatched tree
    # intentionally fails here instead of producing a misleading baseline binary.
    audit = run([sys.executable, str(AUDIT.relative_to(ROOT))])
    if audit.returncode != 0:
        print(audit.stdout, end="")
        print(audit.stderr, end="", file=sys.stderr)
        raise SystemExit("BUILD FAIL: dedicated no-hit source audit did not PASS")

    OUT.mkdir(parents=True, exist_ok=True)
    BIN.parent.mkdir(parents=True, exist_ok=True)
    if BIN.exists():
        BIN.unlink()
    if BIN.exists():
        raise SystemExit("BUILD FAIL: stale binary could not be removed")

    source_hashes = {s: sha256_file(ROOT / s) for s in SOURCES}
    head = git_head()
    cmd = [args.cxx, *FLAGS, SOURCES[0], "-o", str(BIN)]
    started = datetime.now(timezone.utc)
    built = run(cmd)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    if built.returncode != 0 or not BIN.is_file():
        print(built.stdout, end="")
        print(built.stderr, end="", file=sys.stderr)
        raise SystemExit("BUILD FAIL: compiler failed or binary missing")

    # Cheap parser smoke.  This proves the endpoint source contains the
    # nohit runtime choice without running a research state or consuming a result.
    bad = run([str(BIN), "/definitely/missing", "0", "90", "0", "0",
               "--cache-aware-order-impl", "invalid-nohit-smoke"])
    if bad.returncode == 0 or "unknown --cache-aware-order-impl" not in bad.stderr:
        raise SystemExit("BUILD FAIL: implementation-switch validation smoke failed")

    compiler = subprocess.run([args.cxx, "--version"], text=True, capture_output=True)
    compiler_lines = compiler.stdout.splitlines()
    receipt = {
        "experiment": "10x10-cache-aware-nohit-fastpath",
        "built_at_utc": started.isoformat(),
        "build_seconds": elapsed,
        "git_head": head,
        "command": cmd,
        "flags": FLAGS,
        "compiler": compiler_lines[0] if compiler_lines else "unknown",
        "compiler_full": compiler_lines,
        "source_audit": "PASS",
        "audit_script_sha256": sha256_file(AUDIT),
        "sources_sha256": source_hashes,
        "binary": str(BIN.relative_to(ROOT)),
        "binary_sha256": sha256_file(BIN),
        "same_binary_required_for": ["sort", "nohit"],
        "impl_switch": "--cache-aware-order-impl sort|nohit",
        "cli_smoke": "unknown implementation rejected",
        "historical_timing_reused": False,
    }
    receipt_path = OUT / "build_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Re-hash after writing the receipt so accidental post-build binary mutation
    # is caught before this command reports success.
    if sha256_file(BIN) != receipt["binary_sha256"]:
        receipt_path.unlink(missing_ok=True)
        raise SystemExit("BUILD FAIL: binary changed while sealing receipt")

    print("NOHIT FASTPATH BUILD GATE: PASS")
    print(f"git_head={head}")
    print(f"binary_sha256={receipt['binary_sha256']}")
    print(f"receipt={receipt_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

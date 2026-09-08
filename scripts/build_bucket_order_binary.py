#!/usr/bin/env python3
"""Provenance-safe build for the bucket-order optimization endpoint binary.

Procedure (per preregistration):
  1. refuse to reuse any stale binary: the target is deleted BEFORE build;
  2. delete-then-build from frozen sources (scripts/probe_cert_solver.cpp +
     probe_parts/*.inc);
  3. record binary SHA256, compiler version, full flags, source SHA256s,
     git HEAD into results/10x10/cache-aware-bucket-order-optimization/
     build_receipt.json;
  4. verify the source-diff auditor PASS as a precondition.

The same binary serves both S (--cache-aware-order-impl sort) and B
(--cache-aware-order-impl bucket).

Must run under WSL/Linux (ELF solver binary):
  python3 scripts/build_bucket_order_binary.py
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
OUT = ROOT / "results" / "10x10" / "cache-aware-bucket-order-optimization"
BIN = ROOT / "tmp-kb" / "order_ab_native"
SOURCES = ["scripts/probe_cert_solver.cpp"] + sorted(
    str(p.relative_to(ROOT)) for p in
    (ROOT / "scripts" / "probe_parts").glob("*.inc"))
FLAGS = ["-O2", "-std=c++20"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                       text=True, capture_output=True)
    if p.returncode == 0:
        return p.stdout.strip()
    # WSL-in-Windows-worktree fallback (same mapping as the auditor).
    import re as _re
    gitdir_file = ROOT / ".git"
    if gitdir_file.is_file():
        pointer = gitdir_file.read_text(encoding="utf-8",
                                        errors="replace").strip()
        if pointer.startswith("gitdir:"):
            pointer = pointer[len("gitdir:"):].strip()
        m = _re.match(r"(.*)[/\\]\.git[/\\]worktrees[/\\](.+)$", pointer)
        if m:
            cand = m.group(1)
            mm = _re.match(r"^([A-Za-z]):[/\\](.*)$", cand)
            if mm and Path("/mnt").exists() and not Path("C:/").exists():
                cand = ("/mnt/" + mm.group(1).lower() + "/"
                        + mm.group(2).replace("\\", "/"))
            main = Path(cand) / ".git"
            if main.is_dir():
                # The worktree's own HEAD file is readable directly; use it
                # to avoid the main-repo HEAD (which points elsewhere).
                wt_head = (main / "worktrees" / m.group(2) / "HEAD")
                if wt_head.is_file():
                    line = wt_head.read_text(encoding="utf-8",
                                            errors="replace").strip()
                    if line.startswith("ref: "):
                        ref = line[len("ref: "):].strip()
                        ref_file = main / ref
                        if ref_file.is_file():
                            return ref_file.read_text(
                                encoding="utf-8",
                                errors="replace").strip()
                    elif line:
                        return line  # detached SHA
                q = subprocess.run(["git", "--git-dir", str(main),
                                    "rev-parse", "HEAD"],
                                   text=True, capture_output=True)
                if q.returncode == 0:
                    return q.stdout.strip()
    raise SystemExit("cannot read git HEAD")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cxx", default=os.environ.get("CXX", "g++"))
    ap.add_argument("--skip-audit", action="store_true",
                    help="(not allowed for endpoint builds)")
    args = ap.parse_args()
    if args.skip_audit:
        raise SystemExit("--skip-audit is forbidden: source audit must PASS "
                         "before the endpoint binary is built")

    # 0. Source-diff audit must PASS first.
    audit = subprocess.run([sys.executable,
                            "scripts/audit_bucket_order_source_diff.py"],
                            cwd=ROOT, text=True, capture_output=True)
    if audit.returncode != 0:
        print(audit.stdout)
        print(audit.stderr)
        raise SystemExit("source audit failed; refusing to build")
    print("source audit: PASS")
    print("")
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / "tmp-kb").mkdir(parents=True, exist_ok=True)

    # 1. Delete stale binary first.
    if BIN.exists():
        BIN.unlink()
        print(f"deleted stale binary: {BIN}")
    build_start = datetime.now(timezone.utc).isoformat()

    # 2. Build from frozen sources.
    src_sha = {s: sha256_file(ROOT / s) for s in SOURCES}
    cmd = [args.cxx] + FLAGS + [SOURCES[0], "-o", str(BIN)]
    print("build:", " ".join(cmd))
    t0 = datetime.now(timezone.utc)
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    build_seconds = (datetime.now(timezone.utc) - t0).total_seconds()
    if p.returncode != 0 or not BIN.exists():
        print(p.stdout)
        print(p.stderr)
        raise SystemExit("build failed")
    if p.stderr.strip():
        print("compiler stderr:", p.stderr.strip()[:2000])

    # 3. Verify the built binary accepts both impl switches and rejects
    #    garbage (cheap CLI smoke: unknown value must fail).
    probe_bad = subprocess.run([str(BIN), "/nonexistent", "0", "90", "0", "0",
                                 "--cache-aware-order-impl", "bogus"],
                                cwd=ROOT, text=True, capture_output=True)
    if probe_bad.returncode == 0:
        raise SystemExit("impl switch validation missing")
    if "unknown --cache-aware-order-impl" not in probe_bad.stderr:
        raise SystemExit("impl switch error text unexpected: "
                         + probe_bad.stderr[:300])

    # 4. Receipt.
    ver = subprocess.run([args.cxx, "--version"], text=True,
                          capture_output=True).stdout.splitlines()
    receipt = {
        "built_at": build_start,
        "build_seconds": build_seconds,
        "command": cmd,
        "compiler": ver[0] if ver else "unknown",
        "compiler_full": ver,
        "flags": FLAGS,
        "git_head": git_head(),
        "binary": str(BIN.relative_to(ROOT)),
        "binary_sha256": sha256_file(BIN),
        "sources_sha256": src_sha,
        "source_audit": "PASS",
        "impl_switch": {
            "flag": "--cache-aware-order-impl",
            "values": ["sort", "bucket"],
            "sort": "S: single std::sort cache-aware comparator (historical)",
            "bucket": "B: 3-bucket cached-class partition + per-bucket sort",
            "root_and_cache_blind": "not affected by this flag",
        },
        "cli_smoke": "unknown impl value rejected with rc!=0",
    }
    (OUT / "build_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print("BUILD PASS")
    print(f"binary_sha256={receipt['binary_sha256']}")
    print(f"git_head={receipt['git_head']}")
    print(f"receipt={OUT / 'build_receipt.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Apply the preregistered C2 capacity-only solver change deterministically.

This script intentionally edits exactly one constructor initializer in
kyouen_solver_10_kyoenc4_resume_1.inc.  It refuses to run if the expected old
text is absent or if the new text is already present together with the old one.
No ordering, memo semantics, load factor, instrumentation, or game logic is
changed.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

TARGET = Path("scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_1.inc")

OLD = (
    "MultiDepthMemo100(unsigned shrink,unsigned load):"
    "d9_(41,p(23,shrink),load),d10_(44,p(25,shrink),load),"
    "d11_(48,p(26,shrink),load),d11b_(48,p(24,shrink),load),"
    "d12a_(50,p(27,shrink),load),d12b_(50,p(24,shrink),load),"
    "d13a_(53,p(27,shrink>0?shrink-1:0),load),"
    "d13b_(53,p(25,shrink>0?shrink-1:0),load),"
    "d14a_(56,p(27,shrink),load),d14b_(56,p(24,shrink),load),"
    "d15_(58,p(26,shrink),load),d16_(61,p(23,shrink),load),"
    "d17_(p(19,shrink),load){build();}"
)

NEW = (
    "MultiDepthMemo100(unsigned shrink,unsigned load):"
    "d9_(41,p(23,shrink),load),d10_(44,p(25,shrink),load),"
    "d11_(48,p(26,shrink),load),d11b_(48,p(24,shrink),load),"
    "d12a_(50,p(28,shrink),load),d12b_(50,p(25,shrink),load),"
    "d13a_(53,p(28,shrink>0?shrink-1:0),load),"
    "d13b_(53,p(26,shrink>0?shrink-1:0),load),"
    "d14a_(56,p(28,shrink),load),d14b_(56,p(25,shrink),load),"
    "d15_(58,p(27,shrink),load),d16_(61,p(24,shrink),load),"
    "d17_(p(19,shrink),load){build();}"
)

EXPECTED_POWERS = {
    "d9": 23,
    "d10": 25,
    "d11a": 26,
    "d11b": 24,
    "d12a": 28,
    "d12b": 25,
    "d13a": 28,
    "d13b": 26,
    "d14a": 28,
    "d14b": 25,
    "d15": 27,
    "d16": 24,
    "d17": 19,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only; do not modify")
    ap.add_argument("--path", type=Path, default=TARGET)
    args = ap.parse_args()

    path = args.path
    before = path.read_bytes()
    text = before.decode("utf-8")

    old_n = text.count(OLD)
    new_n = text.count(NEW)
    if old_n == 0 and new_n == 1:
        print(f"already prepared: {path}")
        print(f"sha256={sha256_bytes(before)}")
        return 0
    if old_n != 1 or new_n != 0:
        raise SystemExit(
            f"refusing ambiguous patch: old_count={old_n} new_count={new_n} path={path}"
        )

    after_text = text.replace(OLD, NEW, 1)
    after = after_text.encode("utf-8")

    # The edit must be exactly the frozen power substitutions.  Reversing it
    # must reproduce the original byte-for-byte.
    if after_text.replace(NEW, OLD, 1).encode("utf-8") != before:
        raise SystemExit("round-trip safety check failed")

    print(f"before_sha256={sha256_bytes(before)}")
    print(f"after_sha256={sha256_bytes(after)}")
    print("capacity powers:", " ".join(f"{k}={v}" for k, v in EXPECTED_POWERS.items()))

    if args.check:
        print("check-only: preregistered patch is applicable")
        return 0

    path.write_bytes(after)
    print(f"updated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

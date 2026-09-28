#!/usr/bin/env python3
"""Extract the assigned B-IDs' original text from the hypothesis bank (bullet format)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BANK = ROOT / "research" / "hypothesis-bank-2026-09-27.md"

IDS = """B092 B093 B094 B095 B096 B097 B098 B099 B100 B103 B104 B106 B107 B110
B111 B115 B118 B120 B121 B122 B123 B124 B125 B127 B129 B130 B131 B132
B133 B136 B138 B140 B145 B149 B150 B153 B154 B157 B158 B159 B160 B162
B165 B166 B167""".split()


def main() -> None:
    text = BANK.read_text(encoding="utf-8")
    lines = text.splitlines()
    out = {}
    for i, ln in enumerate(lines):
        m = re.match(r"^-\s+\*\*(B\d{3})\s+\[", ln)
        if m:
            bid = m.group(1)
            body = [ln]
            j = i + 1
            while j < len(lines) and lines[j].startswith("  ") and lines[j].strip():
                body.append(lines[j])
                j += 1
            out[bid] = "\n".join(body)
    chunks = []
    missing = []
    for bid in IDS:
        if bid in out:
            chunks.append(out[bid])
        else:
            missing.append(bid)
            chunks.append(f"### {bid} NOT FOUND IN BANK")
    sys.stdout.write("\n\n".join(chunks) + "\n")
    sys.stdout.write(f"\n[found {len(IDS)-len(missing)}/{len(IDS)}; missing={missing}]\n")


if __name__ == "__main__":
    main()

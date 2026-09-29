#!/usr/bin/env python3
"""Extract JSON object from a log file that contains stdout JSON + other text."""
import sys, re

path = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else None
text = open(path, encoding="utf-8", errors="replace").read()

# Find the JSON object: starts with { "n": and ends with matching }
# The solver prints a pretty-printed JSON to stdout
# Look for the pattern that starts a JSON object
idx = text.find('{\n  "n":')
if idx < 0:
    idx = text.find('{')
    if idx < 0:
        print("NO JSON FOUND")
        sys.exit(1)

# Find the end: the last } before "exit=" or end of file
exit_idx = text.find("exit=")
if exit_idx < 0:
    exit_idx = len(text)
chunk = text[idx:exit_idx]
# Find the last closing brace in the chunk
last_brace = chunk.rfind('}')
if last_brace < 0:
    print("NO CLOSING BRACE")
    sys.exit(1)
json_str = chunk[:last_brace+1]

# Validate
import json
try:
    d = json.loads(json_str)
    print(f"Extracted JSON OK: n={d.get('n')}, keys={list(d.keys())[:8]}")
except Exception as e:
    print(f"JSON parse error: {e}")
    print(f"First 300: {json_str[:300]}")
    print(f"Last 100: {json_str[-100:]}")
    sys.exit(1)

if out:
    with open(out, "w", encoding="utf-8") as f:
        f.write(json_str)
    print(f"Wrote {out}")

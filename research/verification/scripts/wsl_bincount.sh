#!/usr/bin/env bash
# Read the header (u64 count) of a kc_maximal_*.bin file.
for f in "$@"; do
  printf '%s  count=' "$f"
  od -A n -t u8 -N 8 "$f" | tr -d ' \n'
  printf '  (size %s bytes)\n' "$(stat -c %s "$f")"
done

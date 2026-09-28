#!/bin/bash
# Extract the scalar fields we care about from the T* JSON, avoiding the
# PowerShell/nu quoting that breaks inline grep patterns.
cd /mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification
for f in "$@"; do
  echo "=== $f"
  grep -E 'V"|F_n"|safe_sets_total"|K_n"|g_empty"|winner"|T_star_empty"|WFT_empty"|T_star_empty_size|WFT_empty_size|B034_|B031_|B037_empty|B037_branch|safe_sets_by_size' "$f" | head -60
done

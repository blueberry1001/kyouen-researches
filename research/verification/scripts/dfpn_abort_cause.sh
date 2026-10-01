#!/bin/bash
# Was the abort elimination in the layered sweep caused by funding
# s6-s8, or by making s5 close reliably at 20M?
#
# Two arms, identical except for the s5 budget:
#   A  s5:5,000,000   s6:1,000,000  s7:1,000,000  s8:200,000
#   B  s5:200,000     s6:1,000,000  s7:1,000,000  s8:200,000
#
# If s5 is reliably closed (arm A) the search never needs to descend
# below s5, so the s6/s7/s8 gates should be unreachable. If instead the
# s6-s8 funding is what mattered, arm B should also show zero aborts.
# It should not: at 200k the s5 layer is mostly unsolvable.
D=/mnt/d/ghq/build11/dfpn
OUT=/mnt/d/ghq/build11/logs/abortcause
mkdir -p "$OUT"

one() {  # tag, s5budget
  local tag=$1 s5b=$2
  rm -f "$OUT/$tag.csv" "$OUT/$tag.log"
  "$D" --n=11 --reps --only=60 --memo=24 --budget=60 \
       --exact-legal=0 --exact-legal-by-stones=5:116,6:115,7:114,8:113 \
       --exact-budget=200000 --exact-budget-by-stones="5:$s5b,6:1000000,7:1000000,8:200000" \
       --exact-retries=1 --exact-publish=root \
       --exact-record --csv="$OUT/$tag.csv" --log="$OUT/$tag.log" >/dev/null 2>&1
  echo "=== $tag (s5 budget=$s5b) ==="
  echo -n "  handoffs by layer: "
  grep -v '^#' "$OUT/$tag.csv" 2>/dev/null | cut -d, -f3 | sort -n | uniq -c | tr '\n' ' '
  echo
  awk -F, '/^v=60,/ { if($11==0) a++; else if($11==1) w++; else l++ }
    END {printf "  handoff outcomes: WIN=%d LOSS=%d UNKNOWN=%d\n", w+0, l+0, a+0}' "$OUT/$tag.csv"
  echo -n "  root: "
  grep -hE 'TIMEOUT reason|^\[done\]' "$OUT/$tag.log" "$OUT/$tag.csv" 2>/dev/null | tail -1 \
    | tr ' ' '\n' | grep -E 'root_pn=|root_dn=|exact_abort=|exact_nodes=' | tr '\n' ' '
  echo
}

one s5big 5000000
one s5small 200000
echo ABORTCAUSE_DONE
#!/bin/bash
# Soundness for the quantified s5 search.
#
# The quant solver decides  exists m3 : forall m4 : exists m5 : s5 WIN
# for a two-stone root. It must agree with a plain exact DFS on the same
# position, which is checkable on a small board where everything solves.
#
# Cross-check: for n=6 and n=7, run the quant search for the center
# first move and compare its WIN/LOSS against --reps --only=<center>,
# which solves the same two-stone root by ordinary df-pn+exact.
D=/mnt/d/ghq/build11/dfpn
FAILED=0

check() {  # n, first
  local n=$1 first=$2
  echo "=== n=$n first=$first ==="
  # baseline: df-pn with an aggressive exact gate, solved to completion
  local base
  base=$("$D" --n="$n" --reps --only="$first" --memo=24 \
         --exact-legal=40 --exact-budget=5000000 --exact-publish=root \
         2>&1 | grep '^\[done\]' | head -1 \
         | sed -n 's/.*\] \([A-Z]*\) expansions.*/\1/p')
  echo "  baseline (df-pn, two-stone root $first): $base"

  # quant: quant_solve expects the first move plus a reply, so run the
  # single reply that the root's own first move implies is the interesting
  # one. Use the center as first and a neighbour as reply.
  local replies="${3:-}"
  if [ -z "$replies" ]; then
    echo "  (no replies given, skipping quant arm)"
    return
  fi
  local out
  out=$("$D" --n="$n" --memo=24 --quant-first="$first" \
        --quant-replies="$replies" --quant-budget=5000000 2>&1)
  echo "$out" | grep -E '^quant,|^# SUMMARY' | sed 's/^/  /'

  # A quant LOSS would be a refutation of that reply; a quant WIN a proof.
  # Either must be consistent with the baseline being WIN or LOSS.
  local q
  q=$(echo "$out" | grep '^quant,' | head -1 | cut -d, -f3)
  echo "  quant first-reply outcome: ${q:-none}"
  if [ "$q" = "WIN" ] && [ "$base" != "WIN" ]; then
    echo "  MISMATCH: quant says WIN but baseline is $base"; FAILED=1
  fi
  if [ "$q" = "LOSS" ] && [ "$base" != "LOSS" ]; then
    echo "  MISMATCH: quant says LOSS but baseline is $base"; FAILED=1
  fi
}

check 6 18 "1"
check 7 24 "1"

if [ "$FAILED" = "0" ]; then echo "QUANT_SOUND_OK"; else echo "QUANT_SOUND_FAILED"; exit 1; fi
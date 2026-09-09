#!/usr/bin/env bash
set -euo pipefail

outdir=${1:-/tmp/kyouen-9x9-factorial}
mkdir -p "$outdir"

pair_gap_bin="$outdir/pair-gap"
factorial_pop_bin="$outdir/export-factorial-population"
pair_gap_csv="$outdir/9x9-pair-gap-population.csv"
confirm_csv="$outdir/9x9-confirmatory-1024.csv"
factorial_pop_csv="$outdir/9x9-factorial-population.csv"
holdout_csv="$outdir/9x9-factorial-holdout.csv"
union_csv="$outdir/9x9-factorial-union.csv"
shard_dir="$outdir/shards"

g++ -O3 -std=c++20 scripts/analyze-9x9-pair-gap-decomposition.cpp -o "$pair_gap_bin"
"$pair_gap_bin" --csv "$pair_gap_csv"

python3 scripts/select-9x9-pair-mobility-confirmatory.py \
  "$pair_gap_csv" \
  results/9x9/pair-vs-true-unique-pilot-64-input.csv \
  "$confirm_csv"

g++ -O3 -std=c++20 scripts/export-9x9-factorial-population.cpp -o "$factorial_pop_bin"
"$factorial_pop_bin" --csv "$factorial_pop_csv"

python3 scripts/select-9x9-factorial-holdout.py \
  "$factorial_pop_csv" \
  "$holdout_csv" \
  --exclude results/9x9/pair-vs-true-unique-pilot-64-input.csv \
  --exclude "$confirm_csv"

python3 scripts/prepare-9x9-factorial-union-input.py \
  "$holdout_csv" \
  "$union_csv"

rm -rf "$shard_dir"
python3 scripts/split-9x9-factorial-union-input.py \
  "$union_csv" \
  "$shard_dir" \
  --parents-per-shard 64

printf 'pair_gap_population=%s\n' "$pair_gap_csv"
printf 'confirmatory_exclusion=%s\n' "$confirm_csv"
printf 'factorial_population=%s\n' "$factorial_pop_csv"
printf 'factorial_holdout=%s\n' "$holdout_csv"
printf 'factorial_union=%s\n' "$union_csv"
printf 'shards=%s\n' "$shard_dir"

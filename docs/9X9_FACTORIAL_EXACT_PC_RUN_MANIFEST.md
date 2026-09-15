# Reproducibility manifest — factorial-exact-pc-run

## Identity

- base_commit: `4152c1a0a74f17ecd89a3085cfdf9afc19fabaa8`
- working_branch: `factorial-exact-pc-run`
- pre_outcome_commit: `9ebc79ea1e8c2b35fe8d76c397491cf984f216e2`
- started_at_utc: 2026-09-15T10:14:00Z (approx; holdout audit timestamp)
- finished_at_utc: 2026-09-15T10:30:00Z (approx; after analysis)

## Environment

- OS: Microsoft Windows 11 Home
- CPU: AMD Ryzen 7 5800HS with Radeon Graphics
- physical_cores: 8
- logical_cores: 16
- RAM_GiB: 39.41
- solver binary: `build-factorial/Release/kyouen-solver-9-compare.exe`
- solver sha256: `186afe2fea75c99870c3eb474b3781826e8dbc9fb1ad73e2789009399138b89a`
- compiler: MSVC 19.44.35228.0 (VS 17 2022 Release)
- cmake: 4.4.3
- cmake flags: `-DBUILD_RESEARCH_SOLVERS=ON -DCMAKE_BUILD_TYPE=Release`
- population exporter compiler: g++ 15.2.0 `-O3 -std=c++20`

## Solve configuration

- memo_power: 28
- shard_size: 12
- max_concurrent_jobs: 6
- failed_shards: []
- retried_shards: []
- memo_power_29_rows: []
- completion: 3403/3403 comparison-rows

## Input hashes

- population_sha256: `d4807ada56fabf2dda5430237f1ca5efb72c93301762b9715ae252a0a1106f72`
- exclusion_sha256: `354d56c4455152876a945f6cf3b61b97ec8d43b5bbe4359829991e516fd302d0`
- holdout_sha256: `5e11b3bd514919c87e2702f60a8e21df026b45ea60fc9044cfa8335da62517fa`
- holdout_manifest_sha256: `83fa25d0f416dab19e551f58d3a1e38326dc4e899734cab7eb5bc7b49be29654`
- E_at_O0 input sha256: `3ad48bf1e08cc2b71e68bc664a593ffe3584e5feefc795b82ede39d855630225`
- O_at_E0 input sha256: `7b7a08def7fdd0e75a5f865ee97ba0d566d1e8df50cbc0c17227b6eb9e85d5f5`
- E_at_O1 input sha256: `5752bd15466861302a0c324b14260d59af4253e4463352f40f1cb4ba8b03e1bd`
- O_at_E1 input sha256: `81e84e016d0bae71362a1196f880a73d1d2e4b4a630998ee02b27018823550b5`

## Result hashes

- E_at_O0 merged sha256: `8a77c6e875a39bae2421cc4b56c02214271c19f8698e51b5b5921186cf1afff6`
- O_at_E0 merged sha256: `1be8157e9a356992297cc9d37d791a9cf0f7d6fa030327792e90b5c65b1145c0`
- E_at_O1 merged sha256: `c0ef1d5f46ce3c8f4dc8e5e3962e3b87e23893531d5b467785697a967e987f28`
- O_at_E1 merged sha256: `9f1841635366208ffeb42951fd92eb613875b7bb8526fdb106a98c75515d8ecd`
- primary-summary sha256: `9d6309d21678e4ce0ef9b27be8ebcc04f0ed52dc05f0e6917186104ab45d3e07`
- secondary-interaction sha256: `a14359c62e4af2aaecb5bbe555386f7db84771875ac3f2848b00492b97eaa434`
- o-census-finite-population sha256: `ac77321d05e42cd91f8a1b9bfd5631e491dc4e59775478419f8cf5e3bcd6f8a9`

## Commands

```text
python scripts/select-9x9-factorial-holdout.py \
  artifacts/9x9-factorial-population.csv \
  artifacts/9x9-factorial-holdout.csv \
  --exclude artifacts/exclusion-canonical-parents.csv

python scripts/prepare-9x9-factorial-solver-inputs.py \
  artifacts/9x9-factorial-holdout.csv \
  artifacts/solver_inputs

python scripts/run-9x9-factorial-sharded-solve.py \
  --solver build-factorial/Release/kyouen-solver-9-compare.exe \
  --input-dir artifacts/solver_inputs \
  --out-dir artifacts/solve \
  --shard-size 12 --max-jobs 6 --memo-power 28 \
  --progress-json artifacts/solve/progress.json

python scripts/analyze-9x9-factorial-outcomes.py \
  artifacts/9x9-factorial-holdout.csv \
  artifacts/solve/primary-summary.csv \
  --E_at_O0 artifacts/solve/merged/E_at_O0.csv \
  --O_at_E0 artifacts/solve/merged/O_at_E0.csv \
  --E_at_O1 artifacts/solve/merged/E_at_O1.csv \
  --O_at_E1 artifacts/solve/merged/O_at_E1.csv
```

## Constraints honored

- No holdout / threshold / score / analysis-set change after outcomes
- No `git worktree add/remove`
- Shared worktree registry untouched
- main not modified
- Holm family, alpha, two-sided test unchanged

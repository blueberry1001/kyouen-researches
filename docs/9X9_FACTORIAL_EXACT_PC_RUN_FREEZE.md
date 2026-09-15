# 9x9 factorial exact-pc-run freeze (pre-outcome)

## Identity

- base_commit: `4152c1a0a74f17ecd89a3085cfdf9afc19fabaa8`
- working_branch: `factorial-exact-pc-run`
- freeze_commit: `a38f43b9776f3b36cbed50c54b7dd95cb5d5d296`
- selector_seed: `kyouen-9x9-pair-components-factorial-v1-2026-09-05`
- outcomes_collected: false

## Holdout counts

- population_total: 5113
- excluded_unique: 1089
- eligible_total: 4024
- E_at_O0 eligible/selected: 4020 / 1024
- O_at_E0 eligible/selected: 715 / 715 (census)
- E_at_O1 eligible/selected: 3944 / 1024
- O_at_E1 eligible/selected: 639 / 639 (census)
- unique_parents_to_solve: 2592
- intersection sample_E_at_O0 && sample_E_at_O1: 254
- pairwise intersections:
  - E_at_O0 & O_at_E0: 67
  - E_at_O0 & E_at_O1: 254
  - E_at_O0 & O_at_E1: 15
  - O_at_E0 & E_at_O1: 9
  - O_at_E0 & O_at_E1: 419
  - E_at_O1 & O_at_E1: 52

## Exclusions (already observed outcomes)

- pilot-64-input: 64 unique
  - sha256 `28b495a6e4864c40d0227eb5d2658dc42d51ea442926a02de2ceaeb19c4c2b7f`
- confirmatory-1024 regenerated from pre-fixed selector:
  - sha256 `07e60d22eac16834726a5972967e2ae426f2a75f89401f9d4508d1ce033fc840`
- first12: 12 unique
  - sha256 `4f9d626b3969b47c4d4dc27c8876ea5ea84347a45301f73c5d30b32575b4a03c`
- smoke: 1 unique
  - sha256 `55ebe330185163de361dbcc094bf0566b8a6da09593ecd2e6e70e3f39ec06fe3`
- exclusion set unique: 1089
- exclusion sha256: `354d56c4455152876a945f6cf3b61b97ec8d43b5bbe4359829991e516fd302d0`

## Hashes

- population sha256: `d4807ada56fabf2dda5430237f1ca5efb72c93301762b9715ae252a0a1106f72`
- holdout sha256: `5e11b3bd514919c87e2702f60a8e21df026b45ea60fc9044cfa8335da62517fa`
- holdout manifest sha256: `83fa25d0f416dab19e551f58d3a1e38326dc4e899734cab7eb5bc7b49be29654`
- E_at_O0.csv sha256: `3ad48bf1e08cc2b71e68bc664a593ffe3584e5feefc795b82ede39d855630225`
- O_at_E0.csv sha256: `7b7a08def7fdd0e75a5f865ee97ba0d566d1e8df50cbc0c17227b6eb9e85d5f5`
- E_at_O1.csv sha256: `5752bd15466861302a0c324b14260d59af4253e4463352f40f1cb4ba8b03e1bd`
- O_at_E1.csv sha256: `81e84e016d0bae71362a1196f880a73d1d2e4b4a630998ee02b27018823550b5`

## Build

- binary: `build-factorial/Release/kyouen-solver-9-compare.exe`
- binary sha256: `186afe2fea75c99870c3eb474b3781826e8dbc9fb1ad73e2789009399138b89a`
- cmake: 4.4.3
- generator: Visual Studio 17 2022, config Release
- msvc: 19.44.35228.0
- export_population compiler: g++ 15.2.0 -O3 -std=c++20
- cmake flags: `-DBUILD_RESEARCH_SOLVERS=ON -DCMAKE_BUILD_TYPE=Release`

## Machine

- OS: Microsoft Windows 11 Home
- CPU: AMD Ryzen 7 5800HS with Radeon Graphics
- physical_cores: 8
- logical_cores: 16
- RAM_GiB: 39.41
- planned_memo_power: 28
- planned_shard_rows: 12
- planned_max_concurrent_jobs: 7
  - floor((39.41 - 6) / 3.2) = 10, capped by physical cores 8; use 7 to leave headroom

## Priority

1. O_at_E0 census
2. O_at_E1 census
3. E_at_O0 sample
4. E_at_O1 sample

Run O first and keep E jobs on remaining capacity.

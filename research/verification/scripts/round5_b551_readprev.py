import os
files = [
 'research/verification/round2-batch-b531.md',
 'research/verification/round2-batch-b561.md',
 'research/verification/round2-batch-b591.md',
 'research/verification/round3-batch-b542-b560.md',
 'research/verification/round3-batch-b591-b592.md',
 'research/verification/round4-batch-b536-b600.md',
 'research/verification/round4-batch-b591-b599.md',
]
for fp in files:
    print('='*80)
    print(fp)
    print('='*80)
    with open(fp, encoding='utf-8') as f:
        print(f.read())

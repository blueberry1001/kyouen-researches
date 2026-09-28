REPO=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches
set -e
cd $REPO/research/verification
g++ -O2 -march=native -std=c++20 -o /tmp/r4b478 scripts/round4_b478b500.cpp 2>&1 | head -40
cd $REPO
/tmp/r4b478
echo "EXIT=$?"
C:/Python311/python.exe research/verification/scripts/fixjson.py research/verification/round4_b478b500.json
C:/Python311/python.exe -c "import json;d=json.load(open('research/verification/round4_b478b500.json',encoding='utf-8'));print('OK keys:',list(d.keys()))"

S=/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/scripts
echo "--- every write to levels[] / lms[] ---"
grep -n 'levels\.\|lms\.\|levels\[\|lms\[' "$S/round5_b501_prand8.cpp" | grep -v '^\s*[0-9]*:\s*//'
echo
echo "--- the solve loop region ---"
sed -n '455,505p' "$S/round5_b501_prand8.cpp"
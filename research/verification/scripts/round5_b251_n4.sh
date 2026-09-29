#!/bin/bash
set -e
mkdir -p /tmp/r5b251
/tmp/r5b251_solver n4 > /tmp/r5b251/n4.json 2>/tmp/r5b251/n4.err
echo "N4_EXIT=$?"
wc -c /tmp/r5b251/n4.json /tmp/r5b251/n4.err
echo "--- stderr ---"
head -30 /tmp/r5b251/n4.err
echo "--- json head ---"
head -c 800 /tmp/r5b251/n4.json
echo
echo "--- json keys ---"
python3 -c "import json; d=json.load(open('/tmp/r5b251/n4.json')); print(list(d.keys())); print('n4 keys', list(d.get('n4',{}).keys())[:30])"

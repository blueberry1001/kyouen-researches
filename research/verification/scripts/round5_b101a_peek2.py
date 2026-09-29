from pathlib import Path
import json

p = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round4_b092.json")
text = p.read_text()
# extract all JSON objects
objs = []
depth = 0
start = None
for i, ch in enumerate(text):
    if ch == '{':
        if depth == 0:
            start = i
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0 and start is not None:
            objs.append(text[start:i+1])
            start = None

for i, o in enumerate(objs):
    print(f"--- obj {i} len={len(o)}")
    print(o[:800])
    print("...")

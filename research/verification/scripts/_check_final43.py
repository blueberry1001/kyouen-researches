import json
from collections import Counter
rows = json.load(open(r'D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round4_status.json', encoding='utf-8'))
ids = ['B029','B058','B066','B069','B070','B079','B089','B118','B122','B127','B140','B153','B160','B170','B184','B188','B190','B193','B197','B210','B220','B223','B243','B284','B287','B313','B315','B318','B355','B356','B359','B366','B405','B440','B457','B458','B460','B468','B520','B530','B561','B569','B570']
c = Counter()
for i in ids:
    r = rows[i]
    f = r['r3r4_file']
    c[f] += 1
    print(f"{i}: {r['final']:12s} via {f}")
print('---')
for f, n in c.most_common():
    print(n, f)
print('settled count:', sum(1 for i in ids if rows[i]['settled']))

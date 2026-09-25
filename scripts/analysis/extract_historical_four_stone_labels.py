#!/usr/bin/env python3
"""Audit historical 4-stone outcome labels reachable from a frozen git commit.

Walk every commit/tree reachable from the frozen base so every finding keeps
exact (commit, path, blob) provenance.  Automatic exclusions are deliberately
limited to structured records that explicitly bind a state field to an outcome
field.  Unstructured text/source is never promoted automatically: suspicious
provenances are emitted for review instead.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
from collections import defaultdict

STATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})(?!\d)")
OUTCOME_RE = re.compile(r"\b(WIN|LOSS)\b", re.I)
STRUCTURED_EXT = {'.csv', '.tsv', '.json', '.jsonl'}
REVIEW_EXT = {
    '.md', '.txt', '.log', '.py', '.pyi', '.cpp', '.cc', '.cxx', '.c', '.h',
    '.hpp', '.inc', '.rs', '.sh', '.ps1', '.yml', '.yaml', '.toml'
}
STATE_KEYS = ('state', 'position', 'stones')
OUTCOME_KEYS = ('outcome', 'result', 'label')


def git(*args: str, binary: bool = False):
    p = subprocess.run(['git', *args], check=True, stdout=subprocess.PIPE)
    return p.stdout if binary else p.stdout.decode('utf-8', errors='strict')


def canonical(st):
    pts = tuple(sorted(st)); best = None
    for t in range(8):
        q=[]
        for p in pts:
            x,y=p%10,p//10
            if t==0: a,b=x,y
            elif t==1: a,b=9-y,x
            elif t==2: a,b=9-x,9-y
            elif t==3: a,b=y,9-x
            elif t==4: a,b=9-x,y
            elif t==5: a,b=x,9-y
            elif t==6: a,b=y,x
            else: a,b=9-y,9-x
            q.append(b*10+a)
        z=tuple(sorted(q)); best=z if best is None or z<best else best
    return ','.join(map(str,best))


def valid_state(xs):
    return len(set(xs)) == 4 and all(0 <= x < 100 for x in xs)


def state_from_value(v):
    if isinstance(v, (list, tuple)) and len(v) == 4 and all(isinstance(x, int) and not isinstance(x, bool) for x in v):
        xs=tuple(v)
    elif isinstance(v, str):
        m=STATE_RE.fullmatch(v.strip())
        if not m: return None
        xs=tuple(map(int,m.groups()))
    else:
        return None
    return xs if valid_state(xs) else None


def explicit_record(obj):
    if not isinstance(obj, dict): return None
    lower={str(k).lower():k for k in obj}
    sk=next((lower[k] for k in STATE_KEYS if k in lower),None)
    ok=next((lower[k] for k in OUTCOME_KEYS if k in lower),None)
    if sk is None or ok is None: return None
    xs=state_from_value(obj.get(sk)); outcome=str(obj.get(ok, '')).strip().upper()
    if xs is None or outcome not in {'WIN','LOSS'}: return None
    return canonical(xs), outcome


def parse_delimited(text, delimiter):
    out=[]
    try: rows=csv.DictReader(io.StringIO(text), delimiter=delimiter)
    except csv.Error: return out
    try:
        for i,r in enumerate(rows,2):
            hit=explicit_record(r)
            if hit: out.append((*hit,f'row:{i}'))
    except csv.Error:
        return out
    return out


def walk_json(obj, loc='$'):
    out=[]
    hit=explicit_record(obj)
    if hit: out.append((*hit,loc))
    if isinstance(obj, dict):
        for k,v in obj.items(): out.extend(walk_json(v, f'{loc}.{k}'))
    elif isinstance(obj, list):
        for i,v in enumerate(obj): out.extend(walk_json(v, f'{loc}[{i}]'))
    return out


def parse_json(text, jsonl=False):
    out=[]
    try:
        if jsonl:
            for i,line in enumerate(text.splitlines(),1):
                if not line.strip(): continue
                obj=json.loads(line)
                out.extend(walk_json(obj, f'line:{i}'))
        else:
            out=walk_json(json.loads(text))
    except (json.JSONDecodeError, TypeError):
        return []
    return out


def parser_kind(path):
    ext=os.path.splitext(path.lower())[1]
    if ext == '.csv': return 'csv'
    if ext == '.tsv': return 'tsv'
    if ext == '.json': return 'json'
    if ext == '.jsonl': return 'jsonl'
    if ext in REVIEW_EXT: return 'review'
    return None


def review_hits(text, radius=3):
    lines=text.splitlines(); hits=[]
    state_lines={i for i,line in enumerate(lines) if STATE_RE.search(line)}
    outcome_lines={i for i,line in enumerate(lines) if OUTCOME_RE.search(line)}
    for i in sorted(state_lines):
        near=[j for j in outcome_lines if abs(j-i) <= radius]
        if not near: continue
        lo=max(0,min([i,*near])-radius); hi=min(len(lines),max([i,*near])+radius+1)
        hits.append({'state_line':i+1,'outcome_lines':[j+1 for j in near],
                     'context_start':lo+1,'context':'\n'.join(lines[lo:hi])})
    return hits


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('base', help='full frozen base commit SHA')
    ap.add_argument('--json-out')
    a=ap.parse_args()
    commits=git('rev-list',a.base).splitlines()
    blob_prov=defaultdict(list)
    for c in commits:
        raw=git('ls-tree','-r','-z',c,binary=True)
        for rec in raw.split(b'\0'):
            if not rec: continue
            meta,path=rec.split(b'\t',1); mode,typ,sha=meta.decode().split()
            if typ=='blob': blob_prov[sha].append((c,path.decode('utf-8','surrogateescape')))

    labels=defaultdict(lambda: {'WIN':[], 'LOSS':[]})
    review=[]
    stats={'commits':len(commits),'unique_blobs':len(blob_prov),'candidate_blobs':0,
           'decoded_blobs':0,'skipped_binary_or_nontext':0,'ambiguous_decode':0,
           'structured_provenances':0,'review_candidate_provenances':0}
    text_cache={}; parse_cache={}; review_cache={}

    for sha,prov in blob_prov.items():
        relevant=[(c,p,parser_kind(p)) for c,p in prov if parser_kind(p) is not None]
        if not relevant:
            stats['skipped_binary_or_nontext']+=1; continue
        stats['candidate_blobs']+=1
        if sha not in text_cache:
            data=git('cat-file','blob',sha,binary=True)
            try: text_cache[sha]=data.decode('utf-8')
            except UnicodeDecodeError: text_cache[sha]=None
        text=text_cache[sha]
        if text is None:
            stats['ambiguous_decode']+=1; continue
        stats['decoded_blobs']+=1

        for c,p,kind in relevant:
            if kind == 'review':
                key=(sha,'review')
                if key not in review_cache: review_cache[key]=review_hits(text)
                if review_cache[key]:
                    stats['review_candidate_provenances']+=1
                    review.append({'commit':c,'path':p,'blob':sha,'hits':review_cache[key]})
                continue

            stats['structured_provenances']+=1
            key=(sha,kind)
            if key not in parse_cache:
                if kind == 'csv': parsed=parse_delimited(text, ',')
                elif kind == 'tsv': parsed=parse_delimited(text, '\t')
                elif kind == 'json': parsed=parse_json(text)
                else: parsed=parse_json(text, jsonl=True)
                parse_cache[key]=parsed
            for state,outcome,loc in parse_cache[key]:
                labels[state][outcome].append({'commit':c,'path':p,'blob':sha,'location':loc})

    conflicts={k:v for k,v in labels.items() if v['WIN'] and v['LOSS']}
    report={'base':a.base,'stats':stats,'canonical_keys':len(labels),
            'conflict_keys':len(conflicts),'manifest_gate_open':not conflicts and not review,
            'labels':dict(labels),'conflicts':conflicts,'review_candidate_provenances':review}
    print(json.dumps({k:v for k,v in report.items() if k not in {'labels','conflicts','review_candidate_provenances'}},indent=2))
    if conflicts: print(f'WARNING: {len(conflicts)} canonical keys have both WIN and LOSS', flush=True)
    if review: print(f'BLOCKED: {len(review)} review candidate provenances remain', flush=True)
    if a.json_out:
        with open(a.json_out,'w',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2,sort_keys=True)

if __name__=='__main__': main()

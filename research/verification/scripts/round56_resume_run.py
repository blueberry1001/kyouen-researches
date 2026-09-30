"""Run one bounded lexicographic suffix, recording its parent and hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = '/home/yuubi/round28_n7/round56_resume'


def invoke(n,k,root,seconds,prefix,enumerate_all=False,node_limit=0):
    command = ['wsl','--exec',BINARY,str(n),str(k),str(seconds),str(root),
               ','.join(map(str,prefix)) if prefix else '-',str(int(enumerate_all)),str(node_limit)]
    result = subprocess.run(command,capture_output=True,text=True)
    data = json.loads(result.stdout)
    assert data['n']==n and data['k']==k and data['first_stone_root']==root
    assert data['resume_prefix']==prefix
    if not data['complete']:
        assert data['timeout_prefix'] and not data['found']
    return data, result.returncode


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=int,required=True,choices=range(5))
    parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--step',type=int,required=True)
    parser.add_argument('--parent',required=True,help='JSON basename under verification')
    args=parser.parse_args()
    parent=ROOT/args.parent
    assert parent.parent==ROOT and parent.exists()
    previous=json.loads(parent.read_text())
    assert previous['n']==10 and previous['k']==8 and previous['first_stone_root']==args.root
    assert previous['complete'] is False and previous['found'] is False
    if 'timeout_prefix' in previous:
        prefix=previous['timeout_prefix']
        origin='saved timeout frontier (active branch is repeated)'
        assert previous['sha256']['scripts/round56_resumable_kmin.cpp']==hashlib.sha256((ROOT/'scripts/round56_resumable_kmin.cpp').read_bytes()).hexdigest()
    else:
        assert args.parent==f'round53_n10_k8_root{args.root}.json'
        assert previous['nodes_by_depth'][1]==1
        # With only one stone present, no point is blocked, no depth-two
        # branch is skipped. The last entered branch was interrupted.
        prefix=[args.root,args.root+previous['nodes_by_depth'][2]]
        origin='round53 completed depth-two prefix; active depth-two branch is repeated'
    print('START',args.root,'step',args.step,'frontier',prefix,flush=True)
    data,exit_code=invoke(10,8,args.root,args.seconds,prefix)
    files=['scripts/round53_n10_eight_roots.cpp','scripts/round56_resumable_kmin.cpp',
           'scripts/round56_resume_run.py',args.parent]
    data.update({'parent':args.parent,'frontier_origin':origin,'native_exit_code':exit_code,
                 'step':args.step,'requested_seconds':args.seconds,
                 'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}})
    path=ROOT/f'round56_n10_k8_root{args.root}_step{args.step}.json'
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print('SAVED',path.name,'complete',data['complete'],'found',data['found'],
          'nodes',data['nodes'],'next',data['timeout_prefix'],flush=True)


if __name__=='__main__':
    main()

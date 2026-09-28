"""Compile the independent checker with the existing WSL g++; no installs.

Write a new certificate per parameter pair; old round6 files stay untouched.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--span',type=int,default=128)
    parser.add_argument('--coefficient',type=int,default=2)
    args = parser.parse_args()
    source = Path(__file__).with_suffix('.cpp').with_name('round7_ap_parabola.cpp').resolve()
    wsl_source = '/mnt/'+source.drive[0].lower()+source.as_posix()[2:]
    binary = '/tmp/round7_ap_parabola'
    subprocess.run(['wsl','g++','-O3','-std=c++17',wsl_source,'-o',binary],check=True)
    start = time.monotonic()
    proc = subprocess.run(['wsl',binary,str(args.span),str(args.coefficient)],
                          text=True,capture_output=True,check=True)
    result = json.loads(proc.stdout)
    result['elapsed_seconds'] = time.monotonic()-start
    result['progress_log'] = proc.stderr.splitlines()
    result['status'] = 'bounded row-span certificate, NOT an unbounded-span proof'
    if args.span==39 and args.coefficient==2:
        old = json.loads((source.parents[1]/'round6_ap_parabola_a2_span39.json').read_text(encoding='utf-8'))
        assert result['patterns']==old['normalized_patterns']
        assert result['by_rows']==[old['patterns_by_distinct_rows'][str(i)] for i in (2,3,4)]
        assert result['degrees']==[old['polynomial_degrees'][str(i)] for i in (0,1,2)]
        assert result['negative_roots']==old['roots_below_family']['negative']
        assert result['nonnegative_roots']==old['roots_below_family'].get('nonnegative',0)
        result['round6_independent_match']=True
    target = source.parents[1]/f'round7_ap_parabola_a{args.coefficient}_span{args.span}.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
    print(target,flush=True)


if __name__=='__main__':
    main()

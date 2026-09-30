"""Fresh translated determinant geometry for independent B065 curve census."""
from pathlib import Path
from round25_forced_verify import geometry

ROOT=Path(__file__).resolve().parents[1]


def main():
    for n in (4,5,6,7):
        _,quads,curves=geometry(n)
        text=f'{n} {n*n} {len(quads)}\n'+' '.join(map(str,quads))+'\n'
        text+=str(len(curves))+'\n'+' '.join(map(str,curves))+'\n'
        (ROOT/f'round39_n{n}_input.txt').write_text(text,encoding='utf-8',newline='\n')
        print(n,len(quads),len(curves))


if __name__=='__main__':main()

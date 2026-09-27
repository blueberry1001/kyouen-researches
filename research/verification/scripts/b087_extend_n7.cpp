// B087 probe n=7->8: can any 7x7 max set (14) embed into 8x8 and add 1 stone (=15)?
#include <bits/stdc++.h>
using namespace std;
using u64 = uint64_t;

static int N, V;
static vector<vector<u64>> triples_by_pt;

static void build_geometry(int n) {
    N = n; V = n * n;
    triples_by_pt.assign(V, {});
    vector<array<long long,4>> rows(V);
    for (int y=0;y<n;y++) for (int x=0;x<n;x++)
        rows[y*n+x] = {(long long)x*x+(long long)y*y, x, y, 1};
    for (int a=0;a<V-3;a++) for (int b=a+1;b<V-2;b++)
    for (int c=b+1;c<V-1;c++) for (int d=c+1;d<V;d++) {
        int ids[4]={a,b,c,d};
        long long m[4][4];
        for (int i=0;i<4;i++) for (int j=0;j<4;j++) m[i][j]=rows[ids[i]][j];
        long long det=0;
        for (int i=0;i<4;i++) {
            long long mm[3][3]; int ri=0;
            for (int r2=0;r2<4;r2++) { if (r2==i) continue; int ci=0;
                for (int c2=1;c2<4;c2++) mm[ri][ci++]=m[r2][c2]; ri++; }
            long long det3 = mm[0][0]*(mm[1][1]*mm[2][2]-mm[1][2]*mm[2][1])
                           - mm[0][1]*(mm[1][0]*mm[2][2]-mm[1][2]*mm[2][0])
                           + mm[0][2]*(mm[1][0]*mm[2][1]-mm[1][1]*mm[2][0]);
            det += (i%2==0?1:-1)*m[i][0]*det3;
        }
        if (det==0) {
            for (int t=0;t<4;t++) {
                u64 o=0;
                for (int s=0;s<4;s++) if (s!=t) o |= 1ULL<<ids[s];
                triples_by_pt[ids[t]].push_back(o);
            }
        }
    }
}

static bool can_add(u64 ch, int p) {
    if (ch & (1ULL<<p)) return false;
    for (u64 t : triples_by_pt[p]) if ((ch & t)==t) return false;
    return true;
}

int main() {
    build_geometry(7);
    FILE* f = fopen("night-research/maxsafe_n7_K14.bin","rb");
    if (!f) { fprintf(stderr,"open bin failed\n"); return 1; }
    vector<u64> sets;
    u64 v;
    while (fread(&v, sizeof(u64), 1, f)==1) sets.push_back(v);
    fclose(f);
    fprintf(stderr,"loaded %zu sets\n", sets.size());

    build_geometry(8);
    int translations[4][2] = {{0,0},{0,1},{1,0},{1,1}};
    int can15=0, tested=0;
    int add_count_hist[16]={0};
    for (u64 s7 : sets) {
        for (auto &tr : translations) {
            int ox=tr[0], oy=tr[1];
            u64 ch=0; int k=0; bool ok=true;
            for (int y=0;y<7;y++) for (int x=0;x<7;x++) {
                int id7=y*7+x;
                if (s7 & (1ULL<<id7)) {
                    int X=x+ox, Y=y+oy;
                    int id8=Y*8+X;
                    if (!can_add(ch, id8)) { ok=false; break; }
                    ch |= (1ULL<<id8); k++;
                }
            }
            if (!ok) continue;
            tested++;
            int nadd=0;
            for (int p=0;p<V;p++) if (can_add(ch,p)) nadd++;
            add_count_hist[nadd]++;
            if (nadd>0) can15++;
        }
    }
    printf("{\n  \"n_sets\": %zu,\n  \"tested_embeddings\": %d,\n  \"embeddings_with_at_least_one_add\": %d,\n  \"add_count_hist\": {", sets.size(), tested, can15);
    bool first=true;
    for (int i=0;i<16;i++) if (add_count_hist[i]) {
        if (!first) printf(",");
        printf("\"%d\": %d", i, add_count_hist[i]);
        first=false;
    }
    printf("}\n}\n");
    return 0;
}

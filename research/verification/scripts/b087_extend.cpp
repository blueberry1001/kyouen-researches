// B087 probe: can any n=6 maximum safe set (size 11) be extended to a
// size-14 safe set on 7x7 under the 4 translation embeddings?
// Usage: b087_extend.exe  (reads night-research/maxsafe_n6_K11.bin)
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

// max extension size from seed (DFS with simple bound)
static int best;
static void dfs_extend(u64 ch, int k, int start, int budget) {
    if (k > best) best = k;
    if (k == 14) return;
    if (budget==0) return;
    for (int p=start;p<V;p++) if (can_add(ch,p)) {
        dfs_extend(ch | (1ULL<<p), k+1, p+1, budget-1);
        if (best==14) return;
    }
}

int main() {
    build_geometry(6);
    FILE* f = fopen("night-research/maxsafe_n6_K11.bin","rb");
    if (!f) { fprintf(stderr,"open bin failed\n"); return 1; }
    vector<u64> sets;
    u64 v;
    while (fread(&v, sizeof(u64), 1, f)==1) sets.push_back(v);
    fclose(f);
    fprintf(stderr,"loaded %zu sets\n", sets.size());

    // rebuild geometry at n=7
    build_geometry(7);
    int translations[4][2] = {{0,0},{0,1},{1,0},{1,1}};
    int reach_hist[15]={0};
    int can14=0, tested=0;
    int max_reach=0;
    vector<string> examples;
    for (u64 s6 : sets) {
        for (auto &tr : translations) {
            int ox=tr[0], oy=tr[1];
            u64 ch=0; int k=0;
            bool ok=true;
            for (int y=0;y<6;y++) for (int x=0;x<6;x++) {
                int id6=y*6+x;
                if (s6 & (1ULL<<id6)) {
                    int X=x+ox, Y=y+oy;
                    int id7=Y*7+X;
                    // must be safe with already placed
                    // check can_add against current, then set
                    if (!can_add(ch, id7)) { ok=false; break; }
                    ch |= (1ULL<<id7); k++;
                }
            }
            if (!ok) continue;
            tested++;
            best=k;
            dfs_extend(ch, k, 0, 14-k);
            reach_hist[best]++;
            if (best>max_reach) max_reach=best;
            if (best==14) {
                can14++;
                if (examples.size()<3) {
                    char buf[128];
                    snprintf(buf,sizeof(buf),"set6=%llx tr=%d,%d", (unsigned long long)s6, ox, oy);
                    examples.push_back(buf);
                }
            }
        }
    }
    printf("{\n  \"tested_embeddings\": %d,\n  \"can_reach_14\": %d,\n  \"max_reach\": %d,\n  \"reach_hist\": {", tested, can14, max_reach);
    bool first=true;
    for (int i=0;i<15;i++) if (reach_hist[i]) {
        if (!first) printf(",");
        printf("\"%d\": %d", i, reach_hist[i]);
        first=false;
    }
    printf("},\n  \"examples\": [");
    for (size_t i=0;i<examples.size();i++) {
        if (i) printf(",");
        printf("\"%s\"", examples[i].c_str());
    }
    printf("]\n}\n");
    return 0;
}

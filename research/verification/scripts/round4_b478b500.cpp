// round4_b478b500.cpp
// 担当: B479 (円/直線束分解), B482-B490 (n=4 全状態統計 + 真 T*/WFT)
#include <cstdio>
#include <cstdint>
#include <cmath>
#include <vector>
#include <array>
#include <map>
#include <set>
#include <string>
#include <algorithm>
#include <numeric>
#include "kc_core.h"
using kc::u64; using namespace std;

static long long C4(int m){ if(m<4) return 0; long long r=1; for(int i=0;i<4;i++) r=r*(m-i)/(i+1); return r; }

// ---- 円/直線の原始鍵 ----
struct CircKey {
    long long A,D,E,F; bool isLine;
    bool operator<(const CircKey&o)const{ return tie(A,D,E,F,isLine)<tie(o.A,o.D,o.E,o.F,o.isLine); }
};
static CircKey circle_or_line(int p1,int p2,int p3,int p4,
                              const vector<int>&X,const vector<int>&Y){
    long long x1=X[p1],y1=Y[p1],x2=X[p2],y2=Y[p2],x3=X[p3],y3=Y[p3],x4=X[p4],y4=Y[p4];
    // 共線判定: 3 点の外積
    long long d1=(x2-x1)*(y3-y1)-(y2-y1)*(x3-x1);
    long long d2=(x2-x1)*(y4-y1)-(y2-y1)*(x4-x1);
    if(d1==0 && d2==0){
        // 直線: 原始方向 (dx,dy) と切片
        long long dx=x2-x1, dy=y2-y1;
        long long g=std::__gcd(std::llabs(dx),std::llabs(dy));
        if(g){ dx/=g; dy/=g; }
        if(dx<0 || (dx==0 && dy<0)){ dx=-dx; dy=-dy; }
        // 切片: dx*y - dy*x = c
        long long c = dx*y1 - dy*x1;
        long long gg=std::__gcd(std::__gcd(std::llabs(dx),std::llabs(dy)),std::llabs(c));
        if(gg){ dx/=gg; dy/=gg; c/=gg; }
        return {0,dx,dy,c,true};
    }
    // 円: A(x^2+y^2)+Dx+Ey+F=0 原始化
    long long s1=x1*x1+y1*y1,s2=x2*x2+y2*y2,s3=x3*x3+y3*y3,s4=x4*x4+y4*y4;
    // 4x4 決定式を A,D,E,F について解く
    long long M[4][4]={{s1,x1,y1,1},{s2,x2,y2,1},{s3,x3,y3,1},{s4,x4,y4,1}};
    long long v[4]={0,0,0,0};
    // Cramer
    long long det=kc::det4(M);
    long long A,D,E,F;
    for(int c=0;c<4;c++){
        long long T[4][4];
        for(int r=0;r<4;r++)for(int cc=0;cc<4;cc++) T[r][cc]=(cc==c)?0:M[r][cc];
        v[c]=(c%2==0?1:-1)*kc::det4(T);
    }
    A=v[0]; D=v[1]; E=v[2]; F=v[3];
    (void)det;
    long long g=std::gcd(std::gcd(std::gcd(std::llabs(A),std::llabs(D)),std::llabs(E)),std::llabs(F));
    if(g==0) g=1;
    A/=g; D/=g; E/=g; F/=g;
    if(A<0){A=-A;D=-D;E=-E;F=-F;}
    return {A,D,E,F,false};
}

// ---- Spearman ----
static double rankify(vector<double>&v){
    int n=v.size(); vector<int> idx(n); for(int i=0;i<n;i++)idx[i]=i;
    sort(idx.begin(),idx.end(),[&](int a,int b){return v[a]<v[b];});
    vector<double> r(n);
    int i=0;
    while(i<n){ int j=i; while(j+1<n && v[idx[j+1]]==v[idx[i]]) j++;
        double avg=(i+j)/2.0+1.0; for(int t=i;t<=j;t++) r[idx[t]]=avg; i=j+1; }
    v=r; return 0;
}
static double pearson(vector<double>&a, vector<double>&b){
    int n=a.size(); if(n<3) return NAN;
    double ma=0,mb=0; for(int i=0;i<n;i++){ma+=a[i];mb+=b[i];} ma/=n; mb/=n;
    double sa=0,sb=0,sab=0;
    for(int i=0;i<n;i++){ double x=a[i]-ma,y=b[i]-mb; sa+=x*x; sb+=y*y; sab+=x*y; }
    if(sa<=0||sb<=0) return NAN;
    return sab/std::sqrt(sa*sb);
}
static double spearman(vector<double> a, vector<double> b){
    if(a.size()<3||a.size()!=b.size()) return NAN;
    rankify(a); rankify(b); return pearson(a,b);
}

int main(){
    FILE* f=fopen("research/verification/round4_b478b500.json","w");
    fprintf(f,"{\n");

    // ================= B479: 円/直線束分解 =================
    fprintf(f,"\"B479\": {\n \"definition\": \"各禁止4点組を一意の円/直線(原始形)に割当。束サイズ=C(m,4) (m=その円/直線上の盤点数)。Z=各円/直線の寄与の和。\",\n");
    fprintf(f," \"m_hist_and_bundles\": {\n");
    bool first=true;
    for(int n=4;n<=7;n++){
        kc::Board B; kc::build_square(B,n);
        map<CircKey,int> cnt; map<CircKey,int> mpts;
        for(u64 q:B.quads){
            int id[4]; u64 t=q; for(int z=0;z<4;z++){id[z]=__builtin_ctzll(t);t&=t-1;}
            CircKey K=circle_or_line(id[0],id[1],id[2],id[3],B.pt_x,B.pt_y);
            cnt[K]++;
        }
        // 各円/直線の盤上点数 m を数える
        map<CircKey,set<int>> onp;
        for(u64 q:B.quads){
            int id[4]; u64 t=q; for(int z=0;z<4;z++){id[z]=__builtin_ctzll(t);t&=t-1;}
            CircKey K=circle_or_line(id[0],id[1],id[2],id[3],B.pt_x,B.pt_y);
            for(int z=0;z<4;z++) onp[K].insert(id[z]);
        }
        // m>=5 の円/直線のみ（m=4 は自明の束サイズ1）
        map<int,long long> mcount;   // m -> 個数
        long long q4_ge5=0, F=(long long)B.quads.size();
        for(auto&kv:cnt){ int m=(int)onp[kv.first].size(); mcount[m]++; if(m>=5) q4_ge5+=kv.second; }
        if(!first) fprintf(f,",\n"); first=false;
        fprintf(f,"  \"%d\": {\"F\": %lld, \"n_circles\": %lld, \"m_hist\": {",n,F,(long long)cnt.size());
        bool f2=true; long long mge5=0;
        for(auto&kv:mcount){ if(kv.first<4) continue; if(!f2)fprintf(f,","); f2=false;
            fprintf(f,"\"%d\": %lld",kv.first,kv.second); if(kv.first>=5) mge5+=kv.second; }
        fprintf(f,"}, \"n_curve_lines_m_ge5\": %lld, \"frac_of_F\": %.6f, \"bundle_sizes\": {",mge5,(double)q4_ge5/F);
        f2=true;
        for(auto&kv:mcount){ if(kv.first<5) continue; if(!f2)fprintf(f,","); f2=false;
            fprintf(f,"\"C(%d,4)=%lld\": %lld",kv.first,C4(kv.first),kv.second); }
        fprintf(f,"}}");
    }
    fprintf(f,"\n },\n");

    // --- B478  tie-in: 原子が C(m,4) か ---
    fprintf(f,"\"B478_atom_check\": {\n");
    fprintf(f," \"note\": \"既存 exact_dists の原子 {5,15,35} は C(5,4),C(6,4),C(7,4) と一致するか\",\n");
    fprintf(f," \"observed_atoms\": {\"n4_k5\": [5], \"n4_k7\": [15,35], \"n5_k6\": [5,15], \"n3_k7\": [3,4,5]},\n");
    fprintf(f," \"C(m,4)_table\": {\"C(4,4)\":1,\"C(5,4)\":5,\"C(6,4)\":15,\"C(7,4)\":35,\"C(8,4)\":70}\n},\n");

    // ================= n=3,4 全状態 =================
    for(int n=3;n<=5;n++){
        kc::Board B; kc::build_square(B,n);
        int V=B.V; size_t SZ=(size_t)1<<V;
        vector<char> safe(SZ,0); vector<int> g(SZ,-1);
        vector<long double> W(SZ,0);      // ランダム勝率（手番側）
        vector<int> Lsz(SZ,0);
        vector<array<unsigned char,64>> Tm(n?0:0); // unused
        // 安全判定
        for(size_t m=0;m<SZ;m++){
            bool ok=true; u64 occ=m;
            for(u64 t:B.triples_by_pt[0]){(void)t;}
            // 全 quad チェック 대신: triples_by_pt で高速判定
            for(int p=0;p<V && ok;p++){
                if(!((occ>>p)&1)) continue;
                for(u64 t:B.triples_by_pt[p]) if((occ&t)==t){ ok=false; break; }
            }
            safe[m]=ok;
        }
        long long n_safe=0; for(size_t m=0;m<SZ;m++) if(safe[m]) n_safe++;
        // 極大集合（terminal）
        vector<u64> maximal;
        for(size_t m=0;m<SZ;m++) if(safe[m]){
            u64 lm=kc::legal_mask(B,(u64)m);
            if(lm==0) maximal.push_back((u64)m);
        }
        int Mmax=(int)maximal.size();
        vector<int> mid(Mmax); for(int i=0;i<Mmax;i++) mid[i]=__builtin_popcountll(maximal[i]);
        fprintf(f,"\"n%d\": {\"V\": %d, \"n_safe\": %lld, \"n_maximal\": %d},\n",
                n,V,n_safe,Mmax);
        if(n==4){
            fprintf(f,"\"B483_bridge3\": {\n");
            // bridge3: 禁止4点組で occ に 1 点だけ、残り 3 空 → 「三点橋」
            struct Cell{long long n=0, sumB=0;};
            map<pair<int,int>,Cell> cells;
            long long totalB3=0;
            for(size_t m=0;m<SZ;m++){
                if(!safe[m]) continue;
                u64 occ=(u64)m;
                int k=__builtin_popcountll(occ);
                int L=__builtin_popcountll(kc::legal_mask(B,occ));
                int b3=0;
                for(u64 q:B.quads){ int c=__builtin_popcountll(q&occ); if(c==1) b3++; }
                totalB3+=b3;
                auto&cc=cells[{k,L}];
                cc.n++; cc.sumB+=b3;
            }
            fprintf(f,"   \"total_bridge3\": %lld, \"cells\": [",totalB3);
            bool f3=true;
            for(auto&kv:cells){ if(!f3)fprintf(f,","); f3=false;
                fprintf(f,"{\"k\": %d, \"L\": %d, \"n\": %lld, \"mean_bridge3\": %.6f}",kv.first.first,kv.first.second,kv.second.n,(double)kv.second.sumB/kv.second.n); }
            fprintf(f,"]\n  },\n");
        }
        if(n==4) fprintf(f,",\n");
        if(n==5) fprintf(f,",\n");
    }
    fprintf(f,"\"_end\": 1\n}\n");
    fclose(f);
    printf("done\n");
    return 0;
}

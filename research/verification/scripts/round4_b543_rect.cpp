// round4_b543_rect.cpp -- Round4 verification worker (2-row and 3-row long scans).
//
// Builds on the exact characterisations already established:
//   * 2-row board {0..m-1} x {0,1} (B214): a forbidden 4-set is either 4 points
//     in one row, or a 2+2 split with a+b = c+d.  A state is (A,B) with
//     |A|,|B| <= 3 and Sigma2(A) cap Sigma2(B) = {}.  Key packs la,A,lb,B into
//     one u64 (columns < 256, so m <= 255).
//   * 3-row board {0..m-1} x {0,1,2}: a 3-row strip has no 4 collinear points,
//     so every forbidden 4-set is concyclic and has row occupancy (2,2,0) or
//     (2,1,1).  Generic hypergraph, states are u64 point masks (3m <= 63).
//     g(empty) = mex_p g({p}) and W = {p : g({p}) = 0}; the 3m single-move
//     closures are independent, so they run in parallel, one memo each.
//
// Integer arithmetic only; ratios are reported as exact integer pairs.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cmath>
#include <string>
#include <vector>
#include <array>
#include <algorithm>
#include <functional>
#include <chrono>

using u64 = uint64_t;
using u32 = uint32_t;
using u8  = uint8_t;
using i64 = long long;

static double now() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

static i64 det4(const i64 r[4][4]) {          // identical to kc_core.h::det4
    i64 total = 0;
    for (int i = 0; i < 4; ++i) {
        i64 mm[3][3]; int ri = 0;
        for (int r2 = 0; r2 < 4; ++r2) {
            if (r2 == i) continue;
            int ci = 0;
            for (int c2 = 1; c2 < 4; ++c2) mm[ri][ci++] = r[r2][c2];
            ++ri;
        }
        i64 d3 = mm[0][0]*(mm[1][1]*mm[2][2]-mm[1][2]*mm[2][1])
               - mm[0][1]*(mm[1][0]*mm[2][2]-mm[1][2]*mm[2][0])
               + mm[0][2]*(mm[1][0]*mm[2][1]-mm[1][1]*mm[2][0]);
        total += (i%2==0?1:-1)*r[i][0]*d3;
    }
    return total;
}

struct HM {
    std::vector<u64> K; std::vector<u8> V;
    size_t mask = 0, cnt = 0, cap = 0;
    void init(size_t c) { cap = c; K.assign(c, 0); V.assign(c, 0); mask = c - 1; cnt = 0; }
    static u64 mix(u64 x) { x^=x>>33; x*=0xff51afd7ed558ccdULL; x^=x>>33; x*=0xc4ceb9fe1a85ec53ULL; x^=x>>33; return x; }
    size_t slot(u64 key) const { return mix(key) & mask; }
    bool get(u64 key, int& out) const {
        size_t i = slot(key);
        while (K[i]) { if (K[i]==key) { out=(int)V[i]-1; return true; } i=(i+1)&mask; }
        return false;
    }
    void put(u64 key, int v) {
        size_t i = slot(key);
        while (K[i]) { if (K[i]==key) { V[i]=(u8)(v+1); return; } i=(i+1)&mask; }
        K[i]=key; V[i]=(u8)(v+1); ++cnt;
        if (cnt*2 > cap) { grow(); put(key, v); }
    }
    void grow() {
        std::vector<u64> ok; ok.swap(K); std::vector<u8> ov; ov.swap(V);
        cap *= 2; K.assign(cap,0); V.assign(cap,0); mask=cap-1; cnt=0;
        for (size_t j=0;j<ok.size();++j) if (ok[j]) put(ok[j], (int)ov[j]-1);
    }
};

static i64 C3[65][65];
static void initC(){ for(int n=0;n<=64;++n){ C3[n][0]=1; for(int k=1;k<=n;++k) C3[n][k]=(k>n)?0:C3[n-1][k-1]+C3[n-1][k]; } }
static inline int crank3(int t0,int t1,int t2){ return t0 + C3[t1][2] + C3[t2][3]; }

// ============================================================== 2-row board =
struct TwoRow {
    int m = 0; HM memo;
    u64 enc(int la, const int* A, int lb, const int* B) const {
        return (u64)la | ((u64)A[0]<<2) | ((u64)A[1]<<10) | ((u64)A[2]<<18)
             | ((u64)lb<<26) | ((u64)B[0]<<28) | ((u64)B[1]<<36) | ((u64)B[2]<<44);
    }
    void decode(u64 k, int& la, int* A, int& lb, int* B) const {
        la=(int)(k&3); A[0]=(int)((k>>2)&255); A[1]=(int)((k>>10)&255); A[2]=(int)((k>>18)&255);
        lb=(int)((k>>26)&3); B[0]=(int)((k>>28)&255); B[1]=(int)((k>>36)&255); B[2]=(int)((k>>44)&255);
    }
    static void sumsOf(int la, const int* A, int* s, int& n) {
        n = 0;
        if (la == 2) s[n++] = A[0]+A[1];
        if (la == 3) { s[n++] = A[0]+A[1]; s[n++] = A[0]+A[2]; s[n++] = A[1]+A[2]; }
    }
    int g(int la, const int* A, int lb, const int* B) {
        u64 k = enc(la,A,lb,B);
        int c; if (memo.get(k,c)) return c;
        int sA[3],sB[3],nA,nB;
        sumsOf(la,A,sA,nA); sumsOf(lb,B,sB,nB);
        bool seen[64]={false};
        if (la<3) for (int x=0;x<m;++x) {
            bool occ=false; for(int t=0;t<la;++t) if(A[t]==x){occ=true;break;}
            if (occ) continue;
            bool bad=false;
            for(int t=0;t<la&&!bad;++t){int s=x+A[t]; for(int j=0;j<nB;++j) if(sB[j]==s){bad=true;break;}}
            if (bad) continue;
            int A2[3]={0,0,0}; int n2=0;
            for(int t=0;t<la;++t) if(A[t]<x) A2[n2++]=A[t];
            A2[n2++]=x;
            for(int t=0;t<la;++t) if(A[t]>x) A2[n2++]=A[t];
            seen[g(la+1,A2,lb,B)]=true;
        }
        if (lb<3) for (int x=0;x<m;++x) {
            bool occ=false; for(int t=0;t<lb;++t) if(B[t]==x){occ=true;break;}
            if (occ) continue;
            bool bad=false;
            for(int t=0;t<lb&&!bad;++t){int s=x+B[t]; for(int j=0;j<nA;++j) if(sA[j]==s){bad=true;break;}}
            if (bad) continue;
            int B2[3]={0,0,0}; int n2=0;
            for(int t=0;t<lb;++t) if(B[t]<x) B2[n2++]=B[t];
            B2[n2++]=x;
            for(int t=0;t<lb;++t) if(B[t]>x) B2[n2++]=B[t];
            seen[g(la,A,lb+1,B2)]=true;
        }
        int v=0; while (seen[v]) ++v;
        memo.put(k, v);
        return v;
    }
};

// ============================================================== 3-row board =
struct ThreeRow {
    int m=0, V=0, variant=0;                 // 0 all, 1 only (2,2,0), 2 only (2,1,1)
    u64 full=0;
    std::vector<int> ys;
    std::vector<u64> tri;                     // per 3-subset: mask of completing 4th points
    int nquads = 0;
    void build(int m_, int variant_, const int* ysv) {
        m=m_; V=m*3; variant=variant_;
        ys.assign(ysv, ysv+3);
        full = (1ull<<V)-1;
        tri.assign(C3[V][3], 0ull);
        std::vector<std::array<i64,4> > rows(V);
        for (int k=0;k<3;++k) for (int x=0;x<m;++x) {
            int i=k*m+x;
            rows[i] = {(i64)x*x + (i64)ys[k]*ys[k], x, ys[k], 1};
        }
        for (int a=0;a<V-3;++a) for (int b=a+1;b<V-2;++b)
        for (int c=b+1;c<V-1;++c) for (int d=c+1;d<V;++d) {
            int ids[4]={a,b,c,d};
            int cnt[3]={0,0,0};
            for (int t=0;t<4;++t) ++cnt[ids[t]/m];
            int type = (cnt[2]>=2) ? 1 : 2;
            if (variant==1 && type!=1) continue;
            if (variant==2 && type!=2) continue;
            i64 mm[4][4];
            for (int t=0;t<4;++t) for (int j=0;j<4;++j) mm[t][j]=rows[ids[t]][j];
            if (det4(mm)!=0) continue;
            ++nquads;
            u64 q[4]; for(int t=0;t<4;++t) q[t]=1ull<<ids[t];
            tri[crank3(ids[0],ids[1],ids[2])] |= q[3];
            tri[crank3(ids[0],ids[1],ids[3])] |= q[2];
            tri[crank3(ids[0],ids[2],ids[3])] |= q[1];
            tri[crank3(ids[1],ids[2],ids[3])] |= q[0];
        }
    }
    u64 blockedBy(int p, u64 mask) const {
        u64 bl=0; int pts[40], n=0;
        u64 t=mask; while(t){ pts[n++]=__builtin_ctzll(t); t&=t-1; }
        for (int i=0;i<n;++i) for (int j=i+1;j<n;++j) {
            int a=pts[i], b=pts[j], s0,s1,s2;
            if (p<a){s0=p;s1=a;s2=b;} else if (p<b){s0=a;s1=p;s2=b;} else {s0=a;s1=b;s2=p;}
            bl |= tri[crank3(s0,s1,s2)];
        }
        return bl & ~mask;
    }
    int solveFrom(u64 mask, HM& memo, int* maxstones) const {
        std::function<int(u64,u64)> go = [&](u64 mk, u64 blocked) -> int {
            int c; if (memo.get(mk, c)) return c;
            u64 avail = full & ~mk & ~blocked;
            u32 seen = 0;
            while (avail) {
                int p = __builtin_ctzll(avail); avail &= avail-1;
                int pc = __builtin_popcountll(mk)+1;
                if (maxstones && pc > *maxstones) *maxstones = pc;
                seen |= 1u << go(mk | (1ull<<p), blocked | blockedBy(p, mk));
            }
            int v=0; while (seen>>v & 1u) ++v;
            memo.put(mk, v);
            return v;
        };
        return go(mask, 0ull);
    }
};

struct Sub3 { int a,b,c; };
struct Sub2 { int a,b; };
static void allTriples(int m, std::vector<Sub3>& out) {
    out.clear();
    for (int a=0;a<m;++a) for (int b=a+1;b<m;++b) for (int c=b+1;c<m;++c) out.push_back({a,b,c});
}
static void allPairs(int m, std::vector<Sub2>& out) {
    out.clear();
    for (int a=0;a<m;++a) for (int b=a+1;b<m;++b) out.push_back({a,b});
}

static std::string J;
static void Jp(const std::string& s){ J += s; }

int main(int argc, char** argv) {
    initC();
    std::string outpath = "/tmp/round4_b543_rect.json";
    std::string sec = "12345";
    int M2 = 22, M3 = 14, M2C = 200;
    for (int i=1;i<argc;++i) {
        std::string a = argv[i];
        if (a.rfind("--out=",0)==0) outpath=a.substr(6);
        else if (a.rfind("--sec=",0)==0) sec=a.substr(6);
        else if (a.rfind("--m2=",0)==0) M2=atoi(a.c_str()+5);
        else if (a.rfind("--m3=",0)==0) M3=atoi(a.c_str()+5);
        else if (a.rfind("--m2c=",0)==0) M2C=atoi(a.c_str()+6);
    }
    auto has=[&](int s){ return sec.find(std::to_string(s))!=std::string::npos; };
    J = "{\n  \"_meta\": {\"script\": \"round4_b543_rect.cpp\"},\n";
    char buf[65536];

    // ============================================== section 1 : 2-row Grundy =
    if (has(1)) {
        fprintf(stderr,"== sec1: 2-row full Grundy m=2..%d\n", M2);
        Jp("  \"two_row\": {\n");
        double tall = now();
        for (int m=2;m<=M2;++m) {
            double s0=now();
            TwoRow T; T.m=m;
            {   double c2=(double)m*(m-1)/2, c3=c2*(m-2)/3;
                double e = 1 + 2*m + 2*c2 + 2*c3 + (double)m*m + 4*m*c2 + 4*m*c3 + c2*c2 + 2*c2*c3 + c3*c3;
                if (m<6) e*=1.2;
                size_t bits=10; while ((double)(1ull<<bits) < 3.0*e) ++bits;
                T.memo.init(1ull<<bits);
            }
            int Z[3]={0,0,0};
            int g0 = T.g(0,Z,0,Z);
            long long ghist[64]={0}, shist[16]={0}, mhist[16]={0};
            int maxg=0; long long K=0, nmax=0, cov_ok=0, cov_fail=0;
            long long tr_check=0, tr_fail=0; int worst_margin=-1;
            int rs_same=0, rs_all=0, n_first=0;
            for (int x=0;x<m;++x) for (int r=0;r<2;++r) {
                ++n_first;
                int cS=0, cA=0;
                for (int y=0;y<m;++y) {
                    if (x==y) continue;
                    // first move (r,x); reply at column y in the other row
                    int a0[3]={0,0,0}, b0[3]={0,0,0};
                    if (r==0){ a0[0]=x; b0[0]=y; } else { a0[0]=y; b0[0]=x; }
                    int gg = T.g(1,a0,1,b0);
                    if (gg==0){ ++cA; if (y==x) ++cS; }
                }
                if (cS) ++rs_same;
                if (cA==m-1) ++rs_all;
            }
            for (size_t i=0;i<T.memo.cap;++i) {
                if (!T.memo.K[i]) continue;
                u64 k=T.memo.K[i]; int gv=(int)T.memo.V[i]-1;
                if (gv<64) ++ghist[gv];
                if (gv>maxg) maxg=gv;
                int la,lb,A[3],B[3]; T.decode(k,la,A,lb,B);
                int kk=la+lb; ++shist[kk]; if (kk>K) K=kk;
                int sA[3],sB[3],nA,nB;
                TwoRow::sumsOf(la,A,sA,nA); TwoRow::sumsOf(lb,B,sB,nB);
                bool legal=false;
                if (la<3) for (int x=0;x<m&&!legal;++x){
                    bool occ=false; for(int t=0;t<la;++t) if(A[t]==x){occ=true;break;}
                    if(occ) continue;
                    for(int t=0;t<la&&!occ;++t){int s=x+A[t];for(int j=0;j<nB;++j) if(sB[j]==s){occ=true;break;}}
                    if(!occ) legal=true;
                }
                if (!legal && lb<3) for (int x=0;x<m&&!legal;++x){
                    bool occ=false; for(int t=0;t<lb;++t) if(B[t]==x){occ=true;break;}
                    if(occ) continue;
                    for(int t=0;t<lb&&!occ;++t){int s=x+B[t];for(int j=0;j<nA;++j) if(sA[j]==s){occ=true;break;}}
                    if(!occ) legal=true;
                }
                if (!legal) {
                    ++mhist[kk]; ++nmax;
                    if (kk >= 5) {
                        // (3,2) and (2,3) are the only 5-stone shapes; (3,3) is
                        // maximal iff it is safe (both rows already full).
                        bool s1=true, s2=true;
                        if (la == 2) { s2 = (A[0]+A[1] != B[0]+B[1] && A[0]+A[1] != B[0]+B[2] && A[0]+A[1] != B[1]+B[2]); }
                        if (lb == 2) { s1 = (B[0]+B[1] != A[0]+A[1] && B[0]+B[1] != A[0]+A[2] && B[0]+B[1] != A[1]+A[2]); }
                        if (s1 && s2) ++cov_ok; else ++cov_fail;
                    } else ++cov_fail;
                    // B550 translation invariance g(A,B) == g(A+1,B+1)
                    int all[6]={A[0],A[1],A[2],B[0],B[1],B[2]};
                    int hi=-1, lo=1000;
                    for (int t=0;t<la+lb;++t){ if(all[t]>hi)hi=all[t]; if(all[t]<lo)lo=all[t]; }
                    if (hi>=0 && hi<m-1) {
                        int nA2[3],nB2[3];
                        for (int t=0;t<3;++t){ nA2[t]=A[t]+1; nB2[t]=B[t]+1; }
                        ++tr_check;
                        if (T.g(la,nA2,lb,nB2)!=gv){ ++tr_fail;
                            int mg=std::min(lo,m-1-hi); if (mg>worst_margin) worst_margin=mg; }
                    }
                }
            }
            std::string gh,sh2,mh;
            for (int t=0;t<64;++t) if(ghist[t]) gh += "\""+std::to_string(t)+"\":"+std::to_string(ghist[t])+(t<63?",":"");
            for (int t=0;t<16;++t) if(shist[t]) sh2 += "\""+std::to_string(t)+"\":"+std::to_string(shist[t])+(t<15?",":"");
            for (int t=0;t<16;++t) if(mhist[t]) mh += "\""+std::to_string(t)+"\":"+std::to_string(mhist[t])+(t<15?",":"");
            snprintf(buf,sizeof buf,
                "    \"m%d\": {\"g_empty\": %d, \"n_states\": %lld, \"max_g\": %d, \"K\": %lld,"
                " \"g_hist\": {%s}, \"size_hist\": {%s}, \"maximal_hist\": {%s}, \"n_maximal\": %lld,"
                " \"cover_fail\": %lld, \"B542_same_col\": \"%d/%d\", \"B542_all_cols\": \"%d/%d\","
                " \"trans_checked\": %lld, \"trans_fail\": %lld, \"trans_worst_fail_margin\": %d, \"sec\": %.3f}%s\n",
                m, g0, (long long)T.memo.cnt, maxg, K, gh.c_str(), sh2.c_str(), mh.c_str(),
                nmax, cov_fail, rs_same, n_first, rs_all, n_first,
                tr_check, tr_fail, worst_margin, now()-s0, m==M2?"":",");
            J += buf;
            fprintf(stderr,"  m=%2d g0=%d states=%lld maxg=%d K=%lld maximal=%lld coverfail=%lld transfail=%lld/%lld same=%d/%d all=%d/%d (%.1fs)\n",
                m,g0,(long long)T.memo.cnt,maxg,K,nmax,cov_fail,tr_fail,tr_check,rs_same,n_first,rs_all,n_first,now()-s0);
            fflush(stderr);
        }
        snprintf(buf,sizeof buf,"  },\n  \"two_row_sec\": %.1f,\n", now()-tall);
        J += buf;
    }

    // ============================== section 2 : 2-row combinatorial long scan =
    if (has(2)) {
        fprintf(stderr,"== sec2: 2-row maximal/K combinatorics, m=2..%d\n", M2C);
        double t0=now();
        Jp("  \"two_row_combinatorial\": {\n");
        std::string out;
        for (int m=2;m<=M2C;++m) {
            long long n5=0, n6=0, n5bad=0, safe33=0, sep33=0;
            std::vector<Sub3> A3; std::vector<Sub2> A2;
            allTriples(m, A3); allPairs(m, A2);
            // (3,3): safe iff Sigma2 disjoint; then automatically maximal
            for (size_t ia=0; ia<A3.size(); ++ia) {
                const int *A=&A3[ia].a; int sA[3]={A[0]+A[1],A[0]+A[2],A[1]+A[2]};
                for (size_t ib=0; ib<A3.size(); ++ib) {
                    const int *B=&A3[ib].a; int sB[3]={B[0]+B[1],B[0]+B[2],B[1]+B[2]};
                    bool bad=false;
                    for (int u=0;u<3&&!bad;++u) for (int v=0;v<3;++v) if (sA[u]==sB[v]){bad=true;break;}
                    if (bad) continue;
                    ++safe33; ++n6;
                    if (sA[2] < sB[0] || sB[2] < sA[0]) ++sep33;
                }
            }
            // (3,2): safe iff b0+b1 notin Sigma2(A); maximal iff
            //         forall x notin B : x+b in Sigma2(A) for some b in B
            for (size_t ia=0; ia<A3.size(); ++ia) {
                const int *A=&A3[ia].a; int sA[3]={A[0]+A[1],A[0]+A[2],A[1]+A[2]};
                for (size_t ib=0; ib<A2.size(); ++ib) {
                    const int *B=&A2[ib].a; int sb=B[0]+B[1];
                    if (sb==sA[0]||sb==sA[1]||sb==sA[2]) continue;   // illegal state
                    bool ok=true;
                    for (int x=0;x<m;++x){
                        if (x==B[0]||x==B[1]) continue;
                        if (!(x+B[0]==sA[0]||x+B[0]==sA[1]||x+B[0]==sA[2]||
                              x+B[1]==sA[0]||x+B[1]==sA[1]||x+B[1]==sA[2])) { ok=false; break; }
                    }
                    if (ok) ++n5; else ++n5bad;
                }
            }
            long long K = (n6>0) ? 6 : ((n5>0) ? 5 : 0);
            snprintf(buf,sizeof buf,
                "    \"m%d\": {\"K\": %lld, \"n_maximal_6_3v3\": %lld, \"n_maximal_5_3v2\": %lld,"
                " \"n_mixed_3v3\": %lld, \"n_safe_3v2\": %lld}%s\n",
                m, K, n6, n5, safe33-sep33, n5+n5bad, m==M2C?"":",");
            out += buf;
            if (m<=14 || m%25==0)
                fprintf(stderr,"  m=%3d K=%lld nmax6=%lld nmax5=%lld mixed3v3=%lld safe3v2=%lld\n",
                        m,K,n6,n5,safe33-sep33,n5+n5bad);
        }
        J += out;
        snprintf(buf,sizeof buf,"  },\n  \"two_row_combinatorial_sec\": %.1f,\n", now()-t0);
        J += buf;
    }

    // ================================================= section 3 : 3-row Grundy
    if (has(3)) {
        fprintf(stderr,"== sec3: 3-row full Grundy m=3..%d (parallel per first move)\n", M3);
        Jp("  \"three_row\": {\n");
        std::string out;
        for (int m=3;m<=M3;++m) {
            double s0=now();
            int ys[3]={0,1,2};
            ThreeRow T; T.build(m,0,ys);
            std::vector<int> gval(T.V,-1), mxs(T.V,0);
            long long totstates=0;
#pragma omp parallel for schedule(dynamic,1) reduction(+:totstates)
            for (int p=0;p<T.V;++p) {
                HM H; H.init(1ull<<19);
                int mm=1;
                gval[p] = T.solveFrom(1ull<<p, H, &mm);
                mxs[p] = mm; totstates += (long long)H.cnt;
            }
            u32 seen=0; for (int p=0;p<T.V;++p) seen |= 1u<<gval[p];
            int g0=0; while (seen>>g0 & 1u) ++g0;
            int K=0; for (int p=0;p<T.V;++p) if (mxs[p]>K) K=mxs[p];
            std::string W; int nW=0;
            std::vector<int> colAny(m,0), colAll(m,1);
            for (int p=0;p<T.V;++p) {
                if (gval[p]==0) { ++nW; colAny[p%m]=1; colAll[p%m]=colAll[p%m]&&1;
                    if (nW<=90){ if(nW>1) W+=","; W+="("+std::to_string(p%m)+","+std::to_string(p/3)+")"; } }
                else colAll[p%m]=0;
            }
            std::string colsAny,colsAll;
            for (int x=0;x<m;++x){ if(colAny[x]){ if(!colsAny.empty())colsAny+=","; colsAny+=std::to_string(x);} }
            for (int x=0;x<m;++x){ if(colAll[x]){ if(!colsAll.empty())colsAll+=","; colsAll+=std::to_string(x);} }
            snprintf(buf,sizeof buf,
                "    \"m%d\": {\"g_empty\": %d, \"K\": %d, \"n_W\": %d, \"n_quads\": %d, \"n_states_sum_over_first_moves\": %lld,"
                " \"W\": [%s], \"cols_with_any_W\": [%s], \"cols_fully_in_W\": [%s], \"sec\": %.2f}%s\n",
                m, g0, K, nW, T.nquads, totstates, W.c_str(), colsAny.c_str(), colsAll.c_str(), now()-s0, m==M3?"":",");
            out += buf;
            fprintf(stderr,"  3-row m=%2d g0=%d K=%d |W|=%d quads=%d states=%lld (%.1fs)\n", m,g0,K,nW,T.nquads,totstates,now()-s0);
            fflush(stderr);
        }
        J += out;
        Jp("  },\n");
    }

    // ============================ section 4 : 3-row circle-type variants + spacing
    if (has(4)) {
        fprintf(stderr,"== sec4a: 3-row circle-type variants m=6..10\n");
        Jp("  \"three_row_variants\": {\n");
        const char* vname[3]={"all_circles","only_2_2_0","only_2_1_1"};
        std::string out;
        for (int m=6;m<=10;++m) for (int v=0;v<3;++v) {
            int ys[3]={0,1,2};
            ThreeRow T; T.build(m,v,ys);
            HM H; H.init(1ull<<22);
            int mxs=0; int g0=T.solveFrom(0ull,H,&mxs);
            HM H2; H2.init(1ull<<22); int mm=0;
            int nW=0; std::string W;
            for (int p=0;p<T.V;++p) if (T.solveFrom(1ull<<p,H2,&mm)==0) {
                ++nW; if(nW<=40){ if(nW>1) W+=","; W+="("+std::to_string(p%m)+","+std::to_string(p/3)+")"; } }
            snprintf(buf,sizeof buf,
                "    \"m%d_%s\": {\"g_empty\": %d, \"K\": %d, \"n_W\": %d, \"W\": [%s], \"n_quads\": %d}%s\n",
                m, vname[v], g0, mxs, nW, W.c_str(), T.nquads,
                (m==10&&v==2)?"":",");
            out += buf;
            fprintf(stderr,"  variant m=%d %s: g0=%d K=%d |W|=%d quads=%d\n", m, vname[v], g0, mxs, nW, T.nquads);
            fflush(stderr);
        }
        J += out;
        Jp("  },\n");
        fprintf(stderr,"== sec4b: row spacing {0,1,3}, m=3..9\n");
        Jp("  \"row_spacing_013\": {\n");
        out.clear();
        for (int m=3;m<=9;++m) {
            double s0=now();
            int ys[3]={0,1,3};
            ThreeRow T; T.build(m,0,ys);
            std::vector<int> gval(T.V,-1), mxs(T.V,0);
#pragma omp parallel for schedule(dynamic,1)
            for (int p=0;p<T.V;++p){ HM H; H.init(1ull<<19); int mm=1; gval[p]=T.solveFrom(1ull<<p,H,&mm); mxs[p]=mm; }
            u32 seen=0; for(int p=0;p<T.V;++p) seen|=1u<<gval[p];
            int g0=0; while(seen>>g0&1u) ++g0;
            int K=0; for(int p=0;p<T.V;++p) if(mxs[p]>K) K=mxs[p];
            int nW=0; for(int p=0;p<T.V;++p) if(gval[p]==0) ++nW;
            snprintf(buf,sizeof buf,
                "    \"m%d\": {\"g_empty\": %d, \"K\": %d, \"n_W\": %d, \"n_quads\": %d, \"sec\": %.2f}%s\n",
                m, g0, K, nW, T.nquads, now()-s0, m==9?"":",");
            out += buf;
            fprintf(stderr,"  spacing013 m=%d g0=%d K=%d |W|=%d quads=%d (%.1fs)\n", m,g0,K,nW,T.nquads,now()-s0);
            fflush(stderr);
        }
        J += out;
        Jp("  },\n");
    }

    // ================== section 5 : AP construction, 3 stones per row (B558) =
    if (has(5)) {
        fprintf(stderr,"== sec5: 3-stones-per-row arithmetic-progression construction\n");
        Jp("  \"ap_construction\": {\n");
        std::string out;
        for (int w=2; w<=5; ++w) {
            for (int m=2*w; m<=2*w+3; ++m) {
                if (w*m > 63) continue;
                int V=w*m;
                std::vector<std::array<int,3> > aps;
                for (int d=1; 2*d<=m-1; ++d) for (int a=0; a+2*d<=m-1; ++a) aps.push_back({a,a+d,a+2*d});
                if (aps.empty()) continue;
                std::vector<u64> quads;
                std::vector<std::array<i64,4> > rows(V);
                for (int y=0;y<w;++y) for (int x=0;x<m;++x) rows[y*m+x]={(i64)x*x+(i64)y*y,x,y,1};
                for (int a=0;a<V-3;++a) for (int b=a+1;b<V-2;++b) for (int c=b+1;c<V-1;++c) for (int d=c+1;d<V;++d) {
                    int ids[4]={a,b,c,d}; i64 mm[4][4];
                    for (int t=0;t<4;++t) for (int j=0;j<4;++j) mm[t][j]=rows[ids[t]][j];
                    if (det4(mm)!=0) continue;
                    u64 q=0; for(int t=0;t<4;++t) q|=1ull<<ids[t]; quads.push_back(q);
                }
                int best=0; std::vector<std::array<int,3> > cur, bestset; long long nodes=0;
                std::function<void(int)> dfs=[&](int r){
                    if (++nodes > 400000000LL) return;
                    if (r==w){ if ((int)cur.size()>best){best=(int)cur.size(); bestset=cur;} return; }
                    for (size_t i=0;i<aps.size();++i) {
                        u64 msk=0; for(int t=0;t<3;++t) msk|=1ull<<(r*m+aps[i][t]);
                        bool ok=true;
                        for (int t=0;t<(int)cur.size()&&ok;++t){
                            u64 pm=0; for(int u=0;u<3;++u) pm|=1ull<<(t*m+cur[t][u]);
                            u64 u2=msk|pm;
                            for (size_t z=0;z<quads.size();++z) if ((quads[z]&u2)==quads[z]){ok=false;break;}
                        }
                        if (!ok) continue;
                        cur.push_back(aps[i]); dfs(r+1); cur.pop_back();
                    }
                };
                dfs(0);
                std::string rowss;
                for (size_t z=0;z<bestset.size();++z){ if(z)rowss+=","; rowss+="("+std::to_string(bestset[z][0])+","+std::to_string(bestset[z][1])+","+std::to_string(bestset[z][2])+")"; }
                bool last = (w==5 && m==2*w+3) || (w==4 && m==2*w+3) || (w==3 && m==2*w+3) || (w==2 && m==2*w+3);
                snprintf(buf,sizeof buf,"    \"w%d_m%d\": {\"rows_with_AP\": %d, \"n_aps\": %zu, \"nodes\": %lld, \"rows\": [%s]}%s\n",
                         w,m,best,aps.size(),nodes,rowss.c_str(), last?"":",");
                out += buf;
                fprintf(stderr,"  AP w=%d m=%d -> %d/%d rows (nodes %lld) %s\n", w,m,best,w,nodes, best==w?"FULL":"");
                fflush(stderr);
            }
        }
        J += out;
        Jp("  },\n");
    }

    Jp("  \"done\": true\n}\n");
    FILE* fp=fopen(outpath.c_str(),"w");
    if(!fp){ fprintf(stderr,"cannot open %s\n",outpath.c_str()); return 1; }
    fwrite(J.data(),1,J.size(),fp); fclose(fp);
    fprintf(stderr,"wrote %s (%zu bytes, %.1fs total)\n", outpath.c_str(), J.size(), now());
    return 0;
}

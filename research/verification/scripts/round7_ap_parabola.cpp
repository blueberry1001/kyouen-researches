// Independent 128-bit integer audit of the quadratic-shift B558 candidate.
// Bounds: (span <= 500, a=2), or (span <= 200, 2<=a<=8).
// Put L=span, U=a*L^2+2. Then |C|<=6*U*L*(U^2+L^2),
// |B|<=24*a*U^2*L^2, |A|<=48*a^2*L^3. Hence |B^2-4AC|<1e38
// at both maximum parameter pairs; signed 128 bits suffice.
// Floating point is used only to seed isqrt; exact corrections verify its value.
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
using I = __int128_t;
std::string str(I x) {
    if (!x) return "0";
    bool neg=x<0; if(neg)x=-x;
    std::string out; while(x){out.push_back('0'+x%10);x/=10;}
    if(neg)out.push_back('-'); std::reverse(out.begin(),out.end()); return out;
}
I isqrt(I n) {
    I x=(I)std::sqrt((long double)n);
    while(x*x>n)--x;
    while((x+1)*(x+1)<=n)++x;
    return x;
}
I det(int a,const std::array<int,4>& r,const std::array<int,4>& j,int h) {
    I xx[4],yy[4],zz[4];
    for(int i=0;i<4;i++) {xx[i]=I(a)*(r[i]+h)*(r[i]+h)+j[i];yy[i]=r[i];}
    for(int i=3;i>=1;i--) {xx[i]-=xx[0];yy[i]-=yy[0];zz[i]=xx[i]*xx[i]+yy[i]*yy[i];}
    return xx[1]*(yy[2]*zz[3]-zz[2]*yy[3])
         - yy[1]*(xx[2]*zz[3]-zz[2]*xx[3])
         + zz[1]*(xx[2]*yy[3]-yy[2]*xx[3]);
}
int main(int argc,char**argv) {
    int limit=argc>1?std::stoi(argv[1]):128, a=argc>2?std::stoi(argv[2]):2;
    if(limit<1||a<2||a>8||!((a==2&&limit<=500)||limit<=200))return 2;
    std::vector<std::array<int,4>> labels;
    for(int i=0;i<81;i++) {int v=i;std::array<int,4> j;
        for(int p=3;p>=0;p--){j[p]=v%3;v/=3;}
        if(*std::min_element(j.begin(),j.end())==0)labels.push_back(j);
    }
    uint64_t count=0, negative=0, nonnegative=0, family=0, byrows[5]={},degrees[3]={};
    std::vector<std::string> witnesses;
    for(int span=1;span<=limit;span++) {
      for(int r1=0;r1<=span;r1++)for(int r2=r1;r2<=span;r2++) {
        std::array<int,4> r={0,r1,r2,span};
        int distinct=1;for(int i=1;i<4;i++)distinct+=r[i]!=r[i-1];
        for(auto j:labels) {
          bool skip=false;for(int i=0;i<3;i++)if(r[i]==r[i+1]&&j[i]>=j[i+1])skip=true;
          if(skip)continue;
          I c=det(a,r,j,0), v1=det(a,r,j,1), v2=det(a,r,j,2);
          I aa=(v2-2*v1+c)/2, bb=v1-c-aa;
          if(aa==0&&bb==0&&c==0)return 3;
          count++;byrows[distinct]++;degrees[aa?2:bb?1:0]++;
          std::vector<I> roots;
          if(aa==0) {if(bb!=0&&c%bb==0)roots.push_back(-c/bb);}
          else {
            I disc=bb*bb-4*aa*c;
            if(disc>=0) {
              I sq=isqrt(disc);
              if(sq*sq==disc) {
                if((-bb+sq)%(2*aa)==0)roots.push_back((-bb+sq)/(2*aa));
                if(sq&&(-bb-sq)%(2*aa)==0)roots.push_back((-bb-sq)/(2*aa));
              }
            }
          }
          for(I h:roots) {
            // Avoid squaring a potentially large integer root.
            if(h==0 ? c!=0 : (c%h!=0 || aa*h+bb+c/h!=0))return 4;
            if(h<0)negative++;
            else {
              nonnegative++; if(h>=span+1)family++;
              if(witnesses.size()<20) {
                std::string z="{\"h\":"+str(h)+",\"rows\":[";
                for(int i=0;i<4;i++)z+=(i?",":"")+std::to_string(r[i]);
                z+="],\"labels\":[";
                for(int i=0;i<4;i++)z+=(i?",":"")+std::to_string(j[i]);
                z+="],\"polynomial\":["+str(aa)+","+str(bb)+","+str(c)+"]}";
                witnesses.push_back(z);
              }
            }
          }
        }
      }
      if(span%32==0)std::cerr<<"span "<<span<<" patterns "<<count<<" nonnegative "<<nonnegative<<"\n";
    }
    std::cout<<"{\"complete\":true,\"a\":"<<a<<",\"span\":"<<limit<<",\"patterns\":"<<count
       <<",\"negative_roots\":"<<negative<<",\"nonnegative_roots\":"<<nonnegative
       <<",\"family_counterexamples\":"<<family<<",\"by_rows\":["<<byrows[2]<<","<<byrows[3]<<","<<byrows[4]
       <<"],\"degrees\":["<<degrees[0]<<","<<degrees[1]<<","<<degrees[2]<<"],\"first_nonnegative\":[";
    for(size_t i=0;i<witnesses.size();i++)std::cout<<(i?",":"")<<witnesses[i];
    std::cout<<"]}\n";
}

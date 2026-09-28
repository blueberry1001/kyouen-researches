// Independent row-triple search. Every four-set involving a new row is checked.
// No dependencies. g++ -O2 -std=c++17 round5_row_triples.cpp -o /tmp/r5rows
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <vector>
using namespace std;
struct Point { long long x,y; };
bool bad(Point a,Point b,Point c,Point d) {
    long long bx=b.x-a.x, by=b.y-a.y, bq=bx*bx+by*by;
    long long cx=c.x-a.x, cy=c.y-a.y, cq=cx*cx+cy*cy;
    long long dx=d.x-a.x, dy=d.y-a.y, dq=dx*dx+dy*dy;
    return bq*(cx*dy-cy*dx)-bx*(cq*dy-cy*dq)+by*(cq*dx-cx*dq)==0;
}
struct Triple { array<int,3> x; uint64_t sums; };
int w,m; bool ap; uint64_t nodes=0,det_checks=0,limit;
bool stopped=false; vector<Triple> options; vector<Point> placed;
vector<array<int,3>> selected,answer;
bool legal(array<int,3> xs,int row) {
    Point q[3]={{xs[0],row},{xs[1],row},{xs[2],row}};
    int k=placed.size();
    // Three old + one new, including old triples across all previous rows.
    for(int i=0;i<k;i++)for(int j=i+1;j<k;j++)for(int l=j+1;l<k;l++) {
        if(placed[i].y==placed[j].y && placed[j].y==placed[l].y)continue;
        for(int z=0;z<3;z++) {
            ++det_checks;
            if(bad(placed[i],placed[j],placed[l],q[z]))return false;
        }
    }
    // Two old + two new; same-old-row cases were checked by pair sums.
    for(int i=0;i<k;i++)for(int j=i+1;j<k;j++) {
        if(placed[i].y==placed[j].y)continue;
        for(int z=0;z<3;z++)for(int t=z+1;t<3;t++) {
            ++det_checks;
            if(bad(placed[i],placed[j],q[z],q[t]))return false;
        }
    }
    return true;
}
bool dfs(int row,uint64_t used_sums) {
    if(++nodes>limit){stopped=true;return false;}
    if(row==w){answer=selected;return true;}
    for(const auto &t:options) {
        if(used_sums&t.sums)continue;
        if(!legal(t.x,row))continue;
        for(int x:t.x)placed.push_back({x,row});
        selected.push_back(t.x);
        if(dfs(row+1,used_sums|t.sums))return true;
        selected.pop_back();placed.resize(placed.size()-3);
        if(stopped)return false;
    }
    return false;
}
int main(int argc,char**argv) {
    if(argc<4)return 2;
    w=atoi(argv[1]);m=atoi(argv[2]);ap=atoi(argv[3]);
    limit=argc>4?strtoull(argv[4],nullptr,10):100000000;
    if(w<1||m<3||m>31)return 2;
    for(int a=0;a<m;a++)for(int b=a+1;b<m;b++)for(int c=b+1;c<m;c++) {
        if(ap&&b-a!=c-b)continue;
        options.push_back({{a,b,c},(1ull<<(a+b))|(1ull<<(a+c))|(1ull<<(b+c))});
    }
    auto begin=chrono::steady_clock::now();
    bool found=dfs(0,0);
    double sec=chrono::duration<double>(chrono::steady_clock::now()-begin).count();
    cout<<"{\"w\":"<<w<<",\"m\":"<<m<<",\"AP_only\":"<<(ap?"true":"false")
        <<",\"found\":"<<(found?"true":"false")<<",\"complete\":"<<(!stopped?"true":"false")
        <<",\"nodes\":"<<nodes<<",\"determinant_checks\":"<<det_checks<<",\"seconds\":"<<sec<<",\"rows\":[";
    for(size_t i=0;i<answer.size();i++) {
        if(i)cout<<",";
        cout<<"["<<answer[i][0]<<","<<answer[i][1]<<","<<answer[i][2]<<"]";
    }
    cout<<"]}\n";
    return stopped?3:0;
}

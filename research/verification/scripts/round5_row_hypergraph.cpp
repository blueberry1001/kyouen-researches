// Independent exhaustive verifier using externally supplied forbidden masks.
// Places points, not row triples; no pair-sum or circle formula is used here.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <vector>
using namespace std;
using Mask=unsigned __int128;
int w,m;uint64_t limit,nodes=0,row_nodes=0;bool stopped=false,ap=false;
vector<vector<Mask>> ending;vector<int> selected,answer;
bool dfs(int row,int start,int left,Mask mask) {
    if(++nodes>limit){stopped=true;return false;}
    if(left==3)++row_nodes;
    if(row==w){answer=selected;return true;}
    if(left==0)return dfs(row+1,0,3,mask);
    for(int x=start;x<=m-left;x++) {
        if(ap&&left==1&&x!=2*(selected.back()%m)-(selected[selected.size()-2]%m))continue;
        int p=row*m+x;bool ok=true;
        for(auto t:ending[p])if((mask&t)==t){ok=false;break;}
        if(!ok)continue;
        selected.push_back(p);
        if(dfs(row,x+1,left-1,mask|(Mask(1)<<p)))return true;
        selected.pop_back();if(stopped)return false;
    }
    return false;
}
int main(int argc,char**argv) {
    if(argc<4)return 2;
    w=atoi(argv[1]);m=atoi(argv[2]);limit=argc>4?strtoull(argv[4],nullptr,10):100000000;
    ap=argc>5?atoi(argv[5]):false;
    if(w*m>120)return 2;
    ending.resize(w*m);ifstream in(argv[3]);string token;int edges=0;
    if(!in)return 2;
    while(in>>token){
        Mask q=0;for(char c:token)q=q*10+(c-'0');
        if(q==0)return 2;
        int p=0;for(Mask t=q;t>>=1;)++p;
        ending[p].push_back(q^(Mask(1)<<p));++edges;
    }
    auto begin=chrono::steady_clock::now();bool found=dfs(0,0,3,0);
    double sec=chrono::duration<double>(chrono::steady_clock::now()-begin).count();
    cout<<"{\"w\":"<<w<<",\"m\":"<<m<<",\"AP_only\":"<<(ap?"true":"false")<<",\"found\":"<<(found?"true":"false")
        <<",\"complete\":"<<(!stopped?"true":"false")<<",\"nodes\":"<<nodes
        <<",\"full_row_prefixes\":"<<row_nodes<<",\"hyperedges\":"<<edges
        <<",\"seconds\":"<<sec<<",\"rows\":[";
    for(int r=0;r<(int)answer.size()/3;r++){
        if(r)cout<<",";cout<<"["<<answer[3*r]%m<<","<<answer[3*r+1]%m<<","<<answer[3*r+2]%m<<"]";
    }
    cout<<"]}\n";return stopped?3:0;
}

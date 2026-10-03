// Exploratory fixed-size safe-set walk. Only concrete independently checked
// witnesses, never failed searches, establish bounds.
#include <bits/stdc++.h>
using namespace std;
struct Mask{uint64_t b[4]{};Mask&operator|=(const Mask&o){for(int i=0;i<4;i++)b[i]|=o.b[i];return *this;}};
static int n,V,k;
static vector<Mask> cm;
static mt19937_64 rng;
static inline int index3(int a,int b,int c){if(a>b)swap(a,b);if(b>c)swap(b,c);if(a>b)swap(a,b);return (a*V+b)*V+c;}
static inline const Mask&get(int a,int b,int c){return cm[index3(a,b,c)];}
static inline bool has(const Mask&m,int p){return (m.b[p>>6]>>(p&63))&1;}
static inline void setp(Mask&m,int p){m.b[p>>6]|=1ull<<(p&63);}
static long long det(int a,int b,int c,int d){long long ax=a%n-d%n,ay=a/n-d/n,bx=b%n-d%n,by=b/n-d/n,cx=c%n-d%n,cy=c/n-d/n;long long az=ax*ax+ay*ay,bz=bx*bx+by*by,cz=cx*cx+cy*cy;return az*(bx*cy-by*cx)-bz*(ax*cy-ay*cx)+cz*(ax*by-ay*bx);}
static Mask forbidden(const vector<int>&s){Mask f;for(int a=0;a<(int)s.size();a++)for(int b=a+1;b<(int)s.size();b++)for(int c=b+1;c<(int)s.size();c++)f|=get(s[a],s[b],s[c]);return f;}
static vector<int> legal(const vector<int>&s,Mask f){for(int p:s)setp(f,p);vector<int>v;for(int p=0;p<V;p++)if(!has(f,p))v.push_back(p);return v;}
int main(int argc,char**argv){n=argc>1?atoi(argv[1]):11;k=argc>2?atoi(argv[2]):10;double seconds=argc>3?atof(argv[3]):60;uint64_t seed=argc>4?stoull(argv[4]):20261003;rng.seed(seed);vector<int>initial;if(argc>5){string t=argv[5];replace(t.begin(),t.end(),',',' ');istringstream is(t);int p;while(is>>p)initial.push_back(p);}V=n*n;if(V>256)return 2;cm.resize(V*V*V);long long quads=0;for(int a=0;a<V;a++)for(int b=a+1;b<V;b++)for(int c=b+1;c<V;c++)for(int d=c+1;d<V;d++)if(!det(a,b,c,d)){quads++;setp(cm[index3(a,b,c)],d);setp(cm[index3(a,b,d)],c);setp(cm[index3(a,c,d)],b);setp(cm[index3(b,c,d)],a);}
int best=V;vector<int>bestset;long long steps=0,restarts=0;auto started=chrono::steady_clock::now();
while(chrono::duration<double>(chrono::steady_clock::now()-started).count()<seconds){restarts++;vector<int>s;if(!initial.empty() && (restarts==1 || rng()%4)){s=bestset.empty()?initial:bestset;int remove=restarts==1?0:1+rng()%min(k,6);while(remove--){s.erase(s.begin()+rng()%s.size());}}while((int)s.size()<k){auto v=legal(s,forbidden(s));if(v.empty())break;s.push_back(v[rng()%v.size()]);}if((int)s.size()!=k)continue;int energy=legal(s,forbidden(s)).size();
for(int iter=0;iter<20000;iter++){steps++;int j=rng()%k,old=s[j];s.erase(s.begin()+j);auto v=legal(s,forbidden(s));int added=v[rng()%v.size()];s.push_back(added);int next=legal(s,forbidden(s)).size();double t=0.12+1.8*(1.0-(iter%4000)/4000.0);if(next<=energy || double(rng()>>11)/9007199254740992.0<exp((energy-next)/t)){energy=next;}else{s.pop_back();s.push_back(old);}if(energy<best){best=energy;bestset=s;cerr<<"n="<<n<<" k="<<k<<" best="<<best<<" steps="<<steps<<"\n";}if(!energy)goto done;if((steps&8191)==0 && chrono::duration<double>(chrono::steady_clock::now()-started).count()>=seconds)goto done;}}
done:sort(bestset.begin(),bestset.end());cout<<"{\"n\":"<<n<<",\"k\":"<<k<<",\"seed\":"<<seed<<",\"seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-started).count()<<",\"quads\":"<<quads<<",\"steps\":"<<steps<<",\"restarts\":"<<restarts<<",\"legal_count\":"<<best<<",\"witness_ids\":[";for(int i=0;i<(int)bestset.size();i++){if(i)cout<<",";cout<<bestset[i];}cout<<"]}\n";return 0;}

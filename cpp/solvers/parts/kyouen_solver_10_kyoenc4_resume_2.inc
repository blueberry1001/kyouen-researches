 std::uint32_t get(Bits s,int n)const{if(n<9||n>17)return 0;auto r=rank(s,n);switch(n){case 9:return d9_.get(r);case 10:return d10_.get(r);case 11:{auto v=d11_.get(r);return v?v:d11b_.get(r);}case 12:{auto v=d12a_.get(r);return v?v:d12b_.get(r);}case 13:{auto v=d13a_.get(r);return v?v:d13b_.get(r);}case 14:{auto v=d14a_.get(r);return v?v:d14b_.get(r);}case 15:return d15_.get(r);case 16:return d16_.get(r);case 17:return d17_.get(r);}return 0;}
 void put(Bits s,int n,std::uint32_t v){if(n<9||n>17)return;auto r=rank(s,n);bool ok=false;switch(n){case 9:ok=d9_.try_put(r,v);break;case 10:ok=d10_.try_put(r,v);break;case 11:ok=d11_.try_put(r,v)||d11b_.try_put(r,v);break;case 12:ok=d12a_.try_put(r,v)||d12b_.try_put(r,v);break;case 13:ok=d13a_.try_put(r,v)||d13b_.try_put(r,v);break;case 14:ok=d14a_.try_put(r,v)||d14b_.try_put(r,v);break;case 15:ok=d15_.try_put(r,v);break;case 16:ok=d16_.try_put(r,v);break;case 17:ok=d17_.try_put(r,v);break;}if(!ok)throw TableFull{};}
 std::size_t used()const{return d9_.used()+d10_.used()+d11_.used()+d11b_.used()+d12a_.used()+d12b_.used()+d13a_.used()+d13b_.used()+d14a_.used()+d14b_.used()+d15_.used()+d16_.used()+d17_.used();}
 void print(std::ostream&o)const{o<<"memo_by_depth 9:"<<d9_.used()<<" 10:"<<d10_.used()<<" 11:"<<(d11_.used()+d11b_.used())<<" 12:"<<(d12a_.used()+d12b_.used())<<" 13:"<<(d13a_.used()+d13b_.used())<<" 14:"<<(d14a_.used()+d14b_.used())<<" 15:"<<d15_.used()<<" 16:"<<d16_.used()<<" 17:"<<d17_.used()<<"\n";}
private:RankCompactTable<4>d9_;RankCompactTable<5>d10_,d11_,d11b_,d12a_,d12b_,d13a_;RankCompactTable<6>d13b_,d14a_,d14b_,d15_;RankCompactTable<7>d16_;RankFlat17 d17_;std::array<std::array<std::uint64_t,18>,101>ch_{};
 void build(){ch_[0][0]=1;for(int n=1;n<=100;++n){ch_[n][0]=1;for(int k=1;k<=17;++k){ch_[n][k]=ch_[n-1][k];if(k<=n)ch_[n][k]+=ch_[n-1][k-1];}}}
 std::uint64_t rank(Bits s,int k)const{std::uint64_t r=0;int i=1;while(any(s))r+=ch_[take_lsb(s)][i++];if(i!=k+1)throw std::runtime_error("stone count mismatch");return r;}
};
class Solver{
 static constexpr int N=10,V=100;static constexpr std::uint64_t HiMask=(1ULL<<36)-1;using Clock=std::chrono::steady_clock;struct TState{std::array<Bits,8>t{};};struct Child{TState ts;Bits legal,key;int count;std::uint32_t cached;};
public:
 struct DepthStats{std::uint64_t entry_get=0,entry_hit_loss=0,entry_hit_win=0,expanded=0,terminal=0,child_get=0,child_hit_loss=0,child_hit_win=0,put_loss=0,put_win=0,unique_children=0,cached_loss_children=0,cached_win_children=0,unknown_children=0,children_entered=0,win_nodes=0,loss_nodes=0,cutoff_index_sum=0,work_into_win_child=0,work_into_loss_child=0,calls_into_win_child=0,calls_into_loss_child=0;};
 struct Stats{std::uint64_t visited=0;int maxdepth=0;std::array<DepthStats,V+1>depth{};};
 Solver(unsigned shrink,unsigned load):completion_(std::size_t(V)*V*V),memo_(shrink,load),start_(Clock::now()){maps();quads();}
 bool solve(const std::vector<int>&pts,Stats&st){TState s{};Bits legal{~0ULL,HiMask};for(int v:pts){if(!any(legal&bitof(v)))throw std::runtime_error("illegal initial state");Bits old=s.t[0];s=add(s,v);legal=(legal&~bitof(v))&~bans(old,v);legal.hi&=HiMask;}return win(s,legal,(int)pts.size(),st);}
 void write_certificate(const std::vector<int>&pts,const std::string&path,bool root_winning,std::size_t max_nodes,const std::string&index_path,bool resume,std::size_t checkpoint_after){
  TState original{};Bits legal{~0ULL,HiMask};
  for(int v:pts){if(!any(legal&bitof(v)))throw std::runtime_error("illegal certificate root");Bits old=original.t[0];original=add(original,v);legal=(legal&~bitof(v))&~bans(old,v);legal.hi&=HiMask;}
  Bits root=canonical(original);
  cert_nodes_.clear();disk_nodes_.reset();if(index_path.empty())cert_nodes_.reserve(std::min<std::size_t>(max_nodes,1u<<20));else disk_nodes_=std::make_unique<MmapProofIndex>(index_path,max_nodes,root,resume);cert_limit_=max_nodes;checkpoint_after_=checkpoint_after;cert_recomputed_=0;
  build_proof(root,root_winning);
  CertHeaderV4 h{};std::memcpy(h.magic,"KYOENC4",7);h.version=4;h.boardSize=N;h.nodeCount=cert_size();h.rootLo=root.lo;h.rootHi=root.hi;h.forbiddenCount=forbidden_count_;
  std::ofstream out(path,std::ios::binary|std::ios::trunc);if(!out)throw std::runtime_error("cannot open certificate output");
  out.write(reinterpret_cast<const char*>(&h),sizeof(h));
  cert_for_each([&](Bits s,CertMeta m){CertNodeV4 n{s.lo,s.hi,m.outcome,m.witness,m.rank,0,0};out.write(reinterpret_cast<const char*>(&n),sizeof(n));});
  if(!out)throw std::runtime_error("certificate write failed");
  std::cerr<<"certificate nodes="<<cert_size()<<" recomputed="<<cert_recomputed_<<" bytes="<<(sizeof(h)+cert_size()*sizeof(CertNodeV4))<<" root_stones="<<popcount(root)<<" proof_index="<<(disk_nodes_?"mmap":"memory");if(disk_nodes_)std::cerr<<" index_bytes="<<disk_nodes_->file_bytes()<<" resumed_nodes="<<disk_nodes_->resumed_nodes()<<" discarded_pending="<<disk_nodes_->discarded_pending();std::cerr<<"\n";
 }
 std::size_t memo_used()const{return memo_.used();}
 double seconds()const{return std::chrono::duration<double>(Clock::now()-start_).count();}
 void print(std::ostream&o)const{memo_.print(o);}
 void write_below_root_csv(std::ostream&o,const std::string&state,const Stats&st)const{for(int d=0;d<=V;++d){const auto&a=st.depth[d];if(!a.entry_get&&!a.expanded&&!a.child_get&&!a.children_entered)continue;o<<state<<','<<d<<','<<st.visited<<','<<a.expanded<<','<<a.terminal<<','<<a.entry_get<<','<<a.entry_hit_loss<<','<<a.entry_hit_win<<','<<a.child_get<<','<<a.child_hit_loss<<','<<a.child_hit_win<<','<<a.put_loss<<','<<a.put_win<<','<<a.unique_children<<','<<a.cached_loss_children<<','<<a.cached_win_children<<','<<a.unknown_children<<','<<a.children_entered<<','<<a.win_nodes<<','<<a.loss_nodes<<','<<a.cutoff_index_sum<<','<<a.work_into_win_child<<','<<a.work_into_loss_child<<','<<a.calls_into_win_child<<','<<a.calls_into_loss_child<<'\n';}}
 std::uint64_t forbidden_count()const{return forbidden_count_;}
private:std::vector<Bits>completion_;std::array<std::array<Bits,V>,8>tbit_{};MultiDepthMemo100 memo_;std::uint64_t forbidden_count_=0;Clock::time_point start_;std::unordered_map<Bits,CertMeta,BitsHash>cert_nodes_;std::unique_ptr<MmapProofIndex>disk_nodes_;std::size_t cert_limit_=0,checkpoint_after_=0;std::uint64_t cert_recomputed_=0;
 static long long det3(long long a,long long b,long long c,long long d,long long e,long long f,long long g,long long h,long long i){return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);}
 static bool forbidden(int a,int b,int c,int d){int ids[4]={a,b,c,d};long long m[4][4]{};for(int r=0;r<4;++r){long long x=ids[r]%N,y=ids[r]/N;m[r][0]=x*x+y*y;m[r][1]=x;m[r][2]=y;m[r][3]=1;}long long z=0;for(int col=0;col<4;++col){long long q[3][3]{};for(int r=1;r<4;++r){int k=0;for(int j=0;j<4;++j)if(j!=col)q[r-1][k++]=m[r][j];}auto md=det3(q[0][0],q[0][1],q[0][2],q[1][0],q[1][1],q[1][2],q[2][0],q[2][1],q[2][2]);z+=(col%2? -1:1)*m[0][col]*md;}return z==0;}
 static constexpr std::size_t idx(int a,int b,int c){return(std::size_t(a)*V+b)*V+c;}static void sort3(int&a,int&b,int&c){if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);}
 void maps(){for(int p=0;p<V;++p){int x=p%N,y=p/N;int nx[8]={x,N-1-x,x,N-1-x,y,N-1-y,y,N-1-y};int ny[8]={y,y,N-1-y,N-1-y,x,x,N-1-x,N-1-x};for(int k=0;k<8;++k)tbit_[k][p]=bitof(ny[k]*N+nx[k]);}}
 void quads(){for(int a=0;a<V;++a)for(int b=a+1;b<V;++b)for(int c=b+1;c<V;++c)for(int d=c+1;d<V;++d)if(forbidden(a,b,c,d)){++forbidden_count_;int q[4]={a,b,c,d};for(int omit=0;omit<4;++omit){int t[3],p=0;for(int j=0;j<4;++j)if(j!=omit)t[p++]=q[j];completion_[idx(t[0],t[1],t[2])]=completion_[idx(t[0],t[1],t[2])]|bitof(q[omit]);}}}
 TState add(const TState&s,int v)const{TState r=s;for(int k=0;k<8;++k)r.t[k]=r.t[k]|tbit_[k][v];return r;}static Bits canonical(const TState&s){Bits r=s.t[0];for(int k=1;k<8;++k)if(s.t[k]<r)r=s.t[k];return r;}
 Bits bans(Bits state,int v)const{int verts[V],k=0;while(any(state))verts[k++]=take_lsb(state);Bits out{};for(int i=0;i<k;++i)for(int j=i+1;j<k;++j){int a=verts[i],b=verts[j],c=v;sort3(a,b,c);out=out|completion_[idx(a,b,c)];}return out;}


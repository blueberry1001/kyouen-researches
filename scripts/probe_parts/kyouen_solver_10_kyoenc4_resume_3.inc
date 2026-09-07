 std::optional<CertMeta>cert_get(Bits state)const{CertMeta m;if(disk_nodes_){if(disk_nodes_->get(state,m))return m;return std::nullopt;}auto it=cert_nodes_.find(state);if(it==cert_nodes_.end())return std::nullopt;return it->second;}
 void cert_insert(Bits state,CertMeta meta){if(checkpoint_after_&&cert_size()>=checkpoint_after_)throw ProofCheckpoint{};if(disk_nodes_)disk_nodes_->insert_pending(state,meta);else{if(cert_nodes_.size()>=cert_limit_)throw std::runtime_error("certificate node limit exceeded");auto[it,inserted]=cert_nodes_.emplace(state,meta);if(!inserted&&it->second.outcome!=meta.outcome)throw std::runtime_error("certificate outcome mismatch");}}
 void cert_complete(Bits state){if(disk_nodes_)disk_nodes_->mark_complete(state);}
 void cert_set_witness(Bits state,std::uint8_t witness){if(disk_nodes_)disk_nodes_->set_witness(state,witness);else{auto it=cert_nodes_.find(state);if(it==cert_nodes_.end())throw std::runtime_error("certificate state missing while setting witness");it->second.witness=witness;}}
 std::size_t cert_size()const{return disk_nodes_?disk_nodes_->size():cert_nodes_.size();}
 template<class F>void cert_for_each(F&&f)const{if(disk_nodes_)disk_nodes_->for_each(std::forward<F>(f));else for(const auto&kv:cert_nodes_)f(kv.first,kv.second);}
 TState from_bits(Bits state)const{TState r{};while(any(state)){int v=take_lsb(state);for(int k=0;k<8;++k)r.t[k]=r.t[k]|tbit_[k][v];}return r;}
 Bits legal_from_state(Bits state)const{int verts[V],n=0;Bits copy=state;while(any(copy))verts[n++]=take_lsb(copy);Bits banned{};for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)for(int k=j+1;k<n;++k)banned=banned|completion_[idx(verts[i],verts[j],verts[k])];Bits legal=(Bits{~0ULL,HiMask}&~state)&~banned;legal.hi&=HiMask;return legal;}
 bool evaluate_canonical(Bits state){auto known=cert_get(state);if(known)return known->outcome==2;TState ts=from_bits(state);Bits legal=legal_from_state(state);Stats scratch;++cert_recomputed_;return win(ts,legal,popcount(state),scratch);}
 void build_proof(Bits state,bool winning){
  auto existing=cert_get(state);if(existing){if((existing->outcome==2)!=winning)throw std::runtime_error("certificate outcome mismatch");return;}
  CertMeta meta;meta.outcome=winning?2:1;meta.witness=255;meta.rank=static_cast<std::uint8_t>(V-popcount(state));cert_insert(state,meta);
  TState ts=from_bits(state);Bits legal=legal_from_state(state);
  if(winning){
   bool found=false;std::uint8_t saved=255;
   if(get_winning_witness(state.lo,state.hi,saved)&&any(legal&bitof(saved))){
    Bits child=canonical(add(ts,saved));cert_set_witness(state,saved);build_proof(child,false);found=true;++winning_witness_hits;
   }else ++winning_witness_misses;
   if(!found){
    Bits moves=legal;
    while(any(moves)){int v=take_lsb(moves);TState child_ts=add(ts,v);Bits child=canonical(child_ts);bool child_winning=evaluate_canonical(child);if(!child_winning){cert_set_witness(state,static_cast<std::uint8_t>(v));record_winning_witness(state.lo,state.hi,static_cast<std::uint8_t>(v),meta.rank);build_proof(child,false);found=true;break;}}
   }
   if(!found)throw std::runtime_error("winning certificate node has no losing child");
  }else{
   std::array<Bits,V>unique{};int count=0;Bits moves=legal;
   while(any(moves)){int v=take_lsb(moves);Bits child=canonical(add(ts,v));bool duplicate=false;for(int i=0;i<count;++i)if(unique[i]==child){duplicate=true;break;}if(duplicate)continue;unique[count++]=child;if(!evaluate_canonical(child))throw std::runtime_error("losing certificate node has a losing child");}
   for(int i=0;i<count;++i)build_proof(unique[i],true);
  }
  cert_complete(state);
  if((cert_size()&((1u<<20)-1))==0)std::cerr<<"certificate progress nodes="<<cert_size()<<" recomputed="<<cert_recomputed_<<"\n";
 }
 bool win(const TState&s,Bits legal,int depth,Stats&st){
  int canonical_k=0;for(int k=1;k<8;++k)if(s.t[k]<s.t[canonical_k])canonical_k=k;Bits key=s.t[canonical_k];
  auto cached=memo_.get(key,depth);if(cached)return cached==MultiDepthMemo100::Winning;++st.visited;st.maxdepth=std::max(st.maxdepth,depth);if(static_cast<std::size_t>(depth)<st.depth_visited.size())++st.depth_visited[depth];if(check_probe_budget(st))throw ProbeExhausted{};if((st.visited&((1ULL<<24)-1))==0)std::cerr<<"progress visited="<<st.visited<<" memo="<<memo_.used()<<" depth="<<depth<<" maxdepth="<<st.maxdepth<<" seconds="<<seconds()<<"\n";if(!any(legal)){memo_.put(key,depth,MultiDepthMemo100::Losing);return false;}std::array<Child,V>ch{};int n=0;Bits moves=legal;while(any(moves)){int v=take_lsb(moves);Bits bit=bitof(v);TState ns=add(s,v);Bits nl=(legal&~bit)&~bans(s.t[0],v);nl.hi&=HiMask;Bits nk=canonical(ns);bool dup=false;for(int i=0;i<n;++i)if(ch[i].key==nk){dup=true;break;}if(dup)continue;auto cv=memo_.get(nk,depth+1);ch[n++]={ns,nl,nk,popcount(nl),cv};}order_children(ch,n,depth);for(int i=0;i<n;++i){if(depth==root_diag_depth_&&!ch[i].cached)++root_children_entered_;bool cw=ch[i].cached?ch[i].cached==MultiDepthMemo100::Winning:win(ch[i].ts,ch[i].legal,depth+1,st);if(!cw){
    int witness=-1;Bits candidates=legal;while(any(candidates)){int v=take_lsb(candidates);if(canonical(add(s,v))==ch[i].key){Bits transformed=tbit_[canonical_k][v];witness=take_lsb(transformed);break;}}if(depth==root_diag_depth_)root_witness_move_=witness;
    if(witness<0)throw std::runtime_error("cannot recover canonical winning witness");
    memo_.put(key,depth,MultiDepthMemo100::Winning);record_winning_witness(key.lo,key.hi,static_cast<std::uint8_t>(witness),static_cast<std::uint8_t>(V-depth));return true;
   }}memo_.put(key,depth,MultiDepthMemo100::Losing);return false;}
};
static std::vector<int> parse(const std::string&s){std::vector<int>v;std::size_t b=0;while(b<s.size()){auto e=s.find(',',b);auto t=s.substr(b,e==std::string::npos?std::string::npos:e-b);if(!t.empty())v.push_back(std::stoi(t));if(e==std::string::npos)break;b=e+1;}return v;}
int main(int argc,char**argv){try{
 if(argc<2){std::cerr<<"usage: solver STATES_FILE [shrink=3] [load=80] [witness_log_file] [witness_resume=0] [witness_index_file] [witness_max_records=10000000]\n       solver --certificate STATE OUTPUT.cert [shrink=3] [load=80] [max_nodes=10000000] [proof_index_file] [resume=0] [checkpoint_after=0] [witness_log_file] [witness_resume=0] [witness_index_file] [witness_max_records=10000000]\n";return 2;}
 if(std::string(argv[1])=="--certificate"){
 for(int ai=1;ai<argc;++ai){std::string a=argv[ai];if(a=="--root-order-file"||a=="--root-depth")throw std::runtime_error("root-order flags not supported in --certificate mode");}
  if(argc<4){std::cerr<<"usage: solver --certificate STATE OUTPUT.cert [shrink=3] [load=80] [max_nodes=10000000] [proof_index_file] [resume=0] [checkpoint_after=0] [witness_log_file] [witness_resume=0] [witness_index_file] [witness_max_records=10000000]\n";return 2;}
  auto pts=parse(argv[2]);unsigned shrink=argc>=5?std::atoi(argv[4]):3,load=argc>=6?std::atoi(argv[5]):80;std::size_t max_nodes=argc>=7?std::stoull(argv[6]):10000000ULL;std::string index_path=argc>=8?argv[7]:"";bool resume=argc>=9?std::atoi(argv[8])!=0:false;std::size_t checkpoint_after=argc>=10?std::stoull(argv[9]):0;std::string witness_path=argc>=11?argv[10]:"";bool witness_resume=argc>=12?std::atoi(argv[11])!=0:false;std::string witness_index_path=argc>=13?argv[12]:"";std::size_t witness_max_records=argc>=14?std::stoull(argv[13]):10000000ULL;
  open_winning_witness_log(witness_path,witness_resume,witness_index_path,witness_max_records);Solver solver(shrink,load);Solver::Stats st;bool w=solver.solve(pts,st);
  std::cout<<"state,outcome,visited,maxdepth,memo,seconds\n"<<argv[2]<<','<<(w?"WIN":"LOSS")<<','<<st.visited<<','<<st.maxdepth<<','<<solver.memo_used()<<','<<solver.seconds()<<"\n";
  try{solver.write_certificate(pts,argv[3],w,max_nodes,index_path,resume,checkpoint_after);}catch(const ProofCheckpoint&){solver.print(std::cerr);print_winning_witness_stats(std::cerr);std::cerr<<"proof_checkpoint=1\n";return 4;}solver.print(std::cerr);print_winning_witness_stats(std::cerr);return 0;
 }

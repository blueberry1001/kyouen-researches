 std::string root_order_file;int root_order_depth=-1;
 for(int ai=1;ai<argc;){std::string a=argv[ai];if(a=="--root-order-file"&&ai+1<argc){root_order_file=argv[ai+1];for(int aj=ai;aj+2<argc;++aj)argv[aj]=argv[aj+2];argc-=2;}else if(a=="--root-depth"&&ai+1<argc){root_order_depth=std::atoi(argv[ai+1]);for(int aj=ai;aj+2<argc;++aj)argv[aj]=argv[aj+2];argc-=2;}else ++ai;}
 unsigned shrink=argc>=3?std::atoi(argv[2]):3,load=argc>=4?std::atoi(argv[3]):80;
 std::uint64_t max_visited=argc>=5?std::strtoull(argv[4],nullptr,10):0;
 double max_seconds=argc>=6?std::strtod(argv[5],nullptr):0.0;
 std::string witness_path=argc>=7?argv[6]:"";bool witness_resume=argc>=8?std::atoi(argv[7])!=0:false;std::string witness_index_path=argc>=9?argv[8]:"";std::size_t witness_max_records=argc>=10?std::stoull(argv[9]):10000000ULL;
 open_winning_witness_log(witness_path,witness_resume,witness_index_path,witness_max_records);
 std::ifstream in(argv[1]);if(!in)throw std::runtime_error("cannot open states file");
 std::vector<std::vector<int>>tasks;std::string line;
 while(std::getline(in,line))if(!line.empty())tasks.push_back(parse(line));
 Solver solver(shrink,load);
 solver.set_probe_budget(max_visited,max_seconds);
 if(!root_order_file.empty()&&root_order_depth<0)throw std::runtime_error("--root-order-file requires --root-depth");
 if(!root_order_file.empty()&&(int)tasks.size()!=1)throw std::runtime_error("--root-order-file requires a single-state file");
 if(root_order_depth>=0)solver.set_root_diag(root_order_depth);
 if(!root_order_file.empty()){std::ifstream rf(root_order_file);if(!rf)throw std::runtime_error("cannot open root order file");std::vector<Bits> rkeys;std::string rl;std::size_t rlines=0;while(std::getline(rf,rl)){if(rl.empty())continue;++rlines;rkeys.push_back(solver.canonical_key_of(parse(rl)));}std::vector<Bits> runiq;for(auto&k:rkeys){bool seen=false;for(auto&q:runiq)if(q==k){seen=true;break;}if(!seen)runiq.push_back(k);}std::cerr<<"root_order_file lines="<<rlines<<" unique="<<runiq.size()<<"\n";solver.set_root_order(root_order_depth,runiq);}
 std::cout<<"state,outcome,visited,maxdepth,memo,seconds";
 for(int i=0;i<20;++i)std::cout<<",depth_visited_"<<i;
 for(int i=9;i<=21;++i)std::cout<<",memo_used_d"<<i;
 for(int i=9;i<=21;++i)std::cout<<",memo_capacity_d"<<i;
 std::cout<<"\n";
 auto write_stats=[&](const Solver::Stats&st){
  std::cout<<','<<st.visited<<','<<st.maxdepth<<','<<solver.memo_used()<<','<<solver.seconds();
  for(std::size_t i=0;i<st.depth_visited.size();++i)std::cout<<','<<st.depth_visited[i];
  std::array<std::size_t,13>used{},cap{};
  solver.memo_used_by_depth(used);
  solver.memo_capacity_by_depth(cap);
  for(std::size_t i=0;i<used.size();++i)std::cout<<','<<used[i];
  for(std::size_t i=0;i<cap.size();++i)std::cout<<','<<cap[i];
 };
 std::size_t done=0;
 for(auto&pts:tasks){Solver::Stats st;
  try{bool w=solver.solve(pts,st);
   for(std::size_t i=0;i<pts.size();++i){if(i)std::cout<<'-';std::cout<<pts[i];}
   std::cout<<','<<(w?"WIN":"LOSS");
   write_stats(st);
   std::cout<<"\n";
   solver.print_bench_root(std::cerr,w?"WIN":"LOSS");
   std::cout.flush();
   ++done;
  }catch(const ProbeExhausted&){
   for(std::size_t i=0;i<pts.size();++i){if(i)std::cout<<'-';std::cout<<pts[i];}
   std::cout<<",PROBE";
   write_stats(st);
   std::cout<<"\n";
   solver.print_bench_root(std::cerr,"PROBE");
   std::cout.flush();
   ++done;
  }catch(const TableFull&){
   solver.print(std::cerr);
   print_winning_witness_stats(std::cerr);
   std::cerr<<"forbidden="<<solver.forbidden_count()<<" completed="<<done<<" requested="<<tasks.size()<<" memo="<<solver.memo_used()<<" seconds="<<solver.seconds()<<" table_full=1\n";
   return 3;
  }
 }
 solver.print(std::cerr);
 print_winning_witness_stats(std::cerr);
 std::cerr<<"forbidden="<<solver.forbidden_count()<<" completed="<<done<<" requested="<<tasks.size()<<" memo="<<solver.memo_used()<<" seconds="<<solver.seconds()<<" table_full=0\n";
 return 0;
}catch(const std::exception&e){std::cerr<<"error: "<<e.what()<<"\n";return 1;}}

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
   std::cout.flush();
   ++done;
  }catch(const ProbeExhausted&){
   for(std::size_t i=0;i<pts.size();++i){if(i)std::cout<<'-';std::cout<<pts[i];}
   std::cout<<",PROBE";
   write_stats(st);
   std::cout<<"\n";
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

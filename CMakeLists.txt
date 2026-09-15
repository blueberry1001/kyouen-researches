cmake_minimum_required(VERSION 3.20)
project(kyouen_1_to_9_classification LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BUILD_RESEARCH_SOLVERS "Build exploratory/full-search solvers" OFF)

if(MSVC)
  add_compile_options(/W4 /permissive-)
else()
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

add_executable(kyouen-certcheck cpp/certificate/kyouen_certcheck.cpp)
add_executable(kyouen-certgen-1-to-8 cpp/certificate/kyouen_certgen_1_to_8.cpp)
add_executable(kyouen-certgen-v4-smoke cpp/certificate/kyouen_certgen_v4_smoke.cpp)
add_executable(convert-9-v2-to-v3 cpp/certificate/convert_9_v2_to_v3.cpp)

# Historical 9x9 certificate tools retained for reproducibility.
add_executable(kyouen-certgen-9-legacy cpp/generator/kyouen_certgen_9.cpp)
add_executable(cert-v1-to-v2 cpp/generator/cert_v1_to_v2.cpp)

if(BUILD_RESEARCH_SOLVERS)
  add_executable(kyouen-solver cpp/solvers/kyouen_solver.cpp)
  add_executable(kyouen-solver-fast cpp/solvers/kyouen_solver_fast.cpp)
  add_executable(kyouen-solver-verify cpp/solvers/kyouen_solver_verify.cpp)
  add_executable(kyouen-solver-9 cpp/solvers/kyouen_solver_9.cpp)
  add_executable(kyouen-solver-9-compare cpp/solvers/kyouen_solver_9_compare.cpp)
  add_executable(kyouen-solver-9-root cpp/solvers/kyouen_solver_9_root.cpp)
  add_executable(kyouen-solver-9-verify cpp/solvers/kyouen_solver_9_verify.cpp)
  add_executable(kyouen-solver-10-kyoenc4 cpp/solvers/kyouen_solver_10_kyoenc4.cpp)
  add_executable(kyouen-solver-8-root cpp/solvers/kyouen_solver_8_root.cpp)
endif()

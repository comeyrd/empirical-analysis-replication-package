# Benchmark binary of the main corpus: blas-baseliner (branch w-option) on Baseliner 1.0.
cmake_minimum_required(VERSION 3.15)
project(baseliner-blas-rq1_rq3)

# Exact commits of the build that produced the corpus. The first declaration of a name wins over the ones
# nested in blas-baseliner.
include(FetchContent)
FetchContent_Declare(baseliner
    GIT_REPOSITORY https://github.com/comeyrd/gpu-kernel-baseliner.git
    GIT_TAG        c9e286f3022302ce1acb53bb729095cd6dda3f17)   # v1.0
FetchContent_Declare(baseliner_adapters
    GIT_REPOSITORY https://github.com/comeyrd/baseliner-adapter.git
    GIT_TAG        ee2899fe3acae308aad8d6867b8e3971beed03d6)   # v1.0
FetchContent_Declare(blas_baseliner
    GIT_REPOSITORY https://github.com/comeyrd/blas-baseliner-benchmark.git
    GIT_TAG        ed92a8f2b5081759f570a89aeebb36113482aa74)   # w-option
FetchContent_MakeAvailable(blas_baseliner)

set(BIN_DIR ${CMAKE_BINARY_DIR} CACHE PATH "Output folder of the binary")
set_target_properties(baseliner-blas PROPERTIES OUTPUT_NAME baseliner-blas-rq1_rq3 RUNTIME_OUTPUT_DIRECTORY ${BIN_DIR})

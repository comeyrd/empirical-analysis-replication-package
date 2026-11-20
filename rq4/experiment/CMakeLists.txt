# Benchmark binary of the SMS experiment: blas-baseliner (branch dev-exp: shuffled workloads, pause between
# campaigns, ordered report) with the two SMS stopping criteria of ../stopping_criterion.
cmake_minimum_required(VERSION 3.15)
project(baseliner-blas-rq4)

# Exact commits of the build that produced the experiment. The first declaration of a name wins over the ones
# nested in blas-baseliner.
include(FetchContent)
FetchContent_Declare(baseliner
    GIT_REPOSITORY https://github.com/comeyrd/gpu-kernel-baseliner.git
    GIT_TAG        638f219abcdc197397432c9051853dc27e924b94)   # dev-exp
FetchContent_Declare(baseliner_adapters
    GIT_REPOSITORY https://github.com/comeyrd/baseliner-adapter.git
    GIT_TAG        1dce0d2687f207eeb9aec2306464ff65e280b7f9)   # dev-exp
FetchContent_Declare(blas_baseliner
    GIT_REPOSITORY https://github.com/comeyrd/blas-baseliner-benchmark.git
    GIT_TAG        78fb619d0957743bfb33fd1a57b7f6579b53799e)   # dev-exp
FetchContent_MakeAvailable(blas_baseliner)

add_library(sms_stopping OBJECT ${CMAKE_CURRENT_SOURCE_DIR}/../stopping_criterion/RegisterStopping.cpp)
target_link_libraries(sms_stopping PRIVATE baseliner_adapters::baseliner)
target_sources(baseliner-blas PRIVATE $<TARGET_OBJECTS:sms_stopping>)

set(BIN_DIR ${CMAKE_BINARY_DIR} CACHE PATH "Output folder of the binary")
set_target_properties(baseliner-blas PROPERTIES OUTPUT_NAME baseliner-blas-rq4 RUNTIME_OUTPUT_DIRECTORY ${BIN_DIR})

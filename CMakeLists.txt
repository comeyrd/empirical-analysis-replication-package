# Builds the benchmark binaries of both experiments into bin/:
#   bin/baseliner-blas-rq1_rq3   main corpus     (rq1_rq3/experiment/CMakeLists.txt)
#   bin/baseliner-blas-rq4       SMS experiment  (rq4/experiment/CMakeLists.txt)
# They need different revisions of the same libraries, so each one is a separate build.
cmake_minimum_required(VERSION 3.15)
project(empirical-analysis LANGUAGES NONE)
include(ExternalProject)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()
set(BIN_DIR ${CMAKE_SOURCE_DIR}/bin CACHE PATH "Output folder of the binaries")

# Compilers, flags and policies given to this configure (CMakePresets.json) are passed on to both builds
set(cache_args -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE} -DBIN_DIR:PATH=${BIN_DIR})
get_cmake_property(cache_vars CACHE_VARIABLES)
foreach(var IN LISTS cache_vars)
    if(var MATCHES "^CMAKE_(C|CXX|HIP|CUDA)_|^CMAKE_(EXE|SHARED)_LINKER_FLAGS$|^CMAKE_POLICY_DEFAULT_|^CMAKE_EXPORT_COMPILE_COMMANDS$|^CMAKE_PREFIX_PATH$|^ROCM_PATH$")
        list(APPEND cache_args "-D${var}:STRING=${${var}}")
    endif()
endforeach()

foreach(experiment rq1_rq3 rq4)
    ExternalProject_Add(${experiment}
        SOURCE_DIR       ${CMAKE_SOURCE_DIR}/${experiment}/experiment
        BINARY_DIR       ${CMAKE_BINARY_DIR}/${experiment}
        CMAKE_CACHE_ARGS ${cache_args}
        BUILD_ALWAYS     ON
        INSTALL_COMMAND  "")
endforeach()

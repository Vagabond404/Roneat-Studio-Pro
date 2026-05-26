cmake_minimum_required(VERSION 3.15)
project(RoneatVideoCore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Use FetchContent to grab pybind11 automatically
include(FetchContent)
FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG        v2.13.1
)
FetchContent_MakeAvailable(pybind11)

pybind11_add_module(roneat_video_core 
    RoneatVideoEngine.cpp 
    bindings.cpp
)

if(WIN32)
    target_link_options(roneat_video_core PRIVATE "-static" "-static-libgcc" "-static-libstdc++")
endif()

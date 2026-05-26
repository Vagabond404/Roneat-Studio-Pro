cmake_minimum_required(VERSION 3.15)
project(RoneatAudioCore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Use FetchContent to grab pybind11 automatically if not installed system-wide
include(FetchContent)
FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG        v2.13.1
)
FetchContent_MakeAvailable(pybind11)

# Ensure miniaudio dependencies are linked (required for standard platform audio output)
if(APPLE)
    set(EXTRA_LIBS "-framework CoreFoundation -framework CoreAudio -framework AudioToolbox")
elseif(UNIX AND NOT APPLE)
    set(EXTRA_LIBS dl m pthread)
else()
    # Windows doesn't need extra libs usually for WASAPI/DirectSound with miniaudio
    set(EXTRA_LIBS "")
endif()

pybind11_add_module(roneat_audio_core 
    miniaudio_impl.cpp
    RoneatAudioEngine.cpp 
    bindings.cpp
)

if(WIN32)
    target_link_options(roneat_audio_core PRIVATE "-static" "-static-libgcc" "-static-libstdc++")
endif()

target_link_libraries(roneat_audio_core PRIVATE ${EXTRA_LIBS})

# Building the Roneat Audio Core

This directory contains the C++ real-time audio engine bindings for Roneat Studio Pro. 
We use `pybind11` to bridge the deterministic C++ DSP code with our modern Python UI.

## Prerequisites

1. **CMake** (3.15 or newer)
2. **C++17 Compiler**:
   - **Windows**: Visual Studio 2019/2022 (MSVC) or MinGW-w64.
   - **macOS**: Xcode Command Line Tools (Clang).
   - **Linux**: GCC or Clang.
3. **Python Environment**: The same Python environment used by Roneat Studio Pro (to link against the correct Python headers).

*Note: `pybind11` is automatically fetched via CMake, so you don't need to install it manually.*

## Compilation Guide

### Step 1: Open a Terminal / Command Prompt
Make sure your Python virtual environment is activated so CMake can find the correct Python headers.

```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Step 2: Run CMake Configure
Navigate to this `src/audio_engine_cpp` folder and configure the project.

```bash
cd src/audio_engine_cpp
cmake -B build
```

### Step 3: Build the Extension
Compile the C++ code into a shared module.

```bash
cmake --build build --config Release
```

### Step 4: Install the Module
After a successful build, a compiled extension file will be generated:
- **Windows**: `roneat_audio_core.cp3xx-win_amd64.pyd` (located in `build/Release/`)
- **macOS/Linux**: `roneat_audio_core.cpython-3xx-darwin.so` (located in `build/`)

Copy this file into the `core/` folder of the main Roneat Studio project so `RoneatAudioCore.py` can import it.

```bash
# Windows Example
copy build\Release\roneat_audio_core.*.pyd ..\..\core\

# macOS/Linux Example
cp build/roneat_audio_core.*.so ../../core/
```

Once copied, `RoneatAudioCore.py` will automatically detect and use the high-performance C++ backend.

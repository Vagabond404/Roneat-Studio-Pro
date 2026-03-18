"""
build.py — Roneat Studio Pro
============================
Run this script to build the Windows .exe using PyInstaller.

Usage:
    python build.py

All parameters are at the top of this file — edit them to match your setup.
The script excludes itself (build.py) from the final .exe.
"""

import subprocess
import sys
import os
import shutil

# ══════════════════════════════════════════════════════════════════════════════
#  PARAMETERS — edit these to match your machine
# ══════════════════════════════════════════════════════════════════════════════

APP_NAME    = "Roneat Studio Pro"
APP_VERSION = "2.0.1"

# Path to ffmpeg.exe (placed next to main.py)
FFMPEG_EXE  = "ffmpeg.exe"

# Icon for the .exe
APP_ICON    = os.path.join("assets", "logo.ico")

# Extra data folders/files to bundle  (source, dest_in_exe)
EXTRA_DATA  = [
    ("assets", "assets"),       # logo, icons, fonts
]

# Modules that PyInstaller misses via static analysis
HIDDEN_IMPORTS = [
    "PIL._tkinter_finder",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "sounddevice",
    "soundfile",
    "scipy.signal",
    "scipy._lib.messagestream",
    "librosa.core",
    "librosa.feature",
    "librosa.onset",
    "librosa.effects",
    "imageio_ffmpeg",
    "imageio.plugins.ffmpeg",
    "core.parse_score",
    "core.audio_player",
    "core.audio_analyzer",
    "core.calibration",
    "core.pdf_exporter",
    "core.file_manager",
    "numba",
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.simpledialog",
]

# Packages to collect entirely (submodules + data)
COLLECT_ALL = [
    "customtkinter",
    "librosa",
    "soundfile",
    "sounddevice",
    "reportlab",
    "tkinterdnd2",
    "imageio",
    "imageio_ffmpeg",
    "PIL",
    "scipy",
]

# Modules to exclude (reduce final size)
EXCLUDES = [
    "matplotlib",
    "pytest",
    "IPython",
    "jupyter",
    "notebook",
    "sphinx",
    "docutils",
    "setuptools",
    "pkg_resources",
]

# Output folder (PyInstaller default: dist/)
DIST_DIR    = "dist"
BUILD_DIR   = "build"

# ══════════════════════════════════════════════════════════════════════════════
#  BUILD LOGIC — no need to edit below this line
# ══════════════════════════════════════════════════════════════════════════════

def run():
    print(f"\n{'='*60}")
    print(f"  Building {APP_NAME} v{APP_VERSION}")
    print(f"{'='*60}\n")

    # Check PyInstaller is installed
    if not shutil.which("pyinstaller"):
        print("[ERROR] PyInstaller not found. Run:  pip install pyinstaller")
        sys.exit(1)

    # Check ffmpeg
    if not os.path.exists(FFMPEG_EXE):
        print(f"[WARN] {FFMPEG_EXE} not found next to build.py — "
              f"MP4 audio muxing will not work in the .exe")

    cmd = [sys.executable, "-m", "PyInstaller"]

    # Core flags
    cmd += [
        "--noconfirm",
        "--windowed",           # no console window
        "--onedir",             # folder output (required for imageio_ffmpeg)
        f"--name={APP_NAME}",
    ]

    # Version file (Windows only)
    if os.path.exists("version.txt") and sys.platform == "win32":
        cmd += ["--version-file=version.txt"]

    # Icon
    if os.path.exists(APP_ICON):
        cmd += [f"--icon={APP_ICON}"]
    else:
        print(f"[WARN] Icon not found: {APP_ICON}")

    # Extra data
    sep = ";" if sys.platform == "win32" else ":"
    for src, dst in EXTRA_DATA:
        if os.path.exists(src):
            cmd += [f"--add-data={src}{sep}{dst}"]
        else:
            print(f"[WARN] Data path not found: {src}")

    # ffmpeg.exe
    if os.path.exists(FFMPEG_EXE):
        cmd += [f"--add-data={FFMPEG_EXE}{sep}."]

    # Exclude build.py itself from the bundle
    # (PyInstaller won't include it unless imported, but just to be safe)

    # Collect all
    for pkg in COLLECT_ALL:
        cmd += [f"--collect-all={pkg}"]

    # Hidden imports
    for hi in HIDDEN_IMPORTS:
        cmd += [f"--hidden-import={hi}"]

    # Excludes
    for ex in EXCLUDES:
        cmd += [f"--exclude-module={ex}"]

    # Entry point
    cmd += ["main.py"]

    print("Running PyInstaller with the following command:\n")
    print("  " + " \\\n    ".join(cmd) + "\n")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\n{'='*60}")
        print(f"  BUILD SUCCESSFUL")
        print(f"  Output: {os.path.join(DIST_DIR, APP_NAME, APP_NAME + '.exe')}")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"  BUILD FAILED (exit code {result.returncode})")
        print(f"{'='*60}\n")
        sys.exit(result.returncode)


if __name__ == "__main__":
    run()
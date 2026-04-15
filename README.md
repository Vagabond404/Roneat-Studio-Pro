<div align="center">
  <img src="assets/logo.png" alt="Roneat Studio Pro Logo" width="200" />
  
  <h1>Roneat Studio Pro ᨠ</h1>
  
  <p>
    <b>A professional suite designed for transcribing, editing, and exporting scores for the Roneat (the traditional Cambodian xylophone).</b>
  </p>
  <p>
    It combines modern AI audio analysis with a specialized score editor to bridge the gap between traditional performance and digital notation.
  </p>
</div>

![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-Non--Commercial-red.svg)

---

## 📋 Table of Contents

- [✨ Core Features](#-core-features)
- [🧩 Plugin Extensibility (New!)](#-plugin-extensibility-new)
- [🎤 What is the Roneat Ek?](#-what-is-the-roneat-ek)
- [🚀 Requirements & Installation](#-requirements--installation-source-code)
- [🛠️ Building the Executable](#️-building-the-executable)
- [📝 License & Contact](#-license--contact)

"""
 ██████╗  ██████╗ ███╗   ██╗███████╗███████╗████████╗
 ██╔══██╗██╔═══██╗████╗  ██║██╔════╝██╔════╝╚══██╔══╝
 ██████╔╝██║   ██║██╔██╗ ██║█████╗  ███████╗   ██║   
 ██╔══██╗██║   ██║██║╚██╗██║██╔══╝  ╚════██║   ██║   
 ██║  ██║╚██████╔╝██║ ╚████║███████╗███████║   ██║   
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚══════╝   ╚═╝   
                                                     
 ███████╗████████╗██╗   ██╗██████╗ ██╗ ██████╗ 
 ██╔════╝╚══██╔══╝██║   ██║██╔══██╗██║██╔═══██╗
 ███████╗   ██║   ██║   ██║██║  ██║██║██║   ██║
 ╚════██║   ██║   ██║   ██║██║  ██║██║██║   ██║
 ███████║   ██║   ╚██████╔╝██████╔╝██║╚██████╔╝
 ╚══════╝   ╚═╝    ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝ 

 Welcome to the Core Engine of Roneat Studio Pro.
 Traditional Cambodian Heritage meets Modern Engineering.
"""

## ✨ Core Features

- **🎼 Professional Score Editor**: An interactive 2D editor specifically designed for Roneat notation. Features fluid visualization and real-time playback.
- **🎤 AI Audio Transcription**: Convert your Roneat recordings directly into digital notation using advanced pitch detection and a custom sound-fingerprinting system.
- **⚖️ Advanced Calibration**: Fine-tune the AI by recording the unique acoustic "fingerprints" of your specific instrument for near-perfect transcription accuracy.
- **📹 MP4 Video Export**: Generate high-definition 2D videos of your scores, perfectly synchronized with the audio. Perfect for YouTube or teaching.
- **📄 PDF Export**: Export high-quality sheet music, ready to be printed and shared.
- **📂 Project Management**: Save, resume, and manage your work easily with the native `.roneat` project format (Drag & Drop supported).

## 🧩 Plugin Extensibility (New!)

Roneat Studio Pro v2.2.0 now features a powerful, **Fully Isolated (Sandboxed) Third-Party Plugin System** via a dedicated Python API (`roneat_api`)! You can:
- Mount new buttons, standalone custom windows, and tabs.
- Instantly modify the application's global theme, colors, or language in real-time.
- Interact directly with the asynchronous audio synthesizer.
- Intercept, analyze, and programmatically alter the live musical score.

Full plugin management (Enable/Disable/Reload/Uninstall) occurs directly from the native "Plugins" tab. The system features an automatic crash-protection wrapper that catches your plugin's exceptions and safely disables the script to prevent corrupting the host software.

👉 **Learn how to build your own plugins by reading the [Plugin Development Guide (docs/PLUGIN_DEVELOPMENT.md)](docs/PLUGIN_DEVELOPMENT.md).**

## 🎹 What is the Roneat Ek?

The **Roneat Ek (រនាតឯក)** is a traditional Cambodian xylophone with 21 bamboo or hardwood bars, tuned to a pentatonic scale. It is one of the central instruments of classical Khmer court music and pin peat ensembles.

Roneat Studio Pro is the first dedicated digital tool built around its unique notation system and sonic characteristics.

> _Easy to Play, Impossible to Forget._

## 🚀 Requirements & Installation (Source Code)

If you are cloning this repository to build or run the software from source code:

**1. Clone the repository and create a virtual environment (Recommended):**
```bash
git clone https://github.com/Vagabond404/Roneat-Studio-Pro.git
cd Roneat-Studio-Pro
python -m venv venv
```

**2. Activate the virtual environment:**
*On Windows:* `.\venv\Scripts\activate`
*On macOS/Linux:* `source venv/bin/activate`

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Add FFmpeg (Required):**
- Download the `ffmpeg.exe` binary for your operating system.
- Place it directly in the root directory (next to `main.py`).

**5. Launch the application:**
```bash
python main.py
```

## 🛠️ Building the Executable

To generate a standalone `.exe` file for Windows (the build process will automatically strip unneeded repositories and tools):

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Run the included build script:
   ```bash
   python build.py
   ```
*The compiled Roneat Studio Pro executable will be outputted into the `dist/` folder.*

## 📝 License & Contact

This project is governed by a Custom Non-Commercial License. You may modify the code, but you may not use this software or any of its derivatives to generate revenue without explicit authorization. See `LICENSE.txt` for full details.

- **Author**: Ange Labbe
- **Contact**: contact@angelvisionlabs.com
- **Copyright**: © 2026 Angel Vision Labs

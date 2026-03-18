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

<br />

## ✨ Key Features

- **🎼 Professional Score Editor**: A specialized 2D editor designed specifically for Roneat notation. Includes real-time 2D visualization and playback.
- **🎤 Audio AI Transcription**: Convert your Roneat recordings directly into digital notation using advanced AI pitch detection and fingerprinting.
- **⚖️ Advanced Calibration**: Fine-tune the AI by recording your own instrument's "fingerprints" for near-perfect transcription accuracy.
- **📹 MP4 Video Export**: Generate high-definition 2D videos of your scores, synced with audio, perfect for social media or teaching.
- **📄 PDF Export**: Export high-quality sheet music ready for printing.
- **📂 Project Management**: Save and load your work using the `.roneat` project format.
- **🖱️ Drag & Drop**: Quickly import audio files or open projects by dragging them directly into the app.

<br />

## 🚀 Getting Started (For Developers & Source Code Users)

If you are running the software from the source code, follow these steps to set up your environment.

### Prerequisites

- **Python 3.10 or higher**: [Download Python](https://www.python.org/downloads/)
- **FFmpeg**: Required for MP4 video export (audio/video muxing).

### Installation

**1. Clone the repository**:
```bash
git clone https://github.com/Vagabond404/Roneat-Studio-Pro.git
cd Roneat-Studio-Pro
```

**2. Create a Virtual Environment (Highly Recommended)**:
```bash
python -m venv .venv
```

**Activate the virtual environment**:

*On Windows*:
```bash
.\.venv\Scripts\activate
```

*On macOS/Linux*:
```bash
source .venv/bin/activate
```

**3. Install Dependencies**:
```bash
pip install -r requirements.txt
```

**4. Add FFmpeg**:
- Download `ffmpeg.exe` for your system.
- Place `ffmpeg.exe` directly in the root folder of the project (next to `main.py`).

### Running the App

Simply run the main entry point:
```bash
python main.py
```

<br />

## 🛠️ Building the Executable

To generate a standalone `.exe` for Windows:

**1. Install PyInstaller**:
```bash
pip install pyinstaller
```

**2. Run the build script**:
```bash
python build.py
```
*The executable will be generated in the `dist/` folder.*

<br />

## 📝 License

This project is governed by a Custom Non-Commercial License. You may modify the code, but you may not use this software or any of its derivatives to generate revenue without explicit authorization. See `LICENSE.txt` for full details.

---
*Developed by Ange Labbe — 2026*

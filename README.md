# Roneat Studio Pro

Roneat Studio Pro is an advanced digital audio workstation (DAW), transcription tool, and educational software designed specifically for the Cambodian Roneat Ek (traditional xylophone). It offers unparalleled tools for scoring, playback, audio-to-score transcription, and high-quality PDF/Video export.

## Key Features

- **Interactive 2D Roneat Player**: An immersive visual instrument that lets you click, type, and record musical ideas directly onto the digital instrument.
- **Audio-to-Score Transcription**: Analyzes rhythm, pitch, and timbre from an audio recording, automatically translating performances into clear, readable sheet music.
- **Dynamic Visual Feedback**: Instant grid-based score rendering with customizable colors, note fonts, and layout densities.
- **Robust Plugin Ecosystem**: Extensive Python-based API to write custom plugins that hook into the Roneat Studio lifecycle (saving, opening files, playing notes, rendering the UI layout).

---

## What's New in Version 4.1.0

### Performance & Startup Optimization
- **Dramatically faster startup**: `librosa`, `numpy` and `sounddevice` are no longer imported at launch. They are now loaded lazily — only when the user opens the **Audio AI** tab for the first time. Startup time reduced by **~1–3 seconds** depending on the machine.
- **Lazy audio imports**: `core/audio_analyzer.py` now imports heavy libraries inside each function rather than at module level, so importing the module itself has zero cost.
- **Splash screen theme sync**: The splash screen now reads the saved theme setting (`Dark`, `Light`, `System`) at startup and renders the matching palette — it will always match the main app appearance.
- **UI v4.0 Overhaul**: 
    - **Audio AI**: Redesigned as a modern "Neural Drop Zone" with clean progress animations and better layout.
    - **Settings**: Complete redesign of Hz tuning and calibration pages for a more professional DAW look.
- **PDF Export Improvement**: The "Composer" field in the PDF export dialog is now automatically pre-filled with the author's name from the score editor.

---

## What's New in Version 3.0.0

Version 3.0.0 represents a massive architectural leap in Roneat Studio, fundamentally improving how project files are stored and parsed, while delivering a deeply refined "Premium DAW" aesthetic.

### 1. Robust File System Architecture (Save/Load Overhaul)
Project files (`.roneat` extension) are now compressed ZIP archives containing isolated data layers designed with "Single Source of Truth" methodologies:
- **`notes.json` (The Source of Truth)**: The entire score is now mathematically mapped into discrete playing events. Each event tracks exact execution times (`time_sec`, `time_str`), velocities, bar/pitch locations, and rest intervals. The plaintext format is dynamically regenerated when launching the app. 
- **`info.json` (Configuration & Metadata)**: Tracks all project boundaries like the song title, composer, hardware sync logic, and environment state independently. Strict typings (Ints and Floats) guarantee bug-free mathematical operations inside the metronome and renderer.

### 2. Premium Interface Overhaul
- **Aesthetic Refinement**: The user interface has been completely modernized into a premium, responsive glassmorphism aesthetic with tailored Gold (`#c8a96e`) layouts.
- **White Paper PDF Export**: PDF & Preview renders now aggressively force a high-visibility white background to accommodate printing standards. 
- **Anonymous Author Logic**: Projects with no specified author now beautifully collapse the standard attribution fields on printed sheets.

### 3. Stability and Quality of Life
- **Preset System Correction**: Fixed a critical bug where UI Presets inadvertently targeted and overwrote the user's score/notes. Presets are now strictly scoped to aesthetic and structural environments (grid setups, accent colors, text sizes).
- **Default Start Environment**: Roneat Studio Pro now opens with "Happy Birthday" out-of-the-box (BPM: 170, 8-column layout), replacing "Bot Sathukar" as the introductory canvas.
- **Error Handling Optimization**: The CTkMessageBox conflicts causing crashes on validation failures were permanently resolved.

---

## Prerequisites

- Python 3.10 or higher
- Windows OS (Tested and built natively)
- Included dependencies: `customtkinter`, `reportlab`, `sounddevice`, `numpy`, `jsonschema`

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/roneat-studio.git
cd roneat-studio
```

### 2. Install Project Dependencies

Create an isolated virtual environment and install dependencies:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Launch Roneat Studio

Start the main orchestrator window:

```bash
python main.py
```

## Architecture

Roneat Studio uses a heavily decoupled architecture:
- `main_window.py`: The entry point that orchestrates routing, frames, and plugin pipelines. 
- `core/file_manager.py`: Serialization boundaries validating JSON payloads against constraints to maintain save-state integrity.
- `ui/views/score_editor.py`: The heart of the program. A massive interactive engine combining text inputs, Roneat rendering, PDF generation triggers, and real-time validation logic.
- `core/parse_score.py`: Handles complex regex parsing for decoding typing (like `4#3` meaning strike the 4th bar with a 3-hit tremolo roll) into the `notes.json` event models.

## Available Scripts

| Command | Description |
| ------- | ----------- |
| `python main.py` | Boot the software to the Main View |
| `python run_tests.py` | Executes the unit test suite verifying pitch parsing |

---
**Roneat Studio Pro v3.0.0** — *Elevating traditional notation to pristine digital standards.*

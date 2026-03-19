---
description: The professional score editor and AI transcription tool for the Roneat Ek.
---

# Welcome to Roneat Studio Pro

### What Is the Roneat Ek?

The Roneat Ek (រនាតឯក) is a traditional Cambodian xylophone with 21 bamboo or hardwood bars, tuned to a pentatonic scale. It is one of the central instruments of classical Khmer court music and pin peat ensembles.

Roneat Studio Pro is the first dedicated digital tool built around its unique notation system and sonic characteristics.

> _Easy to Play, Impossible to Forget._

### What the Software Does

🎼 **Professional Score Editor**\
Write scores using a simple numbered notation system (bars 1–21). The live preview grid renders your notation in real time. Full playback, undo/redo, and real-time validation included.

🎤 **AI Audio Transcription**\
Drop in a WAV, MP3, or FLAC recording of a Roneat performance. The engine detects every note onset, identifies the pitch, and generates a draft score automatically.

⚖️ **Instrument Calibration**\
Record your own instrument's 21 bars once. The AI learns its exact sound and uses spectral fingerprints instead of generic pitch detection — dramatically improving transcription accuracy.

📄 **PDF Export**\
Export print-ready scores with optional cover page, left-hand notation, row numbers, custom columns, and accent color.

📹 **MP4 Video Export**\
Generate scrolling score videos synchronized to audio. Ready for YouTube, teaching, and social media.

💾 **Self-Contained Project Files**\
The `.roneat` format bundles the score, timing data, and source audio into one compressed file. Share one file and keep everything together.

### Who Is This For?

* **Musicians and performers** who want to digitize and archive Roneat repertoire
* **Teachers** creating study materials, printed scores, or video lessons
* **Students** who want visual playback feedback while learning pieces
* **Researchers and ethnomusicologists** documenting Khmer musical heritage
* **Developers** interested in contributing to or extending the open-source codebase

### Quick Concept: How the Notation Works

Scores in Roneat Studio Pro are written as a sequence of numbers from 1 to 21 — one number per bar strike. Bar 1 is the highest pitch, bar 21 is the lowest. Rests are written as `-`. Tremolo rolls use `#`. Bar lines use `/`.

Example:

`9 8 7 6 / 5 4 3 2 / 1 - - -`

That is all you need to start. The full notation system is documented in [Score Notation Reference](reference/score-notation-reference.md).

### Start Here

Follow this path if you are new:

1. [**Install on Windows**](getting-started/install-on-windows.md) — Download and run the installer
2. [**Quickstart: Your First Score**](getting-started/quickstart-your-first-score.md) — Complete the 10-minute hands-on walkthrough
3. [**Score Notation Reference**](reference/score-notation-reference.md) — Learn the full notation system
4. [**Calibration Guide**](guides/ai-audio-transcription/calibration-guide.md) — Calibrate your instrument for accurate AI transcription
5. [**AI Audio Transcription**](guides/ai-audio-transcription/) — Transcribe a real recording
6. [**Exporting (PDF & Video)**](guides/exporting-pdf-and-video.md) — Export your finished score

### For Developers

If you want to build the app from source or package a release, see [Building from Source](developer-guide/building-from-source.md).

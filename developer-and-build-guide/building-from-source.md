---
description: Run or package Roneat Studio Pro from source with the required dependencies.
---

# Building from Source

Use this guide if you want to run or package Roneat Studio Pro from source on Windows.

The project depends on audio, scientific, and video libraries, so environment setup matters.

### Prerequisites

Before you begin, make sure you have:

* **Python 3.10** or later
* A local clone of the project repository
* Access to the project root directory in a terminal

### Install Dependencies

From the project root, install the required packages:

`pip install -r requirements.txt`

Core dependencies include:

* `customtkinter` for the interface
* `librosa`, `numpy`, and `scipy` for audio analysis
* `sounddevice` and `soundfile` for playback
* `reportlab` for PDF export
* `imageio-ffmpeg` for video export

### Add FFmpeg for Video Export

MP4 export requires **`ffmpeg.exe`** to be present.

Place `ffmpeg.exe` directly in the main project folder before running or packaging the app.

{% hint style="warning" %}
If `ffmpeg.exe` is missing, video export will not work in the built application.
{% endhint %}

### Packaging Notes

If you create a standalone build, make sure your build process also copies `ffmpeg.exe` into the final `dist/` output.

Without that file, exported videos cannot be encoded correctly.

### Common Setup Issues

#### Dependency mismatch

If the app fails to start after install, re-check the Python version and reinstall dependencies from `requirements.txt`.

#### Missing video export support

If PDF export works but MP4 export does not, confirm that `ffmpeg.exe` exists in both:

* the project root during development
* the final distribution folder after packaging

---
description: How to save, load, and manage your .roneat project files.
---

# Working with Projects

A `.roneat` file stores your score and, when available, its source audio.

This makes projects easy to reopen, review, and share.

### The .roneat File Format

A `.roneat` file is a compressed ZIP archive.

It contains:

* `data.json` — title, notes text, sync data, and the original audio file name
* `audio/source.*` — the original source audio file, if the score came from audio analysis

This makes the project **self-contained**.

You can share one file and keep both the notation and the audio together.

### Saving a Project

1. Click **💾 Save Project** in the sidebar.
2. Check the suggested filename.
3. Choose where to save the file.
4. Click **Save**.

The app uses the score title as the default filename.

Spaces and special characters are sanitized automatically.

{% hint style="info" %}
Use a clear title before saving.

It becomes the default project filename and the default PDF export title.
{% endhint %}

### Loading a Project

1. Click **📂 Load Project** in the sidebar.
2. Select a `.roneat` file.
3. Wait for the project to load.

The Score Editor restores the saved title, notes, and sync data.

If the archive includes audio, the app extracts it to a temporary location and links it automatically.

### Drag and Drop

You can drag a `.roneat` file onto the application window to open it immediately.

You can also drag an audio file onto the window.

When you do, the app forwards it to the **Audio AI** panel for analysis.

### Legacy Projects (v1 format)

Older `.roneat` files stored as plain JSON are still supported.

The app reads them automatically.

If you save them again, use the current format so audio and sync data stay bundled.

### Recommended Workflow

1. Set the project title.
2. Write or import the score.
3. Save a `.roneat` file before major edits.
4. Export PDF or MP4 only after your project is finalized.

Next, continue with [AI Audio Transcription](ai-audio-transcription.md) or [Exporting (PDF & Video)](exporting-pdf-and-video.md).

---
description: Learn the three main panels of Roneat Studio Pro and how they work together.
---

# Interface Overview

Roneat Studio Pro is organized around a persistent sidebar and three working panels.

Together, they support one clear workflow: **write or import, review, calibrate, and export**.

### 1. The Sidebar (Left Panel)

The sidebar is the navigation spine of the app.

It contains:

* The **Roneat Studio Pro logo and branding** at the top
* Three navigation buttons: **🎼 Score Editor**, **🎤 Audio AI**, and **⚙ Settings**
* A prominent gold **Save Project** button for `.roneat` files
* A **Load Project** button for existing `.roneat` files
* A status indicator at the bottom, such as **● Ready** or **● Working…**

{% hint style="info" %}
You can also open projects by dragging and dropping a `.roneat` file directly onto the application window.
{% endhint %}

### 2. The Score Editor (Main View)

Select **🎼 Score Editor** to open the main writing workspace.

This is where you enter notation, preview it, and export finished work.

#### Main components

* **Title field** — Enter the name of the piece. This becomes the default filename when saving.
* **Notes text box** — Write or paste notation here. See [Score Notation Reference](score-notation-reference.md) for the full syntax.
* **Live Preview grid** — Renders the score in real time and shows the 21 bars of the Roneat Ek visually.
* **BPM control** — Sets playback tempo in beats per minute. This is disabled when synced playback comes from analyzed audio.
* **Sync label** — Shows **⏱ Synced playback loaded** when the score uses original timing from an imported recording.
* **Play / Stop controls** — Start or stop synthesized playback of the score.
* **Left-hand toggle** — Adds the second mallet hand, using bars `+7`, in playback and preview.
* **Undo / Redo** — Full undo history is maintained while editing.
* **Validation panel** — Shows invalid tokens and notation issues in real time.
* **Export buttons** — Open the PDF and MP4 export workflows directly from the editor.

### 3. The Audio AI Panel

Select **🎤 Audio AI** to transcribe recordings into draft scores.

This panel handles file loading, analysis, transcription review, and polyphonic options.

See [AI Audio Transcription](ai-audio-transcription.md) for the full workflow.

### 4. The Settings Panel

Select **⚙ Settings** to control appearance, playback, calibration, and storage paths.

This panel also contains the calibration workflow and advanced frequency presets.

See [Settings Overview](settings-overview.md) for details.

### Suggested First Workflow

1. Set a title in the Score Editor.
2. Write notation manually or import from Audio AI.
3. Review the live preview and validation panel.
4. Calibrate your instrument if transcription accuracy needs improvement.
5. Save the project and export PDF or MP4.

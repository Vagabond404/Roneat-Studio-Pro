---
description: Learn the layout of Roneat Studio Pro and what each panel does.
---

# Interface Overview

Roneat Studio Pro uses a simple layout.

The sidebar stays on the left.

The main content area fills the right side.

### The Two-Panel Layout

Roneat Studio Pro uses a simple two-panel layout:

* **Left:** The Sidebar — navigation, project actions, and status
* **Right:** The Main Content Area — changes depending on which panel is active

There are three panels you can switch between using the sidebar buttons: **Score Editor**, **Audio AI**, and **Settings**.

| Area              | Purpose                                                    |
| ----------------- | ---------------------------------------------------------- |
| Sidebar           | Switch panels, save or load projects, and check app status |
| Main Content Area | Shows the active panel and its controls                    |

### The Sidebar

The sidebar is always visible on the left side of the window.

It contains:

#### Branding

The Roneat Studio Pro logo (`ᨠ`) and name appear at the top in gold.

#### Navigation buttons

Click a button to switch the active panel:

* 🎼 **Score Editor** — the main workspace for writing and editing scores
* 🎤 **Audio AI** — for transcribing audio recordings into scores
* ⚙ **Settings** — appearance, playback, calibration, and preferences

#### Project actions

These controls appear at the bottom of the sidebar:

* 💾 **Save Project** — saves the current score as a `.roneat` file. The song title is used as the default filename.
* 📂 **Load Project** — opens an existing `.roneat` file.

#### Status indicator

A small colored label at the very bottom shows the current app state:

| Label        | Color | Meaning                    |
| ------------ | ----- | -------------------------- |
| `● Ready`    | Green | Idle. Everything is OK.    |
| `● Working…` | Gold  | Processing is in progress. |
| `● Error`    | Red   | Something went wrong.      |

{% hint style="info" %}
You can also open a `.roneat` project by dragging and dropping the file directly onto the application window.

Dropping an audio file forwards it to the **Audio AI** panel automatically.
{% endhint %}

### Panel 1 — Score Editor

This is the main workspace.

It opens by default when the app launches.

#### Title field

Enter the name of the piece here.

This title is used as the default filename when saving the project and as the title in PDF exports.

#### Notes text box

This is where you write or paste the score notation manually.

The notation system uses numbers `1`–`21` for bars, `#` for tremolo, `-` for rests, and `/` for visual bar lines.

See [Score Notation Reference](score-notation-reference.md) for the full syntax.

#### Live preview grid

Below the text box, a visual grid automatically renders your notation in real time.

It shows all 21 bars of the Roneat Ek and updates as you type.

#### BPM field

Sets the playback tempo in beats per minute.

This field is disabled and shows `⏱ Synced playback loaded` when the score was imported from audio analysis, because playback follows the original recorded timing instead.

#### Left-hand toggle

When enabled, the app automatically computes and plays the second mallet hand using `bar + 7` during playback.

It also shows that left-hand value in the preview grid below each right-hand note.

#### Play / Stop

Starts and stops score playback using synthesized instrument tones, or recorded samples if calibration has been completed.

#### Undo / Redo

Full edit history is maintained.

Use `Ctrl+Z` and `Ctrl+Y`.

#### Validation panel

Shows real-time errors if any notation tokens are invalid.

Examples include out-of-range bar numbers, bad tremolo counts, and unrecognized symbols.

#### Export buttons

PDF and MP4 export are accessible directly from the Score Editor panel.

See [Exporting (PDF & Video)](exporting-pdf-and-video.md) for full details.

{% hint style="warning" %}
If imported audio timing is attached, the `BPM` field is locked on purpose.

Playback will follow the original recording instead.
{% endhint %}

### Panel 2 — Audio AI

Access this panel by clicking **🎤 Audio AI** in the sidebar.

Use it to transcribe a recorded audio file into a draft score.

See [AI Audio Transcription](ai-audio-transcription.md) for the full step-by-step workflow.

Key elements of this panel:

* **File selector** — choose or drag and drop your audio recording
* **Two-mallets checkbox** — enable this if the recording uses two-mallet technique
* **Analyze button** — starts the transcription
* **Progress bar** — shows real-time analysis steps such as onset detection and note matching
* **Result preview** — displays the detected note sequence as notation tokens
* **Import to Score Editor** button — sends the result to the Score Editor with sync data

### Panel 3 — Settings

Access this panel by clicking **⚙ Settings** in the sidebar.

It controls appearance, playback behavior, calibration, and frequency presets.

See [Settings Overview](settings-overview.md) for full details.

### Recommended First Workflow

If this is your first time using the app:

1. Read [Score Notation Reference](score-notation-reference.md) to understand how to write scores.
2. If you have a recording, go to **Audio AI** and transcribe it.
3. Review and edit the result in the **Score Editor**.
4. Save your project with **💾 Save Project**.
5. Export to **PDF** for printing or **MP4** for video.

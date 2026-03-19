---
description: >-
  Understand what Roneat Studio Pro does and follow the fastest path to your
  first finished score.
---

# Welcome to Roneat Studio Pro

Welcome to the official documentation for **Roneat Studio Pro**.

The **Roneat Ek (រនាតឯក)** is a traditional Cambodian xylophone with 21 bamboo or hardwood bars, tuned to a pentatonic scale. It is one of the central instruments of classical Khmer court music and pin peat ensembles. Roneat Studio Pro is the first dedicated digital tool built around its unique notation system and sonic characteristics.

_Easy to Play, Impossible to Forget._

{% hint style="info" %}
New here? Follow the **Start Here** path below.
{% endhint %}

### Key Features

#### 🎼 Professional Score Editor

Write scores using a simple numbered notation system with bars `1`–`21`.

The live preview grid renders your notation in real time.

Includes playback, undo/redo, and real-time validation.

#### 🎤 AI Audio Transcription

Drop in a `WAV`, `MP3`, or `FLAC` recording of a Roneat performance.

The engine detects every note onset, identifies the pitch, and generates a draft score automatically.

#### ⚖️ Instrument Calibration

Record your own instrument's 21 bars and the AI learns its exact sound.

This replaces generic pitch detection with fingerprint matching tailored to your specific Roneat.

That dramatically improves accuracy.

#### 📄 PDF Export

Export print-ready scores with optional cover page, left-hand notation, row numbers, custom column counts, and your choice of accent color.

#### 📹 MP4 Video Export

Generate scrolling score videos synchronized to audio.

This is ideal for YouTube, teaching, and social media.

#### 💾 Self-Contained Project Files

The `.roneat` format bundles the score, sync data, and source audio into a single compressed file.

Share one file and nothing gets lost.

### Who Is This For?

* **Musicians and performers** who want to digitize and archive Roneat repertoire
* **Teachers** creating study materials, video lessons, or printed scores for students
* **Students** who want visual playback feedback while learning pieces
* **Researchers and ethnomusicologists** documenting Khmer musical heritage
* **Developers** interested in extending or building on the open-source codebase

### Start Here

{% hint style="success" %}
Recommended flow: **Install → Learn the interface → Write or transcribe → Calibrate → Export**
{% endhint %}

1. [Installation & Setup](getting-started/installation-and-setup.md)
2. [Interface Overview](user-guide/interface-overview.md)
3. [Score Notation Reference](user-guide/score-notation-reference.md)
4. Use [AI Audio Transcription](user-guide/ai-audio-transcription.md) if you have a recording, or write a score manually
5. [Calibration Guide](user-guide/calibration-guide.md) for the best transcription accuracy
6. [Exporting (PDF & Video)](user-guide/exporting-pdf-and-video.md)

### Quick Concept: How the Notation Works

In Roneat Studio Pro, you write scores as a sequence of numbers from `1` to `21` — one number per bar strike. Bar `1` is the highest pitch. Bar `21` is the lowest. Rests are written as `-`. Tremolo rolls use `#`. Bar lines use `/`.

| Token    | Meaning           | Example             |
| -------- | ----------------- | ------------------- |
| `1`–`21` | A bar strike      | `9`                 |
| `-`      | A rest            | `1 - - -`           |
| `#`      | A tremolo roll    | `9#3`               |
| `/`      | A visual bar line | `9 8 7 6 / 5 4 3 2` |

Example: `9 8 7 6 / 5 4 3 2 / 1 - - -`

{% hint style="info" %}
That is enough to start writing.

Use [Score Notation Reference](user-guide/score-notation-reference.md) when you need the full syntax.
{% endhint %}

### Reference Pages

* [Working with Projects](user-guide/working-with-projects.md)
* [Settings Overview](user-guide/settings-overview.md)
* [FAQ](legal-and-contact/faq.md)
* [Support & Contact](legal-and-contact/support-and-contact.md)
* [License Agreement](legal-and-contact/license-agreement.md)

### For Developers

If you want to run or package the app yourself, see [Building from Source](developer-and-build-guide/building-from-source.md).

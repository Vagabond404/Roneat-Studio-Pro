---
description: Convert audio recordings into editable draft scores and clean the result.
---

# AI Audio Transcription

Roneat Studio Pro can analyze a recording and convert it into an editable draft score.

Use it to speed up transcription, then review the result in the Score Editor.

### Supported Audio Formats

* WAV
* MP3
* FLAC
* OGG

{% hint style="info" %}
For the best transcription quality, use a clean solo recording with minimal background noise.
{% endhint %}

### Two Analysis Modes

Roneat Studio Pro uses one of two analysis modes when matching detected notes.

1. **pYIN Pitch Detection Mode** — This is the default when no calibration fingerprints exist. The engine estimates fundamental pitch at each onset with pYIN, then maps that pitch to the nearest Roneat bar by frequency. It works best on clean recordings with standard tuning.
2. **Fingerprint Matching Mode** — This is the recommended mode after calibration. Instead of estimating pitch directly, the engine compares each detected onset against the spectral fingerprints recorded from your own instrument. This is much more accurate when your Roneat deviates from standard tuning.

{% hint style="info" %}
To get the best results, always complete the [Calibration Guide](calibration-guide.md) before running analysis on your recordings.
{% endhint %}

### How Transcription Works

Behind the scenes, the app follows these steps:

1. The audio file is loaded and normalized.
2. The engine checks for polyphonic content. If multiple simultaneous notes are present, harmonic-percussive source separation (HPSS) is applied to isolate the melody.
3. Note onsets, the moment each bar is struck, are detected with `librosa`.
4. For each onset, the app extracts a short analysis window and skips the initial mallet clack.
5. Each window is matched to a bar number, either by pYIN pitch estimation or by spectral fingerprint similarity.
6. Low-energy windows, such as silence, are skipped automatically.
7. The detected events are assembled into score notation and shown for review.

### Transcribe a Recording

{% stepper %}
{% step %}
### Open the Audio AI panel

Click **🎤 Audio AI** in the sidebar.

![](<../.gitbook/assets/image (8).png>)
{% endstep %}

{% step %}
### Choose your file

Select the recording you want to analyze.

WAV usually gives the most reliable result.

![](<../.gitbook/assets/image (9).png>)
{% endstep %}

{% step %}
### Choose analysis options

Enable calibration-based analysis if fingerprints are available.

Enable **Two mallets / Polyphonic** when the recording includes simultaneous left and right hand content.
{% endstep %}

{% step %}
### Run analysis

Click **Analyze** and wait for processing to finish.

A progress bar appears while the file is being analyzed.

![](<../.gitbook/assets/image (10).png>)
{% endstep %}

{% step %}
### Review and clean the result

The generated score is a draft.

Check for wrong bars, missed strikes, ghost notes, and timing issues.

Then refine the notation in the Score Editor.

![](<../.gitbook/assets/image (11).png>)
{% endstep %}
{% endstepper %}

### Tremolo Notation

If the engine detects rapid repeated strikes on the same bar, it may generate tremolo tokens.

Examples:

* `9#` — bar 9 as tremolo
* `9#3` — bar 9 with 3 rapid strikes

These tremolo tokens are preserved when you import the result into the Score Editor.

### Two-Mallets Mode

The **Two mallets / Polyphonic** checkbox changes how the analysis matches notes.

When enabled, the app uses fingerprints recorded in two-mallet style.

This improves accuracy for pieces where the left and right hand play at the same time.

### Best Practices

* Record at a distance of **30–60 cm** from the instrument for a balanced tone
* Avoid clipping and keep peaks below **-3 dB**
* If many bars are wrong, calibrate first and re-analyze
* Supported formats are **WAV, MP3, FLAC, and OGG**
* WAV gives the most reliable results
* Typical analysis time is **5–30 seconds** for a normal piece

Next, see [Calibration Guide](calibration-guide.md) and [Score Notation Reference](score-notation-reference.md).
